# BUG-002 Duplicate Symbol Index Hotfix Report

Status: Completed locally on 2026-07-17

## Reproduced failure

An imported Python repository contained repeated same-qualified-name definitions.
Both received the same stable symbol primary key, causing SQLite publication to fail.
The compatibility indexer then activated the candidate in memory before persistence,
so chat turns used a different index version from the database and returned HTTP 500.

## Fix

- Preserve the established base symbol ID for the first definition and assign stable
  ordered `_definition_N` IDs to later same-identity definitions across Python CPG,
  Tree-sitter, JavaScript regex and Go fallback producers.
- Reject any remaining duplicate symbol IDs before opening the local transaction.
- Persist the complete working candidate before replacing the in-memory active index.
- Route persistence failure through the existing failed-job/previous-index-retained
  path.
- Repair legacy completed-but-unpublished first candidates to a failed retryable state.

## Verification

- Focused regressions: 7 passed.
- `tests/test_code_analysis.py tests/test_codebase_service.py`: 50 passed.
- No imported repository content was executed or inspected by the hotfix.
