from datetime import datetime
from io import BytesIO

import pandas as pd
import pytest

import boq_utils as bu


@pytest.mark.parametrize(
    "section,expected,tol",
    [
        ("H-300x300x10x15", 94.0, 3.0),
        ("H300x150x6.5x9", 36.7, 1.5),
        ("H 300 x 300 x 10 x 15", 94.0, 3.0),
        ("W12x26", 38.7, 0.5),
        ("[200x80x7.5x11", 24.6, 0.1),
        ("C200x80x7.5x11", 24.6, 0.1),
    ],
)
def test_unit_weight_known(section, expected, tol):
    assert bu.unit_weight_kg_m(section) == pytest.approx(expected, abs=tol)


@pytest.mark.parametrize("section", ["PL10", "UNKNOWN_SHAPE", None, "", "???"])
def test_unit_weight_unknown_is_none(section):
    assert bu.unit_weight_kg_m(section) is None


def test_unit_weight_angle_l():
    # L90x90x7: (90+90-7)*7 * 7850 / 1e6 ~ 9.5 kg/m
    assert bu.unit_weight_kg_m("L90x90x7") == pytest.approx(9.5, abs=0.2)


def test_parse_section_h():
    d = bu.parse_section("H-300x150x6.5x9")
    assert d["type"] == "H" and d["h"] == 300 and d["tf"] == 9


def test_rows_to_dataframe_columns_and_dtypes():
    rows = [
        {"member_id": "B1", "section": "W12x26", "length_mm": 4200, "quantity": 3, "notes": None},
        {"member_id": "X", "section": None, "length_mm": None, "quantity": None, "notes": "unclear"},
    ]
    df = bu.rows_to_dataframe(rows)
    assert list(df.columns) == bu.COLUMNS
    assert str(df["quantity"].dtype) == "Int64"
    assert str(df["length_mm"].dtype) == "Float64"
    assert str(df["unit_weight_kg_m"].dtype) == "Float64"
    assert df.loc[0, "unit_weight_kg_m"] == pytest.approx(38.7, abs=0.5)
    assert pd.isna(df.loc[1, "unit_weight_kg_m"])
    assert pd.isna(df.loc[1, "quantity"])


def test_rows_to_dataframe_empty():
    df = bu.rows_to_dataframe([])
    assert list(df.columns) == bu.COLUMNS
    assert len(df) == 0


def test_summarize_with_nulls():
    df = bu.rows_to_dataframe(
        [
            {"member_id": "B1", "section": "W12x26", "length_mm": 4000, "quantity": 2, "notes": None},
            {"member_id": "B1", "section": "W12x26", "length_mm": 4000, "quantity": 1, "notes": None},
            {"member_id": "C1", "section": None, "length_mm": None, "quantity": None, "notes": None},
        ]
    )
    s = bu.summarize(df)
    assert s["distinct_members"] == 2
    assert s["total_quantity"] == 3
    assert s["total_weight_kg"] == pytest.approx(3 * 4.0 * bu.unit_weight_kg_m("W12x26"), rel=1e-6)


def test_summarize_weight_none_when_nothing_derivable():
    df = bu.rows_to_dataframe([{"member_id": "U1", "section": "UNKNOWN_SHAPE", "length_mm": 1000, "quantity": 1, "notes": None}])
    assert bu.summarize(df)["total_weight_kg"] is None


def test_build_filename():
    ts = datetime(2026, 9, 8, 12, 0, 0)
    assert bu.build_filename("Level 2 plan.pdf", ts) == "boq_Level_2_plan_20260908_120000.xlsx"


def test_to_excel_roundtrip():
    df = bu.rows_to_dataframe(
        [{"member_id": "B1", "section": "W12x26", "length_mm": 4200, "quantity": 3, "notes": None}]
    )
    data = bu.to_excel_bytes(df, bu.summarize(df))
    sheets = pd.read_excel(BytesIO(data), sheet_name=None)
    assert set(sheets) == {"BOQ", "Summary"}
    assert list(sheets["BOQ"].columns) == bu.COLUMNS
    assert sheets["BOQ"].loc[0, "member_id"] == "B1"
