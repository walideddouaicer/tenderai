# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A public procurement intelligence platform for Moroccan SMEs. Users upload French/Arabic tender PDFs, query them in plain language, and receive answers with mandatory source citations.

Full spec: `docs/TenderAI_CDC_v3.md` — read it when working on anything architectural.

## Current phase

**Phase 1 — The Analyst only.** Do not build the scraper, Guardian, or Quant Engine yet.

## Service map

| Service    | Port | Notes |
|------------|------|-------|
| Django     | 8000 | Auth, vault, admin |
| FastAPI    | 8001 | RAG, embeddings, AI inference |
| Next.js    | 3000 | Frontend (proxies to both backends) |
| PostgreSQL | 5432 | Credentials: `tenderai`/`tenderai`, db `tenderai` |
| ChromaDB   | 8002 | HTTP client; dev only |

## Stack

- Django 5 + DRF — sync, session auth, custom `User` (has `company_name`, `plan` fields), `VaultDocument` model
- FastAPI — all AI inference; routes are currently 501 stubs at `backend/fastapi/routes/`
- Next.js 14 App Router — `next.config.ts` rewrites `/api/django/*` → Django and `/api/rag/*` → FastAPI (no CORS needed)
- GPT-4o for synthesis, `intfloat/multilingual-e5-base` for embeddings (512-token context; prepend `"passage: "` for docs, `"query: "` for queries per e5 spec)
- Celery + Redis, CrewAI — Phase 2, not yet

## Key commands

```bash
# Environment setup (first time)
cp .env.example .env       # then fill in DJANGO_SECRET_KEY and OPENAI_API_KEY

docker-compose up -d       # start PostgreSQL + ChromaDB

# Django
cd backend/django && python manage.py migrate
cd backend/django && python manage.py runserver

# FastAPI
cd backend/fastapi && uvicorn main:app --reload --port 8001

# Frontend
cd frontend && npm install && npm run dev

# Tests
pytest tests/ -v                        # all tests
pytest tests/rag_eval/ -v              # RAG evaluation (citation accuracy)
pytest tests/rag_eval/test_citations.py -v -k "test_name"  # single test

# Lint
ruff check backend/
```

## Architecture: how the pieces fit together

**Ingestion flow** (not yet implemented — `POST /api/rag/ingest` returns 501):
1. Frontend → Django (stores `VaultDocument` record) → FastAPI ingest endpoint
2. FastAPI: parse PDF with `pymupdf4llm`; OCR fallback via `pytesseract` for scanned docs
3. Chunk at **section headers** (semantic boundary); 512-token target, 64-token overlap
4. Embed chunks with `sentence-transformers`, store via `VectorStore.add_chunks()`

**Query flow** (not yet implemented — `POST /api/rag/query` returns 501):
1. Frontend → FastAPI query endpoint
2. Embed question, call `VectorStore.search(tender_id, query_embedding, top_k=5)`
3. Retrieved chunks go to GPT-4o with a prompt that requires citations
4. Response: `{"answer": "...", "citations": [{"page_number": N, "section_header": "...", "verbatim_quote": "..."}]}`
5. If `citations` is empty, **block the response** — do not return it to the user

**VectorStore**: `backend/fastapi/storage/vector_store.py` — abstract base + `ChromaVectorStore`. New backend? Add an implementation and update `get_vector_store()`. Never import `chromadb` outside this file.

**Frontend routing**: all backend calls go through Next.js rewrites — no direct `localhost:8000` or `localhost:8001` in frontend code.

## Languages in scope

French (FR), English (EN), Modern Standard Arabic (MSA). **Darija is explicitly out of scope.**

## Non-negotiable invariants

### 1. Citations are mandatory
Every RAG answer must include a verbatim quote and page number from the source PDF.
- Format: `[Page N, Section X] : « …quote… »`
- The raw chunk is stored and passed to the frontend separately from the generated answer text — never reconstruct a citation from the generated answer
- Verify: `pytest tests/rag_eval/test_citations.py` after any RAG pipeline change
- A response without a citation **must be blocked** before it reaches the user

### 2. RAG eval gate before Phase 1 launch
`tests/rag_eval/test_citations.py` currently has a placeholder. Before shipping:
- Minimum 20 manually-verified Q&A pairs (FR/MSA-AR/EN) from 3 real CPS documents
- Pass thresholds: ≥90% citation accuracy, ≥85% answer correctness

### 3. VectorStore is always accessed through the interface
Never import ChromaDB or Pinecone directly in application code. Always use `backend/fastapi/storage/vector_store.py`. A direct `import chromadb` outside `vector_store.py` is a bug.

### 4. AI inference belongs in FastAPI, never Django
Django views are sync. Any endpoint that calls GPT-4o, the embedding model, or ChromaDB goes in FastAPI. If you find yourself adding an AI call to a Django view, stop and move it.

### 5. Semantic chunking only
Use section headers as the primary chunking boundary (512-token target, 64-token overlap). `RecursiveCharacterTextSplitter` with a fixed size is a fallback only — and only inside sections that have no headers.

### 6. The scraper does not ship without legal sign-off
Do not write production scraper code until `docs/legal_review.md` exists and is approved.

### 7. No CrewAI in Phase 1
Phase 2 only. If you find yourself writing `import crewai`, stop.

## Debugging and test reporting

When reporting test failures or unexpected API behavior, always paste raw log lines, response bodies, and exception tracebacks verbatim — never summaries. Summaries hide the information needed to diagnose the issue.

## Docs

- Full CDC: `docs/TenderAI_CDC_v3.md`
- RAG eval set: `tests/rag_eval/`
- Procurement portal: https://www.marchespublics.gov.ma
