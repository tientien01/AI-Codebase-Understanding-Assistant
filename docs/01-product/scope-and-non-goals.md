# Production v1 Scope and Non-goals

Status: Accepted  
Authority: Scope boundary  
Owner: Product owner  
Dependencies: `product-positioning.md`, `requirements-index.md`  
Last verified: 2026-07-12

## In scope

- Single-tenant, self-hosted web application targeting release level L3.
- Folder, ZIP, and constrained public Git repository import.
- Safe preview, full indexing, incremental indexing, validation, and atomic version activation.
- Deep Python/FastAPI analysis as the reference language profile.
- Structural JavaScript/TypeScript/React analysis with explicitly declared capability levels.
- File, symbol, endpoint, configuration, documentation, test, graph, and impact exploration.
- Exact, lexical, metadata, graph, and optional semantic retrieval behind typed ports.
- Evidence-backed search and bounded assistant workflows with citations and insufficient-evidence behavior.
- Evaluation, CLI/MCP adapters, observability, backup/restore, and single-node deployment evidence.

## Non-goals

- Autonomous editing, command execution, pull-request generation, or unattended remediation.
- Multi-tenant SaaS, enterprise RBAC, billing, collaboration, or public marketplace.
- Perfect static call resolution for reflection, dynamic dispatch, runtime registration, or generated code.
- Equal deep support for every programming language and framework.
- Kubernetes, microservices, dedicated graph/search/vector services, or high availability without measured need and an accepted ADR.
- Treating LLM-generated summaries, relations, or architecture labels as deterministic facts.
- Executing imported repository code, hooks, instructions, or tests during ingestion/indexing.

## Scope-change rule

Any addition that changes a non-goal requires updated requirements, threat/capacity analysis, an accepted ADR when technology or topology changes, a dependency-aware plan, and a ready task. Research documents alone cannot expand scope.
