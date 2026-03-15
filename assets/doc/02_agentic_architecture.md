# Agentic Architecture - Assistant PoC

## Overview

The agent is implemented as a **single-orchestrator LangGraph StateGraph** — referred to internally as the "Deep Agents SDK" pattern. It is a planner-executor loop where one graph drives the full request lifecycle: from intent analysis through RAG retrieval, optional code execution, plan revision, and final answer composition.

There is deliberately **no multi-agent architecture** in the base version. The PRD specifies this as the correct starting point, with sub-agents added only where they clearly improve the design.

---

## Core Frameworks

| Component | Library | Version | Role |
|-----------|---------|---------|------|
| Graph orchestration | `langgraph` | ≥ 0.2.28 | StateGraph, node routing, checkpointing |
| LLM calls | `langchain-google-genai` / `langchain-openai` | ≥ 2.0.5 / ≥ 0.2.0 | Gemini or Azure OpenAI via LangChain |
| LLM model | Google Gemini **or** Azure OpenAI GPT | Per-session selection | All reasoning, planning, answering |
| Embeddings | `sentence-transformers` / `openai` | 2.7.0 / ≥ 1.40 | MiniLM-L6-v2 (local) **or** Azure text-embedding-3-small/large (admin-configurable) |
| Vector store | `chromadb` | ≥ 1.0.0 | Per-session collections |
| Memory / checkpoints | `langgraph.checkpoint.memory.MemorySaver` | built-in | In-process, per-session thread |

---

## Agent State

All nodes read from and write to a single shared `AgentState` TypedDict. It is the sole communication channel between nodes.

```python
class AgentState(TypedDict):
    # Input
    user_message: str           # current user turn
    session_id: str             # scopes all retrieval and memory
    user_id: str                # scopes all DB and file access
    agent_run_id: str           # UUID for this run, stored in DB

    # Context loaded before graph entry
    messages: List[dict]        # prior conversation [{role, content}, ...]
    active_skills: List[dict]   # skills loaded for this user+session
    llm_provider: str           # "gemini" or "azure_openai" — set from session.llm_model

    # Populated by nodes
    retrieved_chunks: List[dict]        # Chroma search results
    current_plan: List[str]             # step-by-step plan
    clarification_needed: bool          # whether to ask user
    clarification_question: str | None  # the question to ask
    selected_skills: List[str]          # skill names chosen for this run
    code_execution_needed: bool         # whether sandbox code will run
    execution_outputs: List[dict]       # stdout/stderr/exit_code per run
    final_answer: str | None            # composed answer
    citations: List[dict]               # source references in the answer
    plan_revision_count: int            # guard against infinite revision loops
    error: str | None                   # last error if any
```

---

## Graph Topology

```
                          ┌─────────────────────┐
                          │    analyze_input     │  ← entry point
                          │  (intent + clarity)  │
                          └──────────┬───────────┘
                                     │
                   ┌─────────────────┴──────────────────┐
                   │ clarification_needed?               │
                   ▼ yes                                 ▼ no
       ┌───────────────────────┐            ┌───────────────────────┐
       │   clarify_if_needed   │            │      build_plan       │
       │ (sets final_answer =  │            │ (3-6 step task list)  │
       │  clarification Q)     │            └───────────┬───────────┘
       └───────────┬───────────┘                        │
                   │                                    ▼
                   │                       ┌───────────────────────┐
                   │                       │    choose_skills      │
                   │                       │ (LLM selects from     │
                   │                       │  active_skills list)  │
                   │                       └───────────┬───────────┘
                   │                                   │
                   │                                   ▼
                   │                       ┌───────────────────────┐
                   │                       │   retrieve_context    │
                   │                       │ (Chroma top-k search) │
                   │                       └───────────┬───────────┘
                   │                                   │
                   │                                   ▼
                   │                       ┌───────────────────────┐
                   │                       │ decide_code_execution │
                   │                       │ (keyword heuristic +  │
                   │                       │  LLM intent check)    │
                   │                       └───────────┬───────────┘
                   │                                   │
                   │                  ┌────────────────┴───────────────────┐
                   │                  │ code_execution_needed?             │
                   │                  ▼ yes                                ▼ no
                   │     ┌────────────────────────┐                       │
                   │     │   run_tools_or_code    │                       │
                   │     │ (LLM generates Python  │                       │
                   │     │  or JS → subprocess    │                       │
                   │     │  sandbox execution)    │                       │
                   │     └────────────┬───────────┘                       │
                   │                  │                                   │
                   │                  ▼                                   │
                   │     ┌────────────────────────┐                       │
                   │     │      revise_plan       │ (if revision_count<1) │
                   │     │ (LLM checks if plan    │◄──────────────────────┘
                   │     │  needs updating after  │     (also reached if
                   │     │  seeing retrieved ctx) │      no code needed)
                   │     └────────────┬───────────┘
                   │                  │
                   │     ┌────────────┴────────────────────────┐
                   │     │ needs more retrieval?               │
                   │     ▼ yes (count<2)                       ▼ no
                   │  retrieve_context (loop)       ┌──────────────────────┐
                   │                                │   compose_answer     │
                   │                                │ (LLM with context,   │
                   │                                │  history, plan,      │
                   │                                │  exec results →      │
                   │                                │  markdown + cites)   │
                   │                                └──────────┬──────────-┘
                   │                                           │
                   └───────────────────────────────────────────┤
                                                               ▼
                                                   ┌──────────────────────┐
                                                   │   persist_memory     │
                                                   │ (no-op in graph;     │
                                                   │  DB writes handled   │
                                                   │  by agent_service)   │
                                                   └──────────┬──────────-┘
                                                              │
                                                             END
```

---

## LLM Provider Routing

Every node that makes an LLM call reads `state["llm_provider"]` and passes it to the shared `_llm_call(prompt, system, provider)` helper. This helper delegates to `get_llm(provider)` in `llm_provider.py`, which returns either:

- **`gemini`** → `ChatGoogleGenerativeAI` (via `langchain-google-genai`)
- **`azure_openai`** → `AzureChatOpenAI` (via `langchain-openai`)

The provider is set once at session creation time (stored in `sessions.llm_model`), loaded by `agent_service.py`, and injected into `AgentState.llm_provider`. It cannot change during a session's lifetime.

**Nodes that use the LLM provider:** `analyze_input`, `build_plan`, `choose_skills`, `run_tools_or_code` (code generation + skill adaptation), `revise_plan`, `compose_answer`.

**Nodes that do NOT call the LLM:** `clarify_if_needed`, `retrieve_context`, `decide_code_execution`, `persist_memory`.

---

## Node Descriptions

### 1. `analyze_input`
**Purpose:** Classify the user's request and decide whether it is clear enough to act on.

**LLM call:** Yes — structured JSON output.

**Output fields set:** `clarification_needed`, `clarification_question`

**Prompt pattern:**
```
Analyze this message. Respond in JSON:
{
  "is_clear": true/false,
  "needs_clarification": true/false,
  "clarification_question": "..." or null,
  "intent_summary": "..."
}
```

**Clarification is triggered when:**
- Request references "these" or "this" without specifying which source
- "Make a report" without format/audience/scope
- "Analyze this" without specifying expected output
- Ambiguous comparison ("compare these two")

---

### 2. `clarify_if_needed`
**Purpose:** When clarification is needed, set `final_answer` to the clarification question and route to `persist_memory` → END. The agent halts and returns the question to the user.

**LLM call:** No — uses `clarification_question` from previous node.

---

### 3. `build_plan`
**Purpose:** Decompose the user request into 3–6 concrete, ordered steps.

**LLM call:** Yes — structured JSON output.

**Output fields set:** `current_plan`, `plan_revision_count = 0`

**Prompt pattern:**
```
Create a step-by-step plan. Respond in JSON:
{ "plan": ["Step 1: ...", "Step 2: ...", ...] }
```

Active skill names are injected into this prompt so the planner can include skill-related steps.

---

### 4. `choose_skills`
**Purpose:** From the list of active skills for this user+session, select which are relevant for the current request. Running this before retrieval allows skill-based sources (web search, APIs, databases) to inform what gets retrieved.

**LLM call:** Yes — structured JSON output.

**Input:** `active_skills` (loaded before graph entry by `agent_service`)

**Output fields set:** `selected_skills` (list of skill names)

Skills are surfaced to the agent only if:
- Owned by the current user
- `is_globally_enabled = True`
- `validation_status = "valid"`
- Session-level `is_enabled = True` (or no session override, defaults to enabled)

---

### 5. `retrieve_context`
**Purpose:** Semantic search of the session's Chroma collection. Never crosses session boundaries.

**LLM call:** No.

**Search query:** `user_message + first 3 plan steps` (concatenated for broader coverage)

**Output fields set:** `retrieved_chunks` (list of `{text, metadata, distance}`)

**ChromaDB collection:** `session_{session_id}` — strictly one collection per session.

**Embedding model:** Configurable by admin. Default: `sentence-transformers/all-MiniLM-L6-v2` (384-dim, local). Options: Azure OpenAI `text-embedding-3-small` (1536-dim) or `text-embedding-3-large` (3072-dim).

**Top-k:** 8 chunks retrieved, top 6 used in the answer.

---

### 6. `decide_code_execution`
**Purpose:** Determine whether Python/JS code needs to be generated and executed.

**LLM call:** No.

**Trigger logic (priority order):**
1. If `selected_skills` is non-empty → always `True` (skills ARE code)
2. Keyword heuristic on `user_message`: `calculate`, `compute`, `plot`, `chart`, `analyze data`, `run`, `script`, `code`, `python`, `csv`, `excel`, `statistics`, `sort`, `filter`, `transform`

**Output fields set:** `code_execution_needed`

Can be disabled globally via `ENABLE_CODE_EXECUTION=false` in `.env`. When disabled, skill execution is also bypassed.

---

### 7. `run_tools_or_code`
**Purpose:** Execute skill templates or generate ad-hoc code for general computation tasks.

**LLM call:** Yes — either adapts a skill template or generates code from scratch.

**Two execution paths:**

**Path A — Skill execution** (when `selected_skills` is non-empty):
1. Looks up each selected skill in `active_skills` by name
2. Extracts the first ` ```python ``` ` block from `skill_content` (SKILL.md)
3. Calls the LLM to adapt the template: replaces placeholder content with real data from `retrieved_chunks` and `user_message`
4. Executes adapted code in the subprocess sandbox
5. Parses `stdout` as JSON to extract `output_path` (skills print `{"status": "success", "output_path": "..."}`)
6. Stores `output_file` path in `execution_outputs` for post-graph artifact registration

**Path B — General code generation** (no skills selected):
1. LLM generates Python code from scratch using user message + retrieved context
2. Executes in sandbox
3. No file output handling

**Sandbox execution:** `subprocess.run()` with:
- Configurable timeout (`MAX_CODE_EXEC_SECONDS`, default 20s)
- Isolated temp directory
- Stdout/stderr captured

**Output fields set:** `execution_outputs` (list of `{skill_name, code, stdout, stderr, exit_code, success, output_file}`)

Supports both Python and JavaScript (Node.js installed in the backend container).

---

### 8. `revise_plan`
**Purpose:** After seeing retrieved context (and optionally execution results), decide if the plan needs updating.

**LLM call:** Yes — structured JSON output.

**Revision guard:** `plan_revision_count` caps re-retrieval at 2 iterations to prevent infinite loops.

**Output fields set:** updated `current_plan`, incremented `plan_revision_count`

---

### 9. `compose_answer`
**Purpose:** Generate the final user-facing answer in Markdown, grounded in retrieved chunks and execution results.

**LLM call:** Yes — free-form Markdown output.

**Context injected:**
- Last 10 messages from conversation history
- Up to 6 retrieved chunks with source labels `[Source N: filename]`
- Skill execution summary — explicitly states whether each skill succeeded, failed, and whether a file was produced (e.g. "✅ Skill 'generate_pptx' executed successfully and produced a file: /tmp/output_presentation.pptx. This file has been saved and will be available as a downloadable artifact.")
- Full plan

**Output fields set:** `final_answer`, `citations`

**Citation format:**
```json
{
  "source_id": "uuid",
  "source_name": "report.pptx",
  "chunk_index": 2,
  "excerpt": "first 300 chars of chunk..."
}
```

---

### 10. `persist_memory`
**Purpose:** No-op node in the graph. All DB writes (saving messages, updating agent_run record) are handled by `agent_service.py` around the graph invocation, not inside the graph itself. This separation keeps the graph stateless with respect to DB I/O.

---

## Memory Management

### Session Memory (Conversation History)
- **Storage:** PostgreSQL `messages` table
- **Scope:** Per session — `session_id` + `user_id` composite filter
- **Loading:** `agent_service.py` loads the last 20 messages before invoking the graph and injects them into `AgentState.messages`
- **Persistence:** After the graph returns, `agent_service.py` writes the new user and assistant messages to the DB
- **Cross-session:** Explicitly **not** shared. Each session is isolated.

### LangGraph Checkpoints (Graph State)
- **Checkpointer:** `MemorySaver` (in-process Python dict)
- **Thread ID:** `session_id` — each session has its own checkpoint thread
- **Scope:** Process lifetime only (resets on backend restart)
- **Purpose:** Allows LangGraph to resume a graph midway if interrupted, and enables future streaming support
- **Limitation for PoC:** In-memory only; a production version should use `langgraph.checkpoint.postgres.PostgresSaver`

### RAG / Vector Memory
- **Storage:** ChromaDB, one collection per session: `session_{session_id}`
- **Scope:** Strictly per-session — all Chroma queries filter by the session's collection name
- **Persistence:** Persisted to the `chroma_data` Docker volume
- **Lifetime:** Until the session is deleted (which calls `KnowledgeStore.delete_session()`)

---

## Skill Integration

Skills are loaded by `skill_loader.py` before the graph is invoked and placed in `AgentState.active_skills`. Each skill entry contains:

```python
{
    "id": "skill-uuid",
    "name": "generate_pptx",
    "version": "1.0.0",
    "description": "Generates a PowerPoint...",
    "skill_content": "<full SKILL.md content>",
    "metadata": {...}
}
```

The `skill_content` (SKILL.md body) is injected into:
1. **`build_plan`** — agent knows which skills are available when planning
2. **`choose_skills`** — agent selects relevant skills by name + description
3. **`run_tools_or_code`** — extracts the ` ```python ``` ` block from `skill_content`, then asks the LLM to adapt it with real content before executing in the sandbox

**Post-graph artifact registration** (in `agent_service.py`):
- After the graph returns, `_register_skill_artifacts()` inspects `execution_outputs` for entries with `output_file` set
- Copies the file to `/storage/artifacts/{user_id}/{session_id}/`
- Creates an `Artifact` DB record with `artifact_type` derived from the file extension (`.pptx` → `pptx`, `.pdf` → `pdf`, etc.)
- Returns the artifact list in the `run_agent()` result, which flows through to the `ChatResponse`

Skills are **never** executed as untrusted code directly. They provide templates and instructions; all execution happens through the controlled sandbox.

---

## Ingestion Pipeline (pre-agent)

Before the agent can answer questions, uploaded sources go through:

```
Upload/URL/Text
      │
      ▼
  validate input
  (type, size, limits)
      │
      ▼
  save to storage
  /storage/uploads/{user_id}/{session_id}/{source_id}/
      │
      ▼
  FastAPI BackgroundTask
      │
      ▼
  extract_text()
  ├── PDF    → pypdf + pytesseract fallback
  ├── PPTX   → python-pptx (all slides)
  ├── Image  → pytesseract OCR
  ├── TXT    → direct read
  ├── Text   → already string
  └── URL    → httpx fetch + BeautifulSoup main-content extraction
      │
      ▼
  chunk_text_with_overlap()
  (1000 chars, 200 overlap)
      │
      ▼
  get_embeddings()   ← active embedding model (admin-configurable)
      │
      ▼
  ChromaDB upsert    ← collection: session_{session_id}
  + PostgreSQL       ← source_chunks_metadata table
      │
      ▼
  ingest_status = "complete"
```

---

## Admin Configuration — Embedding Model Management

The embedding model is a **platform-wide setting** managed by admin users through the `/admin` frontend page and the `GET/PUT /admin/settings` API endpoints.

### Architecture

```
Admin changes embedding model via /admin UI
        │
        ▼
PUT /admin/settings/embedding-model { model_id: "azure-text-embedding-3-small" }
        │
        ▼
api/admin.py
  → verify is_admin = true (403 if not)
  → validate model_id against AVAILABLE_EMBEDDING_MODELS
  → upsert platform_settings row (key="active_embedding_model")
  → call embeddings.reset_model() to clear cached model
        │
        ▼
Next ingestion picks up new model from DB
  → embeddings._get_active_model_id() reads platform_settings table
  → loads appropriate model (SentenceTransformer or Azure OpenAI client)
  → generates embeddings with new dimensionality
```

### Available Models

| Model ID | Dimensions | Provider | Notes |
|----------|-----------|----------|-------|
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | Local (in-process) | Default. Free, no API calls. |
| `azure-text-embedding-3-small` | 1536 | Azure OpenAI API | Requires `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` |
| `azure-text-embedding-3-large` | 3072 | Azure OpenAI API | Higher quality. Same key requirements. |

### Caching Behavior

The `embeddings.py` service caches the loaded model object (`_model`) and current model ID (`_current_model_id`). On each call to `get_embeddings()`, it checks if the active model in the DB has changed. If so, it clears the cache and loads the new model. The `reset_model()` function is called explicitly by the admin API after a model change to force immediate cache invalidation.

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Single orchestrator graph | Simpler to debug, sufficient for PoC, matches PRD guidance |
| LangGraph MemorySaver (in-memory) | No extra DB setup needed; sufficient for PoC single-process deployment |
| Multi-LLM support (Gemini + Azure OpenAI) | Per-session model selection, locked at creation time, provider passed through `AgentState.llm_provider` |
| Admin-configurable embeddings | Platform-wide setting stored in `platform_settings` table; supports local (MiniLM) and Azure OpenAI models |
| sentence-transformers as default embeddings | Free, runs locally, no API quota — Gemini embedding API not available on free tier |
| One Chroma collection per session | Cleanest isolation; no metadata-based filter bugs possible across sessions |
| Background tasks for ingestion | Avoids blocking HTTP responses; can be moved to Celery/worker later |
| Skills as SKILL.md templates | Agent reads instructions, generates sandbox code — skills don't run arbitrary code |

---

## Limitations (PoC)

1. **LangGraph checkpoints are in-memory** — lost on backend restart; production should use `PostgresSaver`
2. **No streaming** — agent returns full response after completion; streaming requires `astream_events`
3. **Single-process** — ingestion and agent run in the FastAPI process; should be separate workers at scale
4. **Keyword-based code execution detection** — a proper version uses LLM function-calling
5. **No sub-agents** — parallel research, specialised writing/coding agents not implemented
6. **No cross-session memory** — by design for PoC; a "user profile" memory layer could be added
7. **Embedding model change requires re-ingestion** — switching embedding models via admin panel only affects new documents; existing vectors retain their original dimensionality
