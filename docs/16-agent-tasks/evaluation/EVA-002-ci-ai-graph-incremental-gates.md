---
id: EVA-002
title: Add deterministic CI evaluation, graph, incremental, and assistant regression gates
status: in_progress
priority: P0
phase: 5
owner: project maintainer
last_verified: 2026-07-14
depends_on: [EVA-001, AGT-002]
requirements:
  - docs/01-product/success-metrics.md
  - docs/01-product/non-functional-requirements.md
contracts:
  - docs/10-ai-rag-and-evaluation/runtime-and-dataset-contracts.md
  - docs/10-ai-rag-and-evaluation/specifications/detailed-evaluation-plan.md
  - docs/11-testing/specifications/detailed-testing-plan.md
decisions: []
technology_docs:
  - backend/pyproject.toml
  - backend/requirements-lock.txt
  - .github/workflows/ci.yml
allowed_paths:
  - .github/workflows/ci.yml
  - backend/app/services/evaluation/
  - evaluation/gates/eva-002-ci.json
  - tests/evaluation/
  - docs/16-agent-tasks/evaluation/EVA-002-ci-ai-graph-incremental-gates.md
  - docs/18-production-evidence/ai-regression-gate-report.md
  - docs/14-implementation-baseline/capability-baseline.md
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/15-plans/phases/phase-3-code-intelligence.md
  - docs/15-plans/phases/phase-5-bounded-agent.md
  - docs/project-status.md
forbidden_paths:
  - backend/app/api/
  - backend/app/db/
  - backend/app/services/chat/
  - backend/app/services/code_analysis/
  - backend/app/services/indexing/
  - backend/app/services/retrieval/
  - evaluation/datasets/
  - tests/assistant/
  - tests/indexing/
  - tests/intelligence/
  - frontend/
  - storage/
  - secret and credential files
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - content-addressed deterministic CI gate configuration
  - frozen EVA-001 dataset, fixture, raw-result, and method identities
  - reviewed smoke-regression metric floors with explicit non-release classification
  - graph provenance/readiness, full-incremental equivalence, assistant refusal/citation/trace, and evaluation suites run as one named CI gate
  - fail-closed gate result and machine-readable regression diagnostics
  - full backend compatibility regression
evidence_outputs:
  - docs/18-production-evidence/ai-regression-gate-report.md
---

# Task EVA-002 — Add CI AI, graph, and incremental regression gates

## Context

EVA-001 provides a versioned deterministic retrieval dataset, same-input baseline runner, metric formulas and checksummed output. Existing graph normalization/readiness, incremental planner/equivalence, and assistant routing/sufficiency/trace suites already verify their owned deterministic boundaries, but CI exposes them only through the broad backend job and does not publish one named AI regression decision. The project owner authorized EVA-002 on 2026-07-14 after draft PR #26 was opened for EVA-001; delivery remains stacked on EVA-001 until that dependency merges.

## Objective

Add one explicit, fail-closed `AI, graph, and incremental regression` CI job that runs the existing owned suites without weakening them, executes the EVA-001 runner with frozen inputs, applies a content-addressed `evaluation-gate/v1` smoke policy, and emits deterministic machine-readable diagnostics. The smoke policy detects regressions on the checked-in synthetic dataset; it is not an accepted production-quality, provider, latency, cost, or release threshold.

## In scope

- Define immutable gate configuration with schema, dataset/fixture/raw-result identities, required methods/configuration IDs, metric definitions/floors, and `ci_regression_only` classification.
- Validate gate schemas, controlled methods/metrics, finite bounds, unique rules, frozen identities, completed case results, and missing/undefined metrics before deciding pass/fail.
- Produce stable gate configuration identity and ordered per-rule diagnostics without rewriting the evaluation run.
- Add a CLI that exits zero only when all identity and metric rules pass, and non-zero with safe concise diagnostics otherwise.
- Add a named GitHub Actions job using Python 3.11 and the locked backend requirements.
- In that job, run the task-owned evaluation gate tests plus existing graph provenance/readiness, incremental planning/equivalence, assistant workflow/sufficiency/trace, and evaluation suites.
- Run EVA-001 with fixed smoke identities/timestamps, then evaluate its JSON result with the checked-in gate configuration.
- Record local verification and clearly distinguish deterministic smoke floors from accepted release thresholds.

## Out of scope

- Changing graph, indexing, retrieval, evidence, assistant, dataset or production runtime behavior.
- Refreshing expected values merely to pass CI, accepting release thresholds, provider/model evaluation, load/latency/cost qualification, manual answer judging, or security release approval.
- Adding Actions, Python, provider, vector, graph, model, or reporting dependencies.
- Making CI-generated JSON a production evidence artifact; immutable release-candidate evidence remains a later release responsibility.

## Existing code to reuse

- `backend/app/services/evaluation/runner.py` and `evaluation/datasets/retrieval-v1/` for the frozen deterministic run.
- `tests/intelligence/test_graph_candidates.py` and `test_capability_readiness.py` for graph provenance/readiness invariants.
- `tests/indexing/test_incremental_planner.py` and `test_equivalence_service.py` for bounded planning and canonical equivalence mechanics.
- `tests/assistant/` for routing, sufficiency/refusal/citation, and structured trace privacy/persistence.
- Existing pinned setup actions and locked installation steps in `.github/workflows/ci.yml`.

## Implementation sequence

1. Define `evaluation-gate/v1` models, canonical identity, validation and ordered decision records.
2. Add a reviewed EVA-002 smoke configuration bound to EVA-001 identities and current deterministic baseline floors.
3. Implement gate evaluation and CLI exit behavior, including identity drift, missing method/case/metric, undefined/non-finite values and below-floor regressions.
4. Add unit/CLI tests using copied in-memory reports; do not edit the EVA-001 dataset or existing owned tests.
5. Add the named CI job with locked dependencies, targeted owned suites, deterministic runner invocation, and gate invocation.
6. Run targeted, combined owned-suite and full local-profile commands; record exact counts, rules, identities, limitations and CI workflow validation in evidence.

## Data/API compatibility and migration

This task adds internal JSON/CLI contracts and one CI job only. It changes no public API, database schema, dataset revision, retrieval output, assistant behavior, graph artifact or incremental result. `evaluation-gate/v1` changes require a new schema version; policy changes require an intentional reviewed diff and new configuration identity.

## Failure, security, performance, and observability requirements

- Reject unsupported schema/classification, duplicate or unknown rules, identity mismatch, non-finite bounds/results, missing methods/metrics, errored cases and malformed JSON before a passing decision.
- Never read credentials, runtime repositories, provider payloads or `storage/`; operate only on the declared synthetic run and gate files.
- Diagnostics include controlled rule IDs, expected/actual scalar values and reason codes, never source content, prompts or hidden reasoning.
- Bound configuration size and rule count. Gate evaluation is deterministic and network-free after locked dependency installation.
- CI must use least-privilege `contents: read`, pinned existing setup actions and no credential persistence.
- A failing gate must remain visible as a failed named job; do not silently continue, mark neutral or mutate the policy during a run.

## Required tests and commands

Run from the repository root with the locked Python 3.11 clean environment. PostgreSQL/Redis are not used by the targeted gate; the full local profile retains its declared integration skips.

```powershell
$env:PYTHONPATH = "backend"
& backend\.venv-clean\Scripts\python.exe -m pytest tests/evaluation/test_gates.py -q
& backend\.venv-clean\Scripts\python.exe -m pytest tests/evaluation tests/intelligence/test_graph_candidates.py tests/intelligence/test_capability_readiness.py tests/indexing/test_incremental_planner.py tests/indexing/test_equivalence_service.py tests/assistant -q
& backend\.venv-clean\Scripts\python.exe -m pytest tests -q
& backend\.venv-clean\Scripts\python.exe -m app.services.evaluation.runner --dataset evaluation/datasets/retrieval-v1 --output .tmp/eva-002-run.json --code-revision EVA-002-ci-smoke --index-version idx_eva_002_ci --started-at 2026-07-14T00:00:00Z --completed-at 2026-07-14T00:00:00Z
& backend\.venv-clean\Scripts\python.exe -m app.services.evaluation.gates --config evaluation/gates/eva-002-ci.json --run .tmp/eva-002-run.json --output .tmp/eva-002-gate.json
```

Also validate `.github/workflows/ci.yml` by inspection and the pushed draft PR check run. Record local results in `docs/18-production-evidence/ai-regression-gate-report.md`; do not claim the remote CI check passed until GitHub reports it.

## Acceptance criteria

- Gate configuration has a stable content-derived ID, `ci_regression_only` classification and explicit EVA-001 dataset/fixture/raw-result/method identities.
- Every metric rule names method, k, metric, comparison and finite bound; duplicates and unknown/undefined values fail closed.
- The unmodified frozen smoke run passes and emits deterministic ordered diagnostics plus a stable semantic decision checksum.
- Identity drift, missing/errored method data, NaN/Infinity, and a metric below its declared floor each produce a failed result and non-zero CLI exit.
- The named CI job runs the existing graph/readiness, incremental/equivalence, assistant and evaluation suites, then the runner and gate CLI with no provider/network/runtime-repository access.
- Existing owned assertions are not weakened, refreshed or copied into a second implementation.
- Targeted, combined and full local-profile suites pass; the evidence report preserves the distinction between CI smoke regression and production/release qualification.

## Rollback

Remove the EVA-002 gate module/config/tests and named CI job steps, then supersede unissued evidence. EVA-001 and all existing domain behavior remain unchanged. Issued evidence is never rewritten.

## Documentation and evidence updates

After all local commands pass, publish `docs/18-production-evidence/ai-regression-gate-report.md`, update source/test/capability and Phase 3/5/project status accurately, mark this task completed, commit/push the stacked branch, and open a draft PR targeting `agent/eva-001-evaluation-runner`. GitHub CI results are reported separately after the PR exists.
