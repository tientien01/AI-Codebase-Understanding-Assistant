# Error Handling and Fallback

## Document Purpose

This document defines error categories, standard error responses, fallback behavior, and UI mapping for AI Codebase Assistant. Endpoint-level contracts are defined in `04_api_contract.md`; this file focuses on what the system should do when something goes wrong.

## Standard Error Response

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

## Error Code Categories

### Repository

- `REPOSITORY_NOT_FOUND`
- `REPOSITORY_NOT_INDEXED`
- `REPOSITORY_ALREADY_INDEXING`
- `REPOSITORY_DELETE_FAILED`
- `STALE_INDEX`

### Import and Ingestion

- `IMPORT_SESSION_NOT_FOUND`
- `IMPORT_SESSION_EXPIRED`
- `IMPORT_PREVIEW_FAILED`
- `DUPLICATE_REPOSITORY_DETECTED`
- `INVALID_ARCHIVE`
- `ARCHIVE_PATH_TRAVERSAL`
- `INVALID_GITHUB_URL`
- `GITHUB_AUTH_REQUIRED`
- `GITHUB_CLONE_FAILED`
- `LOCAL_PATH_NOT_ALLOWED`
- `REPOSITORY_TOO_LARGE`
- `NO_INDEXABLE_FILES`

### Indexing

- `INDEXING_JOB_NOT_FOUND`
- `INDEXING_IN_PROGRESS`
- `INDEXING_FAILED`
- `SCANNER_FAILED`
- `PARSER_FAILED`
- `EMBEDDING_FAILED`
- `VECTOR_STORE_FAILED`
- `GRAPH_BUILD_FAILED`

### Chat, Retrieval, Agent

- `INSUFFICIENT_EVIDENCE`
- `LLM_PROVIDER_ERROR`
- `PROVIDER_NOT_CONFIGURED`
- `RETRIEVAL_FAILED`
- `AGENT_TRACE_UNAVAILABLE`
- `CITATION_VALIDATION_FAILED`
- `EVIDENCE_NOT_FOUND`
- `STALE_CITATION`

### Settings

- `INVALID_SETTING`
- `SECRET_NOT_READABLE`
- `PROVIDER_TEST_FAILED`

## Repository Not Indexed

Situation:

- User opens overview, chat, graph, search, evidence, API explorer, or impact before index is complete.

HTTP:

- `409 Conflict`.

Fallback:

- Frontend should show start indexing action or redirect to indexing status page.

## Import Session Expired

Situation:

- User starts import preview, waits too long, then tries to confirm.

HTTP:

- `410 Gone`.

Fallback:

- Frontend should ask the user to restart import.
- Temporary files should be cleaned up.

## Duplicate Repository Detected

Situation:

- Preview detects likely duplicate source by path, URL, name, or content hash.

HTTP:

- Usually `200 OK` with duplicate warning in preview.
- Use `409 Conflict` only when policy blocks duplicate import.

Fallback:

- Frontend offers Open Existing, Re-index Existing, Import as New, or Cancel.

## Indexing Already Running

Situation:

- User starts indexing while a job is active.

HTTP:

- `409 Conflict`.

Fallback:

- Return active job status.
- Frontend continues polling.

## Parser Errors

Recoverable:

- one file has syntax error;
- unsupported dynamic pattern;
- encoding failure for one file;
- low-confidence relation.

Behavior:

- mark file failed/skipped;
- create parser error;
- continue job;
- show warning.

Fatal:

- source missing;
- no indexable files;
- database unavailable;
- vector store unavailable when vectors are required.

## Embedding Provider Failure

Behavior:

- retry transient errors;
- mark job failed if all retries fail and embeddings are required;
- preserve parser metadata if possible;
- do not mark repository indexed if vectors are required and missing.

Optional fallback:

- If keyword-only mode is enabled, continue without embeddings and mark repository as indexed with warnings.

## LLM Provider Failure

HTTP:

- `502 Bad Gateway`.

Fallback:

- If retrieval succeeded, return a safe message that evidence was found but answer generation failed.
- Do not fabricate an answer without the model unless a deterministic answer template is available.

## Provider Not Configured

Situation:

- User tries chat, embedding, or evaluation requiring a provider that has not been configured.

HTTP:

- `409 Conflict` or `422 Unprocessable Entity` depending on context.

Fallback:

- Frontend shows provider setup action.
- Tests should use fake providers instead of requiring real keys.

## Vector Store Empty

Situation:

- Repository is marked indexed but vector collection has no chunks.

Behavior:

- attempt metadata search fallback;
- return insufficient evidence if fallback fails;
- recommend re-index.

## Graph Path Missing

Situation:

- flow or impact question lacks graph path.

Fallback order:

1. exact endpoint/symbol metadata;
2. vector search;
3. document search;
4. partial answer with caveat or insufficient evidence.

## Citation Validation Failed

Situation:

- Draft answer cites missing evidence, invalid line range, or unsupported claim.

Behavior:

- Attempt answer repair once if evidence is available.
- If repair fails, return insufficient evidence.
- Do not show invalid citations as reliable.

## Stale Citation

Situation:

- Evidence belongs to an older index version than the repository current index version.

Fallback:

- Evidence viewer shows stale warning.
- Chat history remains visible.
- User can re-run the question against the latest index.

## Insufficient Evidence

Response:

```json
{
  "conversation_id": "conv_123",
  "message_id": "msg_456",
  "question_type": "flow_tracing",
  "answer": "There is not enough evidence to answer confidently. The system found related files but no endpoint or graph relation that confirms the requested flow.",
  "citations": [],
  "evidence_sufficient": false,
  "missing_evidence": [
    "Expected endpoint or handler evidence",
    "Expected graph relation for flow tracing"
  ]
}
```

Rules:

- This is a valid assistant outcome, not a crash.
- UI should not display it as a red fatal error.
- User should see what was searched and what evidence was missing.

## Error to UI Mapping

| Error | UI behavior |
| --- | --- |
| `REPOSITORY_NOT_INDEXED` | Show Start Indexing or Go to Indexing Status. |
| `INDEXING_IN_PROGRESS` | Continue polling active job. |
| `IMPORT_SESSION_EXPIRED` | Ask user to restart import. |
| `DUPLICATE_REPOSITORY_DETECTED` | Show duplicate choices. |
| `PROVIDER_NOT_CONFIGURED` | Show provider setup action. |
| `LLM_PROVIDER_ERROR` | Show evidence found but answer generation failed. |
| `INSUFFICIENT_EVIDENCE` | Show insufficient evidence state, not fatal error. |
| `STALE_INDEX` | Show re-index recommended banner. |
| `STALE_CITATION` | Show stale citation warning. |
| `EVIDENCE_NOT_FOUND` | Show missing evidence state and link back to answer/search if possible. |

## Frontend Error States

Every page must handle:

- loading;
- empty;
- unauthorized/unconfigured provider;
- repository not indexed;
- indexing failed;
- stale index;
- stale citation;
- insufficient evidence;
- network error;
- backend error;
- in development.

Do not show blank pages.

## Notes for AI Coding Agents

- Do not treat every error as an exception toast. Some states are expected product states.
- Keep error messages user-safe.
- Do not expose raw stack traces in production UI.
- Always preserve enough context for retry or recovery actions.

## Production Indexing Errors And Capability Readiness

Production indexing should classify failures by scope:

- fatal;
- recoverable;
- file-scoped;
- batch-scoped;
- phase-scoped;
- warning.

### Additional Error Codes

Index lifecycle:

- `INDEX_PREFLIGHT_FAILED`
- `INDEX_LOCKED`
- `INDEX_VERSION_CONFLICT`
- `INDEX_ACTIVATION_FAILED`

Scan and parser:

- `SCAN_INVENTORY_INCOMPLETE`
- `PARSER_OUTPUT_INVALID`
- `PARSER_OUTPUT_MISSING`
- `FILE_FINGERPRINT_FAILED`

Resolution and graph:

- `REFERENCE_RESOLUTION_PARTIAL`
- `REFERENCE_RESOLUTION_FAILED`
- `GRAPH_ASSEMBLY_FAILED`
- `GRAPH_VALIDATION_FAILED`
- `GRAPH_PROVENANCE_MISSING`

Artifacts:

- `ARTIFACT_WRITE_FAILED`
- `ARTIFACT_NOT_FOUND`
- `ARTIFACT_SCHEMA_INVALID`

Capabilities:

- `CAPABILITY_NOT_READY`
- `SEMANTIC_SEARCH_UNAVAILABLE`
- `GUIDED_TOUR_UNAVAILABLE`

### Failure Policy

| Failure | Policy |
| --- | --- |
| One file parse failure | Continue, record file-scoped warning |
| One resolver miss | Continue, record unresolved reference |
| Critical graph validation failure | Do not activate new index |
| Architecture inference failure | Activate core index, mark architecture failed |
| Guided tour generation failure | Activate core index, mark guided tours failed |
| Embedding provider failure | Activate code/graph/keyword capabilities if valid; mark semantic search failed |
| Vector commit failure | Do not mark semantic search ready |
| Atomic activation failure | Keep previous active index |

### Capability Readiness Response

Index status and repository overview should expose readiness by capability:

```json
{
  "capabilities": {
    "code_explorer": "ready",
    "keyword_search": "ready",
    "graph": "ready_with_warnings",
    "semantic_search": "failed",
    "chat": "limited",
    "architecture": "ready",
    "guided_tours": "in_development"
  }
}
```

UI behavior:

- `ready`: feature is available.
- `ready_with_warnings`: feature is available with diagnostics link.
- `limited`: feature works with reduced behavior.
- `failed`: feature shows error state and remediation.
- `in_development`: feature shell remains visible but disabled.

Do not collapse all partial failures into one repository-level failed state unless the active index is unusable.
