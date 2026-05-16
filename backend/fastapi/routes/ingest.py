from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

router = APIRouter()


class IngestResponse(BaseModel):
    tender_id: str
    chunk_count: int
    ocr_used: bool


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    tender_id: str = Form(...),
    doc_type: str = Form(...),
):
    """
    Accept a PDF, parse it into semantic chunks, embed them, and index in ChromaDB.
    OCR fallback is applied for scanned PDFs with no digital text layer.
    """
    raise HTTPException(status_code=501, detail="Not implemented")
