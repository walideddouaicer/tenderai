from __future__ import annotations

import re
from transformers import AutoTokenizer

from services.embedder import MODEL_NAME
from storage.vector_store import Chunk

_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
_tokenizer: AutoTokenizer | None = None


def _get_tokenizer() -> AutoTokenizer:
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    return _tokenizer


def count_tokens(text: str) -> int:
    return len(_get_tokenizer().encode(text, add_special_tokens=False))


def chunk_pages(
    pages: list[dict],
    tender_id: str,
    document_type: str,
    language: str,
    ocr_page_numbers: list[int],
    max_tokens: int = 508,
    overlap_tokens: int = 64,
) -> list[Chunk]:
    """
    Split per-page markdown texts into Chunks.

    Primary boundary: markdown section headers (^#{1,6}).
    Fallback: token-level sliding window for sections exceeding max_tokens.
    Overlap is within-section only — no cross-section overlap, which would
    make section_header ambiguous on the overlapping tokens.
    """
    ocr_pages_set = set(ocr_page_numbers)
    chunks: list[Chunk] = []
    current_header = ""
    chunk_idx = 0

    for page_dict in pages:
        page_num: int = page_dict["page"]
        page_text: str = page_dict["text"]
        ocr_fallback = page_num in ocr_pages_set

        sections = _parse_sections(page_text, current_header)

        for section in sections:
            current_header = section["header"]
            text = section["text"].strip()
            if not text:
                continue

            if count_tokens(text) <= max_tokens:
                chunks.append(
                    Chunk(
                        id=f"{tender_id}_{chunk_idx}",
                        text=text,
                        tender_id=tender_id,
                        page_number=page_num,
                        section_header=current_header,
                        document_type=document_type,
                        language=language,
                        ocr_fallback=ocr_fallback,
                    )
                )
                chunk_idx += 1
            else:
                sub = _split_long_section(
                    text=text,
                    header=current_header,
                    page=page_num,
                    tender_id=tender_id,
                    document_type=document_type,
                    language=language,
                    ocr_fallback=ocr_fallback,
                    max_tokens=max_tokens,
                    overlap_tokens=overlap_tokens,
                    start_idx=chunk_idx,
                )
                chunks.extend(sub)
                chunk_idx += len(sub)

    return chunks


def _parse_sections(page_text: str, current_header: str) -> list[dict]:
    """
    Split page_text into sections at markdown headings.
    Text before the first heading inherits current_header from prior pages.
    Returns list of {"header": str, "text": str}.
    """
    sections: list[dict] = []
    last_pos = 0
    last_header = current_header

    for match in _HEADING_RE.finditer(page_text):
        pre_text = page_text[last_pos : match.start()]
        if pre_text.strip():
            sections.append({"header": last_header, "text": pre_text})
        last_header = match.group(1).strip()
        last_pos = match.end()

    tail = page_text[last_pos:]
    if tail.strip():
        sections.append({"header": last_header, "text": tail})

    return sections


def _split_long_section(
    text: str,
    header: str,
    page: int,
    tender_id: str,
    document_type: str,
    language: str,
    ocr_fallback: bool,
    max_tokens: int,
    overlap_tokens: int,
    start_idx: int,
) -> list[Chunk]:
    """
    Sliding window over token positions.
    Slices the ORIGINAL text using character offsets from the fast tokenizer —
    preserves verbatim text; never reconstructs text from token IDs.
    """
    tok = _get_tokenizer()
    encoding = tok(text, return_offsets_mapping=True, add_special_tokens=False)
    offsets: list[tuple[int, int]] = encoding["offset_mapping"]
    total = len(offsets)

    chunks: list[Chunk] = []
    idx = start_idx
    stride = max(1, max_tokens - overlap_tokens)
    pos = 0

    while pos < total:
        end = min(pos + max_tokens, total)
        start_char = offsets[pos][0]
        end_char = offsets[end - 1][1]
        window_text = text[start_char:end_char].strip()

        if window_text:
            chunks.append(
                Chunk(
                    id=f"{tender_id}_{idx}",
                    text=window_text,
                    tender_id=tender_id,
                    page_number=page,
                    section_header=header,
                    document_type=document_type,
                    language=language,
                    ocr_fallback=ocr_fallback,
                )
            )
            idx += 1

        pos += stride

    return chunks
