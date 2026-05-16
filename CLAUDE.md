TenderAI — Claude Context
What this project is
A public procurement intelligence platform for Moroccan SMEs. Users upload French/Arabic tender PDFs, query them in plain language, and receive answers with mandatory source citations.
Full spec: docs/TenderAI_CDC_v3.md — read it when working on anything architectural.
Current phase
Phase 1 — The Analyst only. Do not build the scraper, Guardian, or Quant Engine yet.
Stack

Django (auth, vault, admin) on port 8000
FastAPI (RAG, embeddings, AI inference) on port 8001
Next.js frontend (App Router)
PostgreSQL + ChromaDB (dev) — wrapped behind a VectorStore interface
GPT-4o for synthesis, paraphrase-multilingual-mpnet-base-v2 for embeddings
Celery + Redis (Phase 2 — not yet)
CrewAI (Phase 2 — not yet)

Key commands
bashdocker-compose up -d           # start all services
cd backend/django && python manage.py runserver
cd backend/fastapi && uvicorn main:app --reload --port 8001
cd frontend && npm run dev
pytest tests/ -v               # all tests
pytest tests/rag_eval/ -v      # RAG evaluation set specifically
ruff check backend/
Non-negotiable invariants
1. Citations are mandatory.
Every RAG answer must include a verbatim quote and page number from the source PDF.
Format: [Page N, Section X] : « …quote… »
Verification: pytest tests/rag_eval/test_citations.py after any RAG pipeline change.
A response without a citation must be blocked before it reaches the user.
2. Guardian flags conservatively.
Only 100%-certain compliance gaps get flagged BLOCKING. Ambiguous cases → WARNING.
Verification: pytest tests/guardian_eval/ (Phase 2).
3. No secrets in code.
All API keys and credentials in .env. Never hardcode. Pre-commit hook blocks commits with secrets.
4. VectorStore is always accessed through the interface.
Never import ChromaDB or Pinecone directly in application code.
Always use backend/fastapi/storage/vector_store.py.
5. The scraper does not ship without legal sign-off.
Do not write production scraper code until docs/legal_review.md exists and is approved.
What Claude gets wrong on this project

Skipping the citation enforcement layer. The raw chunk must be retrieved and stored separately, displayed to the user alongside the answer. Do not reconstruct a citation from the generated answer text.
Putting AI inference logic in Django. Django views are sync. Any endpoint that calls GPT-4o or ChromaDB goes in FastAPI. If you're adding an AI call to a Django view, stop and move it.
Importing ChromaDB directly. Always go through VectorStore. A direct chromadb import outside of vector_store.py is a bug.
Chunking by character count. Use semantic chunking at section headers as the primary strategy. RecursiveCharacterTextSplitter with a fixed size is a fallback only, within sections that have no headers.
Adding CrewAI in Phase 1. Not in scope. If you find yourself importing crewai, stop.

Docs

Full CDC: docs/TenderAI_CDC_v3.md
RAG eval set: tests/rag_eval/
marchespublics.gov.ma: https://www.marchespublics.gov.ma