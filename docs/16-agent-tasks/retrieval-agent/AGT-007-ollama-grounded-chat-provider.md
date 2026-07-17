---
id: AGT-007
title: Add an optional grounded Ollama chat provider
status: completed
priority: P0
phase: 5
owner: project-maintainer
last_verified: 2026-07-17
depends_on: [AGT-004, AGT-006]
requirements: []
contracts:
  - docs/05-domain-contracts/assistant/detailed-agent-workflow.md
  - docs/05-domain-contracts/evidence/detailed-evidence-and-citation.md
  - docs/10-ai-rag-and-evaluation/runtime-and-dataset-contracts.md
  - docs/15-plans/stateful-local-assistant.md
decisions: []
technology_docs: []
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
allowed_paths:
  - backend/app/core/config.py
  - backend/app/services/chat/**
  - tests/assistant/**
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
  - docs/15-plans/phases/phase-5-bounded-agent.md
  - docs/15-plans/stateful-local-assistant.md
  - docs/16-agent-tasks/retrieval-agent/AGT-007-ollama-grounded-chat-provider.md
  - docs/18-production-evidence/assistant-ollama-provider-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/api/**
  - backend/app/db/**
  - backend/app/services/evidence/**
  - backend/app/services/retrieval/**
  - backend/app/workers/**
  - backend/migrations/**
  - backend/requirements.txt
  - backend/requirements-lock.txt
  - frontend/**
  - storage/**
dependency_changes: { allowed: false, add: [], remove: [] }
production_gates:
  - Ollama is opt-in and uses only an explicitly validated loopback HTTP base URL, validated model identity and bounded timeout.
  - Readiness distinguishes unavailable service, missing configured model and ready model without pulling, creating or mutating models.
  - Chat uses the native non-streaming Ollama API with JSON output and sends only the existing AGT-004 grounded prompt.
  - Outage, timeout, malformed payload, missing model, empty response and invalid citations preserve the deterministic grounded fallback.
  - The adapter adds no tools, embeddings, source execution, prompt logging, provider payload persistence or dependency.
evidence_outputs:
  - docs/18-production-evidence/assistant-ollama-provider-report.md
---

# AGT-007 — Ollama grounded chat provider

## Objective

Add an opt-in local Ollama chat adapter with deterministic readiness and fallback,
without weakening AGT-004 evidence context or citation validation.

## In scope

- A dependency-free native Ollama HTTP adapter for `GET /api/tags` and non-streaming
  `POST /api/chat`.
- Strict loopback-only base URL, model-name, timeout and response-size validation.
- Readiness states for invalid configuration, unavailable service, missing model and
  ready model.
- `LLMClient` selection of Ollama while retaining OpenAI and fake compatibility.
- Deterministic mocked protocol, failure and citation regressions.

## Out of scope

Model pull/create/delete, cloud Ollama, embeddings, provider UI, secrets, streaming,
tool calls, source execution, model quality adoption and release thresholds.

## Network and compatibility contract

The default endpoint is `http://127.0.0.1:11434`. Configured endpoints must use
plain HTTP, contain no credentials/query/fragment/path beyond an optional trailing
slash, and resolve syntactically to `localhost` or a loopback IP literal. Requests
never follow application-selected repository URLs. The adapter uses no API key and
does not log prompts or responses. OpenAI behavior and the public assistant API are
unchanged.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/assistant/test_ollama_provider.py tests/assistant/test_provider_evidence_context.py tests/assistant/test_sufficiency_citation_repair.py -q
backend\.venv\Scripts\python.exe -m pytest tests/assistant tests/evidence tests/retrieval tests/test_codebase_service.py tests/test_service_boundaries.py -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check -- backend/app/core/config.py backend/app/services/chat tests/assistant docs
```

The adapter tests use a deterministic fake transport and require no running Ollama
daemon or network access. A real-provider quality benchmark remains RET-004 scope.

## Acceptance criteria

- Valid readiness requires both a reachable local service and the configured model.
- The chat payload fixes `stream=false`, requests JSON output, disables thinking and
  uses the existing read-only grounded system/user prompt only.
- Provider output is accepted only through the existing non-empty, unique,
  allowlisted citation parser and downstream claim validation.
- All configuration/protocol/transport failures return `None` at the optional
  provider boundary and retain the deterministic answer.
- Targeted, combined, full-backend and diff-hygiene gates pass.

## Rollback

Set `LLM_PROVIDER=fake` or remove the Ollama adapter selection. No data, schema,
dependency or frontend rollback is required.

## Verification

Completed locally on 2026-07-17. The focused provider/citation gate passes 36
tests, the combined assistant/evidence/retrieval/service gate passes 151 tests,
and a verified canonical-LF clone passes the full backend collection with 373
passed and 31 declared integration-profile skips. The main Windows checkout
passes 355 tests and reproduces the known 18 evaluation failures caused by CRLF
materialization of the frozen fixture; no AGT-007 test fails. Exact protocol,
security, fallback and remaining provider-quality limits are recorded in
`docs/18-production-evidence/assistant-ollama-provider-report.md`.
