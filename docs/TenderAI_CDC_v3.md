TenderAI — Cahier des Charges
Version: 3.1 | Status: Finalized | Date: May 2026
Target: Moroccan SMEs — Architecture, BTP, IT Services

1. Executive Summary
TenderAI automates the public procurement lifecycle for Moroccan SMEs: sourcing tenders, verifying compliance, analyzing documents multilingually, and optimizing bid prices. The target is an 80% reduction in administrative time with measurably better bid success rates.
Problem Statement
PainRealityTenderAI FixFragmented portalsmarchespublics.gov.ma + dozens of regional boardsAutomated Radar scraperAdministrative disqualificationMissing RC, CNSS, Attestation FiscaleGuardian gap analysisDense French/Arabic CPS documentsHours of manual readingMultilingual RAG with citationsIntuition-based pricingNo reference to historical adjudicationsQuant Engine with EV model

2. Revised Phasing — Why Phase 1 Changes
The original plan combined the Radar (scraper) and the Analyst (RAG) in Phase 1. This was wrong for three reasons:

The scraper depends on an external website we don't control (anti-bot measures, ToS compliance, portal structure changes). The RAG depends only on ourselves.
Scraping marchespublics.gov.ma requires legal sign-off before a single line of production code ships. Blocking Phase 1 on a legal review is unacceptable.
The core product value — making dense tender documents queryable — is fully demonstrable without a scraper. A user uploads a PDF and gets cited answers. That is the demo.

Phase 1 is now The Analyst only. The Radar moves to Phase 2, after legal review is complete.

3. Functional Specifications
Module 1 — The Analyst (Multilingual RAG) ← Phase 1
Goal: Allow any team member to interrogate a tender document in plain language and receive answers with mandatory source citations.
FS-1.1 — PDF Ingestion

User uploads a PDF (CPS, RC, Bordereau de Prix, CCTP).
Parser extracts text preserving: table structures, bullet hierarchies, section headers, page numbers.
Pipeline: PDF → Markdown (structure-preserving) → Semantic Chunks.
Chunking: split at logical section headers, not arbitrary character counts. Target: 512 tokens, 64-token overlap.
Each chunk tagged: {page_number, section_header, document_type, tender_id}.
Failure mode to handle: Scanned PDFs with no digital text layer. Fallback: OCR via pytesseract or easyocr. Flag to the user when OCR fallback is used (lower confidence).

FS-1.2 — Multilingual Query Interface

Accepts queries in French, English, or Modern Standard Arabic (MSA).
Darija is explicitly out of scope. Most multilingual transformers are severely undertrained on Darija. Claiming Darija support without benchmarking it is a trust risk. MSA is the documented standard for Moroccan legal and administrative texts anyway.
Embedding model: paraphrase-multilingual-mpnet-base-v2 as baseline. Must be validated against a test set before going to production (see Section 6).

FS-1.3 — Mandatory Citations (Non-Negotiable Invariant)

Every AI answer must include: verbatim quote + page number from source PDF.
Format: [Page 12, Article 5.3] : « …verbatim excerpt… »
An answer without a traceable citation is a broken response — it must not reach the user.
Implementation: the retrieval step must return the raw source chunk alongside every generated answer, displayed to the user verbatim as a verification layer.

FS-1.4 — RAG Evaluation Set (Required Before Launch)

Minimum 20 manually-verified question/answer pairs across 3 real CPS documents.
Covers: factual lookup, negation clauses (e.g. "must NOT exceed"), table extraction, cross-references.
Pass threshold: ≥90% citation accuracy, ≥85% answer correctness.
This eval set lives in tests/rag_eval/ and runs in CI.


Module 2 — The Radar (Automated Sourcing) ← Phase 2
Prerequisite: legal sign-off on scraping marchespublics.gov.ma ToS. This module does not enter development until that sign-off is received and documented.
FS-2.1 — Scraping Engine

Primary target: marchespublics.gov.ma
Secondary: regional boards (Casablanca, RSK, Marrakech)
Runs on Celery scheduled tasks, every 30 minutes.
Extracts: title, reference number, deadline, estimated budget, issuing authority, sector.
Stores raw HTML snapshot alongside structured metadata for audit.
Respects robots.txt. Uses randomized delays between requests. No aggressive crawling.
Fallback: Playwright-based rendering for JS-heavy pages.

FS-2.2 — Semantic Matching

User defines an Interest Profile: sectors, keywords, geographic zones.
New tenders embedded and scored via cosine similarity against profile embedding.
Tenders above threshold (default: 0.75) surfaced. Threshold is user-configurable.

FS-2.3 — Digest Delivery

Channels: Slack webhook, Email (SMTP), in-app Dashboard.
Each entry: title, source, deadline, estimated budget, relevance score, one-line AI summary.


Module 3 — The Admin Guardian (Compliance) ← Phase 2
FS-3.1 — The Vault

Users upload company documents: RC, CNSS, Attestation Fiscale, Bank templates, Qualification certificates, Bilans.
On upload: AI extracts document type, expiry date, classification level. Stored in PostgreSQL.
Supported formats: PDF, DOCX, JPEG.

FS-3.2 — Constraint Extraction

On tender selection, Guardian parses the RC PDF.
Extracts: required document types, minimum classification levels, financial guarantee amounts, legal form constraints, submission deadlines.
Output: structured JSON list of requirements, each with source page number.

FS-3.3 — Gap Analysis

Cross-references extracted requirements vs. Vault contents.
Three-tier output:

🔴 BLOCKING — Required document missing entirely.
🟡 WARNING — Document present but expired, or classification below requirement.
🟢 COMPLIANT — Document present and valid.


Conservative flagging policy: only 100%-certain gaps are BLOCKING. Ambiguous interpretations generate a WARNING with explanation. A false BLOCKING is almost as damaging as a missed one — it erodes trust.
Acceptable false-negative rate: < 2% on a validated test set of 20 RC documents.


Module 4 — The Quant Engine (Bid Optimization) ← Phase 3
Hard prerequisite: ≥ 500 historical adjudication records collected and validated before model training begins. The Quant Engine is not released with fewer records — an undertrained model actively harms users by giving false precision on pricing decisions.
Data sourcing plan (must be resolved before Phase 2 ends):

Primary: résultats d'adjudication published on public portals (manual collection + structured extraction).
Secondary: Bulletin Officiel des Marchés de l'État (BOME) — structured public records.
Each record needs: tender reference, sector, winning bid, estimated budget, date, bidder count (when available).

FS-4.1 — Probability Modeling

Initial model: logistic regression on (B/E ratio → win probability). Simple, interpretable, auditable.
Phase 3 enhancement: Bayesian model incorporating sector, issuing authority, and competition count.
Model is always shown with its training set size and confidence interval. Users see the uncertainty, not just the number.

FS-4.2 — Expected Value Calculation
EV(B)=(B−C)×P(win∣B,E)EV(B) = (B - C) \times P(\text{win} \mid B, E)EV(B)=(B−C)×P(win∣B,E)

B = proposed bid price
C = internal cost estimate (user-entered)
E = published estimated budget
Output: bid price B* that maximizes EV(B) + full sensitivity curve across bid range.


4. Technical Architecture
4.1 Technology Stack
LayerTechnologyRationaleAuth / Admin / VaultDjango + DRFMature auth, ORM, built-in admin for vault managementAI Inference EndpointsFastAPIAsync-native for LLM calls and RAG queries; Django's sync default is friction hereFrontendNext.js (App Router) from day 1No Streamlit — any UI work must carry forwardAI OrchestrationPlain Python modules (Phase 1) → CrewAI (Phase 2+)Add CrewAI only when agents actually need to coordinate. Premature orchestration = unnecessary debugging surfaceTask QueueCelery + RedisAsync scraping and digest schedulingVector DBChromaDB (dev/Phase 1) → Pinecone (Phase 2+)Local-first for speed; abstract behind a repository interface from day 1Primary DBPostgreSQLRelational data, vault metadata, bid historyLLM (Reasoning)GPT-4oComplex synthesis, answer generationLLM (Embeddings)paraphrase-multilingual-mpnet-base-v2Cross-lingual FR/MSA-AR/EN vector space — must be benchmarkedPDF Parsingpymupdf4llm (digital) + pytesseract (OCR fallback)Structure-preserving Markdown outputContainerizationDocker + Docker ComposeReproducible environments
Note on the vector DB abstraction: Wrap ChromaDB and Pinecone behind a VectorStore interface from day 1. The Phase 1→2 migration should be a one-line config change, not a refactor.
4.2 Service Split: Django vs FastAPI
Django (port 8000)          FastAPI (port 8001)
───────────────────         ──────────────────────
/auth/                      /api/rag/query
/admin/                     /api/rag/ingest
/api/vault/                 /api/embeddings/
/api/tenders/               /api/compliance/analyze
/api/users/
Django handles everything stateful and relational. FastAPI handles everything async and AI-heavy. Next.js calls both.
4.3 Agent Definitions (Phase 2 onwards — CrewAI)
AgentModuleResponsibilityThe ScoutradarScrapes portals, scores relevance vs. interest profileThe GuardianguardianParses RC, cross-references Vault, generates gap reportThe ArchivistanalystChunks, indexes, retrieves — enforces citation policyThe StrategistquantRuns EV model, generates bid price recommendation
In Phase 1, The Archivist is a plain Python service — no agent framework.

5. Database Design
PostgreSQL Tables
TableKey Fieldsusersid, email, company_name, planinterest_profilesid, user_id, sectors[], keywords[], regions[]tendersid, reference, title, deadline, est_budget, source_url, scraped_attender_matchesuser_id, tender_id, relevance_scorevault_documentsid, user_id, doc_type, expiry_date, classification, file_pathcompliance_checksid, tender_id, user_id, gaps_json, checked_atbid_historyid, reference, sector, winning_bid, est_budget, authority, bidder_count, datebid_simulationsid, tender_id, user_id, user_cost, recommended_bid, ev_score, created_at
ChromaDB / Pinecone Collection
tender_chunks — one collection, metadata per chunk:
{tender_id, page_number, section_header, document_type, language, ocr_fallback: bool}

6. Testing Strategy
Testing is not optional on a product where a missed "NOT" in a legal clause is a product failure.
RAG Evaluation (Phase 1 — required before launch)

20+ manually-verified Q&A pairs across 3 real CPS documents.
Must include: factual queries, negation clauses, table data, cross-section references.
Metrics: citation accuracy (target ≥90%), answer correctness (target ≥85%).
Lives in tests/rag_eval/. Runs in CI on every merge to main.

Guardian Evaluation (Phase 2 — required before launch)

20 real RC documents with manually-identified compliance requirements.
Metrics: gap detection recall (≥98%), false BLOCKING rate (<2%).

Scraper Health (Phase 2)

Daily smoke test: scrape 5 known tenders and verify structured output matches expected schema.
Alert on failure within 30 minutes.

Quant Engine (Phase 3)

Backtesting: train on first 70% of historical records chronologically, validate on last 30%.
Report: predicted vs. actual win rate at each decile of bid price.


7. Risks & Mitigations
RiskSeverityMitigationScanned PDFs with no digital text layer🔴 CriticalOCR fallback via pytesseract; flag confidence to user; prioritize digital-text portalsNegation misses in legal clauses ("must NOT exceed")🔴 CriticalDedicated negation test cases in RAG eval set; display raw chunk to user alwaysmarchespublics.gov.ma ToS violation🔴 CriticalLegal sign-off before scraper code enters production; robots.txt compliance enforcedMultilingual model underperforms on MSA Arabic🟡 HighBenchmark paraphrase-multilingual-mpnet-base-v2 on MSA queries before Phase 1 launch; have fallback model readyInsufficient historical bid data for Quant Engine🟡 HighBegin data collection in Phase 2; launch Quant only with ≥500 records; start with percentile model as safe fallbackPortal structure changes break scraper🟡 HighSchema validation on every scrape run; alert on extraction failure; store raw HTML for debuggingLLM hallucination in citation🔴 CriticalAlways display raw source chunk alongside AI answer; answer blocked if no chunk retrieved

8. Non-Functional Requirements

Data Privacy: Vault documents encrypted at rest (AES-256). User documents never sent raw to OpenAI — only chunk embeddings are used for retrieval.
Latency: RAG query response < 10s for a 50-page document. Scraper-to-dashboard < 2 hours.
Availability: 99.5% uptime for scraping and digest pipeline.
Language: UI in French. Arabic query support validated before launch. English secondary.


9. Phased Roadmap
Phase 1 — The Analyst (Weeks 1–8)
Exit criteria: RAG passes eval set (≥90% citation accuracy, ≥85% answer correctness) on 3 real CPS documents.

 FastAPI service: PDF ingest endpoint, chunk + embed pipeline, ChromaDB indexing
 RAG query endpoint: retrieval → GPT-4o synthesis → citation enforcement
 OCR fallback for scanned PDFs
 Next.js interface: PDF upload, query input, answer + citation display
 Django: user auth, document storage
 RAG evaluation set: 20 Q&A pairs, CI integration
 Docker Compose: PostgreSQL + ChromaDB + FastAPI + Django + Next.js

Phase 2 — The Radar + Guardian (Months 3–6)
Prerequisite: legal sign-off on scraping ToS.

 Celery + Redis task queue
 Scraper for marchespublics.gov.ma
 Semantic matching pipeline
 Slack/Email digest
 The Vault: document upload, metadata extraction, expiry tracking
 Guardian agent: RC parsing + gap analysis
 Compliance dashboard
 Begin bid data collection (structured extraction from BOME + public portals)
 Migrate to CrewAI for agent coordination
 Guardian evaluation set: 20 RC documents

Phase 3 — The Quant Engine + Scale (Months 7–12)
Prerequisite: ≥500 validated historical bid records.

 Logistic regression model: (B/E ratio → P(win))
 EV curve visualization + bid price recommender
 Pinecone migration
 The Drafter agent: technical proposal generation
 Multi-region scraping
 SaaS billing + multi-tenant architecture


10. Open Questions (Must Be Resolved)
#QuestionOwnerDeadline1Does scraping marchespublics.gov.ma comply with ToS?LegalBefore Phase 2 start2Primary source for résultats d'adjudication — BOME, portal PDFs, or manual?ProductEnd of Phase 13Does paraphrase-multilingual-mpnet-base-v2 meet accuracy bar on MSA Arabic test set?EngineeringWeek 4 of Phase 14SaaS pricing model — subscription tiers vs. per-bid pricing?ProductBefore Phase 2

Next deliverable: PostgreSQL ERD + VectorStore interface definition.