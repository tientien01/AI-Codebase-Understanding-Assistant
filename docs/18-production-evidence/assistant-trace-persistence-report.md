# AGT-003 Assistant Trace Persistence Report

Date: 2026-07-14

Task: `AGT-003`

Profile: local SQLite; accepted PostgreSQL schema mapping inspected by the deterministic target test

## Verified outcome

- Every completed `ChatService` turn must pass one persistence call before its response is returned.
- The transaction contains a repository-owned conversation, ordered operator/assistant messages, one structured claim, its evidence citations, a trace budget summary and contiguous controlled events.
- Event payload construction accepts only bounded scalars and bounded identifier/reason lists. It does not copy the question, answer, evidence preview, provider response or arbitrary workflow diagnostics.
- Credential-shaped Bearer/API/token/password values are replaced with `[REDACTED]` before messages and claims are stored.
- Local replay filters by both repository and trace ID and reconstructs messages, claims, citations and events in explicit sequence order.
- A missing/cross-owner citation aborts the transaction; a store failure propagates through `ChatService`, so no successful response is returned without its trace.
- Legacy public conversation IDs remain response-compatible and are mapped deterministically with repository ownership to accepted internal `conversation_*` identities.
- The production adapter targets the accepted DAT-001/DAT-002 conversation/message/claim/citation/trace tables and maps compatibility index numbers to owned opaque production index-version IDs without a migration.

## Commands and results

```text
backend\.venv\Scripts\python.exe -m pytest tests/assistant/test_trace_persistence.py -q
6 passed

backend\.venv\Scripts\python.exe -m pytest tests/assistant tests/evidence tests/retrieval tests/test_codebase_service.py tests/test_service_boundaries.py -q
108 passed, 2 existing warnings

backend\.venv\Scripts\python.exe -m pytest tests -q
228 passed, 29 skipped, 2 existing warnings

git diff --check
passed; line-ending notices only
```

The 29 skips are declared PostgreSQL/Redis integration-profile tests because their service URLs were not supplied to this local run. The warnings are the existing OpenTelemetry importlib-metadata deprecation and duplicate-ZIP fixture warning.

## Remaining boundaries

- No public conversation-history/replay endpoint or frontend history surface was added.
- Automated retention/deletion scheduling and authenticated principal delivery remain governed by later security/operations tasks.
- This report does not establish semantic claim entailment, accepted agent quality/latency/cost thresholds, PostgreSQL runtime execution in this local profile or release readiness.
