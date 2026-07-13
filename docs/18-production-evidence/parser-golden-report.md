# Canonical Parser Golden Report

Status: Verified local-profile contract evidence

Task: `INT-001`

Verified: 2026-07-13

## Delivered boundary

INT-001 makes `PythonAdapter` the only Python AST authority. An immutable `ParseRequest` carries repository/index ownership, a canonical relative POSIX file identity, canonical SHA-256 content identity, language and file-local source. The adapter returns a deterministic JSON-serializable `parsed-file/v1` IR envelope with producer identity, spans, imports, symbols and typed diagnostics.

`CanonicalPythonParser` is the single explicit projection from that IR into the current mutable `RepositoryState`. The former `PythonAstParser` is a deprecated import-compatible class name only and no longer contains a second AST extractor. Non-Python parsers remain compatibility implementations and gain no new capability claim.

## Golden matrix

| Area | Verified cases |
| --- | --- |
| Envelope | schema, repository/index IDs, canonical file key, SHA-256 content identity, adapter name/version and language |
| File-local facts | aliased absolute/from imports, nested class method, parameters and inclusive spans |
| Determinism | repeated byte-equivalent JSON serialization and stable semantic IR identity after leading line insertion |
| Failure | malformed Python yields one stable error diagnostic, no partial exact facts and a safe local-profile summary chunk |
| Security boundary | absolute, traversal, Windows-separated and empty-segment paths are rejected; request repr does not expose source |
| Consolidation | `ParserService` selects `CanonicalPythonParser` and invokes `PythonAdapter` exactly once per valid Python file |

## Verification results

| Command | Result |
| --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest tests/intelligence/test_parser_golden.py -q` | Pass: 11 tests in 0.28 s |
| `backend\.venv\Scripts\python.exe -m pytest tests/test_code_analysis.py tests/test_service_boundaries.py -q` | Pass: 27 tests in 2.61 s; 1 existing dependency deprecation warning |
| `backend\.venv\Scripts\python.exe -m pytest tests -q` | Pass: 132 tests, 29 skipped in 66.08 s; 2 existing dependency/duplicate-ZIP warnings |
| `git diff --check` | Pass |

The skipped tests require the declared PostgreSQL/Redis integration profile and are unaffected by this file-local parser task.

## Evidence boundary and remaining gap

This report proves the Python adapter/IR boundary and legacy compatibility behavior on reviewed synthetic inputs. It does not prove non-Python `parsed-file/v1` adapters, typed resolved-reference artifacts, canonical graph candidates, production worker composition, or full/incremental production-output equivalence. Those claims remain owned by `INT-002` through `INT-004` and later pipeline-composition work.
