from __future__ import annotations

import fitz  # PyMuPDF — installed as dep of pymupdf4llm
import pymupdf4llm
import pytesseract
from PIL import Image

_SPARSE_THRESHOLD = 50  # chars; pages below this trigger OCR


def extract_pages(pdf_bytes: bytes) -> tuple[list[dict], list[int]]:
    """
    Parse PDF bytes into per-page markdown dicts.

    Returns:
        pages            — list of {"text": str, "page": int} (1-indexed)
        ocr_page_numbers — page numbers where pytesseract OCR was applied

    Raises ValueError with a short key for known failure modes:
        "empty"     — zero-byte input
        "encrypted" — password-protected PDF
        "bad_pdf:…" — fitz could not open the file
        "no_text"   — nothing extractable even after OCR
    """
    if not pdf_bytes:
        raise ValueError("empty")

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"bad_pdf: {exc}") from exc

    if doc.is_encrypted:
        raise ValueError("encrypted")

    pages: list[dict] = []
    ocr_page_numbers: list[int] = []

    for i in range(len(doc)):
        page_num = i + 1
        try:
            text: str = pymupdf4llm.to_markdown(doc, pages=[i])
        except Exception:  # pymupdf4llm raises undocumented types on some page layouts; fitz fallback is safe degradation
            text = doc[i].get_text("text")

        if _is_sparse(text):
            ocr_text = _ocr_page(doc, i)
            if ocr_text.strip():
                text = ocr_text
                ocr_page_numbers.append(page_num)

        pages.append({"text": text, "page": page_num})

    if not any(p["text"].strip() for p in pages):
        raise ValueError("no_text")

    return pages, ocr_page_numbers


def _is_sparse(text: str) -> bool:
    return len(text.strip()) < _SPARSE_THRESHOLD


def _ocr_page(doc: fitz.Document, page_index: int) -> str:
    page = doc[page_index]
    mat = fitz.Matrix(300 / 72, 300 / 72)  # 300 DPI for reliable OCR
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return pytesseract.image_to_string(img, lang="fra+ara+eng")
