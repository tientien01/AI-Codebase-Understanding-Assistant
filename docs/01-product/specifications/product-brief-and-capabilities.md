# Product Brief and Capability Contract

Status: Accepted production v1 specification  
Authority: Product intent, users, jobs, capability scope, and trust promise  
Owner: Product owner  
Dependencies: `../product-positioning.md`, `../scope-and-non-goals.md`, `../requirements-index.md`  
Related source: `../../14-implementation-baseline/`  
Related tests: onboarding, trace, change-impact, evidence, and degraded-mode E2E suites  
Last verified: 2026-07-12

## Product outcome

AI Codebase Assistant is a read-only, local-first code-intelligence workspace. It turns an untrusted source snapshot into deterministic, versioned facts and provenance-backed relationships, then supports human exploration and bounded AI explanation without allowing model output to override validated facts.

Production v1 targets a single-tenant, single-node self-hosted L3 deployment. It is not an IDE, autonomous coding agent, runtime debugger, multi-tenant SaaS, or generic chatbot over code chunks.

## Users and primary jobs

| User | Job | Successful outcome |
| --- | --- | --- |
| New developer | Onboard | Identifies architecture, entry points, key modules, configuration, tests, and a justified reading path |
| Maintainer | Trace | Follows a file, symbol, endpoint, configuration, or dependency through typed relations and source evidence |
| Reviewer/maintainer | Assess change | Separates direct, inferred, and unknown impact and identifies related APIs, models, tests, docs, and coverage limits |
| Evaluator/operator | Verify trust and operation | Reproduces indexing/answer quality, inspects evidence, and sees honest failure/capability states |

## End-to-end journeys

### Onboard

```text
import source → preview scope/security/limits → confirm idempotently
→ durable index build → validation/atomic activation
→ overview/architecture/tour → inspect source and evidence
```

Success requires no hidden local-path step, no unsupported “full language support” claim, and explicit limited/stale/unavailable states.

### Trace

```text
exact lookup → entity detail → bounded relations/path
→ provenance and coverage → source/evidence inspection
→ optional grounded explanation
```

Named files, symbols, endpoints, configuration keys, and error codes use deterministic lookup first. Semantic retrieval or an agent is not invoked merely to find an exact entity.

### Assess change

```text
resolve target or version diff → bounded typed traversal
→ group direct/inferred/unknown impact → related tests/endpoints/models/docs
→ evidence, coverage, truncation, and verification actions
```

“No relation found” means unknown within declared coverage, not “no impact.”

## Production v1 capabilities

### P0

- Folder upload, ZIP upload, and constrained public GitHub import with isolated preview, quotas, duplicate handling, and immutable source snapshot.
- Durable full and incremental index jobs, immutable version artifacts, deterministic validation, atomic activation, cancellation/recovery, and full/incremental equivalence evidence.
- File and symbol exploration, exact/lexical search, endpoint exploration, provenance graph, evidence/citation inspection, and repository deletion within ownership boundaries.
- Evidence-backed questions with deterministic fallback and valid insufficient-evidence results.
- Single-operator authentication/access boundary, telemetry, migrations, backup/restore, deployment, security, performance, and release evidence.
- Explicit capability readiness: `ready`, `limited`, `unavailable`, `failed`, or `stale`.

### P1

- Public-Git synchronization, bounded request flows, related tests, impact analysis, version comparison, persistent conversations/traces, optional semantic retrieval, evaluation UI, architecture view, and guided tours.

### P2

- Labeled domain/business-flow inference, persona-specific tours, optional reranking and constrained multi-step investigation when benchmarks justify their cost.

Private Git credentials, arbitrary Git hosts, multi-user sharing/RBAC, source modification, command execution, and unattended remediation are deferred.

## Capability and language disclosure

Readiness is calculated per repository and index version from required artifacts and validation. Job, repository lifecycle, source freshness, index lifecycle, and capability readiness remain separate states.

- Python/FastAPI is the reference deep profile.
- JavaScript/TypeScript/React is structural unless golden evidence proves deeper behavior.
- Markdown/config/Docker formats expose declared document/config facts.

File recognition alone never authorizes a “supported” badge for symbols, resolution, graph, endpoints, CFG/DFG, retrieval, or impact.

## Trust and evidence model

- Retrieval candidates are not evidence until repository/version/source/range/security/freshness/support validation passes.
- Evidence supports claim-level citations; a citation is a reference to evidence, not the evidence object itself.
- Static support types and provenance are primary. Generic confidence values cannot turn heuristic or LLM inference into confirmed fact.
- Imported comments, Markdown, instruction files, and provider output are untrusted data.
- Optional providers may summarize or classify selected evidence. They cannot discover files, create canonical IDs, resolve statically resolvable relations, activate indexes, or invent evidence.

## Quality and release measurement

Measure safe import, recovery, atomic activation, parser/resolver/graph quality, Recall@k, Precision@k, MRR, nDCG, citation validity, claim support, insufficient-evidence accuracy, hallucination, full/incremental equivalence, latency, peak memory, storage growth, tokens/cost, accessibility, restore consistency, and user task completion.

Numeric thresholds are accepted only from versioned benchmark evidence on declared reference classes. A provider, vector store, reranker, graph algorithm, or agent framework is adopted only when measured gain justifies latency, cost, security, maintenance, and operations.

## Acceptance boundary

A capability is implementation-ready only when the owning docs define input/output, data and identity, API/tool shape, state/error/failure behavior, authorization, capacity budget, tests, observability, rollback, and release evidence. Accepted target is not implemented; implemented is not verified; a working demo is not L3-ready.
