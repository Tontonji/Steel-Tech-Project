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
        ("Square Tube 2\"x4\"x2mm", 4.7, 0.3),
        ("Dia 25mm", 3.85, 0.1),
        ("Steel 90mm, 7.76 kg/m", 7.76, 0.01),
        ("Steel 125mm, 12.1 kg/m", 12.1, 0.01),
        ("Steel 50mm, 4.52 kg/m", 4.52, 0.01),
    ],
)
def test_unit_weight_known(section, expected, tol):
    assert bu.unit_weight_kg_m(section) == pytest.approx(expected, abs=tol)


@pytest.mark.parametrize("section", ["PL10", "UNKNOWN_SHAPE", None, "", "???"])
def test_unit_weight_unknown_is_none(section):
    assert bu.unit_weight_kg_m(section) is None


def test_infer_missing_lengths_screenshot_case():
    rows = [
        {"member_id": "Purlin", "section": "Square Tube 2\"x4\"x2mm", "length_mm": 6000, "quantity": 10},
        {"member_id": "Column H-Beam", "section": "H-200x200x8x12", "length_mm": None, "quantity": 4},
        {"member_id": "Base Plate", "section": "Plate 25mm", "length_mm": 300, "quantity": 4},
        {"member_id": "Stiffener Plate", "section": "Plate 12mm", "length_mm": None, "quantity": 16},
        {"member_id": "Anchor Bolt", "section": "Dia 25mm", "length_mm": 700, "quantity": 16},
        {"member_id": "TRUSS 1 Top Chord", "section": "Steel 90mm, 7.76 kg/m", "length_mm": 28000, "quantity": 2},
        {"member_id": "TRUSS 1 Bottom Chord", "section": "Steel 125mm, 12.1 kg/m", "length_mm": 28000, "quantity": 2},
        {"member_id": "TRUSS 2 Members", "section": "Steel 50mm, 4.52 kg/m", "length_mm": None, "quantity": 20},
    ]
    inferred = bu.infer_missing_lengths(rows)
    # Column borrows 6000 from bay or typical
    assert inferred[1]["length_mm"] in (6000, 4000)
    assert "ยืม" in inferred[1]["notes"] or "assume" in inferred[1]["notes"]
    # Stiffener plate borrows 200mm from H-200 or 300mm from Base Plate
    assert inferred[3]["length_mm"] in (200, 300)
    assert "ยืม" in inferred[3]["notes"]
    # TRUSS 2 borrows 28000 from TRUSS 1
    assert inferred[7]["length_mm"] == 28000
    assert "ยืมความยาวจาก TRUSS 1" in inferred[7]["notes"]


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
