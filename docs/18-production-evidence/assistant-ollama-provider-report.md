# AGT-007 Ollama Grounded Chat Provider Report

Status: Completed locally; native adapter verified, real-model quality unverified
Date: 2026-07-17

## Delivered boundary

- Added a dependency-free native Ollama adapter using the documented local
  `GET /api/tags` readiness endpoint and non-streaming `POST /api/chat` endpoint.
- Restricted the base URL to credential-free loopback HTTP origins, validated the
  model identity, bounded timeouts to 120 seconds and responses to one MiB, and
  disabled redirects.
- Readiness distinguishes unavailable service, missing configured model and ready
  model without pulling, creating or deleting models.
- Chat requests JSON output, disables thinking, supplies no tools and passes only
  the existing AGT-004 grounded prompt. Existing citation and claim validation
  remain authoritative.
- Provider outage, timeout, malformed/incomplete/empty response, unrequested tool
  output and invalid citations return the deterministic grounded fallback.

The protocol shape follows the official Ollama [chat API](https://docs.ollama.com/api/chat)
and [model-list API](https://docs.ollama.com/api/tags). No new dependency, public API,
schema, migration, frontend behavior, embedding path or source-execution ability was
added.

## Verification

- Focused Ollama/provider/citation gate: 36 passed.
- Combined assistant/evidence/retrieval/service gate: 151 passed.
- Main Windows full backend invocation: 355 passed, 31 skipped, 18 failed only in
  the pre-existing frozen evaluation fixture because the checkout materialized
  `backend/auth_service.py` as CRLF.
- Canonical-LF clone fixture SHA-256:
  `e48e8badcfc2059ccdbcb7f1c74efc6d29ae9824725426cca0c0268bb4528e40`.
- Canonical-LF full backend gate with the exact staged AGT-007 diff: 373 passed,
  31 declared integration-profile skips.
- Diff hygiene: passed.

Tests use a deterministic fake transport and make no network call. They cover 19
native adapter cases plus existing evidence-context and citation regressions.

## Remaining limits

No live Ollama daemon/model was used, so answer quality, latency, warm/cold load,
memory/VRAM, context-window behavior and model adoption remain unverified. RET-004
owns that same-input benchmark. UI-024 owns public provider/readiness disclosure.
