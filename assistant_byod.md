# assistant_byod.md

## Role
You are Claude Code. Build a working **Dockerized PoC** for a **multi-user, session-isolated, NotebookLM-lite + agentic research chat** application.

This document is the **single source of truth** for the PoC. Unless you are blocked by a hard implementation conflict, **do not ask follow-up questions**. Make reasonable engineering decisions consistent with this spec and proceed.

If you must ask something, ask only when a decision would materially change architecture or violate a non-negotiable requirement.

---

## 1) Product Summary
Build a lightweight research assistant where users can:
- sign up and log in with local username/password
- create multiple private sessions
- upload their own files and web URLs into a session knowledge base
- paste text directly into a session knowledge base
- chat over only that session’s content
- use an agent that plans, replans, asks clarifying questions when required, and remembers session context
- upload private skill ZIPs for their own use
- enable/disable skills at any time
- run generated Python and JavaScript code for task completion in a sandbox
- export outputs as PDF, CSV, and XLSX

This is a **PoC**, but it must be cleanly structured so it can be extended later.

---

## 2) Non-Negotiable Requirements

### 2.1 Multi-user and session isolation
Isolation is the most important requirement.
- Different users must never access each other’s sessions, files, vectors, chat history, artifacts, or skills.
- The same user’s different sessions must also be isolated by default.
- Content from one session must not appear in another session unless it is explicitly re-added.
- Retrieval must always be constrained by both `user_id` and `session_id`.

### 2.2 Base content types
Users must be able to add these source types to a session:
- PDF
- PPTX
- JPG / JPEG
- PNG
- TXT
- pasted text
- web URL

### 2.3 Limits
- Maximum **10 uploaded files + URLs combined per session**.
- Pasted text is allowed in the knowledge base as a separate source type and does **not** count toward the 10 file/URL cap, but should have a sensible max size per entry.
- Reject uploads exceeding configured size limits.

### 2.4 Agent behavior
The assistant must behave like a lightweight deep research / deep agent system:
- understand the user request
- decide whether clarification is needed
- generate a plan
- retrieve evidence from the session knowledge base
- optionally call tools, skills, or code execution
- revise the plan if intermediate results change the path
- answer with grounded references to session sources
- remember prior turns in the same session so the user can ask for refinement

### 2.5 Skill support
Users must have a **separate skill management section/page** where they can:
- upload skill ZIP files
- see all of their own uploaded skills
- inspect skill details
- see validation status
- see whether the skill is active or inactive
- enable or disable skills at any time
- delete their own skills

Skills are private to the owning user.

### 2.6 Local resources for the PoC
Use local/self-hosted components for the PoC:
- PostgreSQL for app metadata and state
- ChromaDB (or equivalent local vector DB) for chunk embeddings and retrieval
- local file storage volume for uploaded files and generated artifacts
- local ID/password authentication
- Gemini API key from `.env`

### 2.7 Docker-first
The project must be Dockerized so it can be started with Docker Compose and later hosted on a free or low-cost environment for PoC purposes.

### 2.8 Admin seed user
Create a seeded test user automatically on first startup:
- username: `admin`
- password: `admin$123`

This is for PoC verification only.

---

## 3) Clarified Interpretation of Ambiguous Requirements
These decisions are intentional and should be treated as resolved.

### 3.1 Source limits
Original requirement mentioned max 10 files/web URLs and also allowed pasted text. To avoid ambiguity:
- enforce max 10 for **uploaded files + URLs combined** per session
- allow pasted text separately with a configured size cap per entry

### 3.2 Deep Agents SDK + LangGraph + skills
Use **Deep Agents SDK + LangGraph as the core runtime**.

Interpretation for this PoC:
- **Deep Agents SDK** is the primary agent harness for deep planning, task decomposition, iterative execution, optional subagents, and tool-using agent behavior.
- **LangGraph** remains the underlying orchestration/state layer for memory, checkpoints, thread/session state, and durable execution.
- The application must be built so Deep Agents runs on top of LangGraph-backed state and session persistence.

For skills, do **not** invent an unrelated skill system if the SDK already supports a skills concept. Instead, implement **user-uploaded skill ZIPs as a private app-layer packaging and validation flow that unpacks into Deep-Agents-compatible skill directories** for that user. The upload format is ZIP, but the runtime exposure should align as closely as practical with the Deep Agents skills pattern.

### 3.3 Multi-agent architecture
A multi-agent architecture is optional, not mandatory.
- Start with a **single orchestrator graph** with planner / retriever / tool / composer stages.
- Add sub-agents only where it clearly improves the design, such as computation or writing specialization.

### 3.4 Memory scope
Session memory must be scoped to a single session/thread.
Do not create cross-session memory for the same user in the base version.

### 3.5 Exports
Users should be able to create:
- PDF reports
- CSV tables
- XLSX workbooks

These outputs may be generated either from retrieved content, transformed data, or code execution results inside the session.

---

## 4) Recommended Tech Stack

### Backend
- Python 3.11+
- FastAPI
- SQLAlchemy + Alembic
- Pydantic settings

### Frontend
- Next.js or React frontend (prefer Next.js)
- clean but simple UI

### State / DB
- PostgreSQL for relational data
- ChromaDB for vector retrieval
- local persistent storage volumes for uploads / artifacts / skill bundles

### Agent Runtime
- Deep Agents SDK as the primary agent harness
- LangGraph as the underlying orchestration, persistence, and memory/checkpointing runtime
- Gemini API for model calls
- provider abstraction for future model replacement

### Execution
- sandboxed Python execution
- sandboxed Node.js / JavaScript execution

### Deployment
- Docker Compose

---

## 5) Product Architecture

### 5.1 High-level components
Implement these services/components:
1. **frontend**
2. **backend API**
3. **ingestion worker**
4. **agent worker**
5. **postgres**
6. **chroma**
7. **sandbox runner** for Python/JS code execution

For PoC simplicity, ingestion and agent worker may initially run in the backend process using background tasks, but structure the code so they can be split into separate worker containers later.

### 5.2 Architectural principle
Every important object must be bound to both:
- `user_id`
- `session_id` when session-scoped

This includes:
- sources
- chunks
- messages
- agent runs
- artifacts
- session skill activations
- code execution outputs

---

## 6) Core Features

## 6.1 Authentication
Implement local authentication with username/password.
Requirements:
- sign up
- sign in
- sign out
- hashed passwords
- JWT or secure session cookies
- authenticated API access
- basic route protection in frontend

Also seed the default admin user at startup if it does not already exist.

## 6.2 Session management
Users can:
- create session
- rename session
- view session list
- archive session
- delete session

Each session has:
- title
- chat history
- sources
- retrieval index
- session memory
- enabled skills
- generated artifacts

## 6.3 Knowledge base / source ingestion
Support source ingestion for:
- PDF
- PPTX
- image files (JPG / JPEG / PNG)
- TXT
- pasted text
- web URL

Behavior:
- validate source type
- save metadata
- extract text/content
- normalize content
- chunk content
- embed chunks
- store vectors in Chroma
- persist source metadata in PostgreSQL
- track source status: `pending`, `processing`, `complete`, `failed`

### 6.3.1 URL ingestion
When a user adds a URL:
- fetch the page
- extract readable main content
- remove obvious boilerplate where possible
- store page title, URL, fetch time
- chunk and index cleaned content

### 6.3.2 Image / scanned content
Do best-effort extraction from images and image-heavy PDFs.
If extraction quality is low, surface that limitation in metadata or logs.

## 6.4 Retrieval / RAG
Implement session-scoped RAG.
Requirements:
- only search within the current session’s knowledge base
- chunk documents rather than sending all source content directly to the model
- top-k retrieval with metadata
- citations or source references in final answers
- retrieval filters must include session ownership constraints

### Preferred Chroma strategy
Prefer **one collection per session** for the PoC, with metadata also storing `user_id` and `session_id`.
This is simpler and safer than broad shared collections.

## 6.5 Agentic chat engine
Build the chat engine using **Deep Agents SDK on top of LangGraph**.

Suggested runtime shape:
1. request analysis
2. clarification check
3. planning / todo decomposition
4. retrieval
5. skill selection
6. code/tool decision
7. execution
8. replanning
9. answer composition
10. memory/checkpoint update

The implementation may wrap Deep Agents inside application services, but the core agent behavior must come from **Deep Agents + LangGraph**, not from a completely custom planner loop.

### Required behaviors
- ask for clarification if needed
- show or store plan structure
- replan when intermediate results change the path
- remember prior turns in same session
- support “refine the previous answer” or “turn this into a report” style follow-ups

### Clarification examples
Ask follow-up questions when the request is materially ambiguous, such as:
- “compare these” when multiple candidate sources are unclear
- “make a report” without format, audience, or purpose
- “analyze this” without clear expected output

### Output behavior
Final answers should, where possible, include:
- answer
- concise supporting evidence summary
- source references
- artifact links if generated
- assumptions if necessary

## 6.6 Skills
This is a first-class feature, not an afterthought.

### 6.6.1 Dedicated skill management page
Create a **separate page/section** for skills, such as `/skills`.

The page must allow users to:
- upload skill ZIP
- view all their own skills
- inspect skill details
- see validation status
- see active/inactive status
- enable/disable skills at any time
- delete skills

### 6.6.2 Skill ownership and privacy
Skills are user-private.
Rules:
- a user can only see their own skills
- a user can only modify their own skills
- a user can only enable/use their own skills
- a user cannot see, use, or modify another user’s skills through UI or API

### 6.6.3 Skill model
Implement skills as **user-uploaded ZIP packages that unpack into a Deep-Agents-compatible private skill directory**.

Preferred approach:
- uploaded file format is `.zip`
- after validation, unzip into a per-user controlled directory
- each unpacked skill should follow the **Deep Agents skill directory pattern**, centered on `SKILL.md` and any supporting files needed by that skill
- store app metadata in PostgreSQL so the UI can list ownership, validation, status, and enablement

Do not assume arbitrary executable code inside a skill ZIP is trusted.

### 6.6.4 Skill upload validation
During upload, validate at minimum:
1. valid ZIP archive
2. max file size
3. safe extraction (prevent zip-slip/path traversal)
4. required top-level skill definition file, preferably `SKILL.md`
5. valid skill metadata/frontmatter if the uploaded skill format uses it
6. valid folder structure for the expected Deep Agents skill layout
7. required human-readable skill identity fields such as name/description/version where applicable
8. referenced supporting files exist
9. only allowed internal file types are present
10. reject suspicious executable content for PoC
11. avoid blind dependency installation
12. record validation errors clearly

### 6.6.5 Skill states
Use explicit statuses such as:
- `uploaded`
- `validating`
- `valid`
- `invalid`
- `enabled`
- `disabled`
- `failed`

### 6.6.6 Skill activation model
Implement two layers:
- **global skill ownership/status** per user
- **session-level enable/disable** for using a valid skill in a specific session

This means:
- the skill exists in the user’s skill library
- the user can globally disable it
- the user can enable/disable it for an individual session

## 6.7 Code generation and execution
The assistant must be able to generate and run code for task completion.
Support:
- Python
- JavaScript

### Requirements
- run code in a sandbox
- no unrestricted host filesystem access
- timeout
- memory limits
- no unrestricted outbound network by default
- capture stdout/stderr
- capture generated files
- store run metadata

### Allowed use cases
- data transformation
- table extraction
- summarization helpers
- analysis on structured content
- creating CSV/XLSX outputs
- report preparation

### Do not allow by default
- arbitrary shell access
- unrestricted package installation during runtime
- reading arbitrary host files
- long-running background jobs

## 6.8 Artifact generation
Users must be able to generate downloadable:
- PDF
- CSV
- XLSX

Artifacts must be stored per session and per user.
Users must only see their own artifacts.

---

## 7) Data Model
Implement a relational schema similar to the following.
Names can vary slightly if the final implementation remains clean and equivalent.

### users
- id
- username
- password_hash
- is_active
- is_admin (optional for seed user convenience)
- created_at
- updated_at

### sessions
- id
- user_id
- title
- status
- created_at
- updated_at
- archived_at nullable

### messages
- id
- session_id
- user_id
- role
- content
- structured_payload json/jsonb nullable
- created_at

### sources
- id
- user_id
- session_id
- source_type
- display_name
- original_filename nullable
- source_url nullable
- local_path nullable
- ingest_status
- content_hash nullable
- created_at
- updated_at

### source_chunks_metadata
- id
- source_id
- user_id
- session_id
- chunk_index
- vector_ref
- metadata json/jsonb

### skills
- id
- user_id
- name
- version
- description
- skill_metadata_json
- install_status
- validation_status
- validation_errors json/jsonb nullable
- is_globally_enabled
- storage_path
- uploaded_at
- updated_at

### session_skills
- id
- session_id
- skill_id
- is_enabled
- created_at
- updated_at

### agent_runs
- id
- user_id
- session_id
- user_message_id nullable
- status
- current_plan json/jsonb nullable
- final_summary nullable
- started_at
- completed_at nullable

### tool_runs
- id
- agent_run_id
- tool_name
- input_json
- output_json nullable
- status
- created_at

### artifacts
- id
- user_id
- session_id
- artifact_type
- display_name
- file_path
- metadata json/jsonb nullable
- created_at

---

## 8) Vector Store Design
Preferred design for PoC:
- one Chroma collection per session
- collection name derived from session id
- chunk metadata also stores user/session/source attributes

Store metadata at least:
- `user_id`
- `session_id`
- `source_id`
- `source_type`
- `chunk_index`
- `source_name`
- `created_at`

Never query a collection that is not bound to the active session.

---

## 9) API Requirements
Design REST APIs that cover at least the following.

## 9.1 Auth
- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

## 9.2 Sessions
- `GET /sessions`
- `POST /sessions`
- `GET /sessions/{session_id}`
- `PATCH /sessions/{session_id}`
- `DELETE /sessions/{session_id}`

## 9.3 Sources
- `GET /sessions/{session_id}/sources`
- `POST /sessions/{session_id}/sources/upload`
- `POST /sessions/{session_id}/sources/url`
- `POST /sessions/{session_id}/sources/text`
- `DELETE /sessions/{session_id}/sources/{source_id}`

## 9.4 Chat
- `GET /sessions/{session_id}/messages`
- `POST /sessions/{session_id}/chat`
- `GET /sessions/{session_id}/agent-runs/{run_id}`

## 9.5 Skills
- `GET /skills`
- `POST /skills/upload`
- `GET /skills/{skill_id}`
- `POST /skills/{skill_id}/enable`
- `POST /skills/{skill_id}/disable`
- `DELETE /skills/{skill_id}`
- `POST /skills/{skill_id}/validate` (optional but recommended)
- `POST /sessions/{session_id}/skills/{skill_id}/enable`
- `POST /sessions/{session_id}/skills/{skill_id}/disable`

All skill routes must verify ownership.

## 9.6 Artifacts
- `GET /sessions/{session_id}/artifacts`
- `POST /sessions/{session_id}/artifacts/generate`
- `GET /artifacts/{artifact_id}/download`

---

## 10) Frontend Requirements
Build a basic but usable UI.

### Required screens
1. login / signup
2. session list / dashboard
3. session workspace
4. skills page
5. artifact downloads view or artifacts panel

### Session workspace layout
Recommended layout:
- left panel: session list or source list
- main panel: chat
- right panel or tabs: plan / sources / artifacts / skill status

### Required UX
- users can see source ingestion status
- users can add files, URLs, and pasted text
- users can see chat history
- users can see available artifacts for the session
- users can inspect skills from a dedicated screen
- users can toggle session skill activation
- users can clearly tell which sources were used in an answer

---

## 11) Security and Guardrails
Implement pragmatic PoC security, especially around isolation, file handling, skill ZIPs, and code execution.

### 11.1 Access control
- every DB query must be ownership filtered
- every session lookup must validate current user
- every artifact, source, and skill download must validate ownership

### 11.2 File upload safety
- allowlist file types
- max upload size
- safe filenames
- per-user / per-session storage directories
- fail safely on malformed files

### 11.3 Skill ZIP safety
- validate ZIP structure
- prevent path traversal
- reject suspicious files
- do not blindly install arbitrary dependencies from skill package

### 11.4 Code sandbox safety
- timeout
- memory cap
- isolated temp directory
- no unrestricted host access
- no unrestricted network by default

---

## 12) Environment Variables
Provide a `.env.example` with at least:

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
CHROMA_PERSIST_DIR=/data/chroma

GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

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

## 13) Seed Data / Bootstrap
During startup or first migration/seed:
- create schema
- run Alembic migrations
- create admin user if it does not exist

Seed user:
- username: `admin`
- password: `admin$123`

Do not recreate or overwrite if already present.

---

## 14) Delivery Requirements
Claude Code should generate:
- backend source code
- frontend source code
- database models and Alembic migrations
- Dockerfiles
- `docker-compose.yml`
- `.env.example`
- basic seed script
- README with local setup steps

The project should be startable with a command equivalent to:
- `docker compose up --build`

---

## 15) Recommended Folder Structure
Use a clean structure similar to this:

```text
repo/
  backend/
    app/
      api/
      core/
      db/
      models/
      schemas/
      services/
      agents/
      skills/
      ingestion/
      execution/
      utils/
      main.py
    alembic/
    Dockerfile
    requirements.txt
  frontend/
    app/ or src/
    components/
    lib/
    Dockerfile
  storage/
    uploads/
    artifacts/
    skills/
  docker-compose.yml
  .env.example
  README.md
```

---

## 16) Agent Implementation Guidance
Use **Deep Agents SDK + LangGraph** for the core orchestration/runtime.

### Suggested graph state
State may include:
- current user message
- session id
- user id
- retrieved chunks
- proposed plan
- clarification needed flag
- selected tools/skills
- execution outputs
- final answer draft
- citation/source list

### Suggested nodes
- analyze_input
- clarify_if_needed
- build_plan
- retrieve_context
- choose_skills
- decide_code_execution
- run_tools_or_code
- revise_plan
- compose_answer
- persist_memory

### Memory behavior
- maintain session-scoped conversation continuity
- persist checkpoints/state
- do not share memory across sessions in base version

### Tool/skill routing behavior
- only expose skills that belong to the authenticated user
- only expose session-enabled skills for that session
- only retrieve from the active session

---

## 17) Implementation Guidance for Skills
Implement skills in a way that is practical for the PoC.

### 17.1 Deep Agents-compatible skill package
A valid uploaded skill should be convertible into a **Deep Agents-compatible skill directory**.

Preferred contents:
- `SKILL.md` as the primary skill definition
- any supporting prompt/resource/example files referenced by the skill
- optional metadata files if the app needs them for indexing or UI display

### 17.2 Skill loading
- unpack to a controlled directory
- validate skill structure
- parse `SKILL.md` and any app metadata needed for the UI
- store skill metadata in DB
- mark valid or invalid
- do not execute invalid skills

### 17.3 Runtime exposure
Skills should be surfaced to the agent only if:
- the skill belongs to the current user
- the skill is globally enabled
- the skill is enabled for the current session
- validation status is valid

---

## 18) Acceptance Criteria
The implementation is complete only if the following are demonstrably true.

### Isolation
1. User A cannot access User B’s sessions, sources, artifacts, or skills.
2. Session A and Session B of the same user are isolated by default.
3. Retrieval from one session never uses content from another session.

### Ingestion
4. Users can upload supported files and add URLs.
5. URL content is fetched, extracted, chunked, and retrievable.
6. Pasted text can be added to the session knowledge base.

### Chat / agent
7. The agent can answer grounded questions over session data.
8. The agent can ask clarification questions when needed.
9. The agent can support “refine previous answer” in the same session.
10. The agent can maintain a plan and revise it during execution.

### Skills
11. Users have a dedicated skills page.
12. Users can upload a skill ZIP.
13. Skill ZIP validation is enforced.
14. Invalid skills cannot be executed.
15. Users can see their own skill details and status.
16. Users can enable/disable skills at any time.
17. Users cannot see or modify another user’s skills.

### Code execution
18. Python and JavaScript execution works in a sandbox.
19. Execution outputs can be used in final responses.

### Artifacts
20. Users can generate PDF, CSV, and XLSX outputs.
21. Users can download only their own artifacts.

### Deployment
22. The stack runs through Docker Compose.
23. The seeded admin user can log in after first startup.

---

## 19) Recommended Build Order
Implement in this order unless there is a better dependency-aware sequence:

### Phase 1
- repo scaffolding
- backend app setup
- frontend app setup
- Docker Compose
- PostgreSQL + Alembic
- authentication
- admin seed user

### Phase 2
- session CRUD
- source metadata tables
- upload endpoints
- local file storage

### Phase 3
- content extraction
- chunking
- embeddings
- Chroma storage
- retrieval pipeline

### Phase 4
- Deep Agents SDK + LangGraph chat orchestration
- session memory/checkpoints
- clarification + plan + replanning

### Phase 5
- skill ZIP upload
- skill validation
- skill library UI
- session skill enable/disable

### Phase 6
- sandboxed code execution
- artifact generation
- polish and README

---

## 20) Important Engineering Notes
- Keep model provider calls behind an abstraction like `LLMProvider`.
- Keep vector store calls behind an abstraction like `KnowledgeStore`.
- Keep skill loading/validation behind a dedicated service.
- Keep code execution isolated from API request handlers.
- Prefer explicit typing and clean service boundaries.
- Use structured logging for agent runs, tool runs, ingestion steps, and failures.
- Make implementation readable and extendable, not just minimally working.

---

## 21) What Not to Do
- Do not merge knowledge across sessions.
- Do not make skills globally visible across users.
- Do not blindly trust skill ZIP contents.
- Do not send all uploaded documents into the model context on every turn.
- Do not rely on only frontend checks for security.
- Do not hardcode the Gemini API key in source code.
- Do not build a fake planning agent; implement an actual planner/replanner flow.

---

## 22) Final Build Instruction
Build the full PoC described above and generate a working repository that is locally runnable with Docker Compose.

**Mandatory core runtime requirement:** use **Deep Agents SDK + LangGraph as the core agent foundation**.
- Deep Agents SDK must be the primary harness for planning, task decomposition, iterative execution, tool use, optional subagents, and deep-agent style behavior.
- LangGraph must remain the underlying runtime for orchestration, persistence, session/thread state, checkpoints, and durable memory.
- Do not replace this with a fully custom planner loop unless a very small wrapper is needed around the SDK/runtime.
- Skill ZIP uploads should validate and unpack into **user-private Deep-Agents-compatible skill directories**.

If any low-level library choice is ambiguous, prefer the option that:
1. preserves user/session isolation most cleanly,
2. keeps the implementation understandable,
3. minimizes hidden magic,
4. is easiest to extend later.

Proceed with implementation. Ask questions only if you hit a true blocker.
