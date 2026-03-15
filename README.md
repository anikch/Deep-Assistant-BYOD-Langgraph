# Assistant PoC — Deep Research Agent

A multi-user, session-isolated research assistant that combines document Q&A (NotebookLM-style) with an agentic planning loop. Upload documents, add URLs, or paste text — then chat with an agent that plans, retrieves, executes skills, and composes grounded answers with citations.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + SQLAlchemy + Alembic |
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind CSS |
| Agent | LangGraph (10-node StateGraph) |
| LLM | Google Gemini `gemini-2.5-flash` **or** Azure OpenAI GPT (selectable per session) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (default) **or** Azure OpenAI `text-embedding-3-small` / `text-embedding-3-large` (admin-configurable) |
| Vector store | ChromaDB (one collection per session) |
| Database | PostgreSQL 15 |
| Auth | JWT + bcrypt |
| Deployment | Docker Compose |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- A [Google Gemini API key](https://aistudio.google.com/app/apikey) (free tier works)
- *(Optional)* Azure OpenAI resource with API key, endpoint, and deployed models (for GPT and/or Azure embeddings)

---

## Quick Start

### 1. Clone the repo

```bash
git clone <repo-url>
cd Assistant_PoC
```

### 2. Configure environment

```bash
cp .env.example .env
```

Open `.env` and set your Gemini API key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

*(Optional)* To enable Azure OpenAI GPT and/or Azure embedding models:

```env
AZURE_OPENAI_API_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_GPT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_SMALL=text-embedding-3-small
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_LARGE=text-embedding-3-large
```

Also change `JWT_SECRET` to a secure random string before running in any shared environment:

```env
JWT_SECRET=change_me_to_a_secure_random_string
```

### 3. Build and start all services

```bash
docker compose up --build
```

First build takes ~3–5 minutes (downloads base images, installs Python deps, builds Next.js).
Subsequent starts are fast.

### 4. Access the app

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| ChromaDB | http://localhost:8001 |

### 5. Default admin account

```
Username: admin
Password: admin$123
```

---

## Services

```
docker-compose.yml
│
├── postgres          PostgreSQL 15 — relational data, migrations via Alembic
│   └── Port 5432
│
├── chroma            ChromaDB — vector store, one collection per session
│   └── Port 8001 (host) → 8000 (container)
│
├── backend           FastAPI + LangGraph agent
│   └── Port 8000
│
└── frontend          Next.js — React UI
    └── Port 3000
```

All services are connected on a single Docker Compose network. The backend connects to `postgres` and `chroma` by service name.

---

## Environment Variables

Full reference in `.env.example`. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | *(required)* | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model ID |
| `AZURE_OPENAI_API_KEY` | *(empty)* | Azure OpenAI API key (required for Azure GPT/embeddings) |
| `AZURE_OPENAI_ENDPOINT` | *(empty)* | Azure OpenAI resource endpoint URL |
| `AZURE_OPENAI_API_VERSION` | `2024-12-01-preview` | Azure OpenAI API version |
| `AZURE_OPENAI_GPT_DEPLOYMENT` | `gpt-4o` | Azure OpenAI GPT deployment name |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT_SMALL` | `text-embedding-3-small` | Azure embedding deployment (small) |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT_LARGE` | `text-embedding-3-large` | Azure embedding deployment (large) |
| `JWT_SECRET` | *(change this)* | Secret for signing JWT tokens |
| `JWT_EXPIRE_MINUTES` | `1440` | Token expiry (24 hours) |
| `POSTGRES_DB` | `deep_research` | Database name |
| `POSTGRES_USER` | `app_user` | DB username |
| `POSTGRES_PASSWORD` | `app_password` | DB password |
| `ENABLE_CODE_EXECUTION` | `true` | Allow Python/JS sandbox execution |
| `ENABLE_SKILLS` | `true` | Allow skill ZIP uploads |
| `MAX_UPLOAD_MB` | `50` | Max file upload size |
| `MAX_FILES_AND_URLS_PER_SESSION` | `10` | Max sources per session |
| `MAX_CODE_EXEC_SECONDS` | `20` | Sandbox execution timeout |
| `SEED_ADMIN_USER` | `true` | Create admin user on first start |
| `SEED_ADMIN_USERNAME` | `admin` | Admin username |
| `SEED_ADMIN_PASSWORD` | `admin$123` | Admin password |

---

## Development (without Docker)

### Backend

Requires Python 3.11+, PostgreSQL, and ChromaDB running locally.

```bash
cd backend
pip install -r requirements.txt
```

Set local environment variables (or create a `.env` in the backend dir):

```env
POSTGRES_HOST=localhost
CHROMA_HOST=localhost
GEMINI_API_KEY=your_key_here
JWT_SECRET=any_dev_secret
```

Run migrations and start:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

Requires Node.js 20+.

```bash
cd frontend
npm install
npm run dev
```

The dev server runs at http://localhost:3000 and proxies API calls to http://localhost:8000.

---

## Common Commands

```bash
# Start all services (detached)
docker compose up -d

# Start with fresh build
docker compose up --build

# Stop all services
docker compose down

# Stop and remove all volumes (wipes database + vector store)
docker compose down -v

# View logs
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend

# Restart a single service after a code change
docker compose restart backend

# Run a one-off command in the backend container
docker compose exec backend python -c "from app.db.session import engine; print('DB OK')"

# Apply new DB migrations
docker compose exec backend alembic upgrade head
```

---

## Project Structure

```
.
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/               DB migrations
│   └── app/
│       ├── main.py            FastAPI app entry point
│       ├── api/               Route handlers (auth, sessions, sources, chat, skills, artifacts, admin)
│       ├── agents/            LangGraph graph, AgentState, skill loader
│       ├── core/              Config, security (JWT/bcrypt), LLM provider
│       ├── db/                SQLAlchemy engine + session
│       ├── execution/         Python/JS subprocess sandbox
│       ├── ingestion/         Text extraction, chunking, embedding
│       ├── models/            SQLAlchemy ORM models
│       ├── schemas/           Pydantic request/response schemas
│       ├── services/          Business logic (agent, sessions, sources, skills, artifacts)
│       └── skills/            Skill ZIP validator
│
├── frontend/
│   ├── Dockerfile
│   ├── app/                   Next.js App Router pages (dashboard, session, skills, admin)
│   ├── components/            React components
│   ├── hooks/                 Zustand auth store
│   ├── lib/                   API client, auth helpers
│   └── types/                 TypeScript type definitions
│
└── assets/
    └── doc/                   Architecture, API reference, solution diagrams, PRD
```

---

## Features

### Multi-LLM Support

Users choose their LLM when creating a new session. The model is **locked for the lifetime of the session** and cannot be changed once set — this ensures consistent behavior within a conversation.

| LLM Provider | Model | Requirements |
|-------------|-------|-------------|
| Google Gemini | `gemini-2.5-flash` | `GEMINI_API_KEY` in `.env` |
| Azure OpenAI GPT | Configurable deployment (default: `gpt-4o`) | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_GPT_DEPLOYMENT` in `.env` |

**How it works:**
1. Click **New Session** on the dashboard
2. Enter a title and select the **AI Model** from the dropdown
3. Click **Create Session** — the model choice is permanent for this session
4. A color-coded badge (green for Gemini, blue for Azure OpenAI) appears on the session card and in the session header

**Backend:** The selected model is stored in the `sessions.llm_model` column and passed through `AgentState.llm_provider` to every LLM call in the 10-node agent graph. The `GET /sessions/llm-models` endpoint returns the list of available models to the frontend.

### Admin Configuration Panel

A dedicated admin page at **http://localhost:3000/admin** lets administrators manage platform-wide settings. Only users with `is_admin = true` can access it — the "Admin" link appears in the dashboard header for admin users only. Non-admin users are automatically redirected to the dashboard.

**How to access:**
1. Log in with the seeded admin account (`admin / admin$123`) or any user flagged as admin
2. Click the **Admin** link in the top-right of the dashboard header
3. Or navigate directly to http://localhost:3000/admin

**Embedding Model Configuration:**

The admin panel provides a radio-button selector to choose the active embedding model used for document ingestion and semantic search across **all platform users**.

| Embedding Model | Dimensions | Provider | Cost |
|----------------|-----------|----------|------|
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | Local (in-process) | Free (default) |
| Azure OpenAI `text-embedding-3-small` | 1536 | Azure OpenAI API | Pay-per-use |
| Azure OpenAI `text-embedding-3-large` | 3072 | Azure OpenAI API | Pay-per-use |

**Important notes:**
- Changing the embedding model only affects **newly ingested documents** — existing embeddings are preserved
- Azure embedding models require `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` to be configured in `.env`
- For best results, re-ingest documents after changing the embedding model (mixing different embedding dimensions in the same session can degrade search quality)
- The active model is stored in the `platform_settings` database table and persists across restarts

**Backend API endpoints (admin-only):**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/admin/settings` | Get current embedding model and available options |
| `PUT` | `/admin/settings/embedding-model` | Update the active embedding model |

### Knowledge Base
- Upload files: PDF, PPTX, JPG/PNG, TXT (up to 50 MB each)
- Add web URLs (page is fetched and ingested automatically)
- Paste text directly (up to 50,000 chars; does not count toward the 10-source limit)
- Automatic text extraction (OCR fallback for images via Tesseract), chunking (1000 chars / 200 overlap), and embedding (model configurable by admin)

### Agentic Chat
The LangGraph graph runs 10 nodes per request:

```
analyze_input → [clarify? or] → build_plan → choose_skills
  → retrieve_context → decide_code_execution
  → [run_tools_or_code?] → revise_plan → compose_answer → persist_memory
```

- Skills are selected **before** retrieval so skill-based context can inform the search
- Skills are executed using the code template in their `SKILL.md`, adapted with real content by the LLM
- Output files from skills (e.g. `.pptx`) are automatically registered as downloadable artifacts

### Skills
- Upload a `.zip` containing a `SKILL.md` with YAML frontmatter (`name`, `description`, `version`) and a `python` code block
- Automatic 12-point validation (path traversal, dangerous code patterns, extension allowlist)
- Enable/disable globally or per-session
- Example: `generate_pptx` skill generates a PowerPoint from session knowledge base content

### Artifacts
Downloadable files generated during a session:

| Type | How created |
|------|------------|
| PDF | Via POST `/sessions/{id}/artifacts/generate` |
| CSV | Via POST `/sessions/{id}/artifacts/generate` |
| XLSX | Via POST `/sessions/{id}/artifacts/generate` |
| PPTX | Automatically when the `generate_pptx` skill runs |

Download via `GET /artifacts/{artifact_id}/download`.

---

## Troubleshooting

**Backend fails to start — "could not connect to server"**
PostgreSQL hasn't finished initializing. Docker Compose waits for the healthcheck but on first run this can take 30–60 seconds. Run `docker compose logs postgres` to check.

**`GEMINI_API_KEY` error on first message**
Make sure `.env` contains a valid key and you ran `docker compose up` after setting it (not just `docker compose restart`).

**Frontend shows "Network Error"**
The frontend expects the backend at `http://localhost:8000`. Confirm the backend container is running: `docker compose ps`.

**Skill validation fails**
Ensure the ZIP has `SKILL.md` at the top level (not inside a subdirectory) with valid YAML frontmatter fields `name`, `description`, and `version`.

**Azure OpenAI model not working**
Ensure `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` are set in `.env`. Verify that the deployment name (`AZURE_OPENAI_GPT_DEPLOYMENT`) matches your Azure portal configuration. Restart with `docker compose up --build` after changes.

**Admin page not accessible**
The `/admin` page is restricted to admin users. Log in with the seeded admin account (`admin / admin$123`) or set `is_admin=true` for your user in the database.

**Code execution disabled**
Set `ENABLE_CODE_EXECUTION=true` in `.env` and restart the backend.

---

## Documentation

Detailed documentation in [`assets/doc/`](assets/doc/):

- [`01_api_reference.md`](assets/doc/01_api_reference.md) — Full REST API reference
- [`02_agentic_architecture.md`](assets/doc/02_agentic_architecture.md) — LangGraph node descriptions, state, skill integration
- [`03_solution_diagram.md`](assets/doc/03_solution_diagram.md) — System architecture and request flow diagrams
- [`04_updated_prd.md`](assets/doc/04_updated_prd.md) — Product requirements and implementation decisions
