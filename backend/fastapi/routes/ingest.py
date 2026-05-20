from __future__ import annotations

import asyncio

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from services.chunker import chunk_pages
from services.embedder import embed_passages
from services.parser import extract_pages
from storage.vector_store import VectorStoreUnavailable, get_vector_store

router = APIRouter()

_MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MB


class IngestResponse(BaseModel):
    tender_id: str
    chunk_count: int
    ocr_used: bool
    warnings: list[str] = []


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    tender_id: str = Form(...),
    doc_type: str = Form(...),
    language: str = Form(...),
) -> IngestResponse:
    """
    Accept a PDF, parse it into semantic chunks, embed with multilingual-e5-base,
    and index in ChromaDB. Returns 409 if tender_id is already indexed.
    OCR (pytesseract) is applied per-page when digital text density is low.
    """
    # 1. Read file bytes
    pdf_bytes = await file.read()

    # 2. Basic format and size checks
    if not pdf_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")
    if len(pdf_bytes) > _MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 50 MB limit")
    if not pdf_bytes.startswith(b"%PDF"):
        raise HTTPException(status_code=422, detail="File must be a PDF")

    # 3. Parse PDF into per-page markdown (blocking I/O + CPU → thread pool)
    try:
        pages, ocr_page_numbers = await asyncio.to_thread(extract_pages, pdf_bytes)
    except ValueError as exc:
        msg = str(exc)
        if msg == "encrypted":
            raise HTTPException(
                status_code=422,
                detail="PDF is password-protected — submit an unlocked copy",
            )
        if msg == "no_text":
            raise HTTPException(
                status_code=422,
                detail="No text could be extracted from this document",
            )
        # bad_pdf: <original exception message>
        reason = msg.split(": ", 1)[-1] if ": " in msg else msg
        raise HTTPException(status_code=422, detail=f"Could not parse PDF: {reason}")

    # 4–7. Vector store interactions + chunking/embedding.
    # VectorStoreUnavailable is raised by the storage layer for any transport
    # failure — routes never import httpx or any backend-specific exception.
    try:
        vs = get_vector_store()
        if await asyncio.to_thread(vs.tender_exists, tender_id):
            raise HTTPException(
                status_code=409,
                detail=f"tender_id '{tender_id}' is already indexed — re-ingest not permitted",
            )

        # 5. Chunk at section headers; fallback sliding window for long sections
        chunks = await asyncio.to_thread(
            chunk_pages,
            pages,
            tender_id,
            doc_type,
            language,
            ocr_page_numbers,
        )
        if not chunks:
            raise HTTPException(
                status_code=422,
                detail="No text could be extracted from this document",
            )

        # 6. Embed passages (CPU-bound — runs in thread pool via embed_passages)
        embeddings = await embed_passages([c.text for c in chunks])
        for chunk, vec in zip(chunks, embeddings):
            chunk.embedding = vec

        # 7. Index in vector store
        await asyncio.to_thread(vs.add_chunks, chunks)

    except VectorStoreUnavailable:
        raise HTTPException(
            status_code=503,
            detail="Vector store is unavailable — try again shortly",
        )

    # 8. Build warnings for caller
    warnings: list[str] = []
    if ocr_page_numbers:
        pages_str = ", ".join(str(p) for p in ocr_page_numbers)
        warnings.append(
            f"Pages {pages_str}: OCR applied (low text density — results may have lower confidence)"
        )

    return IngestResponse(
        tender_id=tender_id,
        chunk_count=len(chunks),
        ocr_used=bool(ocr_page_numbers),
        warnings=warnings,
    )
