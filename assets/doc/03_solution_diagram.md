# Solution Architecture Diagram — Assistant PoC

## 1. High-Level System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Docker Compose Network                           │
│                                                                             │
│  ┌──────────────┐   HTTP    ┌──────────────────────────────────────────┐   │
│  │              │  :3000    │              BACKEND (FastAPI)            │   │
│  │  FRONTEND    │◄─────────►│                                          │   │
│  │  (Next.js)   │           │  ┌─────────────┐   ┌──────────────────┐ │   │
│  │              │           │  │  REST API   │   │  Agent Service   │ │   │
│  │  Port: 3000  │           │  │  (routers)  │   │  (LangGraph)     │ │   │
│  └──────────────┘           │  └──────┬──────┘   └────────┬─────────┘ │   │
│                             │         │                    │           │   │
│                             │  ┌──────▼──────────────────▼──────────┐ │   │
│                             │  │         Service Layer               │ │   │
│                             │  │  auth • session • source • skill   │ │   │
│                             │  │  artifact • knowledge_store • admin│ │   │
│                             │  │  embeddings (multi-model)          │ │   │
│                             │  └──────┬──────────────────┬──────────┘ │   │
│                             │         │                  │            │   │
│                             └─────────┼──────────────────┼────────────┘   │
│                                       │                  │                 │
│              ┌────────────────────────┼──────────────────┼──────┐         │
│              │                        │                  │      │         │
│  ┌───────────▼──────────┐  ┌──────────▼─────┐  ┌────────▼────┐ │         │
│  │   POSTGRESQL :5432   │  │  CHROMADB :8000 │  │   STORAGE   │ │         │
│  │                      │  │                 │  │   VOLUMES   │ │         │
│  │  users               │  │  session_*      │  │             │ │         │
│  │  sessions            │  │  collections    │  │  uploads/   │ │         │
│  │  messages            │  │  (1 per session)│  │  artifacts/ │ │         │
│  │  sources             │  │                 │  │  skills/    │ │         │
│  │  source_chunks_meta  │  │  cosine vectors │  │             │ │         │
│  │  skills              │  │  (configurable  │  │             │ │         │
│  │  session_skills      │  │   embedding)    │  │             │ │         │
│  │  agent_runs          │  └─────────────────┘  └─────────────┘ │         │
│  │  tool_runs           │                                        │         │
│  │  artifacts           │                                        │         │
│  │  platform_settings   │                                        │         │
│  └──────────────────────┘                                        │         │
│                                                                  │         │
└──────────────────────────────────────────────────────────────────┘         │
                                                                             │
                          ┌──────────────────────┐                          │
                          │   LLM API (cloud)     │                          │
                          │   Gemini 2.5-flash    │                          │
                          │   OR Azure OpenAI GPT │                          │
                          │   (per-session select)│                          │
                          └──────────────────────┘                          │
                          ┌──────────────────────┐                          │
                          │ Azure OpenAI Embed.  │  (optional, admin-set)   │
                          │ text-embedding-3-*   │                          │
                          └──────────────────────┘                          │
```

---

## 2. Docker Compose Services

```
docker-compose.yml
│
├── postgres          (image: postgres:15-alpine)
│   ├── Port: 5432
│   ├── Volume: postgres_data
│   └── Health: pg_isready
│
├── chroma            (image: chromadb/chroma:latest)
│   ├── Port: 8000
│   ├── Volume: chroma_data → /chroma/chroma
│   └── Health: TCP bash check :8000
│
├── backend           (build: ./backend)
│   ├── Port: 8000 → host 8000
│   ├── Depends: postgres (healthy), chroma (healthy)
│   ├── Volumes: ./backend:/app, storage_data:/storage
│   ├── Runtime: Python 3.11-slim + Node.js 20.x (NodeSource)
│   └── CMD: uvicorn app.main:app
│
└── frontend          (build: ./frontend)
    ├── Port: 3000 → host 3000
    ├── Depends: backend
    └── Build: node:20-alpine multi-stage
        ├── Stage 1 (deps): npm install
        ├── Stage 2 (builder): next build
        └── Stage 3 (runner): standalone output
```

---

## 3. Backend Internal Architecture

```
backend/app/
│
├── main.py                    FastAPI app entry, lifespan, CORS, router mount
│
├── api/                       Route handlers (thin — delegate to services)
│   ├── auth.py                POST /auth/signup, login, logout, GET /auth/me
│   ├── sessions.py            CRUD /sessions, PATCH archive, GET /llm-models
│   ├── sources.py             Upload / URL / text / delete sources
│   ├── chat.py                POST /chat, GET /messages, GET /agent-runs
│   ├── skills.py              Upload ZIP, enable/disable, delete, session toggle
│   ├── artifacts.py           Generate PDF/CSV/XLSX, download
│   └── admin.py               GET/PUT /admin/settings (embedding model, admin-only)
│
├── core/
│   ├── config.py              Pydantic Settings from .env (Gemini + Azure OpenAI)
│   ├── llm_provider.py        Multi-LLM factory: get_llm(provider) → Gemini or Azure
│   ├── security.py            bcrypt hash/verify, JWT encode/decode
│   └── deps.py                FastAPI dependency: get_current_user
│
├── db/
│   ├── base.py                SQLAlchemy declarative base
│   └── session.py             Engine + SessionLocal, get_db dependency
│
├── models/                    SQLAlchemy ORM models (12 tables, incl. platform_settings)
│
├── schemas/                   Pydantic v2 request/response schemas
│
├── services/
│   ├── auth_service.py        Signup, login, user lookup
│   ├── session_service.py     Session CRUD, ownership checks
│   ├── source_service.py      Source metadata, ingestion dispatch
│   ├── agent_service.py       Graph invocation, pre/post DB writes
│   ├── skill_service.py       ZIP upload, validation, enable/disable
│   ├── artifact_service.py    PDF (ReportLab), CSV/XLSX (openpyxl/pandas)
│   └── knowledge_store.py     ChromaDB abstraction (per-session collections)
│
├── agents/
│   ├── graph.py               LangGraph StateGraph, all 10 nodes, routing
│   ├── state.py               AgentState TypedDict
│   └── skill_loader.py        Load active skills into AgentState
│
├── ingestion/
│   ├── extractor.py           PDF/PPTX/image/TXT/URL text extraction
│   ├── chunker.py             Sliding window 1000 chars / 200 overlap
│   └── embedder.py            Multi-model: MiniLM-L6-v2 / Azure text-embedding-3-*
│
├── skills/
│   └── skill_validator.py     12-point ZIP validation (path traversal, patterns)
│
└── execution/
    └── sandbox.py             subprocess.run() with timeout, temp dir, capture
```

---

## 4. Request Flow — Chat Message

```
User types message in browser
        │
        ▼
Next.js frontend
POST /sessions/{id}/chat { message, stream: false }
        │  JWT token in Authorization header
        ▼
FastAPI chat router
  → verify JWT → load user
  → verify session ownership
        │
        ▼
agent_service.run_agent()
  ┌─────────────────────────────────────────────────────────────┐
  │  1. Load last 20 messages from PostgreSQL → messages[]      │
  │  2. skill_loader: load valid+enabled skills → active_skills │
  │  3. Create agent_run record (status=running) in DB          │
  │  4. Invoke LangGraph graph (thread_id=session_id)           │
  │     ┌──────────────────────────────────────────────────┐    │
  │     │  analyze_input → [clarify? or build_plan]        │    │
  │     │  → choose_skills (LLM selects from active_skills)│    │
  │     │  → retrieve_context (ChromaDB top-8)             │    │
  │     │  → decide_code_execution                         │    │
  │     │    (triggers if skills selected OR keyword match) │    │
  │     │  → [run_tools_or_code?]                          │    │
  │     │    Path A: extract+adapt skill template → sandbox │    │
  │     │    Path B: generate code from scratch → sandbox   │    │
  │     │  → revise_plan (max 2 re-retrieval loops)        │    │
  │     │  → compose_answer (Gemini or Azure OpenAI GPT)   │    │
  │     │  → persist_memory (no-op in graph)               │    │
  │     └──────────────────────────────────────────────────┘    │
  │  5. Register skill output files as artifacts in PostgreSQL  │
  │  6. Write user+assistant messages to PostgreSQL             │
  │  7. Update agent_run (status=complete, plan, summary)       │
  └─────────────────────────────────────────────────────────────┘
        │
        ▼
ChatResponse { answer, plan, citations, agent_run_id, ... }
        │
        ▼
Frontend renders markdown answer + citation chips
```

---

## 5. Request Flow — Source Ingestion

```
User uploads file / adds URL / pastes text
        │
        ▼
POST /sessions/{id}/sources/upload  (multipart)
     /sources/url                   (JSON)
     /sources/text                  (JSON)
        │
        ▼
FastAPI sources router
  → verify JWT + session ownership
  → validate file type & size
  → save file to /storage/uploads/{user_id}/{session_id}/{source_id}/
  → create source record in PostgreSQL (status=pending)
  → return 201 immediately
        │
        ▼  (FastAPI BackgroundTask — async)
ingestion pipeline
  ┌─────────────────────────────────────────────────────────────┐
  │  1. source_service.update_status(processing)               │
  │  2. extractor.extract_text(source)                         │
  │     ├── PDF    → pypdf pages; pytesseract fallback          │
  │     ├── PPTX   → python-pptx all slide text                │
  │     ├── Image  → pytesseract OCR                           │
  │     ├── TXT    → direct read                               │
  │     ├── Text   → already a string                          │
  │     └── URL    → httpx fetch + BeautifulSoup main content  │
  │  3. chunker.chunk(text, size=1000, overlap=200)            │
  │  4. embedder.get_embeddings(chunks) — active embedding model│
  │  5. knowledge_store.add_chunks(session_id, chunks+embeds)  │
  │     → ChromaDB upsert: collection session_{session_id}     │
  │     → PostgreSQL: source_chunks_metadata rows              │
  │  6. source_service.update_status(complete or failed)       │
  └─────────────────────────────────────────────────────────────┘

Frontend polls GET /sessions/{id}/sources for ingest_status
```

---

## 6. Request Flow — Skill Upload

```
User uploads skill ZIP from /skills page
        │
        ▼
POST /skills/upload  (multipart)
        │
        ▼
FastAPI skills router
  → verify JWT
  → save ZIP to /storage/skills/{user_id}/incoming/
  → create skill record (status=uploading)
        │
        ▼
skill_validator.validate(zip_path)
  12-point checks:
  ① valid ZIP archive
  ② max size ≤ MAX_SKILL_ZIP_MB (20 MB)
  ③ no path traversal (zip-slip)
  ④ SKILL.md present at top level
  ⑤ SKILL.md YAML frontmatter parseable
  ⑥ required fields: name, description, version
  ⑦ folder structure valid
  ⑧ referenced files exist in ZIP
  ⑨ only allowed extensions: .md .txt .py .json .yaml .yml .js
  ⑩ no dangerous code patterns (os.system, subprocess, eval, exec,
     __import__, open(, socket, requests, urllib, shutil, rmtree)
  ⑪ no blind dependency installation
  ⑫ record all validation errors
        │
        ▼
  if valid:
    unzip to /storage/skills/{user_id}/{skill_id}/
    update skill record (validation_status=valid, install_status=installed)
  if invalid:
    update skill record (validation_status=invalid, validation_errors=[...])
        │
        ▼
Response 201 { id, name, version, validation_status, ... }
```

---

## 7. Data Flow — Retrieval (RAG)

```
AgentState.user_message + first 3 plan steps
        │
        ▼  (retrieve_context node)
knowledge_store.search(session_id, query, top_k=8)
        │
        ▼
embedder.get_embeddings([query])  ← active embedding model
        │ embedding vector (384/1536/3072-dim depending on model)
        ▼
ChromaDB collection: session_{session_id}
  → cosine similarity search
  → returns top-8 chunks with distance scores
        │
        ▼
AgentState.retrieved_chunks = [
  { text, metadata: {source_name, source_id, chunk_index}, distance },
  ...
]
        │
        ▼  (compose_answer node)
top-6 chunks injected into LLM prompt as:
  [Source 1: report.pptx] <chunk text>
  [Source 2: article.pdf] <chunk text>
  ...
        │
        ▼
LLM (Gemini or Azure OpenAI) generates answer with inline source references
        │
        ▼
citations extracted → stored in message.structured_payload
```

---

## 8. Security Boundary Map

```
                        ┌───────────────────────────────┐
                        │         TRUST BOUNDARY        │
                        │                               │
  Browser ──────JWT────►│  FastAPI                      │
                        │  • verify_token()             │
                        │  • get_current_user()         │
                        │  • ownership checks on ALL    │
                        │    resources (user_id filter) │
                        │  • admin role check on        │
                        │    /admin/* endpoints          │
                        │                               │
                        │  ┌────────────────────────┐  │
                        │  │   SANDBOX BOUNDARY     │  │
                        │  │                        │  │
                        │  │  subprocess.run()      │  │
                        │  │  • timeout 20s         │  │
                        │  │  • isolated /tmp dir   │  │
                        │  │  • stdout/stderr cap   │  │
                        │  │  • no host net access  │  │
                        │  │  • no host fs access   │  │
                        │  └────────────────────────┘  │
                        │                               │
                        │  ┌────────────────────────┐  │
                        │  │   SKILL ZIP BOUNDARY   │  │
                        │  │                        │  │
                        │  │  12-point validator    │  │
                        │  │  • no path traversal   │  │
                        │  │  • no dangerous code   │  │
                        │  │  • extension allowlist │  │
                        │  └────────────────────────┘  │
                        │                               │
                        └───────────────────────────────┘

  Storage isolation:
  /storage/uploads/{user_id}/{session_id}/{source_id}/
  /storage/artifacts/{user_id}/{session_id}/
  /storage/skills/{user_id}/{skill_id}/
```

---

## 9. Frontend Page Map

```
/                           → redirect to /login or /sessions
/login                      → sign in form
/signup                     → create account form
/sessions                   → session list dashboard
/sessions/[id]              → session workspace
│   ├── Left panel          → sources list (upload, add URL, paste text)
│   ├── Main panel          → chat messages + input box
│   └── Right panel/tabs    → plan trace | artifacts | session skills
/skills                     → skill library
│   ├── Upload ZIP          → drop zone
│   └── Skill cards         → name, version, status, enable/disable, delete
/admin                      → admin configuration panel (admin-only)
│   └── Embedding model     → radio buttons to select active embedding model
```

---

## 10. Environment and Configuration

```
.env / .env.example
│
├── App
│   APP_ENV, APP_HOST, APP_PORT, FRONTEND_URL
│
├── Database
│   POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB
│   POSTGRES_USER, POSTGRES_PASSWORD
│
├── Vector Store
│   CHROMA_HOST, CHROMA_PORT
│
├── AI (Gemini)
│   GEMINI_API_KEY, GEMINI_MODEL=gemini-2.5-flash
│
├── AI (Azure OpenAI — optional)
│   AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT
│   AZURE_OPENAI_API_VERSION, AZURE_OPENAI_GPT_DEPLOYMENT
│   AZURE_OPENAI_EMBEDDING_DEPLOYMENT_SMALL
│   AZURE_OPENAI_EMBEDDING_DEPLOYMENT_LARGE
│
├── Auth
│   JWT_SECRET, JWT_EXPIRE_MINUTES
│
├── Limits
│   MAX_FILES_AND_URLS_PER_SESSION=10
│   MAX_UPLOAD_MB=50
│   MAX_PASTED_TEXT_CHARS=50000
│   MAX_SKILL_ZIP_MB=20
│   MAX_CODE_EXEC_SECONDS=20
│
├── Feature flags
│   ENABLE_CODE_EXECUTION=true
│   ENABLE_SKILLS=true
│
└── Seed
    SEED_ADMIN_USER=true
    SEED_ADMIN_USERNAME=admin
    SEED_ADMIN_PASSWORD=admin$123
```

---

## 11. Key Technology Versions

| Component | Technology | Version |
|-----------|-----------|---------|
| Backend runtime | Python | 3.11-slim |
| Web framework | FastAPI | 0.111.0 |
| ASGI server | Uvicorn | 0.29.0 |
| ORM | SQLAlchemy | 2.0.30 |
| Migrations | Alembic | 1.13.1 |
| DB driver | psycopg2-binary | 2.9.9 |
| Schema validation | Pydantic | ≥2.7.4 |
| Auth | python-jose + bcrypt | 3.3.0 / ≥4.0 |
| Agent orchestration | LangGraph | ≥0.2.28 |
| LLM client (Gemini) | langchain-google-genai | ≥2.0.5 |
| LLM client (Azure) | langchain-openai | ≥0.2.0 |
| LLM models | Gemini 2.5-flash / Azure OpenAI GPT | Per-session selection |
| Google AI SDK | google-generativeai | ≥0.8.0 |
| OpenAI SDK | openai | ≥1.40.0 |
| Vector store | ChromaDB | ≥1.0.0 (server 1.5.5) |
| Embeddings | sentence-transformers | 2.7.0 |
| Embedding model (default) | all-MiniLM-L6-v2 | 384-dim (local) |
| Embedding model (optional) | Azure text-embedding-3-small/large | 1536/3072-dim |
| PDF extraction | pypdf + pytesseract | 4.2.0 / 0.3.10 |
| PPTX extraction | python-pptx | 0.6.23 |
| HTTP client | httpx | 0.27.0 |
| HTML parsing | BeautifulSoup4 | 4.12.3 |
| PDF generation | ReportLab | 4.2.0 |
| XLSX generation | openpyxl | 3.1.2 |
| Data frames | pandas | 2.2.2 |
| Frontend runtime | Node.js | 20-alpine |
| Frontend framework | Next.js | (app router) |
| Database | PostgreSQL | 15-alpine |
| Sandbox runtime | Node.js | 20.x (NodeSource) |
