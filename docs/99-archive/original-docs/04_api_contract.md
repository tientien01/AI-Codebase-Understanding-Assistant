# API Contract

Base path: `/api/v1`.

This document defines the public backend API for AI Codebase Assistant. It is intended to be used by the frontend, tests, and AI coding agents. The API must support repository import, preview, indexing, code exploration, search, evidence-based chat, graph traversal, impact analysis, evaluation, settings, and agentic workflow inspection.

All JSON APIs must use `application/json`. File uploads use `multipart/form-data`.

## 1. API Design Principles

- Every endpoint must be scoped by `repository_id` when the operation is repository-specific.
- Responses must avoid leaking secrets, absolute internal storage paths, raw tokens, or private configuration values.
- Technical answers and assistant outputs must be tied to evidence whenever possible.
- Long-running actions such as indexing, evaluation, and GitHub sync should return job/run IDs instead of blocking until complete.
- List endpoints should support pagination when the result can grow large.
- Endpoints that expose implementation/debug details, such as agent traces, should be safe to show in demo mode and must not include secrets.
- API contracts should remain stable even if the internal storage changes from SQLite to PostgreSQL or from a local vector store to an external vector database.

## 2. Common Conventions

### 2.1 Standard Error Format

```json
{
  "error": {
    "code": "REPOSITORY_NOT_INDEXED",
    "message": "Repository has not been indexed yet.",
    "details": {
      "repository_id": "repo_123"
    }
  }
}
```

Rules:

- `code` is stable and machine-readable.
- `message` is safe to show to users.
- `details` must not contain secrets.
- Use correct HTTP status codes.

### 2.2 Common Pagination Format

List endpoints that can return many records should support:

Query parameters:

- `limit`: default 20, maximum 100.
- `cursor`: optional opaque cursor from the previous response.

Response shape:

```json
{
  "items": [],
  "next_cursor": null
}
```

### 2.3 Common Evidence Object

Endpoints that return source-grounded results may include evidence objects:

```json
{
  "evidence_id": "ev_1",
  "file_id": "file_123",
  "file_path": "backend/app/auth/router.py",
  "symbol_name": "login",
  "start_line": 21,
  "end_line": 45,
  "content_preview": "async def login(payload: LoginRequest): ...",
  "confidence_score": 0.91,
  "retrieval_source": "graph",
  "index_version": 3,
  "is_stale": false
}
```

### 2.4 Common Status Values

Repository status:

- `created`
- `previewed`
- `indexing`
- `indexed`
- `indexed_with_warnings`
- `failed`
- `stale`
- `deleted`

Indexing job status:

- `queued`
- `running`
- `completed`
- `completed_with_warnings`
- `failed`
- `cancelled`

Import session status:

- `created`
- `preview_ready`
- `confirmed`
- `expired`
- `cancelled`
- `failed`

## 3. Health

### GET `/health`

Response:

```json
{
  "status": "ok",
  "service": "ai-codebase-assistant",
  "version": "0.1.0"
}
```

## 4. Import Sessions and Preview

Import sessions support the safer flow:

```text
Upload / GitHub URL -> Import Session -> Preview -> Confirm -> Repository + Indexing Job
```

The preview step lets the user see detected stack, file counts, skipped files, warnings, security risks, possible duplicates, and estimated indexing cost before creating a final repository record.

### POST `/import-sessions/upload-zip`

Uploads a zip file and creates an import session.

Form fields:

- `file`: zip file.
- `name`: optional display name.

Response:

```json
{
  "import_session_id": "import_123",
  "status": "created",
  "source_type": "upload_zip"
}
```

Errors:

- `INVALID_ARCHIVE`
- `ARCHIVE_PATH_TRAVERSAL`
- `FILE_TOO_LARGE`
- `UNSUPPORTED_FILE_TYPE`
- `NO_SUPPORTED_FILES`

### POST `/import-sessions/upload-folder`

Uploads a folder from the browser and creates an import session.

Form fields:

- `files`: repeated files.
- `relative_paths`: repeated relative paths matching files.
- `name`: optional display name.

Rules:

- Reject absolute paths.
- Reject paths containing `..`.
- Ignore blocked files and folders.
- Return an error if no supported file remains.

Response:

```json
{
  "import_session_id": "import_123",
  "status": "created",
  "source_type": "upload_folder"
}
```

### POST `/import-sessions/github`

Creates an import session from a GitHub repository.

Request:

```json
{
  "name": "restaurant-app",
  "github_url": "https://github.com/example/restaurant-app",
  "branch": "main",
  "access_token_ref": null
}
```

Notes:

- `access_token_ref` is an identifier for a configured token, not the raw token.
- Public repositories must work without a token.
- Private repositories require a configured token.
- GitHub private import may be implemented when GitHub source support is selected for development.

Response:

```json
{
  "import_session_id": "import_123",
  "status": "created",
  "source_type": "github_url"
}
```

Errors:

- `INVALID_GITHUB_URL`
- `GITHUB_AUTH_REQUIRED`
- `GITHUB_CLONE_FAILED`
- `REPOSITORY_TOO_LARGE`

### GET `/import-sessions/{import_session_id}/preview`

Returns the project preview before final import/indexing.

Response:

```json
{
  "import_session_id": "import_123",
  "status": "preview_ready",
  "project_summary": {
    "suggested_name": "restaurant-app",
    "source_type": "upload_zip",
    "repository_size_bytes": 155000000,
    "estimated_index_time_seconds": 35
  },
  "detected_stack": ["FastAPI", "React", "SQLAlchemy", "Docker"],
  "file_statistics": {
    "total_files": 1247,
    "supported_files": 212,
    "skipped_files": 1035,
    "python_files": 82,
    "javascript_files": 41,
    "typescript_files": 56,
    "markdown_files": 18,
    "config_files": 15
  },
  "folder_preview": [
    "backend/",
    "frontend/",
    "docs/",
    "tests/"
  ],
  "ignore_summary": [
    {
      "pattern": "node_modules/",
      "skipped_count": 6381,
      "reason": "dependency folder"
    }
  ],
  "security_warnings": [
    {
      "file_path": ".env",
      "risk_type": "secret_file",
      "action": "skipped"
    }
  ],
  "indexing_plan": [
    "scan_files",
    "parse_symbols",
    "detect_endpoints",
    "create_chunks",
    "generate_embeddings",
    "build_graph",
    "generate_project_mental_model"
  ],
  "possible_duplicates": [
    {
      "repository_id": "repo_456",
      "name": "restaurant-app",
      "match_reason": "same_content_hash",
      "last_indexed_at": "2026-06-23T08:00:00Z"
    }
  ],
  "warnings": []
}
```

### POST `/import-sessions/{import_session_id}/confirm`

Confirms the import session, creates a repository, and optionally starts indexing.

Request:

```json
{
  "name": "restaurant-app",
  "start_indexing": true,
  "index_profile": "balanced",
  "duplicate_action": "import_as_new"
}
```

`duplicate_action` values:

- `import_as_new`
- `open_existing`
- `reindex_existing`
- `cancel`

Response:

```json
{
  "repository_id": "repo_123",
  "indexing_job_id": "job_123",
  "status": "indexing"
}
```

### DELETE `/import-sessions/{import_session_id}`

Cancels an import session and removes temporary upload artifacts.

Response:

```json
{
  "cancelled": true,
  "import_session_id": "import_123"
}
```

## 5. Repositories

### GET `/repositories`

Lists imported repositories.

Query parameters:

- `q`: optional search by project name or source label.
- `status`: optional repository status filter.
- `limit`: default 20.
- `cursor`: optional pagination cursor.

Response:

```json
{
  "items": [
    {
      "id": "repo_123",
      "name": "restaurant-app",
      "source_type": "upload_zip",
      "source_label": "restaurant-app.zip",
      "status": "indexed",
      "detected_stack": ["FastAPI", "React", "SQLAlchemy"],
      "total_files": 120,
      "indexed_files": 118,
      "symbols": 450,
      "endpoints": 32,
      "chunks": 900,
      "graph_nodes": 700,
      "current_index_version": 3,
      "last_indexed_at": "2026-06-23T08:00:00Z",
      "is_stale": false
    }
  ],
  "next_cursor": null
}
```

### GET `/repositories/{repository_id}`

Returns repository detail for project dashboard and workspace header.

Response:

```json
{
  "id": "repo_123",
  "name": "restaurant-app",
  "source_type": "upload_zip",
  "source_label": "restaurant-app.zip",
  "status": "indexed",
  "summary": "A FastAPI and React restaurant recommendation system.",
  "detected_stack": ["FastAPI", "React", "SQLAlchemy"],
  "current_index_version": 3,
  "created_at": "2026-06-23T07:55:00Z",
  "updated_at": "2026-06-23T08:00:00Z",
  "last_indexed_at": "2026-06-23T08:00:00Z",
  "is_stale": false
}
```

### POST `/repositories/{repository_id}/sync`

Synchronizes the latest source for GitHub-backed repositories.

Request:

```json
{
  "start_reindex": false
}
```

Response:

```json
{
  "repository_id": "repo_123",
  "source_changed": true,
  "previous_commit": "abc123",
  "current_commit": "def456",
  "recommended_action": "reindex"
}
```

Errors:

- `REPOSITORY_SOURCE_NOT_SYNCABLE`
- `GITHUB_AUTH_REQUIRED`
- `GITHUB_SYNC_FAILED`

### DELETE `/repositories/{repository_id}`

Deletes repository metadata, source files, vector collection, graph data, and related conversations/evidence unless retention policy says otherwise.

Response:

```json
{
  "deleted": true,
  "repository_id": "repo_123"
}
```

## 6. Indexing

### POST `/repositories/{repository_id}/index`

Starts indexing or re-indexing.

Request:

```json
{
  "force_reindex": true,
  "profile": "balanced"
}
```

`profile` values:

- `fast`
- `balanced`
- `deep`

Response:

```json
{
  "indexing_job_id": "job_123",
  "repository_id": "repo_123",
  "status": "queued",
  "index_version": 4
}
```

Errors:

- `REPOSITORY_NOT_FOUND`
- `INDEX_ALREADY_RUNNING`
- `REPOSITORY_SOURCE_MISSING`

### GET `/repositories/{repository_id}/index/status`

Returns the latest indexing job status.

Response:

```json
{
  "repository_id": "repo_123",
  "job_id": "job_123",
  "status": "running",
  "current_step": "generate_embeddings",
  "index_version": 4,
  "total_files": 120,
  "processed_files": 82,
  "skipped_files": 5,
  "failed_files": 3,
  "progress": 68,
  "stats": {
    "symbols": 240,
    "endpoints": 18,
    "chunks": 520,
    "graph_nodes": 380,
    "graph_edges": 610
  },
  "recent_logs": [],
  "recent_warnings": [],
  "started_at": "2026-06-23T08:00:00Z",
  "finished_at": null
}
```

### GET `/repositories/{repository_id}/index/jobs`

Returns indexing job history.

Response:

```json
{
  "items": [
    {
      "id": "job_123",
      "repository_id": "repo_123",
      "status": "completed_with_warnings",
      "index_version": 3,
      "total_files": 120,
      "processed_files": 118,
      "skipped_files": 5,
      "failed_files": 2,
      "started_at": "2026-06-23T08:00:00Z",
      "finished_at": "2026-06-23T08:01:10Z"
    }
  ],
  "next_cursor": null
}
```

### GET `/repositories/{repository_id}/index/jobs/{job_id}`

Returns detailed indexing job information.

Response:

```json
{
  "id": "job_123",
  "repository_id": "repo_123",
  "job_type": "reindex",
  "status": "completed_with_warnings",
  "current_step": "completed",
  "index_version": 4,
  "profile": "balanced",
  "total_files": 120,
  "processed_files": 118,
  "skipped_files": 5,
  "failed_files": 2,
  "stats": {
    "symbols": 420,
    "endpoints": 32,
    "chunks": 900,
    "graph_nodes": 700,
    "graph_edges": 1120
  },
  "started_at": "2026-06-23T08:00:00Z",
  "finished_at": "2026-06-23T08:01:10Z",
  "error_code": null,
  "error_message": null
}
```

### GET `/repositories/{repository_id}/index/jobs/{job_id}/warnings`

Returns parser warnings, unsupported file warnings, security warnings, and partial extraction warnings.

Response:

```json
{
  "items": [
    {
      "file_path": "backend/app/broken.py",
      "warning_type": "parse_error",
      "message": "Python syntax error. File was skipped.",
      "line": 12,
      "severity": "warning"
    }
  ],
  "next_cursor": null
}
```

### GET `/repositories/{repository_id}/index/jobs/{job_id}/skipped-files`

Returns files skipped during indexing.

Response:

```json
{
  "items": [
    {
      "file_path": "node_modules/react/index.js",
      "reason": "dependency_folder",
      "matched_pattern": "node_modules/"
    }
  ],
  "next_cursor": null
}
```

### GET `/repositories/{repository_id}/index/jobs/{job_id}/failed-files`

Returns files that failed parsing or processing.

Response:

```json
{
  "items": [
    {
      "file_path": "backend/app/broken.py",
      "stage": "parsing_files",
      "error_code": "PARSER_ERROR",
      "message": "Python syntax error. File was skipped.",
      "line": 12
    }
  ],
  "next_cursor": null
}
```

## 7. Staleness

### GET `/repositories/{repository_id}/staleness`

Checks whether the current source appears newer than the latest successful index.

Response:

```json
{
  "repository_id": "repo_123",
  "is_stale": true,
  "current_index_version": 3,
  "last_indexed_at": "2026-06-23T08:00:00Z",
  "stale_reason": "source_files_modified_after_index",
  "changed_files_count": 8,
  "recommended_action": "reindex"
}
```

## 8. Overview and Project Mental Model

### GET `/repositories/{repository_id}/overview`

Returns the Project Mental Model.

Response:

```json
{
  "repository_id": "repo_123",
  "name": "restaurant-app",
  "index_version": 3,
  "detected_stack": ["FastAPI", "React", "SQLAlchemy", "Docker"],
  "important_files": [
    {
      "file_path": "backend/app/main.py",
      "reason": "FastAPI application entrypoint",
      "confidence": "high"
    }
  ],
  "modules": [
    {
      "name": "auth",
      "summary": "Authentication routes, schemas, token helpers, and user lookup",
      "file_count": 9,
      "symbol_count": 34
    }
  ],
  "entrypoints": [],
  "endpoints": [],
  "main_flows": [],
  "documentation_gaps": [],
  "risk_areas": [],
  "stats": {
    "files": 120,
    "functions": 320,
    "classes": 45,
    "endpoints": 32,
    "chunks": 900,
    "graph_nodes": 700
  }
}
```

### GET `/repositories/{repository_id}/reading-path`

Returns suggested files/modules to read first.

Response:

```json
{
  "repository_id": "repo_123",
  "index_version": 3,
  "items": [
    {
      "rank": 1,
      "file_id": "file_123",
      "file_path": "backend/app/main.py",
      "title": "Application entry point",
      "reason": "Detected FastAPI app initialization and router registration.",
      "confidence": "high",
      "signals": [
        {
          "type": "entrypoint",
          "detail": "Contains FastAPI()",
          "line": 12
        },
        {
          "type": "router_registration",
          "detail": "Includes auth router",
          "line": 21
        }
      ],
      "evidence_ids": ["ev_1"]
    }
  ]
}
```

## 9. Files and Code Explorer

### GET `/repositories/{repository_id}/files/tree`

Returns a file tree.

Response:

```json
{
  "repository_id": "repo_123",
  "items": [
    {
      "type": "folder",
      "path": "backend/app",
      "children_count": 12
    },
    {
      "type": "file",
      "file_id": "file_123",
      "path": "backend/app/main.py",
      "language": "python",
      "parse_status": "parsed"
    }
  ]
}
```

### GET `/repositories/{repository_id}/files/content?path=backend/app/main.py`

Returns file content, language, line list, and detected symbols.

Response:

```json
{
  "file_id": "file_123",
  "path": "backend/app/main.py",
  "language": "python",
  "parse_status": "parsed",
  "index_version": 3,
  "lines": [
    {
      "line_number": 1,
      "text": "from fastapi import FastAPI"
    }
  ],
  "symbols": []
}
```

### GET `/repositories/{repository_id}/files/{file_id}`

Returns file metadata and related entities.

Response:

```json
{
  "file_id": "file_123",
  "repository_id": "repo_123",
  "path": "backend/app/main.py",
  "language": "python",
  "file_type": "source",
  "size_bytes": 2840,
  "content_hash": "sha256:abc123",
  "parse_status": "parsed",
  "index_version": 3,
  "symbols_count": 8,
  "endpoints_count": 2,
  "imports_count": 6,
  "related_tests_count": 1,
  "warnings": []
}
```

### GET `/repositories/{repository_id}/files/{file_id}/symbols`

Returns symbols detected in one file.

Response:

```json
{
  "items": [
    {
      "symbol_id": "sym_123",
      "name": "create_app",
      "qualified_name": "backend.app.main.create_app",
      "symbol_type": "function",
      "start_line": 10,
      "end_line": 24,
      "confidence": 0.95
    }
  ],
  "next_cursor": null
}
```

## 10. Symbols

### GET `/repositories/{repository_id}/symbols`

Searches or lists symbols.

Query parameters:

- `q`: optional symbol name.
- `symbol_type`: optional `class`, `function`, `method`, `component`, `model`, `schema`.
- `file_id`: optional file filter.
- `limit`: default 20.
- `cursor`: optional pagination cursor.

Response:

```json
{
  "items": [
    {
      "symbol_id": "sym_123",
      "file_id": "file_123",
      "file_path": "backend/app/services/auth_service.py",
      "symbol_type": "function",
      "name": "authenticate_user",
      "qualified_name": "app.services.auth_service.authenticate_user",
      "start_line": 10,
      "end_line": 42,
      "confidence": 0.95,
      "index_version": 3
    }
  ],
  "next_cursor": null
}
```

### GET `/repositories/{repository_id}/symbols/{symbol_id}`

Returns symbol detail.

Response:

```json
{
  "symbol_id": "sym_123",
  "repository_id": "repo_123",
  "file_id": "file_123",
  "file_path": "backend/app/services/auth_service.py",
  "symbol_type": "function",
  "name": "authenticate_user",
  "qualified_name": "app.services.auth_service.authenticate_user",
  "signature": "authenticate_user(email: str, password: str)",
  "start_line": 10,
  "end_line": 42,
  "docstring": null,
  "confidence": 0.95,
  "index_version": 3
}
```

### GET `/repositories/{repository_id}/symbols/{symbol_id}/references`

Returns references, callers, callees, imports, and related endpoints for a symbol.

Response:

```json
{
  "symbol_id": "sym_123",
  "used_by": [],
  "calls": [],
  "called_by": [],
  "related_endpoints": [],
  "related_tests": [],
  "citations": []
}
```

## 11. Search

### GET `/repositories/{repository_id}/search`

Query parameters:

- `q`: query string.
- `mode`: `keyword`, `semantic`, `hybrid`.
- `scope`: optional `backend`, `frontend`, `docs`, `tests`, `config`.
- `entity_type`: optional `file`, `function`, `class`, `endpoint`, `model`, `doc`, `symbol`, `config`.
- `limit`: default 10.

Response:

```json
{
  "results": [
    {
      "evidence_id": "ev_1",
      "entity_type": "endpoint",
      "file_path": "backend/app/auth/router.py",
      "title": "POST /login",
      "preview": "async def login(...):",
      "start_line": 20,
      "end_line": 45,
      "score": 0.92,
      "index_version": 3
    }
  ]
}
```

### POST `/repositories/{repository_id}/search/ask-with-evidence`

Creates a chat message using selected search results as explicit evidence context.

Request:

```json
{
  "conversation_id": "conv_123",
  "message": "Explain these login files.",
  "evidence_ids": ["ev_1", "ev_2"]
}
```

Response:

```json
{
  "conversation_id": "conv_123",
  "message_id": "msg_456",
  "answer": "These selected evidence items describe the login route and authentication service.",
  "citations": [
    {
      "evidence_id": "ev_1",
      "file_path": "backend/app/auth/router.py",
      "symbol_name": "login",
      "start_line": 21,
      "end_line": 45,
      "index_version": 3,
      "is_stale": false
    }
  ],
  "evidence_sufficient": true,
  "missing_evidence": []
}
```

## 12. Conversations and Chat

### GET `/repositories/{repository_id}/conversations`

Lists conversations for a repository.

Query parameters:

- `limit`: default 20.
- `cursor`: optional pagination cursor.

Response:

```json
{
  "items": [
    {
      "conversation_id": "conv_123",
      "title": "Login flow investigation",
      "message_count": 4,
      "last_message_at": "2026-06-23T08:10:00Z",
      "created_at": "2026-06-23T08:00:00Z"
    }
  ],
  "next_cursor": null
}
```

### POST `/repositories/{repository_id}/conversations`

Creates a conversation.

Request:

```json
{
  "title": "Login flow investigation"
}
```

Response:

```json
{
  "conversation_id": "conv_123",
  "title": "Login flow investigation",
  "created_at": "2026-06-23T08:00:00Z"
}
```

### GET `/repositories/{repository_id}/conversations/{conversation_id}`

Returns messages and citation summaries in a conversation.

Response:

```json
{
  "conversation_id": "conv_123",
  "repository_id": "repo_123",
  "title": "Login flow investigation",
  "messages": [
    {
      "message_id": "msg_123",
      "role": "user",
      "content": "How does the login flow work?",
      "created_at": "2026-06-23T08:00:00Z",
      "citations": []
    },
    {
      "message_id": "msg_456",
      "role": "assistant",
      "content": "The login flow starts in the React login page...",
      "created_at": "2026-06-23T08:00:05Z",
      "evidence_sufficient": true,
      "citations": [
        {
          "evidence_id": "ev_1",
          "file_path": "backend/app/auth/router.py",
          "start_line": 21,
          "end_line": 45,
          "is_stale": false
        }
      ]
    }
  ]
}
```

### DELETE `/repositories/{repository_id}/conversations/{conversation_id}`

Deletes or archives a conversation based on retention policy.

Response:

```json
{
  "deleted": true,
  "conversation_id": "conv_123"
}
```

### POST `/repositories/{repository_id}/chat`

Sends a user message and returns an evidence-grounded assistant answer.

Request:

```json
{
  "conversation_id": "conv_123",
  "message": "How does the login flow work?",
  "context": {
    "file_id": null,
    "symbol_id": null,
    "endpoint_id": null,
    "selected_evidence_ids": []
  },
  "options": {
    "max_retrieval_rounds": 2,
    "include_graph_trace": true,
    "include_agent_trace": true,
    "explanation_mode": "developer"
  }
}
```

Response:

```json
{
  "conversation_id": "conv_123",
  "message_id": "msg_456",
  "question_type": "flow_tracing",
  "answer": "The login flow starts in the React login page...",
  "citations": [
    {
      "evidence_id": "ev_1",
      "file_path": "backend/app/auth/router.py",
      "symbol_name": "login",
      "start_line": 21,
      "end_line": 45,
      "index_version": 3,
      "is_stale": false
    }
  ],
  "graph_trace": [],
  "agent_trace_summary": {
    "plan": [
      "Find login endpoint",
      "Trace handler to service",
      "Find frontend API call",
      "Validate evidence"
    ],
    "tools_used": ["endpoint_lookup", "graph_traversal", "vector_search"],
    "retrieval_rounds": 2
  },
  "evidence_sufficient": true,
  "missing_evidence": [],
  "follow_up_questions": []
}
```

Errors:

- `REPOSITORY_NOT_INDEXED`
- `LLM_PROVIDER_NOT_CONFIGURED`
- `INSUFFICIENT_EVIDENCE`

### GET `/repositories/{repository_id}/messages/{message_id}/agent-trace`

Returns detailed agent workflow trace for a message.

Response:

```json
{
  "message_id": "msg_456",
  "question_type": "impact_analysis",
  "plan": [],
  "tool_calls": [],
  "retrieval_rounds": [],
  "evidence_checks": [],
  "final_decision": "answered_with_evidence"
}
```

## 13. Evidence and Citations

### GET `/repositories/{repository_id}/evidence/{evidence_id}`

Response:

```json
{
  "evidence_id": "ev_1",
  "repository_id": "repo_123",
  "source_type": "code",
  "file_path": "backend/app/auth/router.py",
  "symbol_name": "login",
  "start_line": 21,
  "end_line": 45,
  "content_preview": "async def login(payload: LoginRequest): ...",
  "relevance_reason": "FastAPI handler for login endpoint",
  "confidence_score": 0.91,
  "retrieval_source": "graph",
  "index_version": 3,
  "is_stale": false,
  "metadata": {}
}
```

### POST `/repositories/{repository_id}/evidence/validate`

Validates whether a set of citations still points to current source content.

Request:

```json
{
  "evidence_ids": ["ev_1", "ev_2"]
}
```

Response:

```json
{
  "items": [
    {
      "evidence_id": "ev_1",
      "is_valid": true,
      "is_stale": false,
      "reason": null
    }
  ]
}
```

## 14. Graph

### GET `/repositories/{repository_id}/graph`

Query parameters:

- `focus_node_id`: optional.
- `depth`: default 2.
- `relation_types`: comma-separated optional list.
- `node_types`: comma-separated optional list.

Response:

```json
{
  "nodes": [
    {
      "id": "endpoint_post_login",
      "type": "endpoint",
      "label": "POST /login",
      "file_path": "backend/app/auth/router.py"
    }
  ],
  "edges": [
    {
      "source": "endpoint_post_login",
      "target": "symbol_login",
      "type": "exposes_endpoint",
      "confidence": 0.95
    }
  ]
}
```

### GET `/repositories/{repository_id}/graph/nodes/{node_id}`

Returns one graph node and its immediate context.

Response:

```json
{
  "node": {
    "node_id": "node_123",
    "node_type": "endpoint",
    "label": "POST /login",
    "file_path": "backend/app/auth/router.py",
    "symbol_name": "login",
    "start_line": 21,
    "end_line": 45,
    "index_version": 3,
    "metadata": {
      "method": "POST",
      "path": "/login"
    }
  },
  "incoming_edges": [],
  "outgoing_edges": [
    {
      "edge_id": "edge_123",
      "source_node_id": "node_123",
      "target_node_id": "node_456",
      "relation_type": "calls",
      "confidence": 0.9,
      "evidence_id": "ev_1"
    }
  ]
}
```

### GET `/repositories/{repository_id}/graph/paths`

Finds graph paths between two nodes or entities.

Query parameters:

- `source_node_id`
- `target_node_id`
- `max_depth`: default 4.

Response:

```json
{
  "source_node_id": "node_123",
  "target_node_id": "node_789",
  "paths": [
    {
      "path_id": "path_1",
      "confidence": 0.86,
      "nodes": [
        {
          "node_id": "node_123",
          "node_type": "endpoint",
          "label": "POST /login"
        },
        {
          "node_id": "node_456",
          "node_type": "symbol",
          "label": "authenticate_user"
        }
      ],
      "edges": [
        {
          "edge_id": "edge_123",
          "relation_type": "calls",
          "evidence_id": "ev_1"
        }
      ]
    }
  ],
  "missing_links": []
}
```

## 15. API Explorer

### GET `/repositories/{repository_id}/api/endpoints`

Returns detected endpoints with handler, file, models, auth hint, and linked frontend API calls.

Response:

```json
{
  "items": [
    {
      "endpoint_id": "endpoint_123",
      "method": "POST",
      "path": "/login",
      "full_path": "/api/login",
      "handler": "login",
      "file_path": "backend/app/auth/router.py",
      "start_line": 21,
      "end_line": 45,
      "request_model": "LoginRequest",
      "response_model": "TokenResponse",
      "auth_required": false,
      "confidence": 0.95
    }
  ]
}
```

### GET `/repositories/{repository_id}/api/endpoints/{endpoint_id}`

Returns endpoint detail.

Response:

```json
{
  "endpoint_id": "endpoint_123",
  "repository_id": "repo_123",
  "method": "POST",
  "path": "/login",
  "full_path": "/api/login",
  "framework": "fastapi",
  "handler": {
    "symbol_id": "sym_123",
    "name": "login",
    "file_id": "file_123",
    "file_path": "backend/app/auth/router.py",
    "start_line": 21,
    "end_line": 45
  },
  "request_model": "LoginRequest",
  "response_model": "TokenResponse",
  "auth_required": false,
  "related_services": [],
  "related_models": [],
  "frontend_api_calls": [],
  "citations": [
    {
      "evidence_id": "ev_1",
      "file_path": "backend/app/auth/router.py",
      "start_line": 21,
      "end_line": 45,
      "index_version": 3,
      "is_stale": false
    }
  ],
  "confidence": 0.95,
  "index_version": 3
}
```

### GET `/repositories/{repository_id}/api/endpoints/{endpoint_id}/flow`

Returns an evidence-grounded request flow trace.

Response:

```json
{
  "endpoint_id": "endpoint_123",
  "flow": [
    {
      "step": 1,
      "type": "route",
      "label": "POST /login",
      "file_path": "backend/app/auth/router.py",
      "start_line": 21,
      "end_line": 45,
      "evidence_id": "ev_1"
    },
    {
      "step": 2,
      "type": "service_call",
      "label": "authenticate_user",
      "file_path": "backend/app/services/auth_service.py",
      "start_line": 10,
      "end_line": 42,
      "evidence_id": "ev_2"
    }
  ],
  "confidence": "high",
  "missing_links": []
}
```

## 16. Impact Analysis

### POST `/repositories/{repository_id}/impact`

Request:

```json
{
  "target_type": "symbol",
  "target_ref": "backend/app/services/auth_service.py::authenticate_user",
  "max_depth": 3,
  "include_tests": true,
  "include_endpoints": true
}
```

Response:

```json
{
  "target": {
    "target_type": "symbol",
    "target_ref": "backend/app/services/auth_service.py::authenticate_user",
    "display_name": "authenticate_user"
  },
  "impact_level": "high",
  "evidence_based_impacts": [
    {
      "type": "called_by",
      "file_path": "backend/app/auth/router.py",
      "symbol_name": "login",
      "evidence_id": "ev_1"
    }
  ],
  "inferred_impacts": [
    {
      "type": "possible_runtime_effect",
      "reason": "The login endpoint calls this service function."
    }
  ],
  "direct_files": [],
  "indirect_files": [],
  "affected_endpoints": [],
  "affected_tests": [],
  "graph_paths": [],
  "citations": []
}
```

### GET `/repositories/{repository_id}/tests/related`

Finds tests related to a file, symbol, endpoint, or graph node.

Query parameters:

- `target_type`: `file`, `symbol`, `endpoint`, `node`.
- `target_ref`: target identifier.

Response:

```json
{
  "target_type": "symbol",
  "target_ref": "sym_123",
  "items": [
    {
      "test_id": "test_123",
      "file_id": "file_456",
      "file_path": "backend/tests/test_auth.py",
      "test_name": "test_login_success",
      "start_line": 8,
      "end_line": 24,
      "relation_type": "tests",
      "confidence": 0.88,
      "evidence_id": "ev_3"
    }
  ],
  "missing_reason": null
}
```

## 17. Evaluation

### GET `/evaluation/datasets`

Lists benchmark datasets.

Response:

```json
{
  "items": [
    {
      "dataset_id": "evalset_123",
      "name": "FastAPI React sample benchmark",
      "repository_fixture": "fastapi_react_sample",
      "question_count": 24,
      "created_at": "2026-06-23T08:00:00Z"
    }
  ],
  "next_cursor": null
}
```

### POST `/evaluation/datasets`

Creates an evaluation dataset.

Request:

```json
{
  "name": "FastAPI React sample benchmark",
  "repository_fixture": "fastapi_react_sample",
  "questions": [
    {
      "id": "q001",
      "category": "api_flow",
      "question": "How does the login flow work?",
      "expected_files": [
        "frontend/src/pages/LoginPage.tsx",
        "backend/app/auth/router.py"
      ],
      "expected_symbols": ["LoginPage", "login"],
      "expected_relations": ["calls_api", "exposes_endpoint"]
    }
  ]
}
```

Response:

```json
{
  "dataset_id": "evalset_123",
  "name": "FastAPI React sample benchmark",
  "question_count": 1,
  "created_at": "2026-06-23T08:00:00Z"
}
```

### GET `/evaluation/datasets/{dataset_id}`

Returns a dataset with questions and ground truth summaries.

Response:

```json
{
  "dataset_id": "evalset_123",
  "name": "FastAPI React sample benchmark",
  "repository_fixture": "fastapi_react_sample",
  "questions": [
    {
      "id": "q001",
      "category": "api_flow",
      "question": "How does the login flow work?",
      "expected_files": [
        "frontend/src/pages/LoginPage.tsx",
        "backend/app/auth/router.py"
      ],
      "expected_symbols": ["LoginPage", "login"],
      "expected_relations": ["calls_api", "exposes_endpoint"]
    }
  ]
}
```

### POST `/evaluation/runs`

Starts an evaluation run.

Request:

```json
{
  "dataset_id": "evalset_123",
  "method": "adaptive_agentic_retrieval"
}
```

`method` values:

- `keyword_search`
- `naive_rag`
- `hybrid_retrieval`
- `adaptive_agentic_retrieval`

Response:

```json
{
  "run_id": "evalrun_123",
  "dataset_id": "evalset_123",
  "method": "adaptive_agentic_retrieval",
  "status": "queued"
}
```

### GET `/evaluation/runs/{run_id}`

Returns status and metrics.

Response:

```json
{
  "run_id": "evalrun_123",
  "status": "completed",
  "summary_metrics": {
    "retrieval_precision": 0.81,
    "citation_accuracy": 0.88,
    "groundedness": 0.9,
    "hallucination_rate": 0.06,
    "average_latency_ms": 1850
  }
}
```

### GET `/evaluation/runs/{run_id}/results`

Returns per-question evaluation results.

Response:

```json
{
  "items": [
    {
      "result_id": "evalres_123",
      "question_id": "q001",
      "category": "api_flow",
      "status": "completed",
      "retrieved_evidence": [
        {
          "evidence_id": "ev_1",
          "file_path": "backend/app/auth/router.py",
          "start_line": 21,
          "end_line": 45,
          "is_relevant": true
        }
      ],
      "citations": [],
      "scores": {
        "retrieval_precision": 0.8,
        "retrieval_recall": 0.75,
        "citation_accuracy": 1.0,
        "groundedness": 2,
        "answer_correctness": 3
      },
      "answer": "The login flow starts...",
      "agent_trace_summary": {}
    }
  ],
  "next_cursor": null
}
```

## 18. Settings

### GET `/settings`

Returns non-secret settings.

Response:

```json
{
  "indexing": {
    "default_profile": "balanced",
    "max_file_size_bytes": 1000000
  },
  "providers": {
    "llm_provider": "openai",
    "embedding_provider": "local_sentence_transformer",
    "llm_configured": true,
    "embedding_configured": true
  },
  "security": {
    "secret_scanning_enabled": true
  }
}
```

### PATCH `/settings`

Updates user-adjustable non-secret settings.

Raw API keys must not be returned by any settings endpoint.

Request:

```json
{
  "indexing": {
    "default_profile": "balanced",
    "max_file_size_bytes": 1000000
  },
  "retrieval": {
    "top_k": 8,
    "evidence_min_score": 0.65
  },
  "security": {
    "secret_scanning_enabled": true
  }
}
```

Response:

```json
{
  "updated": true,
  "settings": {
    "indexing": {
      "default_profile": "balanced",
      "max_file_size_bytes": 1000000
    },
    "retrieval": {
      "top_k": 8,
      "evidence_min_score": 0.65
    },
    "security": {
      "secret_scanning_enabled": true
    }
  }
}
```

### GET `/settings/ignore-patterns`

Returns default and user-defined ignore patterns.

Response:

```json
{
  "default_patterns": [
    "node_modules/",
    ".venv/",
    "dist/",
    "build/",
    ".env",
    "*.pem"
  ],
  "user_patterns": [],
  "effective_patterns": [
    "node_modules/",
    ".venv/",
    "dist/",
    "build/",
    ".env",
    "*.pem"
  ]
}
```

### PATCH `/settings/ignore-patterns`

Updates user-defined ignore patterns.

Request:

```json
{
  "patterns": ["node_modules/", ".venv/", "dist/", "build/", ".env", "*.pem"]
}
```

Response:

```json
{
  "updated": true,
  "user_patterns": ["node_modules/", ".venv/", "dist/", "build/", ".env", "*.pem"],
  "effective_patterns": ["node_modules/", ".venv/", "dist/", "build/", ".env", "*.pem"]
}
```

### GET `/settings/providers`

Returns configured provider summaries without raw secrets.

Response:

```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4.1-mini",
    "configured": true,
    "api_key_set": true
  },
  "embedding": {
    "provider": "local_sentence_transformer",
    "model": "all-MiniLM-L6-v2",
    "configured": true,
    "api_key_set": false
  },
  "vector_store": {
    "provider": "chroma",
    "configured": true
  }
}
```

### PATCH `/settings/providers`

Updates provider configuration. Raw keys may be accepted but must never be returned.

Request:

```json
{
  "llm_provider": "openai",
  "embedding_provider": "local_sentence_transformer",
  "api_key": "<raw key accepted once and stored securely>"
}
```

Response:

```json
{
  "updated": true,
  "llm": {
    "provider": "openai",
    "configured": true,
    "api_key_set": true
  },
  "embedding": {
    "provider": "local_sentence_transformer",
    "configured": true,
    "api_key_set": false
  }
}
```

### POST `/settings/providers/test`

Tests configured LLM and embedding providers.

Response:

```json
{
  "llm": {
    "configured": true,
    "ok": true,
    "message": "LLM provider is reachable."
  },
  "embedding": {
    "configured": true,
    "ok": true,
    "message": "Embedding provider is reachable."
  }
}
```

## 19. API Surface Coverage Map

| Frontend page / feature | Main API endpoints |
| --- | --- |
| Project Dashboard | `GET /repositories`, `DELETE /repositories/{repository_id}` |
| Import Wizard | `POST /import-sessions/*`, `GET /import-sessions/{id}/preview`, `POST /import-sessions/{id}/confirm` |
| Indexing Status | `GET /repositories/{id}/index/status`, `GET /repositories/{id}/index/jobs/{job_id}/warnings` |
| Workspace Overview | `GET /repositories/{id}/overview`, `GET /repositories/{id}/reading-path` |
| Code Explorer | `GET /repositories/{id}/files/tree`, `GET /repositories/{id}/files/content`, `GET /repositories/{id}/symbols/{symbol_id}` |
| Search | `GET /repositories/{id}/search`, `POST /repositories/{id}/search/ask-with-evidence` |
| Chat | `GET/POST /repositories/{id}/conversations`, `POST /repositories/{id}/chat` |
| Evidence Viewer | `GET /repositories/{id}/evidence/{evidence_id}`, `POST /repositories/{id}/evidence/validate` |
| Graph View | `GET /repositories/{id}/graph`, `GET /repositories/{id}/graph/paths` |
| API Explorer | `GET /repositories/{id}/api/endpoints`, `GET /repositories/{id}/api/endpoints/{endpoint_id}/flow` |
| Impact Analysis | `POST /repositories/{id}/impact`, `GET /repositories/{id}/tests/related` |
| Evaluation | `GET /evaluation/datasets`, `POST /evaluation/runs`, `GET /evaluation/runs/{run_id}` |
| Settings | `GET/PATCH /settings`, `GET/PATCH /settings/ignore-patterns`, `GET/PATCH /settings/providers` |

## 20. Error Codes

Common error codes:

- `BAD_REQUEST`
- `VALIDATION_ERROR`
- `NOT_FOUND`
- `REPOSITORY_NOT_FOUND`
- `REPOSITORY_NOT_INDEXED`
- `REPOSITORY_SOURCE_MISSING`
- `INDEX_ALREADY_RUNNING`
- `INVALID_ARCHIVE`
- `ARCHIVE_PATH_TRAVERSAL`
- `FILE_TOO_LARGE`
- `NO_SUPPORTED_FILES`
- `INVALID_GITHUB_URL`
- `GITHUB_AUTH_REQUIRED`
- `GITHUB_CLONE_FAILED`
- `GITHUB_SYNC_FAILED`
- `LLM_PROVIDER_NOT_CONFIGURED`
- `EMBEDDING_PROVIDER_NOT_CONFIGURED`
- `INSUFFICIENT_EVIDENCE`
- `EVIDENCE_STALE`
- `CITATION_INVALID`
- `UNSUPPORTED_OPERATION`
- `INTERNAL_ERROR`

## 21. Notes for AI Coding Agents

- This contract describes the full product API. The development team may choose any implementation order, but implemented endpoints should follow the request and response shapes documented here.
- Prefer stable response shapes even when some fields are empty.
- Do not return internal absolute paths unless explicitly required for local debug mode.
- Do not return raw API keys, tokens, `.env` contents, private keys, credentials, or secret file snippets.
- For incomplete features, return a stable response with empty arrays and a clear status rather than breaking the frontend.
- Chat and impact endpoints must distinguish between evidence-based results and inferred results.
- If evidence is insufficient, return an explicit insufficient-evidence response instead of hallucinating.

## 22. Production Index, Artifact, And Diagnostics APIs

These APIs support the production indexing model described in `05_indexing_pipeline.md`. They can be implemented incrementally, but response shapes should remain stable.

### GET `/repositories/{repository_id}/indexes`

Lists index versions.

Response:

```json
{
  "repository_id": "repo_123",
  "active_index_version": 4,
  "items": [
    {
      "index_version": 4,
      "status": "ready_with_warnings",
      "source_revision": "abc123",
      "started_at": "...",
      "finished_at": "...",
      "activated_at": "...",
      "capability_readiness": {
        "code_explorer": "ready",
        "graph": "ready_with_warnings",
        "semantic_search": "failed",
        "chat": "limited"
      }
    }
  ]
}
```

### GET `/repositories/{repository_id}/indexes/{version}`

Returns index manifest.

Response:

```json
{
  "repository_id": "repo_123",
  "index_version": 4,
  "status": "ready_with_warnings",
  "base_index_version": 3,
  "source_revision": "abc123",
  "pipeline_versions": {},
  "coverage": {},
  "validation_summary": {},
  "capability_readiness": {},
  "artifact_counts": {},
  "activated_at": "..."
}
```

### GET `/repositories/{repository_id}/indexes/{version}/validation`

Returns validation report.

Response:

```json
{
  "repository_id": "repo_123",
  "index_version": 4,
  "summary": {
    "critical": 0,
    "error": 0,
    "warning": 8,
    "info": 12
  },
  "coverage": {
    "scan_files": 240,
    "parsed_files": 238,
    "files_with_chunks": 236,
    "unresolved_imports": 11,
    "orphan_nodes": 8,
    "dangling_edges_removed": 3
  },
  "issues": []
}
```

### GET `/repositories/{repository_id}/indexes/{version}/artifacts`

Lists artifacts. This endpoint may be restricted to local or debug mode.

Response:

```json
{
  "repository_id": "repo_123",
  "index_version": 4,
  "items": [
    {
      "artifact_type": "scan_result",
      "relative_path": "artifacts/scan-result.json",
      "retention_class": "permanent",
      "size_bytes": 12345,
      "content_hash": "sha256:..."
    }
  ]
}
```

### GET `/repositories/{repository_id}/indexes/{version}/unresolved-references`

Returns unresolved imports, calls, tests, config references, and API call matches.

Response:

```json
{
  "repository_id": "repo_123",
  "index_version": 4,
  "items": [
    {
      "reference_type": "import",
      "source_file_path": "backend/app/api/auth.py",
      "raw_reference": "app.services.missing",
      "message": "Could not resolve module inside repository.",
      "confidence": 0.0
    }
  ]
}
```

### GET `/repositories/{repository_id}/indexes/{old_version}/compare/{new_version}`

Compares two index versions.

Response:

```json
{
  "repository_id": "repo_123",
  "old_version": 3,
  "new_version": 4,
  "files": {
    "added": [],
    "removed": [],
    "changed": []
  },
  "symbols": {
    "added": [],
    "removed": [],
    "changed": []
  },
  "endpoints": {
    "added": [],
    "removed": [],
    "changed": []
  },
  "graph": {
    "nodes_added": 0,
    "nodes_removed": 0,
    "edges_added": 0,
    "edges_removed": 0
  },
  "architecture_changed": false,
  "affected_tours": []
}
```

### GET `/repositories/{repository_id}/graph/edges/{edge_id}/evidence`

Returns relation provenance and supporting evidence.

Response:

```json
{
  "edge_id": "edge_123",
  "source_node_id": "node_1",
  "target_node_id": "node_2",
  "relation_type": "calls",
  "origin": "resolver_exact",
  "confidence": 0.94,
  "supporting_evidence_ids": ["ev_1", "ev_2"],
  "provenance": []
}
```

### GET `/repositories/{repository_id}/guided-tours`

Lists available guided tours.

Response:

```json
{
  "repository_id": "repo_123",
  "index_version": 4,
  "items": [
    {
      "tour_key": "backend_request_flow",
      "title": "Backend Request Flow",
      "goal": "Understand how a request enters the backend and reaches service logic.",
      "persona": "newcomer",
      "step_count": 5
    }
  ]
}
```

### GET `/repositories/{repository_id}/guided-tours/{tour_key}`

Returns guided tour detail.

Response:

```json
{
  "tour_key": "backend_request_flow",
  "title": "Backend Request Flow",
  "steps": [
    {
      "step_id": "step_1",
      "title": "Start at the API router",
      "target_keys": ["file:backend/app/api/v1/routes/repositories.py"],
      "explanation": "This file defines the request entrypoints.",
      "why_this_step": "Routes are the first boundary users hit.",
      "learning_outcome": "Know where requests enter the backend.",
      "evidence_ids": []
    }
  ]
}
```

### Additional Error Codes

Add these production indexing error codes:

- `INDEX_PREFLIGHT_FAILED`
- `INDEX_LOCKED`
- `SCAN_INVENTORY_INCOMPLETE`
- `PARSER_OUTPUT_INVALID`
- `REFERENCE_RESOLUTION_PARTIAL`
- `GRAPH_ASSEMBLY_FAILED`
- `GRAPH_VALIDATION_FAILED`
- `FINGERPRINT_BUILD_FAILED`
- `INDEX_ACTIVATION_FAILED`
- `INDEX_VERSION_CONFLICT`
- `ARTIFACT_NOT_FOUND`
- `CAPABILITY_NOT_READY`
