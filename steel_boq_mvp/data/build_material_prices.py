"""One-off extractor: material price book PDF (section A7, structural steel) -> data/material_prices_2568.csv.

Usage: python data/build_material_prices.py "path/to/ราคาวัสดุ.pdf"

Only categories the BOQ can match are kept (H-Beam, I-Beam, lip channel, equal angle, black plate).
Rows whose weight is a range (e.g. "20-21 กก.") are skipped rather than guessed.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import pymupdf

CATEGORIES = [
    ("เหล็ก H-Beam", "H"),
    ("เหล็ก I-Beam", "I"),
    ("เหล็กตัวซี", "LIPC"),
    ("เหล็กฉาก", "ANGLE"),
    ("เหล็กแผ่นเรียบดํา", "PLATE"),
]
ROW_RE = re.compile(r"^(A7\d{3}) (.+?) \| (ท่อน|แผ่น) \| ([\d,]+) \| ([\d,]+) \| ([\d,.]+) กก\.?/(?:ท่อน|แผ่น)")
DIMS_RE = re.compile(r"(\d+(?:\.\d+)?(?:\s*x\s*\d+(?:\.\d+)?)+)\s*มม")
THICK_RE = re.compile(r"หนา\s*(\d+(?:\.\d+)?)\s*มม")


def main(pdf_path: str) -> None:
    doc = pymupdf.open(pdf_path)
    text = "\n".join(doc[i].get_text() for i in range(len(doc)) if "A7" in doc[i].get_text())
    parts = re.split(r"\n(?=A7\d{3} )", text)
    rows = []
    for p in parts:
        if not re.match(r"A7\d{3} ", p):
            continue
        line = " | ".join(x.strip() for x in p.split("\n") if x.strip())
        m = ROW_RE.match(line)
        if not m:
            continue
        code, name, unit, mat, lab, weight = m.groups()
        category = next((c for prefix, c in CATEGORIES if name.startswith(prefix)), None)
        if category is None:
            continue
        if category == "PLATE":
            t = THICK_RE.search(name)
            dims = t.group(1) if t else ""
        else:
            d = DIMS_RE.search(name)
            dims = re.sub(r"\s+", "", d.group(1)) if d else ""
        if not dims:
            continue
        w = float(weight.replace(",", ""))
        rows.append(
            {
                "code": code, "category": category, "dims_mm": dims, "unit": unit,
                "material_price_thb": int(mat.replace(",", "")),
                "labor_price_thb": int(lab.replace(",", "")),
                "weight_kg_per_unit": w,
                "material_price_per_kg": round(int(mat.replace(",", "")) / w, 2),
            }
        )
    out = Path(__file__).with_name("material_prices_2568.csv")
    with out.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    print(f"wrote {len(rows)} rows -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
