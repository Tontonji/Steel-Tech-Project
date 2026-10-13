"""
Project Proposal Word Doc Generator
นายจิรายุ ประสพสุขโชคมณี 6610501475
มหาวิทยาลัยเกษตรศาสตร์
อาจารย์ที่ปรึกษา: รศ.ดร.กิจพัฒน์ ภู่วรวรรณ
"""
import docx
from docx.shared import Inches, Pt, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

FONT_NAME = "TH SarabunPSK"
BODY_SIZE = 16
TABLE_SIZE = 14

# ─────────────────────────────────────────────────────────────────────────────
# Low-level helpers
# ─────────────────────────────────────────────────────────────────────────────
def _set_run_font(run, name=FONT_NAME, size_pt=16, bold=False, italic=False, color_rgb=(0, 0, 0)):
    run.font.name = name
    rPr = run._r.get_or_add_rPr()
    rFonts = parse_xml(
        f'<w:rFonts {nsdecls("w")} w:ascii="{name}" w:hAnsi="{name}" w:cs="{name}"/>'
    )
    rPr.append(rFonts)
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(*color_rgb)


def _set_cell_fill(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}" w:val="clear"/>')
    tcPr.append(shd)


def _set_cell_margins(cell, top=60, bottom=60, left=80, right=80):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def _set_cell_vertical_align(cell, val="center"):
    tcPr = cell._tc.get_or_add_tcPr()
    vAlign = parse_xml(f'<w:vAlign {nsdecls("w")} w:val="{val}"/>')
    tcPr.append(vAlign)


def _set_table_borders(table, color="333333", sz="4", val="single"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:right w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


# ─────────────────────────────────────────────────────────────────────────────
# High-level paragraph helpers
# ─────────────────────────────────────────────────────────────────────────────
def add_p(doc, text="", bold=False, italic=False, size_pt=BODY_SIZE,
          space_before=0, space_after=3, indent=0.0,
          align=WD_ALIGN_PARAGRAPH.LEFT, line_spacing=1.15):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing
    p.alignment = align
    if indent:
        p.paragraph_format.left_indent = Inches(indent)
    if text:
        r = p.add_run(text)
        _set_run_font(r, size_pt=size_pt, bold=bold, italic=italic)
    return p


def add_mixed(doc, runs, space_before=0, space_after=3, indent=0.0,
              align=WD_ALIGN_PARAGRAPH.LEFT, line_spacing=1.15):
    """runs = list of (text, bold, italic, size_pt)"""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing
    p.alignment = align
    if indent:
        p.paragraph_format.left_indent = Inches(indent)
    for text, bold, italic, size_pt in runs:
        r = p.add_run(text)
        _set_run_font(r, size_pt=size_pt, bold=bold, italic=italic)
    return p


def _table_header_cell(cell, text, bg="2D5FA0", fg=(255, 255, 255), size_pt=TABLE_SIZE,
                        top=80, bottom=80, left=80, right=80):
    _set_cell_fill(cell, bg)
    _set_cell_margins(cell, top=top, bottom=bottom, left=left, right=right)
    _set_cell_vertical_align(cell, "center")
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    _set_run_font(r, size_pt=size_pt, bold=True, color_rgb=fg)


def _table_body_cell(cell, text, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT,
                     size_pt=TABLE_SIZE, bg=None, top=60, bottom=60, left=80, right=80):
    if bg:
        _set_cell_fill(cell, bg)
    _set_cell_margins(cell, top=top, bottom=bottom, left=left, right=right)
    _set_cell_vertical_align(cell, "center")
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.1
    p.alignment = align
    r = p.add_run(text)
    _set_run_font(r, size_pt=size_pt, bold=bold)


# ─────────────────────────────────────────────────────────────────────────────
# Gantt table builder
# Each task occupies 2 rows: row[0] = task name (merged), row[1] = colored bar
# ─────────────────────────────────────────────────────────────────────────────
BAR_COLOR = "1E3A8A"     # solid dark-navy bar for active weeks
BG_LIGHT  = "F0F4FA"     # light stripe for readability

def build_gantt(doc, title_text, months, tasks):
    """
    months = [("ชื่อเดือน", start_week_0indexed, end_week_0indexed_inclusive), ...]
    tasks  = [("ชื่องาน", first_week_0indexed, last_week_0indexed), ...]
    Weeks are numbered 0-15 across 4 months × 4 weeks.
    """
    n_weeks = sum(4 for _ in months)        # usually 16
    n_cols  = 1 + n_weeks                   # col0 = task, col1..n_weeks = weeks
    n_rows  = 2 + len(tasks) * 2            # 2 header rows + 2 per task

    # Caption
    cap = doc.add_paragraph()
    cap.paragraph_format.left_indent = Inches(0.5)
    cap.paragraph_format.space_before = Pt(6)
    cap.paragraph_format.space_after = Pt(2)
    r = cap.add_run(title_text)
    _set_run_font(r, size_pt=TABLE_SIZE, bold=True)

    tbl = doc.add_table(rows=n_rows, cols=n_cols)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    _set_table_borders(tbl, color="6B7280", sz="4")

    # ── Column widths ────────────────────────────────────────────────────────
    TASK_W  = Inches(2.60)
    WEEK_W  = Inches(0.235)
    tbl.columns[0].width = TASK_W
    for c in range(1, n_cols):
        tbl.columns[c].width = WEEK_W

    # ── Row 0: task-name header (left) + month labels (merged across 4 cols) ──
    h0 = tbl.rows[0]
    h1 = tbl.rows[1]

    # Left corner cell spans rows 0-1
    corner = h0.cells[0].merge(h1.cells[0])
    corner.width = TASK_W
    _set_cell_fill(corner, "1E3A8A")
    _set_cell_margins(corner, top=60, bottom=60, left=80, right=80)
    _set_cell_vertical_align(corner, "center")
    p = corner.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run("กิจกรรม / แผนงาน")
    _set_run_font(r, size_pt=TABLE_SIZE, bold=True, color_rgb=(255, 255, 255))

    # Month + week header
    week_offset = 1
    for m_name, _, _ in months:
        # merge 4 week columns for month name
        mc = h0.cells[week_offset].merge(h0.cells[week_offset + 3])
        _set_cell_fill(mc, "2D5FA0")
        _set_cell_margins(mc, top=60, bottom=60, left=20, right=20)
        _set_cell_vertical_align(mc, "center")
        p = mc.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(m_name)
        _set_run_font(r, size_pt=TABLE_SIZE, bold=True, color_rgb=(255, 255, 255))

        # Week numbers
        for w in range(4):
            wc = h1.cells[week_offset + w]
            wc.width = WEEK_W
            _set_cell_fill(wc, "DBEAFE")
            _set_cell_margins(wc, top=40, bottom=40, left=4, right=4)
            _set_cell_vertical_align(wc, "center")
            wp = wc.paragraphs[0]
            wp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            wp.paragraph_format.space_after = Pt(0)
            wr = wp.add_run(str(w + 1))
            _set_run_font(wr, size_pt=11, bold=True, color_rgb=(30, 58, 138))

        week_offset += 4

    # ── Task rows ─────────────────────────────────────────────────────────────
    for t_idx, (t_name, w_start, w_end) in enumerate(tasks):
        row_a = tbl.rows[2 + t_idx * 2]     # task name row
        row_b = tbl.rows[2 + t_idx * 2 + 1] # gantt bar row
        stripe = "F8FAFC" if t_idx % 2 == 0 else "EFF6FF"

        # Task label: spans both rows
        label_cell = row_a.cells[0].merge(row_b.cells[0])
        label_cell.width = TASK_W
        _set_cell_fill(label_cell, stripe)
        _set_cell_margins(label_cell, top=50, bottom=50, left=80, right=40)
        _set_cell_vertical_align(label_cell, "center")
        lp = label_cell.paragraphs[0]
        lp.paragraph_format.space_after = Pt(0)
        lp.paragraph_format.line_spacing = 1.1
        lr = lp.add_run(t_name)
        _set_run_font(lr, size_pt=TABLE_SIZE, bold=False)

        # Week cells
        for c in range(1, n_cols):
            w_num = c - 1  # 0-indexed week
            ca = row_a.cells[c]
            cb = row_b.cells[c]
            ca.width = WEEK_W
            cb.width = WEEK_W

            if w_start <= w_num <= w_end:
                # Active bar: full navy fill, no border between top/bottom
                _set_cell_fill(ca, BAR_COLOR)
                _set_cell_fill(cb, BAR_COLOR)
            else:
                _set_cell_fill(ca, stripe)
                _set_cell_fill(cb, "E2E8F0" if t_idx % 2 == 0 else "DBEAFE")

            _set_cell_margins(ca, top=4, bottom=0, left=2, right=2)
            _set_cell_margins(cb, top=0, bottom=4, left=2, right=2)
            ca.paragraphs[0].paragraph_format.space_after = Pt(0)
            cb.paragraphs[0].paragraph_format.space_after = Pt(0)

    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(8)
    return tbl


# ─────────────────────────────────────────────────────────────────────────────
# MAIN DOCUMENT BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def build_proposal():
    doc = docx.Document()

    for s in doc.sections:
        s.top_margin    = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin   = Inches(1.0)
        s.right_margin  = Inches(1.0)
        s.page_width    = Inches(8.27)
        s.page_height   = Inches(11.69)

    # ══════════════════════════════════════════════════════════════════════════
    # หน้าปก
    # ══════════════════════════════════════════════════════════════════════════
    COVER = [
        ("รายงานเสนออนุมัติโครงงานวิศวกรรม",                                          Pt(24)),
        ("",                                                                             Pt(6)),
        ("ระบบสกัดและประมาณราคาข้อมูลโครงสร้างเหล็ก",                                 Pt(4)),
        ("จากแบบแปลนดิจิทัลด้วยปัญญาประดิษฐ์เชิงทัศน์มัลติโมดอล",                  Pt(4)),
        ("(Multimodal Vision LLM-Driven Steel Member Extraction",                       Pt(4)),
        ("and Automated Bill of Quantities Generation",                                 Pt(4)),
        ("from Structural CAD Drawings)",                                               Pt(36)),
        ("เสนอต่อ",                                                                     Pt(6)),
        ("หัวหน้าภาควิชาวิศวกรรมคอมพิวเตอร์",                                        Pt(4)),
        ("คณะวิศวกรรมศาสตร์",                                                          Pt(4)),
        ("มหาวิทยาลัยเกษตรศาสตร์",                                                    Pt(36)),
        ("เสนอโดย",                                                                     Pt(6)),
        ("นายจิรายุ  ประสพสุขโชคมณี       รหัสนักศึกษา  6610501475",                   Pt(36)),
        ("อาจารย์ที่ปรึกษา",                                                           Pt(6)),
        ("รศ.ดร.กิจพัฒน์  ภู่วรวรรณ",                                                  Pt(36)),
        ("ภาควิชาวิศวกรรมคอมพิวเตอร์  คณะวิศวกรรมศาสตร์",                            Pt(4)),
        ("มหาวิทยาลัยเกษตรศาสตร์",                                                    Pt(24)),
        ("วันที่เริ่มโครงงาน  1  กรกฎาคม  2568",                                       Pt(4)),
        ("ระยะเวลา  1  ปี",                                                             Pt(0)),
    ]
    for text, sp_after in COVER:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = sp_after
        p.paragraph_format.line_spacing = 1.15
        if text:
            r = p.add_run(text)
            _set_run_font(r, size_pt=20)

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════════
    # หัวหน้าเนื้อหา
    # ══════════════════════════════════════════════════════════════════════════
    p_hdr = doc.add_paragraph()
    p_hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_hdr.paragraph_format.space_after = Pt(12)
    r = p_hdr.add_run("ข้อเสนอโครงงาน (Project Proposal)")
    _set_run_font(r, size_pt=20, bold=True)

    # ══════════════════════════════════════════════════════════════════════════
    # 1. ความเป็นมาของโครงงาน
    # ══════════════════════════════════════════════════════════════════════════
    add_p(doc, "1. ความเป็นมาของโครงงาน", bold=True, size_pt=BODY_SIZE,
          space_before=6, space_after=4)

    add_p(doc, (
        "ในอุตสาหกรรมสถาปัตยกรรม วิศวกรรม และการก่อสร้าง (Architecture, Engineering, and "
        "Construction: AEC) ขั้นตอนการถอดแบบและประมาณราคาปริมาณงาน (Quantity Takeoff) เพื่อ"
        "จัดทำบัญชีแสดงปริมาณวัสดุและราคา (Bill of Quantities: BOQ) ของโครงสร้างเหล็กรูปพรรณ "
        "(Structural Steel) ถือเป็นภารกิจสำคัญที่ส่งผลโดยตรงต่อความแม่นยำของงบประมาณการ"
        "จัดซื้อจัดจ้างและความปลอดภัยของโครงสร้างอาคาร"
    ), indent=0.5, space_after=3)

    add_p(doc, (
        "อย่างไรก็ตาม ในทางปฏิบัติปัจจุบัน วิศวกรและผู้ประมาณราคายังคงต้องอ่านแบบแปลน"
        "วิศวกรรมโครงสร้างจากไฟล์ดิจิทัล (CAD/PDF) ทีละแผ่นด้วยตนเอง โดยต้องตรวจนับและ"
        "คัดลอกข้อมูลเบอร์ชิ้นส่วน (Member ID) ขนาดหน้าตัดเหล็ก (Section) ความยาว (Length) "
        "และจำนวน (Quantity) จากตารางรายการชิ้นส่วน (Member Schedules) และแปลนโครงสร้าง "
        "(Framing Plans) เข้าสู่ตารางคำนวณสเปรดชีต กระบวนการนี้ก่อให้เกิดปัญหาสำคัญ 3 ประการ"
    ), indent=0.5, space_after=3)

    add_mixed(doc, [
        ("1) ปัญหาด้านระยะเวลาและทรัพยากรบุคคล (Time-Consuming):  ", True, False, BODY_SIZE),
        ("แบบแปลนอาคารขนาดกลางถึงใหญ่มีตารางรายการชิ้นส่วนหลายสิบหน้า ส่งผลให้ต้องใช้เวลา"
         "ในการตรวจนับนานหลายวันถึงหลายสัปดาห์ เกิดคอขวดในกระบวนการเสนอราคาประมูล", False, False, BODY_SIZE),
    ], indent=0.5, space_after=3)

    add_mixed(doc, [
        ("2) ปัญหาความผิดพลาดจากมนุษย์ (Human Error):  ", True, False, BODY_SIZE),
        ("การคีย์ข้อมูลสเปกหน้าตัดที่มีความซับซ้อน (เช่น H-300x150x6.5x9) หรือการนับซ้ำซ้อน "
         "ส่งผลต่องบประมาณจัดซื้อเหล็กที่คลาดเคลื่อนอย่างมีนัยสำคัญ", False, False, BODY_SIZE),
    ], indent=0.5, space_after=3)

    add_mixed(doc, [
        ("3) ข้อจำกัดของ OCR แบบดั้งเดิม (Traditional OCR Limitations):  ", True, False, BODY_SIZE),
        ("ระบบ OCR ทั่วไป (เช่น Tesseract) ไม่สามารถเข้าใจบริบทเชิงมิติ ความสัมพันธ์ระหว่าง"
         "ตารางกับแปลน หรือสัญลักษณ์เส้นบอกขนาด ทำให้ไม่สามารถนำมาใช้สกัดข้อมูลแบบแปลน "
         "CAD โครงสร้างได้จริง", False, False, BODY_SIZE),
    ], indent=0.5, space_after=3)

    add_p(doc, (
        "ด้วยเหตุนี้ โครงงานจึงนำเสนอการประยุกต์ใช้แบบจำลองภาษาขนาดใหญ่เชิงทัศน์มัลติโมดอล "
        "(Multimodal Vision LLM) อย่าง Google Gemini Vision ซึ่งสามารถทำความเข้าใจทั้งภาพ "
        "ตัวอักษร และโครงสร้างตารางในแบบแปลนทางเทคนิคพร้อมกัน เข้ามาสกัดข้อมูลชิ้นส่วนโครงสร้าง"
        "เหล็กโดยอัตโนมัติ ควบคู่กับระบบคำนวณน้ำหนักเหล็กตามมาตรฐาน JIS/AISC และเว็บแอป"
        "พลิเคชันเชิงปฏิสัมพันธ์สำหรับตรวจสอบและส่งออกข้อมูล BOQ"
    ), indent=0.5, space_after=6)

    # ══════════════════════════════════════════════════════════════════════════
    # 2. วัตถุประสงค์ของโครงงาน
    # ══════════════════════════════════════════════════════════════════════════
    add_p(doc, "2. วัตถุประสงค์ของโครงงาน", bold=True, size_pt=BODY_SIZE,
          space_before=6, space_after=4)
    add_p(doc, "การพัฒนาโครงงานนี้มีวัตถุประสงค์เพื่อนำไปใช้ประโยชน์ในงานวิศวกรรมโครงสร้างและการประมาณราคา ดังนี้",
          indent=0.5, space_after=3)

    for obj in [
        "2.1 เพื่อพัฒนาระบบสกัดข้อมูลชิ้นส่วนโครงสร้างเหล็ก (Member ID, Section, Length, Quantity) "
        "จากไฟล์แบบแปลนดิจิทัล (CAD-exported PDF) โดยอัตโนมัติด้วยแบบจำลองภาษาเชิงทัศน์มัลติโมดอล "
        "เพื่อลดระยะเวลาและขั้นตอนการทำงานของผู้ประมาณราคา",

        "2.2 เพื่อพัฒนาระบบคำนวณน้ำหนักต่อเมตร (Unit Weight: kg/m) และน้ำหนักรวมของโครงสร้างเหล็ก"
        "รูปพรรณตามมาตรฐาน JIS และ AISC ช่วยให้การจัดทำ BOQ มีความถูกต้องแม่นยำตามมาตรฐานวิศวกรรม",

        "2.3 เพื่อพัฒนาเว็บแอปพลิเคชันเชิงปฏิสัมพันธ์ (Interactive Web Application) ที่มีระบบพรีวิว"
        "แบบแปลน ตารางตรวจสอบและแก้ไขข้อมูลแบบเรียลไทม์ (Inline Table Editing) และระบบส่งออกข้อมูล"
        "เป็นไฟล์ Excel (.xlsx) เพื่อให้ฝ่ายจัดซื้อนำไปใช้งานต่อได้ทันที",

        "2.4 เพื่อประเมินความถูกต้องแม่นยำ (Precision, Recall, F1-Score, Dimension Accuracy) และ"
        "ประสิทธิภาพด้านเวลาประมวลผล (Processing Latency) เปรียบเทียบกับการถอดแบบด้วยวิศวกร"
        "ผู้เชี่ยวชาญ (Manual Takeoff)",
    ]:
        add_p(doc, obj, indent=0.5, space_after=3)

    # ══════════════════════════════════════════════════════════════════════════
    # 3. ขอบเขตของโครงงาน
    # ══════════════════════════════════════════════════════════════════════════
    add_p(doc, "3. ขอบเขตของโครงงาน", bold=True, size_pt=BODY_SIZE,
          space_before=6, space_after=4)
    add_p(doc, "การดำเนินงานแบ่งออกเป็น 2 ภาคการศึกษา ดังนี้", indent=0.5, space_after=3)

    # 3.1
    add_p(doc, "3.1 ขอบเขตของโครงงาน 1 (การวิจัย ศึกษา และพัฒนาระบบสกัดข้อมูลต้นแบบ)",
          bold=True, indent=0.5, space_after=3)

    add_p(doc, "3.1.1 ขอบเขตด้านข้อมูลนำเข้าและการเตรียมข้อมูล (Input & Preprocessing)",
          indent=0.75, space_after=2)
    for item in [
        "1) รองรับไฟล์แบบแปลนโครงสร้างเหล็กรูปแบบ PDF ที่ส่งออกจากโปรแกรม CAD (Vector-based PDF)",
        "2) ทำการแปลงหน้าแบบแปลนที่เลือกเป็นภาพความละเอียดสูง (200–300 DPI) ด้วยไลบรารี PyMuPDF",
    ]:
        add_p(doc, item, indent=1.0, space_after=2)

    add_p(doc, "3.1.2 ขอบเขตด้านการสกัดข้อมูลชิ้นส่วนโครงสร้าง (AI Vision Extraction)",
          indent=0.75, space_after=2)
    for item in [
        "1) ครอบคลุมการอ่านแบบแปลน 2 ประเภท ได้แก่ ตารางรายการชิ้นส่วน (Member Schedules) และแปลนโครงสร้าง (Framing Plans)",
        "2) สกัดชิ้นส่วนโครงสร้างเหล็กหลัก ได้แก่ เสา (Columns) คาน (Beams) คานคอดิน (Grade Beams) แป (Purlins) และค้ำยัน (Bracing)",
        "3) สกัดคุณลักษณะ 5 ตัวแปร ได้แก่ member_id, section, length_mm, quantity, notes",
        "4) ใช้เทคนิค Defensive JSON Prompting ร่วมกับ Zero-temperature เพื่อให้ผลลัพธ์เป็น JSON Array ที่แน่นอน",
    ]:
        add_p(doc, item, indent=1.0, space_after=2)

    add_p(doc, "3.1.3 ขอบเขตด้านการคำนวณและประเมินผลต้นแบบ (MVP Engine & Benchmarking)",
          indent=0.75, space_after=2)
    for item in [
        "1) คำนวณน้ำหนักต่อเมตรอ้างอิงสูตรพื้นที่หน้าตัดเรขาคณิต (ความหนาแน่นเหล็ก 7,850 kg/m³) และตารางมาตรฐาน JIS / AISC",
        "2) พัฒนาชุดข้อมูลทดสอบสังเคราะห์ (Synthetic Dataset) 3 หน้า พร้อมไฟล์เฉลย Ground Truth และสคริปต์วัด Precision / Recall / F1-Score",
    ]:
        add_p(doc, item, indent=1.0, space_after=2)

    # 3.2
    add_p(doc,
          "3.2 ขอบเขตของโครงงาน 2 (การพัฒนาเว็บแอปพลิเคชัน การทดสอบกับแบบแปลนจริง และการปรับปรุงประสิทธิภาพ)",
          bold=True, indent=0.5, space_after=3)

    add_p(doc, "3.2.1 ขอบเขตด้านระบบส่วนติดต่อผู้ใช้งาน (Web Application Interface)",
          indent=0.75, space_after=2)
    for item in [
        "1) พัฒนาเว็บแอปพลิเคชันด้วย Next.js และ Tailwind CSS รองรับการอัปโหลดไฟล์ PDF และเลือกหน้าที่ต้องการประมวลผล",
        "2) พัฒนาระบบ Interactive Table รองรับการแก้ไขข้อมูลแบบ Inline Editing พร้อมระบบสรุปผลรวมน้ำหนักอัตโนมัติ",
        "3) ระบบส่งออกข้อมูล BOQ เป็นไฟล์ Excel (.xlsx) แยก Sheet BOQ และ Summary และไฟล์ CSV",
    ]:
        add_p(doc, item, indent=1.0, space_after=2)

    add_p(doc, "3.2.2 ขอบเขตด้านการประเมินผลและทดสอบประสิทธิภาพเชิงลึก",
          indent=0.75, space_after=2)
    for item in [
        "1) ทดสอบระบบกับแบบแปลนก่อสร้างจริงจากโครงการภายนอก 5–10 โครงการ เพื่อวัดความแม่นยำในสภาวะใช้งานจริง",
        "2) บันทึกและวิเคราะห์ค่าความหน่วงในการประมวลผล (Latency) และข้อผิดพลาดที่เกิดขึ้นใน Research Logs",
        "3) ประเมินระยะเวลาที่ประหยัดได้เปรียบเทียบกับการถอดแบบด้วยวิศวกรผู้เชี่ยวชาญ",
    ]:
        add_p(doc, item, indent=1.0, space_after=2)

    # 3.3
    add_p(doc, "3.3 ข้อจำกัดและสิ่งที่อยู่นอกเหนือขอบเขต (Delimitations & Out-of-Scope)",
          bold=True, indent=0.5, space_after=3)
    for item in [
        "1) ไม่ครอบคลุมแบบแปลนประเภทภาพสแกนจากกระดาษเก่า ภาพถ่ายลายมือ หรือความคมชัดต่ำมาก",
        "2) ไม่ครอบคลุมการนับสลักเกลียว (Bolts) แผ่นเหล็กประกับรอยต่อ (Gusset Plates) และแนวเชื่อม (Welds)",
        "3) การคำนวณน้ำหนักเหล็กใช้สำหรับการประมาณราคา BOQ มิใช่ค่าสำหรับการสั่งตัดในโรงงาน (Fabrication Detailing)",
    ]:
        add_p(doc, item, indent=1.0, space_after=2)
    add_p(doc, "", space_after=4)  # spacer

    # ══════════════════════════════════════════════════════════════════════════
    # 4. แผนการดำเนินงาน – Gantt Charts
    # ══════════════════════════════════════════════════════════════════════════
    add_p(doc, "4. แผนการดำเนินงาน", bold=True, size_pt=BODY_SIZE,
          space_before=6, space_after=4)
    add_p(doc, (
        "แผนการดำเนินงานของโครงงานมีระยะเวลาทั้งสิ้น 1 ปี แบ่งเป็น 2 ภาคการศึกษา "
        "ได้แก่ โครงงาน 1 (ภาคต้น: มิถุนายน – กันยายน 2568) และโครงงาน 2 "
        "(ภาคปลาย: พฤศจิกายน 2568 – กุมภาพันธ์ 2569)"
    ), indent=0.5, space_after=6)

    # ─── ตารางที่ 1 ───────────────────────────────────────────────────────────
    months_1 = [
        ("มิถุนายน 2568",     0,  3),
        ("กรกฎาคม 2568",     4,  7),
        ("สิงหาคม 2568",     8, 11),
        ("กันยายน 2568",    12, 15),
    ]
    tasks_1 = [
        # (label, first_active_week_0idx, last_active_week_0idx)
        ("1. เสนอหัวข้อโครงงานและศึกษาทฤษฎีที่เกี่ยวข้อง",          0,  3),
        ("2. รวบรวม Dataset แบบแปลน CAD และออกแบบสถาปัตยกรรมระบบ",  2,  7),
        ("3. พัฒนาระบบต้นแบบ AI Backend และปรับแต่ง Prompting",       6, 10),
        ("4. พัฒนาระบบคำนวณน้ำหนักหน้าตัดเหล็ก JIS/AISC",            9, 12),
        ("5. ทดสอบ Benchmark กับ Ground Truth และจัดทำรายงาน",       12, 15),
    ]
    build_gantt(doc, "ตารางที่ 1  ตารางการดำเนินงานโครงงาน 1", months_1, tasks_1)

    # ─── ตารางที่ 2 ───────────────────────────────────────────────────────────
    months_2 = [
        ("พฤศจิกายน 2568",   0,  3),
        ("ธันวาคม 2568",      4,  7),
        ("มกราคม 2569",       8, 11),
        ("กุมภาพันธ์ 2569",  12, 15),
    ]
    tasks_2 = [
        ("1. ออกแบบสถาปัตยกรรม Web Application และ UI/UX",             0,  3),
        ("2. พัฒนาระบบ Inline Editable BOQ Table บน Next.js",          3,  7),
        ("3. เชื่อมโยง Live Gemini API และระบบ Export Excel/CSV",       6, 10),
        ("4. ทดสอบความถูกต้องกับแบบแปลนจริง 5–10 โครงการ",            9, 13),
        ("5. สรุปผลการวิจัยและจัดทำรูปเล่มปริญญานิพนธ์",             12, 15),
    ]
    build_gantt(doc, "ตารางที่ 2  ตารางการดำเนินงานโครงงาน 2", months_2, tasks_2)

    # ══════════════════════════════════════════════════════════════════════════
    # 5. เอกสารอ้างอิง
    # ══════════════════════════════════════════════════════════════════════════
    add_p(doc, "5. เอกสารอ้างอิง", bold=True, size_pt=BODY_SIZE,
          space_before=6, space_after=4)

    refs = [
        ("[1]", "Google DeepMind, \"Gemini: A Family of Highly Capable Multimodal Models,\" "
                "Technical Report, arXiv:2312.11805, 2023."),
        ("[2]", "American Institute of Steel Construction (AISC), \"Steel Construction Manual,\" "
                "15th Edition, Chicago, IL, 2017."),
        ("[3]", "Japanese Industrial Standards Committee (JISC), \"JIS G 3101: Rolled steels for "
                "general structure,\" Japanese Standards Association, 2020."),
        ("[4]", "C. Eastman, P. Teicholz, R. Sacks, and K. Liston, \"BIM Handbook: A Guide to "
                "Building Information Modeling,\" 3rd Edition, John Wiley & Sons, 2018."),
        ("[5]", "PyMuPDF Development Team, \"PyMuPDF: High-performance Python bindings for "
                "MuPDF,\" [Online]. Available: https://github.com/pymupdf/PyMuPDF, 2024."),
        ("[6]", "Next.js Team, \"Next.js App Router Documentation and Server Actions,\" Vercel "
                "Inc., [Online]. Available: https://nextjs.org/docs, 2026."),
    ]
    for num, content in refs:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent    = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.5)
        p.paragraph_format.space_before   = Pt(0)
        p.paragraph_format.space_after    = Pt(3)
        p.paragraph_format.line_spacing   = 1.15
        r_n = p.add_run(num + "  ")
        _set_run_font(r_n, size_pt=BODY_SIZE, bold=True)
        r_c = p.add_run(content)
        _set_run_font(r_c, size_pt=BODY_SIZE)

    # ══════════════════════════════════════════════════════════════════════════
    # 6. สถาบันหรือหน่วยงานที่จะให้การสนับสนุน
    # ══════════════════════════════════════════════════════════════════════════
    add_p(doc, "6. สถาบันหรือหน่วยงานที่จะให้การสนับสนุน และข้อกำหนดของผู้ให้การสนับสนุน",
          bold=True, size_pt=BODY_SIZE, space_before=6, space_after=4)

    add_mixed(doc, [
        ("6.1 หน่วยงานที่ให้การสนับสนุนและสถานที่ดำเนินงาน:  ", True, False, BODY_SIZE),
        ("ภาควิชาวิศวกรรมคอมพิวเตอร์ คณะวิศวกรรมศาสตร์ มหาวิทยาลัยเกษตรศาสตร์ ให้การสนับสนุน"
         "ด้านสถานที่ ห้องปฏิบัติการคอมพิวเตอร์ และเครือข่ายอินเทอร์เน็ตสำหรับการพัฒนาและทดสอบ", False, False, BODY_SIZE),
    ], indent=0.5, space_after=3)

    add_mixed(doc, [
        ("6.2 หน่วยงานที่ให้ข้อมูลแบบแปลนทดสอบ:  ", True, False, BODY_SIZE),
        ("ขอความอนุเคราะห์ตัวอย่างแบบแปลนโครงสร้างเหล็กจริงจากบริษัทผู้ออกแบบและรับเหมา"
         "ก่อสร้าง เพื่อใช้เป็นชุดข้อมูลทดสอบประสิทธิภาพในสภาวะการทำงานจริง", False, False, BODY_SIZE),
    ], indent=0.5, space_after=3)

    add_mixed(doc, [
        ("6.3 เครื่องมือ ทรัพยากรคลาวด์ และข้อกำหนดของผู้ให้บริการ:  ", True, False, BODY_SIZE),
        ("การใช้งาน Google Gemini Multimodal Vision API ภายใต้ข้อกำหนดการให้บริการ (Terms of Service) "
         "โดยข้อมูลแบบแปลนที่ส่งผ่าน API ใช้เพื่อการวิจัยเท่านั้น ไม่มีการจัดเก็บข้อมูลที่เป็นความลับ", False, False, BODY_SIZE),
    ], indent=0.5, space_after=6)

    # ══════════════════════════════════════════════════════════════════════════
    # 7. ภาคผนวก
    # ══════════════════════════════════════════════════════════════════════════
    add_p(doc, "7. ภาคผนวก", bold=True, size_pt=BODY_SIZE, space_before=6, space_after=4)

    # ── ภาคผนวก ก: Pipeline Flowchart ────────────────────────────────────────
    add_p(doc, "ภาคผนวก ก  แผนผังลำดับขั้นตอนการทำงานของระบบ (System Workflow Architecture)",
          bold=True, indent=0.5, space_after=2)

    # Build a clean single-column table for the flowchart steps
    flow_steps = [
        ("1. นำเข้าไฟล์",   "อัปโหลดไฟล์ CAD Drawing (Vector PDF) ผ่านหน้าเว็บ",                                "DBEAFE", "1E3A8A"),
        ("2. เรนเดอร์ภาพ",  "PyMuPDF แปลงหน้าที่เลือกเป็นภาพ PNG ความละเอียด 200–300 DPI",                     "E0F2FE", "0369A1"),
        ("3. วิเคราะห์ AI", "Gemini Vision รับภาพ + System Prompt → ส่งคืน JSON Array ชิ้นส่วนโครงสร้าง",    "EDE9FE", "5B21B6"),
        ("4. ตรวจสอบ JSON", "Defensive Validator ตรวจโครงสร้าง แก้ชนิดข้อมูล (Type Coercion)",                 "FCE7F3", "9D174D"),
        ("5. คำนวณน้ำหนัก", "Steel Weight Engine เปรียบเทียบ JIS/AISC คำนวณ Unit Weight + Total Weight",         "D1FAE5", "065F46"),
        ("6. ตรวจสอบ",      "Inline Table Editor – วิศวกรตรวจและแก้ไขข้อมูลแบบ Real-time",                     "FEF3C7", "92400E"),
        ("7. ส่งออก",        "Export Excel (.xlsx) แยก Sheet BOQ + Summary / CSV",                               "F0FDF4", "166534"),
    ]
    ft = doc.add_table(rows=len(flow_steps), cols=2)
    ft.alignment = WD_TABLE_ALIGNMENT.CENTER
    ft.autofit = False
    _set_table_borders(ft, color="6B7280", sz="4")
    ft.columns[0].width = Inches(1.4)
    ft.columns[1].width = Inches(5.1)

    for i, (step_label, step_desc, bg_hex, fg_hex) in enumerate(flow_steps):
        fg = tuple(int(fg_hex[j:j+2], 16) for j in (0, 2, 4))
        bg_lt = bg_hex
        _table_body_cell(ft.rows[i].cells[0], step_label, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
                         size_pt=TABLE_SIZE, bg=bg_lt, top=80, bottom=80, left=60, right=60)
        _table_body_cell(ft.rows[i].cells[1], step_desc, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT,
                         size_pt=TABLE_SIZE, bg="FFFFFF", top=80, bottom=80, left=80, right=60)
        ft.rows[i].cells[0].width = Inches(1.4)
        ft.rows[i].cells[1].width = Inches(5.1)
        # apply fg color to step label
        run = ft.rows[i].cells[0].paragraphs[0].runs[0]
        run.font.color.rgb = RGBColor(*fg)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ── ภาคผนวก ข: System Prompt ─────────────────────────────────────────────
    add_p(doc, "ภาคผนวก ข  ข้อความคำสั่งควบคุม (Defensive Extraction System Prompt)",
          bold=True, indent=0.5, space_after=2)

    prompt_text = (
        'You are reading a structural steel drawing (framing plan or member schedule).\n'
        'Extract every distinct steel member you can identify. For each member, return:\n'
        '  - member_id  : the label/tag shown on the drawing (e.g. B1, C2, GB-01)\n'
        '  - section    : the section designation (e.g. H-300x300x10x15, W12x26)\n'
        '  - length_mm  : member length in millimeters if shown or derivable from dimensions\n'
        '  - quantity   : number of instances of this member type\n'
        '  - notes      : anything ambiguous, illegible, or inferred rather than directly read\n\n'
        'Return ONLY a JSON array of objects with these exact keys.\n'
        'No prose, no markdown fences, no explanation.\n'
        'If a value cannot be determined, use null for that field and explain briefly in notes.'
    )
    prompt_tbl = doc.add_table(rows=1, cols=1)
    prompt_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    prompt_tbl.autofit = False
    _set_table_borders(prompt_tbl, color="94A3B8", sz="4")
    prompt_tbl.columns[0].width = Inches(6.5)
    pc = prompt_tbl.rows[0].cells[0]
    _set_cell_fill(pc, "1E293B")
    _set_cell_margins(pc, top=100, bottom=100, left=120, right=120)
    pp = pc.paragraphs[0]
    pp.paragraph_format.space_after = Pt(0)
    pp.paragraph_format.line_spacing = 1.2
    pr = pp.add_run(prompt_text)
    _set_run_font(pr, name="Courier New", size_pt=11, color_rgb=(203, 213, 225))

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ── ภาคผนวก ค: BOQ Output Table Schema ───────────────────────────────────
    add_p(doc, "ภาคผนวก ค  ตัวอย่างโครงสร้างตารางผลลัพธ์ BOQ (Output Table Schema)",
          bold=True, indent=0.5, space_after=2)

    boq_headers = ["Member ID", "Section", "Length (mm)", "Qty", "Unit Wt\n(kg/m)", "Total Wt\n(kg)"]
    boq_widths  = [Inches(1.0), Inches(1.8), Inches(1.0), Inches(0.6), Inches(1.0), Inches(1.1)]
    boq_rows = [
        ("B1",           "H-300x150x6.5x9",  "6,000",   "8",  "36.7",   "1,761.6"),
        ("B2",           "H-350x175x7x11",   "7,000",   "4",  "49.6",   "1,388.8"),
        ("C1",           "H-300x300x10x15",  "4,500",   "6",  "94.0",   "2,538.0"),
        ("P1",           "W12x26",           "6,000",  "12",  "38.7",   "2,786.4"),
        ("รวมทั้งสิ้น",  "4 รายการ",          "–",      "30",  "–",      "8,474.8"),
    ]

    bt = doc.add_table(rows=1 + len(boq_rows), cols=len(boq_headers))
    bt.alignment = WD_TABLE_ALIGNMENT.CENTER
    bt.autofit = False
    _set_table_borders(bt, color="475569", sz="4")

    for i, (h, w) in enumerate(zip(boq_headers, boq_widths)):
        bt.columns[i].width = w
        _table_header_cell(bt.rows[0].cells[i], h, bg="1E3A8A", top=70, bottom=70)

    for r_idx, row_data in enumerate(boq_rows, start=1):
        is_total = (r_idx == len(boq_rows))
        for c_idx, val in enumerate(row_data):
            cell = bt.rows[r_idx].cells[c_idx]
            cell.width = boq_widths[c_idx]
            bg = "F1F5F9" if is_total else ("F8FAFC" if r_idx % 2 == 1 else "FFFFFF")
            _table_body_cell(cell, val,
                             bold=is_total or c_idx == 0,
                             align=WD_ALIGN_PARAGRAPH.CENTER,
                             size_pt=TABLE_SIZE, bg=bg,
                             top=60, bottom=60, left=40, right=40)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    return doc


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    doc = build_proposal()
    import time
    ts = time.strftime("%H%M%S")
    out = rf"c:\Users\Jirayu\OneDrive\Steel-Tech-Project\Steel-Tech-Project\Project_Proposal_v{ts}.docx"
    doc.save(out)
    print("Saved OK ->", out)


