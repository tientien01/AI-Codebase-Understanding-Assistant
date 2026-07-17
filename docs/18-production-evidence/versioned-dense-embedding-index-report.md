# RET-005 Versioned Dense Embedding Index Report

Status: Completed locally on 2026-07-17

## Delivered boundary

- Shared bounded loopback Ollama embedding adapter for evaluation and local retrieval.
- Canonical immutable `dense-embedding-index/v1` artifacts in the existing verified
  artifact store.
- Compatibility binding for repository/index ownership, resolved model name/digest,
  dimension, preprocessing version and every chunk content hash.
- Explicit dense semantic search integration with deterministic ranking input.
- Fail-closed sparse fallback for provider outage/model change, stale chunks/index,
  corruption, malformed vectors and ownership mismatch.

No database/API/frontend/dependency change was made. Production indexing-worker
composition, automatic dense activation/configuration, approximate-nearest-neighbor
storage and production-scale load evidence remain outside RET-005.

## Verification

- Focused dense artifact/retrieval gate: 10 passed.
- Canonical-LF evaluation/retrieval regression, including insufficient-evidence
  cases: 81 passed.
- Canonical-LF full backend retry: 394 passed, 31 declared integration-profile skips.
- `git diff --check`: passed.

The first canonical-LF full run reached 393 passed and 31 skipped but exposed one
unrelated equal-timestamp conversation replay ordering failure. A single retry passed
without code changes; RET-005 focused and retrieval regression gates were stable.

The real `embeddinggemma:latest` model/digest/dimension, quality, latency and memory
adoption evidence remains the accepted RET-004 result; RET-005 did not repeat that
costly three-repetition provider benchmark.
