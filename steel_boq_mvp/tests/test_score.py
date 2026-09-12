import json

import pandas as pd
import pytest

import score as sc

TRUTH = pd.DataFrame(
    [
        {"member_id": "B1", "section": "H-300x150x6.5x9", "length_mm": "6000", "quantity": "8"},
        {"member_id": "C1", "section": "H-300x300x10x15", "length_mm": "3600", "quantity": "6"},
        {"member_id": "CH-2", "section": "[250x90x9x13", "length_mm": "", "quantity": "6"},
    ]
)


def test_perfect_match():
    pred = pd.DataFrame(
        [
            {"member_id": "B1", "section": "H 300×150×6.5×9", "length_mm": 6000, "quantity": 8},
            {"member_id": "C1", "section": "H300x300x10x15", "length_mm": 3600, "quantity": 6},
            {"member_id": "CH-2", "section": "[250x90x9x13", "length_mm": None, "quantity": 6},
        ]
    )
    r = sc.score(pred, TRUTH)
    assert r["precision"] == 1.0 and r["recall"] == 1.0 and r["f1"] == 1.0
    assert r["section_acc"] == 1.0
    assert r["length_acc"] == 1.0
    assert r["quantity_acc"] == 1.0
    assert r["missed"] == [] and r["spurious"] == []


def test_miss_and_spurious():
    pred = pd.DataFrame(
        [
            {"member_id": "b1", "section": "H-300x150x6.5x9", "length_mm": 6000, "quantity": 7},
            {"member_id": "C1", "section": "H-300x300x10x15", "length_mm": 3600, "quantity": 6},
            {"member_id": "ZZ", "section": "PL10", "length_mm": 1, "quantity": 1},
        ]
    )
    r = sc.score(pred, TRUTH)
    assert r["matched"] == 2
    assert r["precision"] == pytest.approx(2 / 3, abs=1e-3)
    assert r["recall"] == pytest.approx(2 / 3, abs=1e-3)
    assert r["missed"] == ["CH-2"]
    assert r["spurious"] == ["ZZ"]
    assert r["quantity_acc"] == 0.5


def test_load_pred_from_log_json(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"parsed_rows": [{"member_id": "B1", "section": "W12x26", "length_mm": 1, "quantity": 1, "notes": None}]}))
    df = sc.load_pred(p)
    assert df.loc[0, "member_id"] == "B1"


def test_cli_runs(tmp_path, capsys):
    truth = tmp_path / "t.csv"
    TRUTH.to_csv(truth, index=False)
    pred = tmp_path / "p.json"
    pred.write_text(json.dumps({"parsed_rows": TRUTH.to_dict("records")}))
    assert sc.main(["--pred", str(pred), "--truth", str(truth)]) == 0
    out = capsys.readouterr().out
    assert '"f1": 1.0' in out
