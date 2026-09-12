from io import BytesIO

import pytest
from PIL import Image

import pdf_utils as pu


def test_open_pdf_rejects_garbage():
    with pytest.raises(pu.PdfError):
        pu.open_pdf(b"this is not a pdf")


def test_open_pdf_rejects_empty():
    with pytest.raises(pu.PdfError):
        pu.open_pdf(b"")


def test_sample_has_three_pages(sample_pdf_bytes):
    doc = pu.open_pdf(sample_pdf_bytes)
    try:
        assert pu.page_count(doc) == 3
    finally:
        doc.close()


def test_render_page_png_dpi(sample_pdf_bytes):
    doc = pu.open_pdf(sample_pdf_bytes)
    try:
        png = pu.render_page_png(doc, 0, dpi=220)
    finally:
        doc.close()
    assert png[:4] == b"\x89PNG"
    img = Image.open(BytesIO(png))
    # A4 portrait: 595.28 pt wide -> 595.28/72*220 ~= 1819 px
    assert abs(img.width - 1819) <= 3


def test_thumbnail_bounded(sample_pdf_bytes):
    doc = pu.open_pdf(sample_pdf_bytes)
    try:
        png = pu.render_thumbnail_png(doc, 1, max_px=240)
    finally:
        doc.close()
    img = Image.open(BytesIO(png))
    assert max(img.width, img.height) <= 240


def test_render_pages_convenience(sample_pdf_bytes):
    out = pu.render_pages(sample_pdf_bytes, [0, 2], dpi=100)
    assert [i for i, _ in out] == [0, 2]
    assert all(b[:4] == b"\x89PNG" for _, b in out)
