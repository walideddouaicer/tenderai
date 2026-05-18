from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class QueryRequest(BaseModel):
    tender_id: str
    question: str
    language: str = "fr"


class Citation(BaseModel):
    page_number: int
    section_header: str
    verbatim_quote: str


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]


@router.post("/query", response_model=QueryResponse)
async def query_document(payload: QueryRequest):
    """
    Retrieve relevant chunks from ChromaDB, synthesize an answer with GPT-4o,
    and return the answer alongside mandatory verbatim citations.
    A response with no retrievable citations must not be returned to the caller.
    """
    raise HTTPException(status_code=501, detail="Not implemented")
