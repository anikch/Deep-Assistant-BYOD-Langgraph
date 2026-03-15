# API Reference — Assistant PoC

**Base URL:** `http://localhost:8000`
**Auth:** Bearer JWT token in `Authorization: Bearer <token>` header (all endpoints except `/auth/signup` and `/auth/login`)
**Content-Type:** `application/json` unless stated otherwise

---

## Table of Contents
1. [Authentication](#1-authentication)
2. [Sessions](#2-sessions)
3. [Sources (Knowledge Base)](#3-sources-knowledge-base)
4. [Chat & Agent](#4-chat--agent)
5. [Skills](#5-skills)
6. [Artifacts](#6-artifacts)
7. [Admin (Platform Settings)](#7-admin-platform-settings)
8. [Common Error Responses](#8-common-error-responses)

---

## 1. Authentication

### POST /auth/signup
Create a new user account and receive a JWT token.

**Request Body**
```json
{
  "username": "alice",
  "password": "mysecurepass"
}
```

**Response 201**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "d3f1a2b3-...",
  "username": "alice",
  "is_admin": false
}
```

**Errors**
| Status | Detail |
|--------|--------|
| 409 | Username already exists |

---

### POST /auth/login
Authenticate and receive a JWT token.

**Request Body**
```json
{
  "username": "admin",
  "password": "admin$123"
}
```

**Response 200**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "a5990d2f-...",
  "username": "admin",
  "is_admin": true
}
```

**Errors**
| Status | Detail |
|--------|--------|
| 401 | Invalid username or password |

---

### POST /auth/logout
Stateless logout (client discards the token).

**Response 200**
```json
{ "message": "Logged out successfully" }
```

---

### GET /auth/me
Get the currently authenticated user's profile.

**Response 200**
```json
{
  "id": "a5990d2f-...",
  "username": "admin",
  "is_active": true,
  "is_admin": true,
  "created_at": "2026-03-14T10:41:02.500193"
}
```

---

## 2. Sessions

### GET /sessions
List all active sessions for the current user.

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| include_archived | bool | false | Include archived sessions |

**Response 200**
```json
[
  {
    "id": "ca266e3d-...",
    "user_id": "a5990d2f-...",
    "title": "My Research Session",
    "status": "active",
    "llm_model": "gemini",
    "created_at": "2026-03-14T10:48:16.400755",
    "updated_at": "2026-03-14T10:48:16.400756",
    "archived_at": null
  }
]
```

---

### GET /sessions/llm-models
List available LLM models for session creation.

**Response 200**
```json
[
  { "id": "gemini", "name": "Google Gemini (gemini-2.5-flash)" },
  { "id": "azure_openai", "name": "Azure OpenAI GPT (gpt-4o)" }
]
```

---

### POST /sessions
Create a new session. The `llm_model` is locked for the lifetime of the session and cannot be changed after creation.

**Request Body**
```json
{
  "title": "My Research Session",
  "llm_model": "gemini"
}
```

`llm_model` accepted values: `gemini` (default), `azure_openai`

**Response 201**
```json
{
  "id": "ca266e3d-...",
  "user_id": "a5990d2f-...",
  "title": "My Research Session",
  "status": "active",
  "llm_model": "gemini",
  "created_at": "2026-03-14T10:48:16.400755",
  "updated_at": "2026-03-14T10:48:16.400756",
  "archived_at": null
}
```

---

### GET /sessions/{session_id}
Get a single session by ID. Returns 403 if the session belongs to another user.

**Response 200** — same shape as POST /sessions response.

---

### PATCH /sessions/{session_id}
Rename or archive a session.

> **Note:** The `llm_model` field is immutable — it is set at creation time and cannot be changed via PATCH. Attempting to pass `llm_model` in the request body has no effect.

**Request Body** (all fields optional)
```json
{
  "title": "New Title",
  "status": "archived"
}
```
`status` accepted values: `active`, `archived`

**Response 200** — updated session object (includes `llm_model` in response but the value is read-only).

---

### DELETE /sessions/{session_id}
Soft-delete a session (status → `deleted`). Also deletes the Chroma collection for this session.

**Response 200**
```json
{ "message": "Session deleted" }
```

---

## 3. Sources (Knowledge Base)

All source routes enforce:
- Session ownership (403 if not owned by current user)
- Max 10 files + URLs per session (pasted text is exempt)

### GET /sessions/{session_id}/sources
List all sources in a session.

**Response 200**
```json
[
  {
    "id": "169d28cd-...",
    "user_id": "a5990d2f-...",
    "session_id": "ca266e3d-...",
    "source_type": "pptx",
    "display_name": "report.pptx",
    "original_filename": "report.pptx",
    "source_url": null,
    "ingest_status": "complete",
    "created_at": "2026-03-14T10:48:52.883226",
    "updated_at": "2026-03-14T10:48:52.904848"
  }
]
```

`source_type` values: `pdf`, `pptx`, `image`, `txt`, `text`, `url`
`ingest_status` values: `pending`, `processing`, `complete`, `failed`

---

### POST /sessions/{session_id}/sources/upload
Upload a file to the session knowledge base.

**Content-Type:** `multipart/form-data`

**Form Fields**
| Field | Type | Description |
|-------|------|-------------|
| file | File | Allowed types: `.pdf`, `.pptx`, `.jpg`, `.jpeg`, `.png`, `.txt` |

**Limits**
- Max file size: `MAX_UPLOAD_MB` (default 50 MB)
- Max 10 files+URLs total per session

**Response 201**
```json
{
  "id": "169d28cd-...",
  "source_type": "pptx",
  "display_name": "report.pptx",
  "original_filename": "report.pptx",
  "ingest_status": "pending",
  "created_at": "2026-03-14T10:48:52.883226",
  "updated_at": "2026-03-14T10:48:52.883227"
}
```
Ingestion runs as a background task. Poll `GET /sessions/{id}/sources` to check `ingest_status`.

**Errors**
| Status | Detail |
|--------|--------|
| 400 | File type not allowed |
| 400 | File too large |
| 400 | Session source limit reached (max 10) |

---

### POST /sessions/{session_id}/sources/url
Add a web URL to the knowledge base. The page is fetched and ingested automatically.

**Request Body**
```json
{
  "url": "https://example.com/article",
  "display_name": "Example Article"
}
```
`display_name` is optional; defaults to the URL.

**Response 201** — same shape as file upload response, `source_type: "url"`.

---

### POST /sessions/{session_id}/sources/text
Add pasted text to the knowledge base. Does **not** count toward the 10-source limit.

**Request Body**
```json
{
  "content": "Your pasted text content here...",
  "display_name": "My Notes"
}
```
Max content length: `MAX_PASTED_TEXT_CHARS` (default 50,000 chars).

**Response 201** — same shape, `source_type: "text"`.

---

### DELETE /sessions/{session_id}/sources/{source_id}
Delete a source and remove its vectors from Chroma.

**Response 200**
```json
{ "message": "Source deleted" }
```

---

## 4. Chat & Agent

### GET /sessions/{session_id}/messages
Retrieve the full chat history for a session.

**Response 200**
```json
[
  {
    "id": "msg-uuid-...",
    "session_id": "ca266e3d-...",
    "user_id": "a5990d2f-...",
    "role": "user",
    "content": "What are the main findings?",
    "structured_payload": null,
    "created_at": "2026-03-14T11:00:00"
  },
  {
    "id": "msg-uuid-...",
    "session_id": "ca266e3d-...",
    "user_id": "a5990d2f-...",
    "role": "assistant",
    "content": "Based on the uploaded documents...",
    "structured_payload": {
      "citations": [
        {
          "source_id": "169d28cd-...",
          "source_name": "report.pptx",
          "chunk_index": 2,
          "excerpt": "The key finding was..."
        }
      ],
      "plan": ["Retrieve relevant chunks", "Analyse findings", "Compose answer"],
      "agent_run_id": "run-uuid-...",
      "artifacts": []
    },
    "created_at": "2026-03-14T11:00:05"
  }
]
```

`role` values: `user`, `assistant`, `system`

---

### POST /sessions/{session_id}/chat
Send a message and invoke the agent. This is the primary chat endpoint. The agent uses the LLM model configured at session creation time (`session.llm_model` — either `gemini` or `azure_openai`). The model cannot be changed mid-session.

**Request Body**
```json
{
  "message": "Summarise the key findings from the uploaded report",
  "stream": false
}
```

**Response 200**
```json
{
  "message_id": "msg-uuid-...",
  "agent_run_id": "run-uuid-...",
  "content": "Based on the uploaded report, the key findings are:\n\n1. **Finding 1** [Source 1]...\n2. **Finding 2** [Source 2]...",
  "plan": [
    "Step 1: Retrieve relevant chunks from knowledge base",
    "Step 2: Identify key findings",
    "Step 3: Compose structured summary"
  ],
  "citations": [
    {
      "source_id": "169d28cd-...",
      "source_name": "report.pptx",
      "chunk_index": 2,
      "excerpt": "The key finding was..."
    }
  ],
  "clarification_needed": false,
  "clarification_question": null,
  "artifacts": [
    {
      "id": "artifact-uuid-...",
      "display_name": "generate_pptx_a1b2c3d4",
      "artifact_type": "pptx",
      "skill_name": "generate_pptx"
    }
  ]
}
```

If the agent needs clarification:
```json
{
  "answer": "Could you clarify which report you'd like me to focus on — the Q1 report or the annual review?",
  "clarification_needed": true,
  "clarification_question": "Which report should I focus on?",
  "plan": ["Awaiting clarification from user"],
  "citations": []
}
```

---

### GET /sessions/{session_id}/agent-runs/{run_id}
Get details of a specific agent run (plan, status, tool runs).

**Response 200**
```json
{
  "id": "run-uuid-...",
  "user_id": "a5990d2f-...",
  "session_id": "ca266e3d-...",
  "status": "complete",
  "current_plan": ["Step 1", "Step 2", "Step 3"],
  "final_summary": "Summary of what the agent did",
  "started_at": "2026-03-14T11:00:00",
  "completed_at": "2026-03-14T11:00:05"
}
```

`status` values: `pending`, `running`, `complete`, `failed`

---

## 5. Skills

All skill routes enforce ownership — users can only access their own skills.

### GET /skills
List all skills owned by the current user.

**Response 200**
```json
[
  {
    "id": "skill-uuid-...",
    "user_id": "a5990d2f-...",
    "name": "generate_pptx",
    "version": "1.0.0",
    "description": "Generates a PowerPoint presentation from structured content",
    "validation_status": "valid",
    "install_status": "installed",
    "is_globally_enabled": true,
    "uploaded_at": "2026-03-14T12:00:00",
    "updated_at": "2026-03-14T12:00:00",
    "validation_errors": null
  }
]
```

`validation_status` values: `uploaded`, `validating`, `valid`, `invalid`, `failed`

---

### POST /skills/upload
Upload a skill ZIP file.

**Content-Type:** `multipart/form-data`

**Form Fields**
| Field | Type | Description |
|-------|------|-------------|
| file | File | `.zip` file containing at minimum `SKILL.md` |

**ZIP requirements**
- `SKILL.md` at top level with YAML frontmatter fields: `name`, `description`, `version`
- Only allowed file extensions: `.md`, `.txt`, `.py`, `.json`, `.yaml`, `.yml`, `.js`
- No path traversal, no dangerous code patterns
- Max size: `MAX_SKILL_ZIP_MB` (default 20 MB)

**Response 201**
```json
{
  "id": "skill-uuid-...",
  "name": "generate_pptx",
  "version": "1.0.0",
  "description": "Generates a PowerPoint presentation...",
  "validation_status": "valid",
  "is_globally_enabled": false,
  "uploaded_at": "2026-03-14T12:00:00"
}
```

**Errors**
| Status | Detail |
|--------|--------|
| 400 | Not a valid ZIP / validation failed |
| 400 | ZIP too large |

---

### GET /skills/{skill_id}
Get skill details including validation errors if any.

**Response 200** — same shape as GET /skills list item.

---

### POST /skills/{skill_id}/enable
Enable a skill globally for the current user.

**Response 200**
```json
{ "message": "Skill enabled" }
```

---

### POST /skills/{skill_id}/disable
Disable a skill globally.

**Response 200**
```json
{ "message": "Skill disabled" }
```

---

### DELETE /skills/{skill_id}
Delete a skill and remove its files from storage.

**Response 200**
```json
{ "message": "Skill deleted" }
```

---

### POST /sessions/{session_id}/skills/{skill_id}/enable
Enable a skill for a specific session only.

**Response 200**
```json
{ "message": "Skill enabled for session" }
```

---

### POST /sessions/{session_id}/skills/{skill_id}/disable
Disable a skill for a specific session only.

**Response 200**
```json
{ "message": "Skill disabled for session" }
```

---

## 6. Artifacts

### GET /sessions/{session_id}/artifacts
List all generated artifacts for a session.

**Response 200**
```json
[
  {
    "id": "artifact-uuid-...",
    "user_id": "a5990d2f-...",
    "session_id": "ca266e3d-...",
    "artifact_type": "pdf",
    "display_name": "Research Report.pdf",
    "created_at": "2026-03-14T12:30:00"
  }
]
```

`artifact_type` values: `pdf`, `csv`, `xlsx`, `pptx`

> **Note:** `pptx` artifacts are created automatically by the agent when a skill (e.g. `generate_pptx`) executes successfully and produces a file. They are not created via the `/generate` endpoint.

---

### POST /sessions/{session_id}/artifacts/generate
Generate a downloadable artifact from session content.

**Request Body**
```json
{
  "artifact_type": "pdf",
  "display_name": "Research Report",
  "content": "# Research Report\n\nThis is the report content...",
  "data": null
}
```

For CSV/XLSX, use `data` instead of `content`:
```json
{
  "artifact_type": "csv",
  "display_name": "Findings Table",
  "content": null,
  "data": [
    {"Finding": "Item 1", "Evidence": "Source A", "Confidence": "High"},
    {"Finding": "Item 2", "Evidence": "Source B", "Confidence": "Medium"}
  ]
}
```

**Response 201**
```json
{
  "id": "artifact-uuid-...",
  "artifact_type": "pdf",
  "display_name": "Research Report.pdf",
  "created_at": "2026-03-14T12:30:00"
}
```

---

### GET /artifacts/{artifact_id}/download
Download an artifact file. Validates ownership before serving.

**Response 200** — Binary file stream with appropriate `Content-Type` header.

| Type | Content-Type |
|------|-------------|
| pdf | `application/pdf` |
| csv | `text/csv` |
| xlsx | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| pptx | `application/vnd.openxmlformats-officedocument.presentationml.presentation` |

---

## 7. Admin (Platform Settings)

All admin routes require the authenticated user to have `is_admin = true`. Non-admin users receive a `403 Forbidden` response.

### GET /admin/settings
Get current platform settings including the active embedding model.

**Response 200**
```json
{
  "active_embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "available_embedding_models": [
    {
      "id": "sentence-transformers/all-MiniLM-L6-v2",
      "name": "MiniLM-L6-v2 (Local, Free)",
      "provider": "sentence-transformers"
    },
    {
      "id": "azure-text-embedding-3-small",
      "name": "Azure OpenAI text-embedding-3-small",
      "provider": "azure_openai"
    },
    {
      "id": "azure-text-embedding-3-large",
      "name": "Azure OpenAI text-embedding-3-large",
      "provider": "azure_openai"
    }
  ]
}
```

**Errors**
| Status | Detail |
|--------|--------|
| 403 | Admin access required |

---

### PUT /admin/settings/embedding-model
Change the active embedding model for all platform users. Affects new document ingestion only.

**Request Body**
```json
{
  "model_id": "azure-text-embedding-3-small"
}
```

`model_id` accepted values: `sentence-transformers/all-MiniLM-L6-v2`, `azure-text-embedding-3-small`, `azure-text-embedding-3-large`

**Response 200**
```json
{
  "message": "Embedding model updated",
  "active_embedding_model": "azure-text-embedding-3-small"
}
```

**Errors**
| Status | Detail |
|--------|--------|
| 400 | Invalid model |
| 403 | Admin access required |

---

## 8. Common Error Responses

```json
{ "detail": "Error message here" }
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request / validation error |
| 401 | Missing or invalid JWT token |
| 403 | Forbidden — resource belongs to another user |
| 404 | Resource not found |
| 409 | Conflict (e.g. duplicate username) |
| 422 | Unprocessable entity (Pydantic validation failure) |
| 500 | Internal server error |

All 4xx/5xx responses use the `{"detail": "..."}` shape from FastAPI.

---

*Interactive API docs available at `http://localhost:8000/docs` (Swagger UI)*
