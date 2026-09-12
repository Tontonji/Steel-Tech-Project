"""PyMuPDF helpers: validate, count pages, rasterize pages and thumbnails."""
from __future__ import annotations

import pymupdf as fitz


class PdfError(Exception):
    pass


def open_pdf(data: bytes) -> "fitz.Document":
    if not data:
        raise PdfError("The uploaded file is empty.")
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        raise PdfError(f"Couldn't read this file as a PDF ({type(e).__name__}).") from e
    if doc.is_encrypted and not doc.authenticate(""):
        doc.close()
        raise PdfError("This PDF is password-protected.")
    if doc.page_count < 1:
        doc.close()
        raise PdfError("This PDF has no pages.")
    return doc


def page_count(doc: "fitz.Document") -> int:
    return int(doc.page_count)


def render_page_png(doc: "fitz.Document", page_index: int, dpi: int = 220) -> bytes:
    page = doc[page_index]
    zoom = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return pix.tobytes("png")


def render_thumbnail_png(doc: "fitz.Document", page_index: int, max_px: int = 240) -> bytes:
    page = doc[page_index]
    rect = page.rect
    scale = max_px / max(rect.width, rect.height)
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    return pix.tobytes("png")


def render_pages(data: bytes, page_indices: list[int], dpi: int = 220) -> list[tuple[int, bytes]]:
    doc = open_pdf(data)
    try:
        return [(i, render_page_png(doc, i, dpi)) for i in page_indices]
    finally:
        doc.close()
