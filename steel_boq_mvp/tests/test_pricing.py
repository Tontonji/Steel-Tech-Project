"""Tests for pricing.py using a fake fetcher (no network)."""
from datetime import date, timedelta

import pandas as pd

import boq_utils as bu
import pricing as pr

CATEGORY = (
    '<a href="/th/products/111/h-beam-100x100-ss400_sys">x</a>'
    '<a href="/th/products/222/wide-flange-200x100-ss400-hb-200x100_sys">y</a>'
)


def _item(name, price, weight):
    return (
        f'{{"id":"1","itemId":"1","name":"{name}","url":"\\/th\\/items\\/1\\/x",'
        f'"displayPrice":"{price}","displaySize":"s","eanCode":"","weight":{weight},"unit":"ท่อน"}}'
    )


PRODUCT_111 = (
    _item("เหล็กบีม H-Beam SYS 100x100x6x8 มม. (4 นิ้ว) SS400 ยาว 6 ม.", "2,834.90", 103.2)
    + _item("เหล็กบีม H-Beam SYS 100x100x6x8 มม. (4 นิ้ว) SS400 ยาว 12 ม.", "5,669.81", 206.4)
    + _item("เหล็กบีม H-Beam SYS 100x100x6x8 มม. SM520 ยาว 6 ม.", "3,500.00", 103.2)
)
PRODUCT_222 = _item("เหล็กบีม Wide Flange 200x100x5.5x8 มม. SS400 ยาว 6 ม.", "4,000.00", 128.0)


def make_fetch(calls):
    def fetch(url):
        calls.append(url)
        if "product_categories/h-beam" in url:
            return CATEGORY if url.endswith("page=1") else ""
        if "/products/111/" in url:
            return PRODUCT_111
        if "/products/222/" in url:
            return PRODUCT_222
        raise pr.PriceSourceError("404")
    return fetch


BOOK = [
    {"code": "A7033", "category": "H", "dims_mm": "200x200x8x12", "unit": "u", "material_price_thb": "10345",
     "labor_price_thb": "3588", "weight_kg_per_unit": "299.0", "material_price_per_kg": "34.6"},
    {"code": "A7040", "category": "I", "dims_mm": "200x100x7x10", "unit": "u", "material_price_thb": "5304",
     "labor_price_thb": "1872", "weight_kg_per_unit": "156.0", "material_price_per_kg": "34.0"},
    {"code": "A7019", "category": "LIPC", "dims_mm": "100x50x20x2.3", "unit": "u", "material_price_thb": "610",
     "labor_price_thb": "244", "weight_kg_per_unit": "23.5", "material_price_per_kg": "25.96"},
]


def run(sections, tmp_path, calls=None, today=date(2026, 10, 15), book=()):
    calls = [] if calls is None else calls
    return pr.lookup_prices(
        sections, fetch=make_fetch(calls), today=today, cache_path=tmp_path / "c.json",
        sleep=lambda s: None, book=list(book),
    )


def test_parse_items_ignores_bad_rows():
    items = pr.parse_items(PRODUCT_111 + _item("no dims here", "10.00", 1) + _item("H 1x1x1x1 SS400", "0", 5))
    assert len(items) == 3
    assert items[0]["price_per_kg"] == 27.47 and items[0]["length_m"] == 6.0 and items[0]["grade"] == "SS400"


def test_exact_match_prefers_ss400_and_uses_median(tmp_path):
    r = run(["H100X100X6X8"], tmp_path)["H100X100X6X8"]
    assert r["price_status"] == pr.STATUS_OK
    assert r["price_per_kg"] == 27.47
    assert r["price_as_of"] == "2026-10-15" and "SS400" in r["price_note"]


def test_wide_flange_matches(tmp_path):
    assert run(["H200X100X5.5X8"], tmp_path)["H200X100X5.5X8"]["price_per_kg"] == 31.25


def test_not_found_and_unsupported_are_never_guessed(tmp_path):
    r = run(["H100X100X9X9", "C200X80X7.5X11", "L50X50X5"], tmp_path)
    assert r["H100X100X9X9"]["price_status"] == pr.STATUS_NOT_FOUND and r["H100X100X9X9"]["price_per_kg"] is None
    assert r["C200X80X7.5X11"]["price_status"] == pr.STATUS_NOT_FOUND  # JIS channel: no book row
    assert r["L50X50X5"]["price_status"] == pr.STATUS_UNSUPPORTED


def test_book_prices_i_beam_and_lip_c(tmp_path):
    r = run(["I200X100X7X10", "C100X50X20X2.3"], tmp_path, book=BOOK)
    assert r["I200X100X7X10"]["price_per_kg"] == 34.0 and r["I200X100X7X10"]["price_as_of"] == pr.BOOK_AS_OF
    assert r["C100X50X20X2.3"]["price_per_kg"] == 25.96 and "A7019" in r["C100X50X20X2.3"]["price_note"]
    assert r["I200X100X7X10"]["price_source"] == pr.BOOK_SOURCE


def test_h_prefers_onestockhome_then_falls_back_to_book(tmp_path):
    # In the shop list: shop price wins even though the book has a different value.
    shop = run(["H100X100X6X8"], tmp_path, book=BOOK)["H100X100X6X8"]
    assert shop["price_source"] == pr.SOURCE_NAME and shop["price_per_kg"] == 27.47
    # Not in the shop list but in the book: fallback, labelled as such.
    fb = run(["H200X200X8X12"], tmp_path, book=BOOK)["H200X200X8X12"]
    assert fb["price_source"] == pr.BOOK_SOURCE and fb["price_per_kg"] == 34.6 and "fallback" in fb["price_note"]


def test_shop_outage_falls_back_to_book(tmp_path):
    def boom(url):
        raise pr.PriceSourceError("offline")
    r = pr.lookup_prices(["H200X200X8X12"], fetch=boom, cache_path=tmp_path / "c.json",
                         sleep=lambda s: None, book=BOOK)["H200X200X8X12"]
    assert r["price_status"] == pr.STATUS_OK and r["price_source"] == pr.BOOK_SOURCE and "offline" in r["price_note"]


def test_bundled_book_loads_and_is_sane():
    book = pr.load_price_book()
    assert len(book) > 60
    assert {"H", "I", "LIPC", "ANGLE", "PLATE"} <= {r["category"] for r in book}
    for r in book:
        assert 10 < float(r["material_price_per_kg"]) < 100, r  # catches parse slips
        pr._book_dims(r)


def test_i_beam_has_unit_weight():
    assert bu.parse_section("I200x100x7x10")["type"] == "I"
    assert 150 / 6 < bu.unit_weight_kg_m("I200x100x7x10") < 160 / 6 + 5


def test_source_error_becomes_status(tmp_path):
    def boom(url):
        raise pr.PriceSourceError("offline")
    r = pr.lookup_prices(["H100X100X6X8"], fetch=boom, cache_path=tmp_path / "c.json", sleep=lambda s: None, book=[])
    assert r["H100X100X6X8"]["price_status"] == pr.STATUS_ERROR


def test_cache_avoids_refetch_and_expires(tmp_path):
    calls: list[str] = []
    run(["H100X100X6X8"], tmp_path, calls)
    first = len(calls)
    run(["H100X100X6X8"], tmp_path, calls)
    assert len(calls) == first  # served from cache
    run(["H100X100X6X8"], tmp_path, calls, today=date(2026, 10, 15) + timedelta(days=2))
    assert len(calls) > first  # expired


def test_apply_prices_and_summary(tmp_path):
    df = bu.rows_to_dataframe(
        [
            {"member_id": "B1", "section": "H100X100X6X8", "length_mm": 6000, "quantity": 2},
            {"member_id": "B2", "section": "C200X80X7.5X11", "length_mm": 6000, "quantity": 1},
        ]
    )
    priced = pr.apply_prices(df, run(list(df["section"]), tmp_path))
    r0, r1 = priced.iloc[0], priced.iloc[1]
    uw = bu.unit_weight_kg_m("H100X100X6X8")
    assert r0["amount_thb"] == round(round(27.47 * uw, 2) * 6.0 * 2, 2)
    assert pd.isna(r1["amount_thb"]) and r1["price_status"] == pr.STATUS_NOT_FOUND
    s = pr.summarize_prices(priced)
    assert s["priced_rows"] == 1 and s["unpriced_rows"] == 1 and s["price_complete"] is False
    assert s["total_amount_thb"] == r0["amount_thb"]
