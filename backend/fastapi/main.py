from fastapi import FastAPI
from routes.ingest import router as ingest_router
from routes.query import router as query_router

app = FastAPI(title="TenderAI — Analyst Service", version="0.1.0")

app.include_router(ingest_router, prefix="/api/rag")
app.include_router(query_router, prefix="/api/rag")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/rag/health")
async def rag_health():
    return {"status": "ok"}
