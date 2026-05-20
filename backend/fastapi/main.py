import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from routes.ingest import router as ingest_router
from routes.query import router as query_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up the embedding model at startup so the first ingest request
    # isn't blocked by a ~560 MB model download + load (~2-3 s from cache).
    from services.embedder import get_embedder
    await asyncio.to_thread(get_embedder)
    yield


app = FastAPI(title="TenderAI — Analyst Service", version="0.1.0", lifespan=lifespan)

app.include_router(ingest_router, prefix="/api/rag")
app.include_router(query_router, prefix="/api/rag")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/rag/health")
async def rag_health():
    return {"status": "ok"}
