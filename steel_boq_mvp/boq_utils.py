"""Pure helpers: rows -> DataFrame, unit-weight lookup, summary, Excel export, filename."""
from __future__ import annotations

import math
import re
from datetime import datetime
from io import BytesIO

import pandas as pd

COLUMNS = ["member_id", "section", "length_mm", "quantity", "unit_weight_kg_m", "notes"]

STEEL_DENSITY_KG_M3 = 7850.0
LB_FT_TO_KG_M = 1.48816

# Catalogue values (kg/m) for a few common JIS channels & H-beams; consulted before the formula.
SECTION_TABLE: dict[str, float] = {
    "C200X80X7.5X11": 24.6,
    "C250X90X9X13": 34.6,
    "C300X90X9X13": 38.1,
    "C150X75X6.5X10": 18.6,
    "C100X50X5X7.5": 9.36,
    "H200X200X8X12": 49.9,
    "H250X250X9X14": 72.4,
    "H300X300X10X15": 94.0,
    "H350X350X12X19": 137.0,
    "H400X400X13X21": 172.0,
    "H250X125X6X9": 29.6,
    "H300X150X6.5X9": 36.7,
    "H350X175X7X11": 49.6,
    "H400X200X8X13": 66.0,
    "H500X200X10X16": 89.6,
}

_EXPLICIT_WEIGHT_RE = re.compile(
    r"(?:^|[,\s\(/@])([0-9]+(?:\.[0-9]+)?)\s*(?:kg/m|กก\./ม|kg\.m|kg-m|kg/m2|กก\./ตร\.ม\.)",
    re.IGNORECASE,
)
_ROUND_BAR_RE = re.compile(
    r"(?:DIA\.?|DIAMETER|Ø|RB|DB|ANCHOR\s*BOLT|BOLT)\s*[-:]?\s*(\d+(?:\.\d+)?)\s*(?:MM|มม)?",
    re.IGNORECASE,
)
_INCH_TUBE_RE = re.compile(
    r"(?:SQUARE|RECTANGULAR|STEEL)?\s*(?:TUBE|SHS|RHS|กล่องเหลี่ยม|ท่อเหลี่ยม)?\s*(\d+(?:\.\d+)?)\s*(?:\"|IN|นิ้ว)\s*[xX×*]\s*(\d+(?:\.\d+)?)\s*(?:\"|IN|นิ้ว)\s*[xX×*]\s*(\d+(?:\.\d+)?)\s*(?:MM|มม)?",
    re.IGNORECASE,
)
_METRIC_TUBE_RE = re.compile(
    r"(?:SQUARE|RECTANGULAR|STEEL)?\s*(?:TUBE|SHS|RHS|กล่องเหลี่ยม|ท่อเหลี่ยม)\s*[-:]?\s*(\d+(?:\.\d+)?)\s*[xX×*]\s*(\d+(?:\.\d+)?)\s*[xX×*]\s*(\d+(?:\.\d+)?)\s*(?:MM|มม)?",
    re.IGNORECASE,
)
_PIPE_RE = re.compile(
    r"(?:PIPE|CHS|ท่อกลม)\s*[-:]?\s*(\d+(?:\.\d+)?)\s*(?:DIA|Ø)?\s*[xX×*]\s*(\d+(?:\.\d+)?)\s*(?:MM|มม)?",
    re.IGNORECASE,
)
_PLATE_DIM_RE = re.compile(
    r"(?:PLATE|PL|แผ่นเพลท)\s*[-:]?\s*(\d+(?:\.\d+)?)\s*(?:MM|มม)?\s*[xX×*]\s*(\d+(?:\.\d+)?)\s*(?:MM|มม)?",
    re.IGNORECASE,
)
_PLATE_THICK_RE = re.compile(
    r"^PLATE\s*(\d+(?:\.\d+)?)\s*(?:MM|มม)?$",
    re.IGNORECASE,
)

_H_RE = re.compile(
    r"^(?:H|HN|HW|HM|HP|UB|UC|IPE|HE[ABM]?)\s*-?\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)$"
)
_C_RE = re.compile(
    r"^(?:\[|C|PFC|U)\s*-?\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)$"
)
_W_RE = re.compile(r"^W\s*(\d+)\s*[xX×]\s*(\d+(?:\.\d+)?)$")
_I_RE = re.compile(
    r"^I\s*-?\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)$"
)
_L_RE = re.compile(
    r"^(?:L|∠)\s*-?\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)$"
)


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
    m = _I_RE.match(s)
    if m:
        h, b, tw, tf = (float(x) for x in m.groups())
        return {"type": "I", "h": h, "b": b, "tw": tw, "tf": tf}
    m = _L_RE.match(s)
    if m:
        a, b, t = (float(x) for x in m.groups())
        return {"type": "L", "a": a, "b": b, "t": t}
    return None


def _flanged_weight(h: float, b: float, tw: float, tf: float) -> float:
    # Area of two flanges plus web (mm^2), ignoring root fillets -> ~1-2 % low.
    area_mm2 = 2 * b * tf + (h - 2 * tf) * tw
    return round(STEEL_DENSITY_KG_M3 * area_mm2 / 1e6, 1)


def unit_weight_kg_m(
    section: str | None,
    member_id: str | None = None,
    length_mm: float | None = None,
) -> float | None:
    """Approximate unit weight (kg/m) for standard structural steel sections."""
    if not section or not isinstance(section, str):
        return None

    raw = section.strip()

    # 1. Explicit weight in text e.g. "Steel 90mm, 7.76 kg/m", "12.1 kg/m"
    m_exp = _EXPLICIT_WEIGHT_RE.search(raw)
    if m_exp:
        return float(m_exp.group(1))

    # 2. Round bar / Anchor bolt (e.g. "Dia 25mm", "RB25", "DB25")
    m_rb = _ROUND_BAR_RE.search(raw)
    if m_rb:
        d = float(m_rb.group(1))
        return round(0.006165 * d * d, 2)

    # 3. Square & Rectangular Tubes - Imperial (e.g. 'Square Tube 2"x4"x2mm')
    m_it = _INCH_TUBE_RE.search(raw)
    if m_it:
        a = float(m_it.group(1)) * 25.4
        b = float(m_it.group(2)) * 25.4
        t = float(m_it.group(3))
        area = 2 * (a + b - 2 * t) * t
        return round(STEEL_DENSITY_KG_M3 * area / 1e6, 1)

    # 4. Square & Rectangular Tubes - Metric (e.g. 'Square Tube 100x50x3.2')
    m_mt = _METRIC_TUBE_RE.search(raw)
    if m_mt:
        a = float(m_mt.group(1))
        b = float(m_mt.group(2))
        t = float(m_mt.group(3))
        area = 2 * (a + b - 2 * t) * t
        return round(STEEL_DENSITY_KG_M3 * area / 1e6, 1)

    # 5. Round Pipe (e.g. 'Pipe 100 dia x 3.2')
    m_p = _PIPE_RE.search(raw)
    if m_p:
        od = float(m_p.group(1))
        t = float(m_p.group(2))
        area = math.pi * (od - t) * t
        return round(STEEL_DENSITY_KG_M3 * area / 1e6, 1)

    # 6. Standard flanged / angles / W sections
    s = _norm(section)
    key = s.replace("[", "C").replace("H-", "H")
    if key in SECTION_TABLE:
        return SECTION_TABLE[key]

    parsed = parse_section(section)
    if parsed is not None:
        if parsed["type"] == "C":
            return _flanged_weight(parsed["h"], parsed["b"], parsed["tw"], parsed["tf"])
        if parsed["type"] in ("H", "I"):
            return _flanged_weight(parsed["h"], parsed["b"], parsed["tw"], parsed["tf"])
        if parsed["type"] == "L":
            return round(STEEL_DENSITY_KG_M3 * (parsed["a"] + parsed["b"] - parsed["t"]) * parsed["t"] / 1e6, 2)
        if parsed["type"] == "W":
            return round(parsed["lb_ft"] * LB_FT_TO_KG_M, 1)

    # 7. Plates with dimensions (e.g. 'Plate 25x300')
    m_pd = _PLATE_DIM_RE.search(raw)
    if m_pd:
        t = float(m_pd.group(1))
        w = float(m_pd.group(2))
        return round(STEEL_DENSITY_KG_M3 * t * w / 1e6, 1)

    # 8. Plate with thickness and member context (e.g. 'Plate 25mm' on Base Plate)
    m_pt = _PLATE_THICK_RE.search(raw)
    if m_pt:
        t = float(m_pt.group(1))
        mid = (member_id or "").lower()
        if "base" in mid and length_mm and length_mm > 0:
            return round((length_mm * t * STEEL_DENSITY_KG_M3) / 1e6, 1)
        if "stiffener" in mid:
            return round((200.0 * t * STEEL_DENSITY_KG_M3) / 1e6, 1)
        return round((250.0 * t * STEEL_DENSITY_KG_M3) / 1e6, 1)

    return None


def infer_missing_lengths(rows: list[dict]) -> list[dict]:
    """Heuristic length borrowing algorithm for rows where length_mm is missing/null."""
    known = [r for r in rows if r.get("length_mm") not in (None, "", 0)]
    if not known:
        return rows

    out = []
    for r in rows:
        item = dict(r)
        if item.get("length_mm") not in (None, "", 0):
            out.append(item)
            continue

        mid = str(item.get("member_id") or "").lower()
        sec = str(item.get("section") or "").lower()
        existing_notes = str(item.get("notes") or "").strip()

        borrowed_len: float | None = None
        source_desc = ""

        # 1. Truss members borrowing from other truss chords
        if "truss" in mid or "truss" in sec:
            other = next((k for k in known if "truss" in str(k.get("member_id", "")).lower()), None)
            if other and other.get("length_mm"):
                borrowed_len = float(other["length_mm"])
                source_desc = f"ยืมความยาวจาก {other.get('member_id')} ({borrowed_len:,.0f} mm)"

        # 2. Stiffener plate derived from column/beam section
        if not borrowed_len and ("stiffener" in mid or "stiffener" in sec):
            h_beam = next((k for k in rows if re.search(r"H\s*-?\s*(\d+)", str(k.get("section", "")))), None)
            if h_beam:
                m = re.search(r"H\s*-?\s*(\d+)", str(h_beam.get("section", "")))
                if m:
                    borrowed_len = float(m.group(1))
                    source_desc = f"ยืมมิติตามหน้าตัด {h_beam.get('member_id') or h_beam.get('section')} ({borrowed_len:.0f} mm)"
            if not borrowed_len:
                bp = next((k for k in known if "base" in str(k.get("member_id", "")).lower()), None)
                if bp and bp.get("length_mm"):
                    borrowed_len = float(bp["length_mm"])
                    source_desc = f"ยืมความยาวจาก {bp.get('member_id')} ({borrowed_len:,.0f} mm)"

        # 3. Column (เสา)
        if not borrowed_len and ("column" in mid or "เสา" in mid or (mid.startswith("c") and any(ch.isdigit() for ch in mid))):
            other_col = next(
                (k for k in known if "column" in str(k.get("member_id", "")).lower() or "เสา" in str(k.get("member_id", "")).lower()),
                None,
            )
            if other_col and other_col.get("length_mm"):
                borrowed_len = float(other_col["length_mm"])
                source_desc = f"ยืมความยาวจาก {other_col.get('member_id')} ({borrowed_len:,.0f} mm)"
            else:
                bay = next((k for k in known if float(k.get("length_mm") or 0) in (6000, 3000, 4000)), None)
                if bay and bay.get("length_mm"):
                    borrowed_len = float(bay["length_mm"])
                    source_desc = f"ยืมความยาวจากระยะช่วงเสา {bay.get('member_id')} ({borrowed_len:,.0f} mm)"
                else:
                    borrowed_len = 4000.0
                    source_desc = "assume ความสูงเสามาตรฐาน 4,000 mm"

        # 4. Same section match
        if not borrowed_len:
            same_sec = next((k for k in known if _norm(str(k.get("section", ""))) == _norm(str(item.get("section", "")))), None)
            if same_sec and same_sec.get("length_mm"):
                borrowed_len = float(same_sec["length_mm"])
                source_desc = f"ยืมความยาวจาก {same_sec.get('member_id')} (หน้าตัดเดียวกัน)"

        # 5. Closest known item
        if not borrowed_len and known:
            borrowed_len = float(known[0]["length_mm"])
            source_desc = f"ยืมความยาวจาก {known[0].get('member_id')} ({borrowed_len:,.0f} mm)"

        if borrowed_len is not None:
            item["length_mm"] = borrowed_len
            item["notes"] = f"{existing_notes} [{source_desc}]".strip() if existing_notes else f"[{source_desc}]"

        out.append(item)
    return out


def rows_to_dataframe(rows: list[dict]) -> pd.DataFrame:
    rows = infer_missing_lengths(rows or [])
    records = []
    for r in rows:
        r = dict(r or {})
        uw = r.get("unit_weight_kg_m")
        if uw in (None, ""):
            uw = unit_weight_kg_m(
                r.get("section"),
                member_id=r.get("member_id"),
                length_mm=r.get("length_mm"),
            )
        records.append(
            {
                "member_id": r.get("member_id"),
                "section": r.get("section"),
                "length_mm": r.get("length_mm"),
                "quantity": r.get("quantity"),
                "unit_weight_kg_m": uw,
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
