# Non-Functional Requirements

Status: Accepted metric requirements; numeric thresholds are proposed until accepted by release evidence  
Authority: Required NFR metrics and measurement contract  
Owner: Product, reliability, security, and evaluation owners  
Dependencies: `success-metrics.md`, `../08-reliability-and-operations/observability-and-slo-contract.md`, `../18-production-evidence/`  
Related source: `../14-implementation-baseline/`  
Related tests: capacity, load, resilience, security, retrieval/evidence, accessibility, and restore suites  
Last verified: 2026-07-12

## Measurement contract

Every accepted threshold records metric/formula, fixture/dataset and revision, repository capacity class, code/index/config/provider versions, production-like environment hardware/software, warm/cold/cache condition, concurrency, at least three repeatable runs, variance/confidence, owner, raw results, aggregate, threshold decision and immutable evidence link/checksum.

Until that evidence exists, a number below is a **proposed target**, not an achieved or release-approved claim. `REL-001` produces capacity evidence; product/evaluation/release owners approve thresholds for one release candidate.

## Required metrics

| Area | Metric and method | Proposed target or acceptance owner | Release gate |
| --- | --- | --- | --- |
| Availability | Eligible successful API requests / eligible requests, excluding declared maintenance only | 99.5% proposed for single-host profile; reliability owner accepts | Production-like availability/fault report |
| Deterministic search | End-to-end p50/p95 by repository class, query type, concurrency and cache condition | p95 ≤ 1.5 s proposed; capacity evidence accepts | Load report |
| Evidence lookup | Authorized evidence fetch + source/range validation p50/p95 | p95 ≤ 300 ms proposed | Evidence/load report |
| Job recovery | Time from eligible stale lease detection to recovered/terminal state; duplicate effects count | Stale detection ≤ 60 s proposed; zero duplicate authoritative effects required | Worker recovery report |
| Activation safety | Failed/invalid/cancelled builds that change active version | Exactly zero | Atomic activation suite |
| Graph integrity | Critical dangling served edges and provenance coverage for served confirmed edges | Zero critical dangling edges; 100% provenance required | Graph validation report |
| Citation | Syntactic/source/range/hash validity and claim support | 100% syntactic validity required; support threshold set by evaluation owner | Citation/claim report |
| AI quality | Recall@k, Precision@k, MRR, nDCG, hallucination and insufficient-evidence accuracy | Dataset-versioned thresholds set before release | AI regression report |
| Cost | Input/output tokens, provider calls and cost per case/run/request class | Budget set by product/release owner from benchmark | Evaluation/cost report |
| Capacity | Files, source/indexable bytes, symbols, edges, chunks, embeddings; duration, CPU, peak memory, DB/artifact growth | Small/Medium/Large boundaries set by `REL-001` | Capacity report and enforced config |
| Frontend | Route load, interaction, long tasks, memory, virtualized tree/range code and graph projection/render | UX/reliability owners accept on representative hardware | Frontend performance report |
| Recovery | RPO/RTO and database/artifact/active-version consistency | Operations/release owner accepts before L3 | Backup/restore drill |

Repository, upload, file, graph, concurrency, provider and storage limits are explicit deployment configuration. Startup or readiness validates mandatory values; APIs return safe limit errors before expensive processing; telemetry records rejection and resource usage without high-cardinality source labels.
