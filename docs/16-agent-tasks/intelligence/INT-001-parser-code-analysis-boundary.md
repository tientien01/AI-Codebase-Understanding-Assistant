---
id: INT-001
title: Consolidate the parser and code-analysis boundary
status: completed
priority: P0
phase: 3
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [IDX-002, IDX-004]
requirements: []
contracts:
  - docs/04-domain-and-data/identity-and-artifact-contract.md
  - docs/05-domain-contracts/parsing-and-graph.md
  - docs/05-domain-contracts/parsing/detailed-parser-output-schema.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs:
  - docs/11-testing/fixture-catalog.md
  - docs/11-testing/specifications/detailed-testing-plan.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/services/parsing/**
  - backend/app/services/code_analysis/**
  - tests/intelligence/**
  - tests/test_code_analysis.py
  - tests/test_service_boundaries.py
  - docs/11-testing/fixture-catalog.md
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/16-agent-tasks/intelligence/INT-001-parser-code-analysis-boundary.md
  - docs/18-production-evidence/parser-golden-report.md
  - docs/15-plans/phases/phase-3-code-intelligence.md
  - docs/project-status.md
forbidden_paths:
  - backend/app/api/**
  - backend/app/db/**
  - backend/app/services/indexing/**
  - backend/app/services/graph/**
  - backend/app/services/repositories/**
  - backend/app/workers/**
  - backend/migrations/**
  - backend/requirements.txt
  - backend/requirements-lock.txt
  - frontend/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Python source crosses one declared LanguageAdapter-to-IR boundary before compatibility projection into the current RepositoryState.
  - The legacy Python parser contains no second AST extraction implementation and is an explicit compatibility adapter only.
  - IR producer identity, schema version, canonical file key, repository/index ownership, content hash, source spans, and diagnostics are deterministic and JSON-serializable.
  - Malformed Python returns a typed diagnostic and no partial exact facts; parser failure still preserves safe local-profile fallback behavior.
  - Non-Python parsers remain explicit compatibility implementations and no unsupported language capability is newly claimed.
evidence_outputs:
  - docs/18-production-evidence/parser-golden-report.md
---

# Task INT-001 — Consolidate the parser and code-analysis boundary

## Context

The local parser registry mutates `RepositoryState` through `LanguageParser`. Python additionally invokes the code-analysis adapter/IR pipeline, but `PythonAstParser` still contains a second AST extractor as a fallback. This leaves two Python parsing implementations and hides the canonical adapter/IR boundary from orchestration.

## Objective

Make the Python language adapter the single file-local parser authority, expose its versioned deterministic IR result through the parser boundary, and retain current repository output through one explicit compatibility projection.

## In scope

- A typed immutable parse request carrying repository/index ownership, canonical file identity, content hash, language, and source.
- A versioned JSON-serializable ParsedFile/IR envelope for the current Python adapter output.
- One adapter registry entry for canonical Python analysis.
- A thin `LanguageParser` compatibility wrapper for the current `RepositoryState` consumer.
- Removal of the duplicate legacy Python AST extraction path.
- Golden tests for deterministic output, ownership/provenance fields, imports/aliases, nested symbols, line shifts, malformed syntax, and safe fallback.

## Out of scope

Resolver artifact design, cross-file resolution changes, graph-candidate normalization, non-Python IR adapters, indexing-worker composition, database persistence, API/frontend behavior, capability readiness, and production full/incremental equivalence.

## Existing code to reuse

- `PythonAdapter`, `IRModule`, `CodeAnalysisPipeline`, and the current CPG compatibility emitter.
- Stable ID helpers and parser diagnostics.
- Current `ParserService`, source fallback parser, and Python behavior regression tests.

## Implementation sequence

1. Define the immutable parse request and deterministic IR envelope serialization.
2. Make `LanguageAdapter` consume the request and make `PythonAdapter` populate the envelope.
3. Route Python through the canonical pipeline and reduce `PythonAstParser` to a compatibility wrapper.
4. Add golden boundary tests and preserve current parser/code-analysis behavior.
5. Run the declared suites and publish evidence/baseline/status updates.

## Data/API compatibility and migration

No database, migration, persisted artifact, or API changes. Current local `RepositoryState` symbols, chunks, endpoints, diagnostics, and graph hints remain compatibility output. The new IR envelope is internal and prepares a later typed indexing composition task.

## Failure, security, performance, and observability requirements

- Parse requests accept canonical relative POSIX paths only and never contain host paths.
- Source is file-local input and is not included in diagnostics or golden failure output.
- Syntax failure produces a stable typed error diagnostic and no symbols/imports/endpoints.
- Same input and component versions serialize byte-equivalently.
- No parser reads repositories, databases, artifacts, providers, skipped files, or secret/config credential files.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/intelligence/test_parser_golden.py -q
backend\.venv\Scripts\python.exe -m pytest tests/test_code_analysis.py tests/test_service_boundaries.py -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
```

The current local profile is used; PostgreSQL/Redis-only tests may retain their declared skips. Exact counts and limitations are recorded in `docs/18-production-evidence/parser-golden-report.md`.

## Acceptance criteria

- Python parsing reaches exactly one `PythonAdapter` AST implementation.
- The parsed envelope contains the declared schema, ownership, canonical file key, producer, content hash, language, IR facts, and diagnostics.
- Repeated parse and serialization are deterministic; line insertion does not change semantic symbol IDs.
- Imports and aliases, nested qualified symbols, valid inclusive spans, and malformed syntax match reviewed golden expectations.
- Existing Python endpoint, symbol, CFG/DFG, call/import, debug-output, and service-boundary tests pass.
- Targeted golden, regression, full backend, and diff-hygiene commands pass.

## Rollback

Restore the compatibility-only Python parser to its prior implementation and remove the unused typed request/envelope and golden tests. No data migration or runtime state rollback is required.

## Documentation and evidence updates

After all commands pass, publish the golden report, update source/test baselines and project status, mark this task completed, and advance the next candidate to `INT-002` without claiming resolver or canonical graph completion.

## Closing evidence

- `PythonAdapter` is the single Python AST authority behind an immutable request and deterministic `parsed-file/v1` envelope.
- `CanonicalPythonParser` owns the current-state projection; the deprecated `PythonAstParser` name contains no duplicate extractor.
- The 11-test golden suite, 27-test parser/code-analysis regression and 132-test local-profile backend suite passed.
- Exact results and remaining non-Python/resolver/graph/pipeline limitations are published in `docs/18-production-evidence/parser-golden-report.md`.
