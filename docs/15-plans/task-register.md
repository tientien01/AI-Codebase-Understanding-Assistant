# Master Production Task Register

This register defines delivery order. Before implementation, each row becomes a task file from `16-agent-tasks/task-template.md` with exact paths and tests.

Phase outcomes and gates are canonical in `master-roadmap.md` and `phases/`. This register owns identifiers and task dependencies only. A row does not authorize source changes.

| ID | Outcome | Depends on | Exit gate |
| --- | --- | --- | --- |
| DOC-001 | Establish executable production documentation | — | Docs navigation/link/diff validation |
| DOC-002 | Produce verified Phase 0 implementation baseline | DOC-001 | Source/API/test/setup/capability report validation |
| DOC-003 | Complete concrete cross-cutting production contracts | DOC-002 | Identity/runtime/threat/telemetry/UX contract validation |
| FND-001 | Approve production scope, NFRs, governance, ADRs | — | Blueprint review |
| FND-002 | Adopt locked Python dependency/project metadata | FND-001 | Reproducible install/CI |
| FND-003 | Split route/schema domains without behavior change | FND-001 | API contract regression |
| FND-004 | Replace broad application facade incrementally | FND-003 | Boundary/service tests |
| DAT-001 | Design PostgreSQL schema and ERD | FND-001 | Schema review |
| DAT-002 | Add Alembic and baseline migration | DAT-001,FND-002 | Empty/upgrade/drift tests |
| DAT-003 | Add production DB profile and repositories | DAT-002 | PostgreSQL integration suite |
| JOB-001 | Persist job/version/artifact state machine | DAT-003 | Transition/constraint tests |
| JOB-002 | Select queue implementation by PoC/ADR | JOB-001 | Recovery/cancel benchmark |
| JOB-003 | Add queue adapter and dedicated worker | JOB-002 | Duplicate delivery/restart tests |
| JOB-004 | Add lease, heartbeat, retry, cancellation, recovery | JOB-003 | Resilience suite |
| IDX-001 | Define immutable artifact manifest/store | DAT-003 | Checksum/schema tests |
| IDX-002 | Refactor typed indexing phases | IDX-001,JOB-003 | Phase contract tests |
| IDX-003 | Implement validation and atomic activation | IDX-002,JOB-004 | Failed-build preservation |
| IDX-004 | Implement incremental affected set/equivalence | IDX-003 | Full/incremental equivalence |
| INT-001 | Consolidate parsing/code-analysis boundary | IDX-002 | Golden parser tests |
| INT-002 | Add canonical resolver/reference artifacts | INT-001 | Resolution accuracy report |
| INT-003 | Enforce graph candidates/provenance/normalization | INT-002 | Zero critical graph issues |
| INT-004 | Compute capability readiness | INT-003 | Readiness invariant tests |
| RET-001 | Split typed retrievers and query classifier | INT-004 | Baseline retrieval unchanged |
| RET-002 | Add score normalization/ranker configuration | RET-001 | Ranking regression |
| RET-003 | Add evidence selector and token-budget context | RET-002 | Evidence/budget tests |
| AGT-001 | Add typed bounded workflow/tool registry | RET-003 | Routing/tool contract tests |
| AGT-002 | Add sufficiency, repair, citation validation | AGT-001 | Hallucination/refusal tests |
| AGT-003 | Persist structured trace/conversations | AGT-002,DAT-003 | Trace privacy/integration tests |
| EVA-001 | Implement datasets, baselines and evaluation runner | RET-003 | Reproducible evaluation run |
| EVA-002 | Add CI AI/graph/incremental regression gates | EVA-001,AGT-002 | Threshold report |
| UI-001 | Add Router and deep-linked workspace | FND-003 | Navigation E2E |
| UI-002 | Move server state to feature queries | UI-001 | Error/cache/invalidation tests |
| UI-003 | Add bounded evidence-aware graph projections | INT-004,UI-002 | Large graph/performance tests |
| UI-004 | Add architecture view, guided tour, diff impact | UI-003,AGT-002 | Evidence-backed UX E2E |
| UI-005 | Connect real evaluation/settings/status surfaces | EVA-001,UI-002 | Feature E2E |
| SEC-001 | Complete threat model, quotas and Git/import isolation | JOB-003 | Adversarial security suite |
| SEC-002 | Complete auth/access/audit design | DAT-003 | Authorization tests |
| OPS-001 | Add structured logs, metrics, traces and health | JOB-003 | Telemetry/readiness tests |
| OPS-002 | Add production containers/Compose/TLS profile | OPS-001,SEC-002 | Deployment smoke |
| OPS-003 | Add backup, restore, rollback and runbooks | OPS-002 | Recovery drill |
| EXT-001 | Add CLI/MCP over shared application ports | AGT-002,SEC-002 | Contract/auth tests |
| REL-001 | Run complete security/performance/resilience/E2E suite | all P0/P1 | All reports pass |
| REL-002 | Complete release evidence and production checklist | REL-001 | Release approval |

Optional pgvector, external vector/graph/search stores, LangGraph, Kubernetes, and multi-tenancy are intentionally absent. They enter the register only after radar triggers, PoC, and accepted ADR.
