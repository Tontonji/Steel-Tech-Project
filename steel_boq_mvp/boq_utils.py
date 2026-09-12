"""Pure helpers: rows -> DataFrame, unit-weight lookup, summary, Excel export, filename."""
from __future__ import annotations

import re
from datetime import datetime
from io import BytesIO

import pandas as pd

COLUMNS = ["member_id", "section", "length_mm", "quantity", "unit_weight_kg_m", "notes"]

STEEL_DENSITY_KG_M3 = 7850.0
LB_FT_TO_KG_M = 1.48816

# Catalogue values (kg/m) for a few common JIS channels; consulted before the formula.
SECTION_TABLE: dict[str, float] = {
    "C200X80X7.5X11": 24.6,
    "C250X90X9X13": 34.6,
    "C300X90X9X13": 38.1,
    "C150X75X6.5X10": 18.6,
    "C100X50X5X7.5": 9.36,
}

_H_RE = re.compile(
    r"^(?:H|HN|HW|HM|HP|UB|UC|IPE|HE[ABM]?)\s*-?\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)$"
)
_C_RE = re.compile(
    r"^(?:\[|C|PFC|U)\s*-?\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)$"
)
_W_RE = re.compile(r"^W\s*(\d+)\s*[xX×]\s*(\d+(?:\.\d+)?)$")


def _norm(section: str) -> str:
    return re.sub(r"\s+", "", section.strip()).upper().replace("×", "X")


def parse_section(section: str | None) -> dict | None:
    if not section or not isinstance(section, str):
        return None
    s = _norm(section)
    m = _H_RE.match(s)
    if m:
        h, b, tw, tf = (float(x) for x in m.groups())
        return {"type": "H", "h": h, "b": b, "tw": tw, "tf": tf}
    m = _C_RE.match(s)
    if m:
        h, b, tw, tf = (float(x) for x in m.groups())
        return {"type": "C", "h": h, "b": b, "tw": tw, "tf": tf}
    m = _W_RE.match(s)
    if m:
        return {"type": "W", "depth_in": float(m.group(1)), "lb_ft": float(m.group(2))}
    return None


def _flanged_weight(h: float, b: float, tw: float, tf: float) -> float:
    # Area of two flanges plus web (mm^2), ignoring root fillets -> ~1-2 % low.
    area_mm2 = 2 * b * tf + (h - 2 * tf) * tw
    return round(STEEL_DENSITY_KG_M3 * area_mm2 / 1e6, 1)


def unit_weight_kg_m(section: str | None) -> float | None:
    """Approximate unit weight (kg/m) for H/I, channel and imperial W sections; None otherwise."""
    parsed = parse_section(section)
    if parsed is None:
        return None
    if parsed["type"] == "C":
        key = "C" + _norm(section).lstrip("[CPFU")
        if key in SECTION_TABLE:
            return SECTION_TABLE[key]
        return _flanged_weight(parsed["h"], parsed["b"], parsed["tw"], parsed["tf"])
    if parsed["type"] == "H":
        return _flanged_weight(parsed["h"], parsed["b"], parsed["tw"], parsed["tf"])
    if parsed["type"] == "W":
        return round(parsed["lb_ft"] * LB_FT_TO_KG_M, 1)
    return None


def rows_to_dataframe(rows: list[dict]) -> pd.DataFrame:
    records = []
    for r in rows or []:
        r = dict(r or {})
        records.append(
            {
                "member_id": r.get("member_id"),
                "section": r.get("section"),
                "length_mm": r.get("length_mm"),
                "quantity": r.get("quantity"),
                "unit_weight_kg_m": r.get("unit_weight_kg_m")
                if r.get("unit_weight_kg_m") not in (None, "")
                else unit_weight_kg_m(r.get("section")),
                "notes": r.get("notes"),
            }
        )
    df = pd.DataFrame.from_records(records, columns=COLUMNS)
    df["member_id"] = df["member_id"].astype("string")
    df["section"] = df["section"].astype("string")
    df["notes"] = df["notes"].astype("string")
    df["length_mm"] = pd.to_numeric(df["length_mm"], errors="coerce").astype("Float64")
    df["unit_weight_kg_m"] = pd.to_numeric(df["unit_weight_kg_m"], errors="coerce").astype("Float64")
    qty = pd.to_numeric(df["quantity"], errors="coerce").round()
    df["quantity"] = qty.astype("Float64").astype("Int64")
    return df


def summarize(df: pd.DataFrame) -> dict:
    ids = df["member_id"].dropna()
    ids = ids[ids.astype(str).str.strip() != ""]
    distinct = int(ids.nunique())
    total_qty = int(df["quantity"].sum(skipna=True)) if len(df) else 0
    mask = df["quantity"].notna() & df["length_mm"].notna() & df["unit_weight_kg_m"].notna()
    if mask.any():
        sub = df[mask]
        weight = float(
            (sub["quantity"].astype(float) * sub["length_mm"].astype(float) / 1000.0 * sub["unit_weight_kg_m"].astype(float)).sum()
        )
        total_weight = round(weight, 1)
    else:
        total_weight = None
    return {"distinct_members": distinct, "total_quantity": total_qty, "total_weight_kg": total_weight}


TS_FORMAT = "%Y%m%d_%H%M%S"


def build_filename(original_filename: str, ts: datetime | None = None) -> str:
    ts = ts or datetime.now()
    stem = original_filename.rsplit(".", 1)[0] if "." in original_filename else original_filename
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_") or "drawing"
    return f"boq_{stem}_{ts.strftime(TS_FORMAT)}.xlsx"


def to_excel_bytes(df: pd.DataFrame, summary: dict) -> bytes:
    out = df.astype(object).where(df.notna(), None)
    summary_df = pd.DataFrame({"metric": list(summary.keys()), "value": list(summary.values())})
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        out.to_excel(writer, sheet_name="BOQ", index=False)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
    return buf.getvalue()
