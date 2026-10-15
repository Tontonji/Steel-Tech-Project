"""Steel price lookup from OneStockHome (public product pages) -> price per kg, THB.

OneStockHome has no public API. Each product page embeds its variants (name, displayPrice,
weight) as JSON, so we read that instead of scraping rendered HTML. Prices are *retail list
prices* and the site warns they can change: always show ``price_source`` and ``price_as_of``.

Scope: H / wide-flange sections come from OneStockHome (matched on h x b x tw x tf, SS400
preferred), falling back to the bundled FY2568 material price book (data/material_prices_2568.csv).
I-beam and lip-C (ตัวซี) sections are priced from the price book only. Everything else is reported
as ``price_not_found`` / ``unsupported_section`` -- we never guess a price.
"""
from __future__ import annotations

import csv
import json
import os
import re
import statistics
import time
import urllib.request
from datetime import date
from pathlib import Path
from typing import Callable

import pandas as pd

import boq_utils as bu

BASE_URL = "https://www.onestockhome.com"
CATEGORY_PATH = "/th/product_categories/h-beam"
SOURCE_NAME = "OneStockHome (retail list price, ex-VAT unknown)"
USER_AGENT = "SteelBOQ-MVP/0.1 (research; contact: project owner)"
MAX_CATEGORY_PAGES = 10
REQUEST_DELAY_S = 0.5
CACHE_TTL_DAYS = 1

STATUS_OK = "ok"
STATUS_NOT_FOUND = "price_not_found"
STATUS_UNSUPPORTED = "unsupported_section"
STATUS_ERROR = "price_source_error"

Fetcher = Callable[[str], str]

_PRODUCT_RE = re.compile(r"/th/products/(\d+)/((?:h-beam|wide-flange)-(\d+)x(\d+)[a-z0-9\-_]*)")
_ITEM_RE = re.compile(
    r'"name":"([^"]+)","url":"[^"]*","displayPrice":"([0-9,\.]+)","displaySize":"[^"]*",'
    r'"eanCode":"[^"]*","weight":([0-9.]+),"unit":"([^"]*)"'
)
_DIMS_RE = re.compile(r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", re.I)
_GRADE_RE = re.compile(r"\b(SS400|SM520|SM490|SS540|Q345)\b", re.I)
_LEN_RE = re.compile(r"ยาว\s*(\d+(?:\.\d+)?)\s*ม")


class PriceSourceError(RuntimeError):
    pass


def http_get(url: str, timeout: float = 20.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "th"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:  # network / HTTP errors
        raise PriceSourceError(f"{type(e).__name__}: {e}") from e


# ---------------------------------------------------------------- parsing
def parse_product_links(html: str) -> list[dict]:
    """Product links found on a category page: id, slug, nominal h and b (mm)."""
    seen: dict[str, dict] = {}
    for pid, slug, h, b in _PRODUCT_RE.findall(html):
        seen.setdefault(pid, {"id": pid, "slug": slug, "h": float(h), "b": float(b)})
    return list(seen.values())


def parse_items(html: str) -> list[dict]:
    """Variants embedded in a product page. Skips anything without dims or a positive weight."""
    html = html.replace("\\/", "/")
    items, seen = [], set()
    for name, price, weight, unit in _ITEM_RE.findall(html):
        if (name, price) in seen:
            continue
        seen.add((name, price))
        dims = _DIMS_RE.search(name)
        try:
            price_f = float(price.replace(",", ""))
            weight_f = float(weight)
        except ValueError:
            continue
        if not dims or weight_f <= 0 or price_f <= 0:
            continue
        h, b, tw, tf = (float(x) for x in dims.groups())
        grade = _GRADE_RE.search(name)
        length = _LEN_RE.search(name)
        items.append(
            {
                "name": name,
                "h": h, "b": b, "tw": tw, "tf": tf,
                "grade": grade.group(1).upper() if grade else None,
                "length_m": float(length.group(1)) if length else None,
                "price_thb": price_f,
                "weight_kg": weight_f,
                "unit": unit,
                "price_per_kg": round(price_f / weight_f, 2),
            }
        )
    return items


# ---------------------------------------------------------------- source access + cache
def _cache_path() -> Path:
    base = Path(os.environ.get("BOQ_CACHE_DIR") or Path(__file__).resolve().parent / "logs")
    return base / "onestockhome_prices.json"


def _load_cache(path: Path, today: date) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        age = (today - date.fromisoformat(data["as_of"])).days
        if age < CACHE_TTL_DAYS:
            return data
    except (OSError, ValueError, KeyError):
        pass
    return {"as_of": today.isoformat(), "category": None, "products": {}}


def _save_cache(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # cache is best effort


def _category_index(cache: dict, fetch: Fetcher, sleep: Callable[[float], None]) -> list[dict]:
    if cache.get("category"):
        return cache["category"]
    products: dict[str, dict] = {}
    for page in range(1, MAX_CATEGORY_PAGES + 1):
        html = fetch(f"{BASE_URL}{CATEGORY_PATH}?page={page}")
        new = [p for p in parse_product_links(html) if p["id"] not in products]
        if not new:
            break
        products.update({p["id"]: p for p in new})
        sleep(REQUEST_DELAY_S)
    if not products:
        raise PriceSourceError("No H-beam products found on the category page (site layout changed?)")
    cache["category"] = list(products.values())
    return cache["category"]


def _product_items(cache: dict, product: dict, fetch: Fetcher) -> list[dict]:
    key = product["id"]
    if key not in cache["products"]:
        cache["products"][key] = parse_items(fetch(f"{BASE_URL}/th/products/{key}/{product['slug']}"))
    return cache["products"][key]


# ---------------------------------------------------------------- public API
def _result(status: str, **kw) -> dict:
    base = {
        "price_per_kg": None,
        "price_status": status,
        "price_source": None,
        "price_as_of": None,
        "price_note": None,
    }
    base.update(kw)
    return base


BOOK_PATH = Path(__file__).resolve().parent / "data" / "material_prices_2568.csv"
BOOK_SOURCE = "Material price book FY2568 (designobec, based on TPSO; material cost only)"
BOOK_AS_OF = "FY2568"


def load_price_book(path: Path | None = None) -> list[dict]:
    path = path or BOOK_PATH
    try:
        with path.open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def _book_dims(row: dict) -> tuple[float, ...]:
    return tuple(float(x) for x in row["dims_mm"].split("x"))


def _book_lookup(parsed: dict, book: list[dict]) -> dict | None:
    """Exact h x b x tw x tf match in the price book. C sections match the lip-channel (ตัวซี) rows
    as h x b x lip x t; JIS channels would not match any row and stay unpriced."""
    category = {"H": "H", "I": "I", "C": "LIPC"}.get(parsed["type"])
    if category is None:
        return None
    want = (parsed["h"], parsed["b"], parsed["tw"], parsed["tf"])
    for row in book:
        if row["category"] == category and _book_dims(row) == want:
            return _result(
                STATUS_OK,
                price_per_kg=float(row["material_price_per_kg"]),
                price_source=BOOK_SOURCE,
                price_as_of=BOOK_AS_OF,
                price_note=f"Book item {row['code']}: {row['material_price_thb']} THB per "
                f"{row['weight_kg_per_unit']} kg piece",
            )
    return None


def lookup_prices(
    sections: list[str | None],
    *,
    fetch: Fetcher = http_get,
    today: date | None = None,
    cache_path: Path | None = None,
    sleep: Callable[[float], None] = time.sleep,
    book: list[dict] | None = None,
) -> dict[str, dict]:
    """Price per kg for each distinct section. Never raises; failures become a status per section.

    H sections: OneStockHome first, then the price book. I and lip-C sections: price book only.
    """
    today = today or date.today()
    path = cache_path or _cache_path()
    cache = _load_cache(path, today)
    book = load_price_book() if book is None else book
    out: dict[str, dict] = {}
    index: list[dict] | None = None
    index_error: str | None = None

    for section in dict.fromkeys(s for s in sections if s):
        parsed = bu.parse_section(section)
        if not parsed or parsed["type"] not in ("H", "I", "C"):
            out[section] = _result(
                STATUS_UNSUPPORTED,
                price_note="Only H, I and lip-C (ตัวซี) sections are priced.",
            )
            continue
        result: dict | None = None
        if parsed["type"] == "H":
            try:
                if index is None and index_error is None:
                    index = _category_index(cache, fetch, sleep)
                if index is None:
                    raise PriceSourceError(index_error or "price index unavailable")
                candidates = [p for p in index if p["h"] == parsed["h"] and p["b"] == parsed["b"]]
                matches: list[dict] = []
                for product in candidates:
                    matches += [
                        it for it in _product_items(cache, product, fetch)
                        if it["h"] == parsed["h"] and it["b"] == parsed["b"]
                        and it["tw"] == parsed["tw"] and it["tf"] == parsed["tf"]
                    ]
                    sleep(REQUEST_DELAY_S)
                ss400 = [m for m in matches if m["grade"] == "SS400"]
                chosen = ss400 or matches
                if chosen:
                    grade = "SS400" if ss400 else (chosen[0]["grade"] or "unknown grade")
                    result = _result(
                        STATUS_OK,
                        price_per_kg=round(statistics.median(m["price_per_kg"] for m in chosen), 2),
                        price_source=SOURCE_NAME,
                        price_as_of=cache["as_of"],
                        price_note=f"{grade}, median of {len(chosen)} length variant(s)",
                    )
                else:
                    result = _result(
                        STATUS_NOT_FOUND,
                        price_note="No matching h x b x tw x tf variant listed at OneStockHome.",
                    )
            except PriceSourceError as e:
                index_error = index_error or str(e)
                result = _result(STATUS_ERROR, price_note=f"OneStockHome: {e}")
        if result is None or result["price_status"] != STATUS_OK:
            from_book = _book_lookup(parsed, book)
            if from_book is not None:
                if result is not None:
                    from_book["price_note"] += f" (fallback; {result['price_note']})"
                result = from_book
        out[section] = result or _result(
            STATUS_NOT_FOUND, price_note="No matching variant in the price book."
        )
    _save_cache(path, cache)
    return out


PRICE_COLUMNS = ["price_per_kg", "unit_price_thb_m", "amount_thb", "price_status", "price_source", "price_as_of", "price_note"]


def apply_prices(df: pd.DataFrame, prices: dict[str, dict]) -> pd.DataFrame:
    """Add price columns. amount_thb is left blank unless price, weight, length and qty are all known."""
    out = df.copy()
    rows = []
    for _, r in out.iterrows():
        p = prices.get(r["section"]) if pd.notna(r["section"]) else None
        if p is None:
            p = _result(STATUS_NOT_FOUND, price_note="No section")
        ppk = p["price_per_kg"]
        uw = r["unit_weight_kg_m"]
        unit_price = round(ppk * float(uw), 2) if ppk is not None and pd.notna(uw) else None
        amount = None
        if unit_price is not None and pd.notna(r["length_mm"]) and pd.notna(r["quantity"]):
            amount = round(unit_price * float(r["length_mm"]) / 1000.0 * float(r["quantity"]), 2)
        rows.append(
            {
                "price_per_kg": ppk,
                "unit_price_thb_m": unit_price,
                "amount_thb": amount,
                "price_status": p["price_status"] if (ppk is None or amount is not None) else "missing_weight_length_or_qty",
                "price_source": p["price_source"],
                "price_as_of": p["price_as_of"],
                "price_note": p["price_note"],
            }
        )
    extra = pd.DataFrame(rows, columns=PRICE_COLUMNS, index=out.index)
    for col in ("price_per_kg", "unit_price_thb_m", "amount_thb"):
        extra[col] = pd.to_numeric(extra[col], errors="coerce").astype("Float64")
    return pd.concat([out, extra], axis=1)


def summarize_prices(df: pd.DataFrame) -> dict:
    """Total is only a partial sum when some rows are unpriced; ``complete`` says which."""
    if "amount_thb" not in df.columns or not len(df):
        return {"total_amount_thb": None, "priced_rows": 0, "unpriced_rows": 0, "price_complete": False}
    priced = int(df["amount_thb"].notna().sum())
    unpriced = int(len(df) - priced)
    total = round(float(df["amount_thb"].astype(float).sum(skipna=True)), 2) if priced else None
    return {
        "total_amount_thb": total,
        "priced_rows": priced,
        "unpriced_rows": unpriced,
        "price_complete": priced > 0 and unpriced == 0,
    }
