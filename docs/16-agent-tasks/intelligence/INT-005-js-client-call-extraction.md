---
id: INT-005
title: Extract and resolve JavaScript client API calls
status: completed
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-15
depends_on: [INT-001, INT-002, INT-003, UI-012]
requirements: []
contracts:
  - docs/05-domain-contracts/parsing-and-graph.md
  - docs/05-domain-contracts/parsing/detailed-parser-output-schema.md
technology_docs:
  - docs/03-technology/stack-overview.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/services/parsing/javascript_parser.py
  - backend/app/services/parsing/client_call_extractor.py
  - backend/app/services/graph/graph_service.py
  - tests/intelligence/test_parser_golden.py
  - tests/test_service_boundaries.py
  - docs/16-agent-tasks/intelligence/INT-005-js-client-call-extraction.md
  - docs/18-production-evidence/js-client-call-extraction-report.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/db/**
  - backend/migrations/**
  - frontend/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - JavaScript and TypeScript extraction recognizes direct fetch and Axios calls, configured Axios instances, imported aliases, and static template routes.
  - Every emitted client call has deterministic identity, source location, method, normalized route evidence, and no execution of imported repository content.
  - Endpoint resolution compares HTTP method and normalized route templates without guessing unresolved dynamic expressions.
  - Existing parser, graph-schema, provenance, deterministic-ordering, and no-dangling-edge invariants remain enforced.
  - Focused parser and graph tests pass without dependency changes.
evidence_outputs:
  - docs/18-production-evidence/js-client-call-extraction-report.md
---

# INT-005 - JavaScript Client Call Extraction

## Context

The current JavaScript parser recognizes only direct `axios.get(...)` and `fetch("literal")` syntax. Repositories using `axios.create`, imported client aliases, or template routes can contain many real client requests while Request Flow reports zero client calls.

The project owner authorized implementation in the active conversation on 2026-07-15. This task establishes a reusable canonical extraction boundary while delivering the JavaScript/TypeScript adapter first.

## In scope

- Deterministic static extraction of direct Fetch/Axios calls and Axios instances created with a statically known base URL.
- Import/export alias propagation for local configured client modules.
- Static template route normalization with dynamic segments represented as route parameters.
- Method-aware endpoint matching using existing endpoint and graph contracts.
- Focused regression fixtures matching the structure used by WHAT2EAT.

## Out of scope

- Runtime execution, package installation, whole-program dataflow, arbitrary wrapper inference, or dynamic URL evaluation.
- Dart, Kotlin, Java, Swift, C#, GraphQL, gRPC, or WebSocket adapters; these require follow-up tasks using the same extraction boundary.
- Frontend Request Flow changes, schema migrations, or new dependencies.

## Required verification

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest ..\tests\intelligence\test_parser_golden.py ..\tests\test_service_boundaries.py -q
Set-Location ..
git diff --check -- backend/app/services/parsing/javascript_parser.py backend/app/services/parsing/client_call_extractor.py backend/app/services/graph/graph_service.py tests/intelligence/test_parser_golden.py tests/test_service_boundaries.py docs/16-agent-tasks/intelligence/INT-005-js-client-call-extraction.md docs/18-production-evidence/js-client-call-extraction-report.md
```

## Acceptance criteria

- A WHAT2EAT-style `apiClient = axios.create({ baseURL: "/api" })` exported from one file and imported by services produces client-call nodes.
- Literal and template routes such as `/restaurants/${restaurantId}` are represented deterministically and match compatible endpoint templates by method.
- Calls with unresolved base URLs or route expressions remain unlinked rather than being guessed.
- Existing direct Axios and Fetch extraction remains compatible.
