# AGT-005 Assistant Context Request Evidence

Status: Verified local implementation evidence  
Verified: 2026-07-16  
Scope: Optional page/file/inclusive-line/symbol context, backend validation/retrieval anchoring, visible removable frontend context

## Delivered behavior

- `ChatRequest.context` is optional and additive. It accepts controlled workspace pages and bounded identifiers, forbids unknown fields, and never accepts raw source content or evidence IDs.
- Code Explorer derives the active indexed file, selected URL line and containing parsed symbol. Overview emits page-only context and does not claim file, line or symbol identity.
- The composer renders the exact outgoing context and removes it independently of source navigation. Changing to a different source context makes the new context visible again.
- The backend resolves code context only against the authenticated repository's active indexed file record, verifies the current source hash, inclusive range and symbol membership, then appends canonical identifiers—not source text—to the retrieval query.
- Invalid context fails with a stable HTTP 422 detail before retrieval/provider construction. Context-free clients retain the previous request and fallback behavior.
- Retrieval classification remains based on the operator question rather than context terms. Evidence selection, source revalidation, sufficiency and citation validation remain unchanged and authoritative.

## Verification results

| Gate | Result |
| --- | --- |
| `pytest tests/assistant/test_request_context.py -q` | Passed: 5 |
| `pytest tests/assistant tests/retrieval tests/test_api_contract.py -q` | Passed: 81 |
| OpenAPI export and API/context regression | Passed: artifact matches generated schema |
| Frontend `npx.cmd tsc -b` | Passed |
| Frontend `npm.cmd run lint` | Passed |
| Frontend `npm.cmd test -- --run` | Passed: 113 tests across 16 files |
| Frontend `npm.cmd run build` | Passed: 147 modules; existing >500 kB chunk warning only |
| Canonical-LF `pytest tests -q` with the complete working diff | Passed: 347, skipped: 31 |
| `git diff --check` | Passed |

The mandatory full suite was also invoked directly in the main Windows checkout. It passed 329 tests, skipped 31 integration-profile tests and failed the same 18 evaluation tests whose frozen `backend/auth_service.py` hash disagrees with CRLF checkout bytes. A temporary `core.autocrlf=false` clone with the exact tracked diff and three new files overlaid passed the complete 347-test collection, demonstrating that AGT-005 introduces no full-suite failure. The temporary clone and patch were removed after path verification.

## Security and failure evidence

- Extra request properties such as raw `source` are rejected by schema validation.
- Absolute, parent-relative and non-canonical file paths are rejected or cannot resolve to an indexed owned file.
- Missing files, changed source hashes, invalid ranges, missing symbols and symbol/range mismatches have stable reason codes.
- A regression proves invalid context cannot call the agent/retrieval boundary.
- Context identifiers only bias candidate discovery; they do not create evidence or bypass current owner/index/hash/range/citation validation.

## Remaining limitations

- Graph-node, endpoint/API, impact target and arbitrary `@` context selection are not implemented.
- Conversation replay, durable frontend history and multi-turn memory are not implemented.
- Ollama, dense embeddings and real-provider quality/latency qualification are not part of AGT-005.
- The production build retains the existing JavaScript chunk-size warning; no new dependency was added.
