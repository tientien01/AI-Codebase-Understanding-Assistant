# Canonical Resolution Accuracy Report

Status: Verified local-profile contract evidence

Task: `INT-002`

Verified: 2026-07-13

## Delivered boundary

INT-002 adds a deterministic `PythonReferenceResolver` between canonical IR and graph compatibility output. It emits a JSON-serializable `resolved-reference-set/v1` artifact containing strict `resolved-reference/v1` items with repository/index ownership, canonical source/target keys, raw reference, outcome, method, support type, inclusive SHA-256-bound span and stable unresolved reason where applicable.

Every Python import/call discovered in the reviewed matrix is retained. Resolved references contain one target, ambiguity retains sorted candidates, and unresolved references contain no target. Resolution uses only IR plus a declared repository file catalog; it performs no source reread, graph traversal, database, provider, network or LLM call.

`CPGEmitter` no longer selects targets. It projects typed references into the current graph categories so existing local API behavior remains compatible.

## Accuracy matrix

| Case | Expected and verified outcome |
| --- | --- |
| Relative internal import | resolved to one canonical file key |
| Duplicate internal module suffix | ambiguous with two sorted file candidates |
| Local function call | resolved to one canonical symbol key |
| `self.method` and qualified class method | resolved to the owning canonical method key |
| Duplicate bare method name | ambiguous with both canonical method candidates retained |
| Builtin and aliased stdlib calls | unresolved with stable `builtin_target` / `stdlib_target` classification; no repository target claimed |
| Missing and dynamic attribute calls | unresolved with stable `target_not_found` / `dynamic_attribute_target` reasons |
| Reordered declared file catalog | byte-equivalent artifact output |

The reviewed fixture contains 9 references: 2 imports and 7 calls. All 9 produced the expected outcome class, for **9/9 exact fixture outcomes**. This is contract accuracy on a bounded synthetic matrix, not a general language benchmark.

## Verification results

| Command | Result |
| --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest tests/intelligence/test_resolver_accuracy.py -q` | Pass: 5 tests in 0.06 s |
| `backend\.venv\Scripts\python.exe -m pytest tests/intelligence tests/test_code_analysis.py -q` | Pass: 34 tests in 0.45 s |
| `backend\.venv\Scripts\python.exe -m pytest tests -q` | Pass: 137 tests, 29 skipped in 76.23 s; 2 existing dependency/duplicate-ZIP warnings |
| `git diff --check` | Pass |

The skipped tests require the declared PostgreSQL/Redis integration profile and are unaffected by this resolver task.

## Evidence boundary and remaining gap

This report does not prove cross-file symbol calls, inheritance/MRO, dynamic dispatch, framework route-handler matching, non-Python resolution, persisted reference artifacts, canonical graph candidates/normalization, capability thresholds, or full/incremental production-output equivalence. Those claims require later `INT-*` and pipeline-composition tasks.
