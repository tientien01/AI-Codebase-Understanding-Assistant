---
id: ARCH-001
title: Deliver a framework-aware rule-based architecture engine v2
status: in_progress
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-15
depends_on: [UI-008]
requirements: []
contracts:
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
decisions: []
technology_docs: []
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/schemas/exploration.py
  - backend/app/services/architecture/**
  - backend/app/services/repositories/repository_service.py
  - frontend/src/AppRoutes.tsx
  - frontend/src/components/common/Icon.tsx
  - frontend/src/pages/workspace/OverviewPage.tsx
  - frontend/src/pages/workspace/UI008Architecture.test.tsx
  - frontend/src/styles/pages/workspace.css
  - frontend/src/types/api.ts
  - tests/test_architecture_engine.py
  - tests/test_codebase_service.py
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
  - docs/06-api-and-integrations/artifacts/openapi-v1.json
  - docs/16-agent-tasks/production-ux/ARCH-001-rule-based-architecture-engine-v2.md
  - docs/18-production-evidence/rule-based-architecture-engine-v2-report.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/db/**
  - backend/migrations/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Architecture classification remains deterministic, bounded, evidence-backed and independent of LLM output.
  - Framework-aware detectors cover JavaScript/TypeScript, Python, Java/Kotlin, C# and Go conventions without forcing every repository into a web-layered model.
  - Layout selection supports layered web, MVC, modular/monorepo, event-driven, library, CLI and package-map fallback where indexed evidence permits.
  - Component relations originate in indexed graph facts or remain visibly inferred; infrastructure has no fabricated generic owner.
  - Overview groups operational endpoints, preserves full component names and renders directional support-aware relations without implying adjacency is a connection.
  - Existing architecture, graph, source navigation and full backend/frontend gates remain green.
evidence_outputs:
  - docs/18-production-evidence/rule-based-architecture-engine-v2-report.md
---

# ARCH-001 — Rule-based Architecture Engine v2

## Context

The current UI-008 read model is useful for a React/FastAPI layered repository but classifies components mainly from a small path/marker rule set and renders one dominant web layout. The owner explicitly chose to retain deterministic rules for the current phase while expanding useful coverage across common languages, frameworks and architecture styles.

## Objective

Introduce a maintainable detector registry and normalized rule-based architecture classifier, improve relation ownership and render the resulting repository-specific structure without LLM classification.

## In scope

- Framework/language signals for common JavaScript/TypeScript, Python, JVM, C# and Go conventions using existing indexed files, endpoints, symbols, graph relations and safe bounded source markers.
- Scored component roles, domain grouping, operational endpoint grouping, dynamic architecture-style selection and explicit fallback.
- Confirmed/inferred relation aggregation with source evidence and no generic infrastructure edge when the owner cannot be resolved.
- Additive architecture response metadata and an adaptive Overview presentation.
- Focused synthetic fixtures for representative language/style cases and insufficient evidence.

## Out of scope

- LLM architecture classification, new parsers/dependencies, runtime execution of imported code, migrations, persistence changes, graph producer replacement or exhaustive support for every ecosystem.

## Required tests and commands

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest ..\tests\test_architecture_engine.py ..\tests\test_codebase_service.py -q
.\.venv\Scripts\python.exe -m pytest ..\tests\test_service_boundaries.py ..\tests\test_api_contract.py -q
.\.venv\Scripts\python.exe scripts\export_openapi.py --check
Set-Location ..\frontend
npm.cmd test -- --run src/pages/workspace/UI008Architecture.test.tsx src/pages/workspace/UI007Overview.test.tsx src/pages/workspace/UI004Workspace.test.tsx src/App.test.tsx
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check -- backend frontend tests docs
```

## Acceptance criteria

- Detector logic is isolated from repository orchestration and can be extended without editing one monolithic conditional chain.
- Representative FastAPI/React, Spring, ASP.NET and Go repositories receive useful normalized roles; non-web/library and insufficient cases fall back honestly.
- Operational endpoints are not presented as peer business APIs.
- Confirmed and inferred arrows are visually and semantically distinct, directional and labelled.
- Data stores and external systems connect only to evidence-backed owners; otherwise the UI discloses the missing owner.
- Full declared gates pass and exact results are recorded.

## Rollback

Restore `RepositoryService.build_architecture` as the architecture builder and remove the additive v2 metadata/rendering. No data rollback is required.
