# RET-001 Typed Retrieval Boundary Report

Status: Verified task evidence; not release qualification
Task: `RET-001`
Verified: 2026-07-13
Environment: local Windows Python 3.11 profile

## Outcome

The current deterministic retrieval baseline now crosses one immutable request/candidate boundary. Candidates carry repository/index ownership, controlled retriever name/version, deterministic ID and rank, entity/source keys, raw score, matched terms, stable reason codes, support type and provenance references. A typed deterministic classifier preserves the existing question labels used by search and assistant callers.

The enabled adapters cover exact named targets, lexical chunks, symbols, endpoints, file metadata, graph nodes/context and the optional local sparse-semantic provider. `RetrievalService` remains the compatibility facade and retains its current max-score projection; this task does not introduce or claim accepted score normalization or fusion.

## Verification

| Command | Result |
| --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest tests/retrieval -q` | 16 passed |
| `backend\.venv\Scripts\python.exe -m pytest tests/retrieval tests/test_service_boundaries.py tests/test_code_analysis.py -q` | 43 passed; 1 dependency deprecation warning |
| `backend\.venv\Scripts\python.exe -m pytest tests -q` | 168 passed, 29 skipped; 1 existing duplicate-ZIP warning and 1 dependency deprecation warning |
| `git diff --check` | Recorded after documentation closure |

The regression matrix verifies classifier compatibility, all controlled retriever types, deterministic candidate identities/ranks and hybrid projection, repository ownership rejection, blank/stopword-only queries, and an unrelated-query insufficient-evidence case.

## Limitations

- The local compatibility index uses `idx_compat_<number>` until production query composition supplies opaque active index-version IDs.
- Current hybrid output still selects the maximum compatibility score per chunk. Versioned normalization, RRF/fusion, filters, deduplication policy and ranking configuration belong to `RET-002`.
- This is a deterministic regression fixture, not the versioned evaluation dataset or accepted quality/latency threshold evidence required by `EVA-001` and release gates.
- Evidence selection, token-budget context, citation validation and bounded agent repair remain outside `RET-001`.
