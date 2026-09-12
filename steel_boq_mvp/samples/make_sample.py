"""Generate a deterministic synthetic 3-page steel drawing PDF plus ground truth CSV.

Page 1: member schedule table (with deliberate nulls / a faint row).
Page 2: framing plan with grid, dimension strings, beam/column tags (adds B5, gives B4 length).
Page 3: title block + general notes (no members; hallucination check).

Run:  python samples/make_sample.py
"""
from __future__ import annotations

import csv
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

HERE = Path(__file__).resolve().parent
PDF_PATH = HERE / "sample_schedule.pdf"
CSV_PATH = HERE / "ground_truth.csv"

W, H = A4

# member_id, section, length_mm (None = blank/dash), quantity, remarks, page, notes_expected
SCHEDULE = [
    ("B1", "H-300x150x6.5x9", 6000, 8, "", 1, ""),
    ("B2", "H-400x200x8x13", 7500, 4, "", 1, ""),
    ("B3", "H-250x125x6x9", 4500, 6, "", 1, ""),
    ("GB-01", "H-500x200x10x16", 9000, 2, "GRADE BEAM", 1, ""),
    ("C1", "H-300x300x10x15", 3600, 6, "", 1, ""),
    ("C2", "H-250x250x9x14", 3600, 4, "", 1, ""),
    ("CH-1", "[200x80x7.5x11", 3000, 10, "PURLIN", 1, ""),
    ("CH-2", "[250x90x9x13", None, 6, "LENGTH TBC", 1, "length missing"),
    ("BR-1", "L90x90x7", 4243, 8, "BRACE", 1, ""),
    ("P1", "W12x26", 4200, 3, "IMPERIAL", 1, ""),
    ("B4", "H-350x175x7x11", "SEE PLAN", 2, "", 2, "length from plan dimension"),
    ("X1", "H-200x100x5.5x8", 2800, 1, "", 1, "faint text"),
]
PLAN_ONLY = [("B5", "", 6000, 2, "", 2, "plan only; section not in schedule")]


def _title_block(c: canvas.Canvas, sheet: str, title: str):
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.2)
    c.rect(20, 20, W - 40, H - 40)
    c.rect(20, 20, W - 40, 60)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(30, 62, "STEEL-TECH RESEARCH PROJECT")
    c.setFont("Helvetica", 8)
    c.drawString(30, 48, "SYNTHETIC TEST DRAWING - NOT FOR CONSTRUCTION")
    c.drawString(30, 36, "SCALE 1:100 @ A4    UNITS: mm    GRADE: S355")
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(W - 30, 58, sheet)
    c.setFont("Helvetica", 9)
    c.drawRightString(W - 30, 40, title)


def _page_schedule(c: canvas.Canvas):
    _title_block(c, "S-201", "STEEL MEMBER SCHEDULE - LEVEL 2")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, H - 60, "STEEL MEMBER SCHEDULE - LEVEL 2")

    cols = [40, 110, 270, 370, 420, 555]  # x boundaries
    headers = ["MARK", "SECTION", "LENGTH (mm)", "QTY", "REMARKS"]
    top = H - 90
    row_h = 22
    n_rows = len(SCHEDULE) + 1
    c.setLineWidth(0.8)
    for i in range(n_rows + 1):
        y = top - i * row_h
        c.line(cols[0], y, cols[-1], y)
    for x in cols:
        c.line(x, top, x, top - n_rows * row_h)

    c.setFont("Helvetica-Bold", 9)
    for j, htxt in enumerate(headers):
        c.drawString(cols[j] + 4, top - 15, htxt)

    for i, (mid, sec, length, qty, rem, _page, _note) in enumerate(SCHEDULE, start=1):
        y = top - i * row_h - 15
        if mid == "X1":
            c.setFillColor(colors.Color(0.82, 0.82, 0.82))
            c.setFont("Helvetica", 6)
        else:
            c.setFillColor(colors.black)
            c.setFont("Courier", 9)
        c.drawString(cols[0] + 4, y, mid)
        c.drawString(cols[1] + 4, y, sec)
        length_txt = "-" if length is None else str(length)
        c.drawString(cols[2] + 4, y, length_txt)
        c.drawString(cols[3] + 4, y, str(qty))
        c.drawString(cols[4] + 4, y, rem)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 8)
    c.drawString(40, top - (n_rows + 1) * row_h - 10, "NOTES: 1. ALL LENGTHS ARE CUT LENGTHS.  2. QTY = NUMBER OF PIECES.")


def _page_plan(c: canvas.Canvas):
    _title_block(c, "S-101", "LEVEL 2 FRAMING PLAN")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, H - 60, "LEVEL 2 FRAMING PLAN")

    # Grid: A-D horizontally (3 bays), 1-3 vertically (2 bays). 6000 mm = 120 pt.
    ox, oy = 100, 200
    bay = 120
    xs = [ox + i * bay for i in range(4)]
    ys = [oy + i * bay for i in range(3)]
    ys_with_b4 = [oy + 0, oy + 140, oy + 260]  # second bay 7000 mm for B4

    c.setStrokeColor(colors.grey)
    c.setDash(6, 3)
    c.setLineWidth(0.5)
    for i, x in enumerate(xs):
        c.line(x, oy - 30, x, ys_with_b4[-1] + 30)
        c.circle(x, ys_with_b4[-1] + 42, 10)
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.black)
        c.drawCentredString(x, ys_with_b4[-1] + 39, "ABCD"[i])
    for i, y in enumerate(ys_with_b4):
        c.line(xs[0] - 30, y, xs[-1] + 30, y)
        c.circle(xs[0] - 42, y, 10)
        c.drawCentredString(xs[0] - 42, y - 3, str(i + 1))
    c.setDash()
    c.setStrokeColor(colors.black)

    # Dimension strings
    c.setLineWidth(0.6)
    c.setFont("Helvetica", 8)
    dy = ys_with_b4[-1] + 62
    for i in range(3):
        c.line(xs[i], dy, xs[i + 1], dy)
        c.line(xs[i], dy - 4, xs[i], dy + 4)
        c.drawCentredString((xs[i] + xs[i + 1]) / 2, dy + 4, "6000")
    c.line(xs[3], dy - 4, xs[3], dy + 4)
    dx = xs[-1] + 55
    labels = ["6000", "7000"]
    for i in range(2):
        c.line(dx, ys_with_b4[i], dx, ys_with_b4[i + 1])
        c.line(dx - 4, ys_with_b4[i], dx + 4, ys_with_b4[i])
        c.saveState()
        c.translate(dx + 10, (ys_with_b4[i] + ys_with_b4[i + 1]) / 2)
        c.rotate(90)
        c.drawCentredString(0, 0, labels[i])
        c.restoreState()
    c.line(dx - 4, ys_with_b4[2], dx + 4, ys_with_b4[2])

    # Beams (thick lines) along grid lines, with tags.
    c.setLineWidth(2)
    c.setFont("Courier-Bold", 9)
    # Horizontal beams on rows 1..3: B1 in bay A-B and B-C, B2 in bay C-D
    for y in ys_with_b4:
        c.line(xs[0], y, xs[3], y)
    for y in ys_with_b4:
        c.drawCentredString((xs[0] + xs[1]) / 2, y + 5, "B1")
        c.drawCentredString((xs[1] + xs[2]) / 2, y + 5, "B1")
        c.drawCentredString((xs[2] + xs[3]) / 2, y + 5, "B2")
    # Vertical beams: B4 in the 7000 bay on grids B and C; B5 in the 6000 bay on grids B and C
    for x in xs[1:3]:
        c.line(x, ys_with_b4[1], x, ys_with_b4[2])
        c.drawString(x + 4, (ys_with_b4[1] + ys_with_b4[2]) / 2, "B4")
        c.line(x, ys_with_b4[0], x, ys_with_b4[1])
        c.drawString(x + 4, (ys_with_b4[0] + ys_with_b4[1]) / 2, "B5")

    # Columns: squares at intersections; C1 on outer grids, C2 inner
    c.setLineWidth(1)
    for i, x in enumerate(xs):
        for y in ys_with_b4:
            c.rect(x - 5, y - 5, 10, 10, fill=1)
            tag = "C1" if i in (0, 3) else "C2"
            c.setFont("Courier", 7)
            c.drawString(x - 16, y - 16, tag)
            c.setFont("Courier-Bold", 9)

    c.setFont("Helvetica", 8)
    c.drawString(40, 130, "NOTES: 1. SEE SCHEDULE S-201 FOR MEMBER SIZES.  2. B5 SIZE TO BE CONFIRMED BY ENGINEER.")
    c.drawString(40, 118, "3. DIMENSIONS ARE GRID TO GRID.  4. B4 SPANS 7000 BETWEEN GRIDS 2 AND 3.")


def _page_notes(c: canvas.Canvas):
    _title_block(c, "S-001", "GENERAL NOTES AND COVER SHEET")
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, H - 70, "STRUCTURAL STEEL - GENERAL NOTES")
    notes = [
        "1. ALL STRUCTURAL STEEL SHALL BE GRADE S355 UNLESS NOTED OTHERWISE.",
        "2. ALL BOLTS SHALL BE M20 GRADE 8.8 UNLESS NOTED OTHERWISE.",
        "3. ALL WELDS SHALL BE 6 mm CONTINUOUS FILLET UNLESS NOTED OTHERWISE.",
        "4. STEELWORK TO BE HOT-DIP GALVANISED AFTER FABRICATION.",
        "5. CONTRACTOR TO VERIFY ALL DIMENSIONS ON SITE BEFORE FABRICATION.",
        "6. THIS DRAWING IS A SYNTHETIC RESEARCH SAMPLE AND CONTAINS NO MEMBER SCHEDULE.",
        "",
        "DRAWING LIST:",
        "   S-001  GENERAL NOTES AND COVER SHEET",
        "   S-101  LEVEL 2 FRAMING PLAN",
        "   S-201  STEEL MEMBER SCHEDULE - LEVEL 2",
    ]
    c.setFont("Helvetica", 10)
    y = H - 110
    for line in notes:
        c.drawString(50, y, line)
        y -= 18


def build_pdf(path: Path = PDF_PATH) -> Path:
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle("Synthetic steel drawing sample")
    c.setAuthor("steel_boq_mvp")
    # Deterministic output: reportlab embeds a creation date unless invariant is set.
    c._doc.invariant = True
    _page_schedule(c)
    c.showPage()
    _page_plan(c)
    c.showPage()
    _page_notes(c)
    c.showPage()
    c.save()
    return path


def build_csv(path: Path = CSV_PATH) -> Path:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["member_id", "section", "length_mm", "quantity", "page", "notes_expected"])
        for mid, sec, length, qty, _rem, page, note in SCHEDULE + PLAN_ONLY:
            if mid == "B4":
                length = 7000
            if length is None:
                length = ""
            w.writerow([mid, sec, length, qty, page, note])
    return path


if __name__ == "__main__":
    print("wrote", build_pdf())
    print("wrote", build_csv())
