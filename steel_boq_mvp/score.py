"""Score an extraction (log JSON or exported xlsx) against a ground-truth CSV.

Usage:
    python score.py --pred logs/20260908_120000.json --truth samples/ground_truth.csv
    python score.py --pred boq_sample_schedule_20260908_120000.xlsx --truth samples/ground_truth.csv
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import pandas as pd


def normalize_id(s) -> str:
    if s is None or (isinstance(s, float) and math.isnan(s)):
        return ""
    s = str(s).upper().strip()
    s = re.sub(r"[\s_]+", "", s)
    s = re.sub(r"-+", "-", s)
    return s


def normalize_section(s) -> str:
    if s is None or (isinstance(s, float) and math.isnan(s)):
        return ""
    s = str(s).upper().strip().replace("×", "X")
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"^H-", "H", s)
    return s


def _num(v):
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def load_pred(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data.get("parsed_rows") if isinstance(data, dict) else data
        return pd.DataFrame(rows or [])
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        return pd.read_excel(path, sheet_name="BOQ")
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported prediction file: {path}")


def load_truth(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _rows_by_id(df: pd.DataFrame) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for rec in df.to_dict("records"):
        key = normalize_id(rec.get("member_id"))
        if key and key not in out:
            out[key] = rec
    return out


def score(pred: pd.DataFrame, truth: pd.DataFrame) -> dict:
    p = _rows_by_id(pred)
    t = _rows_by_id(truth)
    matched = sorted(set(p) & set(t))
    missed = sorted(set(t) - set(p))
    spurious = sorted(set(p) - set(t))
    precision = len(matched) / len(p) if p else 0.0
    recall = len(matched) / len(t) if t else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    def field_acc(fn) -> float | None:
        if not matched:
            return None
        return sum(1 for k in matched if fn(p[k], t[k])) / len(matched)

    section_acc = field_acc(lambda a, b: normalize_section(a.get("section")) == normalize_section(b.get("section")))
    length_acc = field_acc(lambda a, b: _num(a.get("length_mm")) == _num(b.get("length_mm")))
    quantity_acc = field_acc(lambda a, b: _num(a.get("quantity")) == _num(b.get("quantity")))
    return {
        "n_pred": len(p),
        "n_truth": len(t),
        "matched": len(matched),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "section_acc": None if section_acc is None else round(section_acc, 3),
        "length_acc": None if length_acc is None else round(length_acc, 3),
        "quantity_acc": None if quantity_acc is None else round(quantity_acc, 3),
        "missed": missed,
        "spurious": spurious,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pred", required=True, help="log JSON, exported xlsx, or csv")
    ap.add_argument("--truth", required=True, help="ground truth csv")
    args = ap.parse_args(argv)
    result = score(load_pred(args.pred), load_truth(args.truth))
    width = max(len(k) for k in result)
    for k, v in result.items():
        print(f"{k:<{width}}  {v}")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
