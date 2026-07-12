# Product Specification

## Vision

An evidence-first web platform that uses deterministic static analysis, versioned knowledge graphs, hybrid retrieval, and bounded Agentic RAG to help developers and AI agents understand and change code safely.

The canonical production positioning and scope boundaries are in `product-positioning.md` and `scope-and-non-goals.md`.

## Production v1 users

- Developer onboarding to an unfamiliar repository.
- Maintainer tracing flows and dependencies.
- Reviewer assessing change impact and related tests.
- Technical evaluator inspecting evidence and measurable AI quality.

## Production v1 scope

- Single-tenant, self-hosted web application with a mandatory L3 single-operator access boundary.
- Safe folder, ZIP, and public Git repository import.
- Durable full and incremental indexing.
- File, symbol, endpoint, architecture, and graph exploration.
- Hybrid search, evidence-backed Q&A, and bounded multi-step investigation.
- Citation validation, stale evidence, impact analysis, guided tours, evaluation, CLI/MCP access.

## Explicitly deferred

- Multi-tenant SaaS, enterprise RBAC, autonomous source modification, Kubernetes, dedicated graph/vector/search services, and equal deep analysis for every language.

## Core success metrics

- Users can import, index, understand, trace, and assess impact without hidden manual steps.
- All technical answer claims are evidence-backed or explicitly limited.
- Failed indexing never replaces the last valid active index.
- Benchmark and operational gates in `10-ai-rag-and-evaluation/` and `18-production-evidence/` pass.

`success-metrics.md` owns the cross-domain metric catalog. Detailed formulas, datasets, and versioned thresholds remain in the evaluation and evidence sections.

## Detailed specifications

- `specifications/product-brief-and-capabilities.md`: problem, objectives, proposed solution, architecture, capabilities, AI differentiator, workspace, quality, and success criteria.
- `specifications/requirements-and-use-cases.md`: stakeholders, core flows, U001-U045 use cases, functional/non-functional requirements, acceptance conditions, capability groups, and production additions.

These files are normative for feature intent and acceptance behavior. Technology names inside them are informative unless accepted by `03-technology/`. Implementation status is read from `14-implementation-baseline/`.
