# Updated PRD — Assistant PoC
**Status: Implemented and Running**
**Last Updated: 2026-03-15**

> This document is the updated version of the original PRD (`assistant_byod.md`). It reflects the actual implementation decisions, technology choices, bug fixes, and current state of the PoC. Where the original PRD was aspirational, this document is descriptive — what was built and why.

---

## 1. Product Summary

A lightweight, multi-user, session-isolated research assistant that combines NotebookLM-style document Q&A with an agentic planning loop. Users upload their own documents, add web URLs, or paste text into private session knowledge bases, then converse with an agent that retrieves, plans, executes code, and composes grounded answers.

**Currently running:** `docker compose up --build` starts all four services locally.

---

## 2. What Was Built — Feature Checklist

| Feature | Status | Notes |
|---------|--------|-------|
| Local username/password auth | ✅ | bcrypt + JWT |
| Multiple private sessions | ✅ | per-user, isolated |
| File upload (PDF, PPTX, JPG, PNG, TXT) | ✅ | text extraction per type |
| Web URL ingestion | ✅ | httpx + BeautifulSoup |
| Pasted text ingestion | ✅ | no file count toward limit |
| RAG chat over session content | ✅ | ChromaDB cosine search |
| Agentic planning loop (LangGraph) | ✅ | 10-node graph |
| Plan / replan | ✅ | max 2 re-retrieval iterations |
| Clarification when ambiguous | ✅ | `analyze_input` node |
| Session memory (conversation history) | ✅ | last 20 messages from PostgreSQL |
| Skill ZIP upload and management | ✅ | 12-point validation |
| Session-level skill enable/disable | ✅ | `session_skills` table |
| Python/JS sandbox execution | ✅ | subprocess with timeout |
| PDF / CSV / XLSX artifact export | ✅ | ReportLab / openpyxl / pandas |
| PPTX artifact generation via skill | ✅ | Skill template → sandbox → auto-registered artifact |
| Skill output files auto-registered as artifacts | ✅ | `_register_skill_artifacts` in agent_service |
| Admin seed user on startup | ✅ | username: admin / admin$123 |
| Docker Compose deployment | ✅ | 4 services |
| Dedicated skills page (/skills) | ✅ | upload, list, toggle, delete |
| Source ingestion status tracking | ✅ | pending → processing → complete |
| Citation references in answers | ✅ | `[Source N: filename]` format |
| Multi-LLM: Gemini + Azure OpenAI GPT | ✅ | Per-session model selection, locked at creation |
| Admin embedding model configuration | ✅ | MiniLM-L6-v2 / Azure text-embedding-3-small / large |
| Admin configuration page (/admin) | ✅ | Admin-only, platform-wide embedding settings |
| LLM model badge on sessions | ✅ | Dashboard cards + session header show active model |

---

## 3. Non-Negotiable Requirements — Compliance

### 3.1 Multi-user and Session Isolation ✅
Every database query is filtered by `user_id`. Session-scoped queries additionally filter by `session_id`. ChromaDB uses one collection per session (`session_{session_id}`), making cross-session retrieval structurally impossible. Vector searches never cross collection boundaries.

### 3.2 Base Content Types ✅
PDF, PPTX, JPG/JPEG, PNG, TXT, pasted text, and web URLs are all supported. File types are validated against a strict allowlist before storage.

### 3.3 Limits ✅
- Max 10 uploaded files + URLs per session (`MAX_FILES_AND_URLS_PER_SESSION=10`)
- Pasted text is exempt from the 10-source limit
- Max pasted text: 50,000 chars per entry (`MAX_PASTED_TEXT_CHARS=50000`)
- Max upload size: 50 MB (`MAX_UPLOAD_MB=50`)

### 3.4 Agent Behavior ✅
The LangGraph graph implements all required behaviors: intent analysis, clarification gating, plan construction, RAG retrieval, skill selection, code execution decision, plan revision, answer composition with citations, and session memory loading.

### 3.5 Skill Support ✅
Dedicated `/skills` page with upload, list view, detail inspection, validation status, enable/disable toggle, and delete. Skills are private to the owning user — enforced at both API and DB level.

**Skill execution pipeline:**
- `choose_skills` selects skills by name before retrieval runs
- `decide_code_execution` triggers automatically when any skill is selected
- `run_tools_or_code` extracts the `\`\`\`python` block from SKILL.md, adapts it with real content via LLM, and executes in the sandbox
- Skills print `{"status": "success", "output_path": "..."}` to stdout; the agent parses this and registers the file as a downloadable artifact automatically
- `ChatResponse.artifacts` surfaces the artifact ID to the frontend for download

### 3.6 Local Resources ✅
- PostgreSQL 15 for relational data
- ChromaDB (local container, persisted volume) for vectors
- sentence-transformers running in-process (default embedding — no external API required)
- Optional: Azure OpenAI embedding models (`text-embedding-3-small` / `text-embedding-3-large`) configurable by admin
- Local file storage volumes via Docker
- Gemini API key from `.env` (required)
- Azure OpenAI API key from `.env` (optional — required only for Azure GPT model and Azure embeddings)

### 3.7 Docker-first ✅
`docker compose up --build` starts all four services. The stack runs on a single machine with no external infrastructure except the LLM APIs (Gemini and/or Azure OpenAI, depending on user's model selection).

### 3.8 Admin Seed User ✅
The FastAPI lifespan function seeds `admin / admin$123` on startup if not already present. The fix required replacing `passlib` with direct `bcrypt` usage (see Section 7).

---

## 4. Architecture Summary

### Services (Docker Compose)

| Service | Image | Port | Role |
|---------|-------|------|------|
| postgres | postgres:15-alpine | 5432 | Relational store |
| chroma | chromadb/chroma:latest | 8000 | Vector store |
| backend | ./backend (python:3.11-slim) | 8000 | FastAPI + LangGraph agent |
| frontend | ./frontend (node:20-alpine) | 3000 | Next.js UI |

### Agent Runtime

The agent is implemented as a **single-orchestrator LangGraph StateGraph** — the "Deep Agents SDK" pattern. There is no multi-agent architecture in this PoC version. The graph drives the full request lifecycle through 10 nodes:

```
analyze_input → [clarify_if_needed | build_plan]
  → retrieve_context → choose_skills → decide_code_execution
  → [run_tools_or_code →] revise_plan
  → [retrieve_context (loop, max 2×) | compose_answer]
  → persist_memory → END
```

### LLM Strategy
Users select their LLM model (Gemini or Azure OpenAI GPT) at session creation time. The choice is locked for the lifetime of the session and cannot be changed. The `llm_model` field is stored on the `sessions` table and threaded through `AgentState.llm_provider` to all graph nodes. The `_llm_call()` helper in `graph.py` delegates to the appropriate LangChain wrapper based on the provider string.

### Embedding Strategy
The default embedding model is `sentence-transformers/all-MiniLM-L6-v2` (384-dim, runs entirely in-process, no API quota). Admin users can switch the platform-wide embedding model to Azure OpenAI `text-embedding-3-small` (1536-dim) or `text-embedding-3-large` (3072-dim) via the `/admin` configuration panel. The active model is stored in the `platform_settings` database table and read by the embedding service at runtime. Changing the model only affects new document ingestion — existing vectors retain their original embeddings.

---

## 5. Data Model (as implemented)

### users
```sql
id            UUID PK
username      TEXT UNIQUE NOT NULL
password_hash TEXT NOT NULL
is_active     BOOLEAN DEFAULT true
is_admin      BOOLEAN DEFAULT false
created_at    TIMESTAMP
updated_at    TIMESTAMP
```

### sessions
```sql
id          UUID PK
user_id     UUID FK → users
title       TEXT
status      TEXT  -- active | archived | deleted
llm_model   TEXT  -- gemini | azure_openai (locked at creation)
created_at  TIMESTAMP
updated_at  TIMESTAMP
archived_at TIMESTAMP nullable
```

### messages
```sql
id                UUID PK
session_id        UUID FK → sessions
user_id           UUID FK → users
role              TEXT  -- user | assistant | system
content           TEXT
structured_payload JSONB nullable  -- { citations, plan, agent_run_id }
created_at        TIMESTAMP
```

### sources
```sql
id                UUID PK
user_id           UUID FK → users
session_id        UUID FK → sessions
source_type       TEXT  -- pdf | pptx | image | txt | text | url
display_name      TEXT
original_filename TEXT nullable
source_url        TEXT nullable
local_path        TEXT nullable
ingest_status     TEXT  -- pending | processing | complete | failed
content_hash      TEXT nullable
created_at        TIMESTAMP
updated_at        TIMESTAMP
```

### source_chunks_metadata
```sql
id          UUID PK
source_id   UUID FK → sources
user_id     UUID FK → users
session_id  UUID FK → sessions
chunk_index INTEGER
vector_ref  TEXT
metadata    JSONB
```

### skills
```sql
id                    UUID PK
user_id               UUID FK → users
name                  TEXT
version               TEXT
description           TEXT
skill_metadata_json   JSONB
install_status        TEXT  -- pending | installed | failed
validation_status     TEXT  -- uploaded | validating | valid | invalid | failed
validation_errors     JSONB nullable
is_globally_enabled   BOOLEAN DEFAULT false
storage_path          TEXT
uploaded_at           TIMESTAMP
updated_at            TIMESTAMP
```

### session_skills
```sql
id         UUID PK
session_id UUID FK → sessions
skill_id   UUID FK → skills
is_enabled BOOLEAN DEFAULT true
created_at TIMESTAMP
updated_at TIMESTAMP
```

### agent_runs
```sql
id              UUID PK
user_id         UUID FK → users
session_id      UUID FK → sessions
user_message_id UUID nullable
status          TEXT  -- pending | running | complete | failed
current_plan    JSONB nullable
final_summary   TEXT nullable
started_at      TIMESTAMP
completed_at    TIMESTAMP nullable
```

### tool_runs
```sql
id           UUID PK
agent_run_id UUID FK → agent_runs
tool_name    TEXT
input_json   JSONB
output_json  JSONB nullable
status       TEXT
created_at   TIMESTAMP
```

### artifacts
```sql
id            UUID PK
user_id       UUID FK → users
session_id    UUID FK → sessions
artifact_type TEXT  -- pdf | csv | xlsx
display_name  TEXT
file_path     TEXT
metadata      JSONB nullable
created_at    TIMESTAMP
```

### platform_settings
```sql
id          UUID PK
key         TEXT UNIQUE  -- e.g. "active_embedding_model"
value       TEXT         -- e.g. "sentence-transformers/all-MiniLM-L6-v2"
updated_by  UUID nullable FK → users
updated_at  TIMESTAMP
```

---

## 6. API Surface (as implemented)

All endpoints require `Authorization: Bearer <token>` except `/auth/signup` and `/auth/login`.

| Method | Path | Description |
|--------|------|-------------|
| POST | /auth/signup | Create account, receive JWT |
| POST | /auth/login | Authenticate, receive JWT |
| POST | /auth/logout | Stateless (client discards token) |
| GET | /auth/me | Current user profile |
| GET | /sessions | List user's sessions |
| GET | /sessions/llm-models | List available LLM models |
| POST | /sessions | Create session (with `llm_model` selection) |
| GET | /sessions/{id} | Get session |
| PATCH | /sessions/{id} | Rename or archive |
| DELETE | /sessions/{id} | Soft-delete + drop Chroma collection |
| GET | /sessions/{id}/sources | List sources |
| POST | /sessions/{id}/sources/upload | Upload file (multipart) |
| POST | /sessions/{id}/sources/url | Add URL |
| POST | /sessions/{id}/sources/text | Paste text |
| DELETE | /sessions/{id}/sources/{source_id} | Delete source |
| GET | /sessions/{id}/messages | Full chat history |
| POST | /sessions/{id}/chat | Send message, invoke agent |
| GET | /sessions/{id}/agent-runs/{run_id} | Agent run details |
| GET | /skills | List own skills |
| POST | /skills/upload | Upload skill ZIP |
| GET | /skills/{skill_id} | Skill detail |
| POST | /skills/{skill_id}/enable | Enable globally |
| POST | /skills/{skill_id}/disable | Disable globally |
| DELETE | /skills/{skill_id} | Delete skill |
| POST | /sessions/{id}/skills/{skill_id}/enable | Enable for session |
| POST | /sessions/{id}/skills/{skill_id}/disable | Disable for session |
| GET | /sessions/{id}/artifacts | List session artifacts |
| POST | /sessions/{id}/artifacts/generate | Generate PDF/CSV/XLSX |
| GET | /artifacts/{artifact_id}/download | Download artifact |
| GET | /admin/settings | Platform settings (admin-only) |
| PUT | /admin/settings/embedding-model | Update embedding model (admin-only) |

---

## 7. Implementation Decisions and Deviations from Original PRD

### 7.1 "Deep Agents SDK" — Interpretation
The original PRD specified "Deep Agents SDK + LangGraph as the core runtime." There is no public SDK with this exact name. The PRD was interpreted as the architectural pattern: a LangGraph StateGraph driving a planner-executor loop that matches the "Deep Agents" behavior described — planning, re-planning, clarification, retrieval, tool use, and answer composition. The implementation uses LangGraph directly as the "SDK" harness.

### 7.2 passlib → bcrypt (Breaking Change Fixed)
`passlib[bcrypt]` raises `AttributeError: module 'bcrypt' has no attribute '__about__'` when used with `bcrypt>=4.0`. This caused the admin seed user to fail silently on startup.

**Fix:** Removed `passlib`. [security.py](backend/app/core/security.py) now calls `bcrypt.hashpw` and `bcrypt.checkpw` directly.

### 7.3 ChromaDB Version Alignment
The `chromadb/chroma:latest` Docker image auto-updated to v1.5.5 (v1.x API), but `requirements.txt` pinned the client to `>=0.5.0,<0.6.0` (v0.x API). This caused `KeyError: '_type'` in `CollectionConfigurationInternal.from_json()`.

**Fix:** `chromadb>=1.0.0` in requirements.txt. Both client and server now run v1.5.5.

### 7.4 LangChain Ecosystem Version Alignment
Original pins (`langchain-google-genai==1.0.6`, `google-generativeai==0.7.2`) were incompatible — `langchain-google-genai 1.0.6` requires `google-generativeai<0.6.0`.

**Fix:** Upgraded the entire ecosystem:
- `langchain>=0.3.7,<0.4.0`
- `langchain-google-genai>=2.0.5,<3.0.0`
- `langchain-community>=0.3.7,<0.4.0`
- `langchain-core>=0.3.15,<0.4.0`
- `google-generativeai>=0.8.0`
- `pydantic>=2.7.4` (langchain 0.3.x requires ≥2.7.4)

### 7.5 Node.js in Backend Container
The Dockerfile originally used `apt-get install nodejs` which pulled 673 packages (229 MB extra). Replaced with NodeSource setup script:
```dockerfile
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*
```
This installs Node.js 20.x cleanly without the bloat.

### 7.6 Frontend npm Install
`npm ci` requires a `package-lock.json`. Changed to `npm install --legacy-peer-deps` since no lock file is committed to the repo.

### 7.7 ChromaDB Health Check
The `chromadb/chroma` image contains neither `curl`, `wget`, nor Python in the shell PATH. Health check changed from HTTP probe to TCP:
```yaml
test: ["CMD", "bash", "-c", "echo > /dev/tcp/localhost/8000"]
start_period: 20s
```

### 7.8 Default Embedding Model
Gemini embedding API requires billing to be enabled — not available on the free tier. `sentence-transformers/all-MiniLM-L6-v2` was chosen as the **default** embedding model. It runs entirely in-process, requires no API quota, and produces 384-dim cosine-comparable vectors stored in ChromaDB. Admin users can switch to Azure OpenAI embedding models via the `/admin` panel — see Section 7.11 for details.

### 7.9 LangGraph MemorySaver
The agent uses `MemorySaver` (in-memory) rather than `PostgresSaver`. This is sufficient for the PoC single-process deployment. Checkpoints are lost on backend restart; conversation continuity across restarts is maintained through PostgreSQL message history loading at graph invocation time.

### 7.10 Multi-LLM Support (Gemini + Azure OpenAI GPT)
Users select between Google Gemini and Azure OpenAI GPT when creating a session. The `llm_model` is stored on the `sessions` table and cannot be changed after creation. The `AgentState` carries a `llm_provider` field, and every `_llm_call()` in the graph routes to the correct LangChain wrapper (`ChatGoogleGenerativeAI` or `AzureChatOpenAI`).

**Key design:** Model selection is per-session and immutable. This ensures consistent behavior within a session and avoids mid-conversation model switching artifacts.

### 7.11 Admin-Configurable Embedding Models
The embedding model is a platform-wide setting stored in the `platform_settings` table. Admin users can switch between:
- `sentence-transformers/all-MiniLM-L6-v2` (384-dim, local, free — default)
- `azure-text-embedding-3-small` (1536-dim, Azure OpenAI API)
- `azure-text-embedding-3-large` (3072-dim, Azure OpenAI API)

The admin panel at `/admin` provides a UI for this. Changing the model only affects new document ingestion. The `embeddings.py` service reads the active model from the DB at runtime and caches it until explicitly reset.

**Important caveat:** Mixing embedding dimensions within a single ChromaDB collection will cause search degradation. When changing embedding models, existing sessions should be considered read-only or documents should be re-ingested.

### 7.12 Ingestion in Backend Process
File ingestion runs as a `FastAPI BackgroundTask` inside the backend process rather than as a separate worker service. The code is structured in a way (`ingestion/` module, service boundary) that allows it to be extracted to a Celery worker later without API changes.

---

## 8. Environment Variables

```env
APP_ENV=local
APP_HOST=0.0.0.0
APP_PORT=8000
FRONTEND_URL=http://localhost:3000

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=deep_research
POSTGRES_USER=app_user
POSTGRES_PASSWORD=app_password

CHROMA_HOST=chroma
CHROMA_PORT=8000

GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Azure OpenAI (optional — required for Azure GPT and Azure embedding models)
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_GPT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_SMALL=text-embedding-3-small
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_LARGE=text-embedding-3-large

JWT_SECRET=change_me
JWT_EXPIRE_MINUTES=1440

MAX_FILES_AND_URLS_PER_SESSION=10
MAX_UPLOAD_MB=50
MAX_PASTED_TEXT_CHARS=50000
MAX_SKILL_ZIP_MB=20
MAX_CODE_EXEC_SECONDS=20

ENABLE_CODE_EXECUTION=true
ENABLE_SKILLS=true

SEED_ADMIN_USER=true
SEED_ADMIN_USERNAME=admin
SEED_ADMIN_PASSWORD=admin$123
```

---

## 9. Skill ZIP Format

A valid skill ZIP must contain at the top level:

- `SKILL.md` with YAML frontmatter:
  ```yaml
  ---
  name: skill_name
  version: 1.0.0
  description: What this skill does
  ---
  ```
- Optional supporting files: `.py`, `.js`, `.txt`, `.json`, `.yaml`, `.yml`
- No path traversal, no dangerous code patterns

The `generate_pptx` skill (`assets/generate_pptx_skill.zip`) is the reference implementation demonstrating the correct format.

---

## 10. Known Limitations (PoC)

| Limitation | Impact | Production Fix |
|-----------|--------|----------------|
| LangGraph checkpoints are in-memory | Lost on backend restart | Use `PostgresSaver` |
| No streaming | Full response after completion | Use `astream_events` |
| Single-process ingestion + agent | Cannot scale independently | Extract to Celery workers |
| Keyword-based code execution detection | Some false positives/negatives | LLM function-calling |
| No sub-agents | No parallel research or specialisation | Add sub-agent nodes to graph |
| No cross-session user memory | User must re-upload context per session | Add user-profile memory layer |
| sentence-transformers loaded at startup | Adds ~500 MB RAM, ~15s startup | Use a dedicated embeddings service |
| ChromaDB in Docker (single-node) | No HA or distributed search | Use Qdrant / Weaviate / managed Chroma |
| JWT without refresh tokens | Expires after `JWT_EXPIRE_MINUTES` | Add refresh token flow |
| No rate limiting | API is unprotected beyond auth | Add slowapi rate limits |
| Embedding model change affects only new documents | Existing vectors retain original dimensionality | Re-ingest documents or migrate vectors |
| No per-session embedding isolation | Changing embedding model mid-session creates mixed-dim collections | Create new ChromaDB collection on model change |

---

## 11. Acceptance Criteria — Verification Status

### Isolation
- [x] User A cannot access User B's sessions, sources, artifacts, or skills
- [x] Session A and Session B of the same user are isolated
- [x] Retrieval from one session never uses content from another session

### Ingestion
- [x] Users can upload PDF, PPTX, JPG, PNG, TXT files
- [x] URL content is fetched, extracted, chunked, and retrievable
- [x] Pasted text can be added to the session knowledge base

### Chat / Agent
- [x] Agent can answer grounded questions over session data with citations
- [x] Agent can ask clarification questions when request is ambiguous
- [x] Agent supports "refine previous answer" style follow-ups (session history)
- [x] Agent maintains a plan and can revise it during execution

### Skills
- [x] Users have a dedicated /skills page
- [x] Users can upload a skill ZIP
- [x] Skill ZIP validation is enforced (12-point check)
- [x] Invalid skills are rejected and cannot be executed
- [x] Users can see their own skill details and status
- [x] Users can enable/disable skills globally and per-session
- [x] Users cannot see or modify another user's skills

### Code Execution
- [x] Python execution works in subprocess sandbox with timeout
- [x] JavaScript (Node.js) execution works in subprocess sandbox
- [x] Execution outputs are available to the agent for composing answers

### Artifacts
- [x] Users can generate PDF, CSV, and XLSX outputs
- [x] Users can download only their own artifacts

### Multi-LLM
- [x] Users can select Gemini or Azure OpenAI GPT when creating a session
- [x] LLM model is locked per session and cannot be changed after creation
- [x] Session cards and session header display the active model badge
- [x] All agent graph nodes use the session-scoped LLM provider

### Admin Configuration
- [x] Admin users can access `/admin` configuration panel
- [x] Non-admin users are redirected away from `/admin`
- [x] Admin can view and change the platform-wide embedding model
- [x] Three embedding model options available (MiniLM-L6-v2, Azure small, Azure large)
- [x] Embedding model change resets the cached model for new ingestions

### Deployment
- [x] Stack runs via `docker compose up --build`
- [x] Seeded admin user can log in after first startup (username: admin, password: admin$123)

---

## 12. Local Setup

```bash
# 1. Clone and navigate to project root
cd /path/to/Assistant_PoC

# 2. Copy and configure environment
cp .env.example .env
# Edit .env — set GEMINI_API_KEY (required)
# Optionally set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT for Azure GPT/embeddings

# 3. Build and start all services
docker compose up --build

# 4. Access
#   Frontend:      http://localhost:3000
#   Backend API:   http://localhost:8000
#   Swagger docs:  http://localhost:8000/docs
#   Admin panel:   http://localhost:3000/admin (admin users only)
#   Default login: admin / admin$123
```
