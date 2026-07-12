# Detailed Production Indexing Pipeline

Status: Accepted production v1 specification  
Authority: Import-to-index stages, artifacts, failure policy, incremental behavior, and publish gates  
Owner: Indexing owner  
Dependencies: `../indexing.md`, `../../04-domain-and-data/identity-and-artifact-contract.md`, `../parsing-and-graph.md`  
Related source: `../../14-implementation-baseline/source-map.md`  
Related tests: import security, stage contract, recovery, activation, capacity, and equivalence suites  
Last verified: 2026-07-12

## Contract

```text
isolated import/preview → immutable source snapshot → durable job claim
→ preflight → canonical scan → parse → resolve → graph candidates
→ normalize/validate graph → chunks/lexical/optional semantic indexes
→ capability calculation → immutable manifest → atomic activation
```

Every stage has typed input/output, declared artifact/schema/component versions, bounded resource policy, idempotency key, progress/telemetry, recoverable/fatal failures, and cancellation boundary. Stages never infer undeclared input by rescanning storage.

## Import and preview

The acquisition/security contract is defined by the threat model and storage design. Preview returns source type/revision, canonical inventory summary, indexable bytes/files, language capability candidates, ignored/skipped reason counts, safe security warnings, duplicate candidates, enforced limits, and whether confirmation is allowed.

Preview does not estimate chunks, embeddings, graph size, time, or “AI readiness” unless a versioned estimator has benchmark evidence and reports uncertainty. Confirmation is idempotent and binds the exact session snapshot/policy. A changed/expired session is rescanned.

## Durable job model

PostgreSQL owns job/version/attempt state. Queue messages contain only IDs. Workers conditionally claim a lease, heartbeat, checkpoint safe phases, honor durable cancellation, and reject commits after lease loss. Redelivery and worker restart are normal; correctness relies on database constraints, idempotent stage effects and immutable artifacts.

Retries are bounded by error class and attempt budget with backoff/jitter. Permanent security/schema/validation errors do not retry. Concurrent incompatible builds for one repository are rejected or serialized. API processes submit/observe only.

Production v1 chooses **reject with the existing active job** for a second incompatible index submission. The API returns `409 INDEX_ALREADY_RUNNING`, the current `job_id`, and `retryable=false`; it does not silently enqueue another build. A repeated submission with the same idempotency key returns the original job. A future queueing policy requires a contract revision and migration.

Lease fencing follows the data-model contract: claim increments `lease_generation`; every heartbeat/checkpoint/write/publish uses a conditional predicate over job, attempt, generation, running state, lease expiry, repository operation generation, and cancellation. A stale worker stops on the first failed predicate. Checkpoints resume only at completed stage boundaries whose declared artifacts and checksums validate; otherwise that stage restarts idempotently. Partial in-stage output is temporary and never treated as a checkpoint.

## Stage contracts

| Stage | Required input | Output | Key gate |
| --- | --- | --- | --- |
| Preflight | job, snapshot, active manifest, requested profile | reserved inactive version and build plan | compatibility, lock, source and disk budget |
| Scan | immutable snapshot and scan policy | canonical inventory with one hash/read accounting | every file included or skipped with reason; no escape/secret |
| Parse | inventory items and parser cache | file-local typed IR and diagnostics | deterministic schema; parser does not write DB/resolve cross-file |
| Resolve | IR, canonical keys, framework rules | resolved/ambiguous/unresolved references | no LLM static authority; all outcomes retained |
| Graph candidates | IR/references/rules | provenance-bearing node/edge candidates | known keys, valid spans/support/origin |
| Normalize | candidates and graph schema | canonical graph plus changed/dropped diagnostics | deterministic merge; no served critical dangling edge |
| Validate | inventory, facts, graph, prior stage reports | issues, coverage and readiness inputs | critical issues block activation |
| Retrieval build | validated facts/source | chunks, lexical state, optional semantic state | valid spans; optional provider failure is capability-scoped |
| Optional views | validated graph/docs | architecture/tours summaries | inferred output labeled and source-linked |
| Fingerprint | all canonical outputs | component/file/artifact fingerprints | compatible incremental reuse |
| Publish | manifest, checksums, validation, DB rows | active-version audit event | one atomic expected-previous-version transaction |

Database writes use bounded batches and version-scoped upserts. No stage holds one transaction for the complete repository. Parallel parsing is capped by measured CPU/memory and uses bounded queues/backpressure; entire file contents are not retained across unbounded worker sets.

## Parsing cache and repeated work

Canonical scan owns file size/hash/encoding decisions. Parser cache key includes exact content hash, language adapter/parser/schema/rule versions and relevant normalized configuration. A cache entry is validated before reuse and cannot cross authorization/security policy incompatibility. Preview and indexing reuse scan data only under the exact snapshot contract.

Chunk hashes derive from source identity/content plus chunker version. Embeddings reuse only when chunk content, model/dimension and preprocessing match. Graph centrality/global summaries are computed only when a declared consumer and benchmark justify them.

## Graph and query constraints

Store one canonical edge direction; reverse lookup uses indexes. Graph normalization never stores an authoritative duplicate whole graph in JSON. Projection/query APIs enforce relation/node types, direction, depth, node/edge/result/time budgets and return included/total estimates, coverage, truncation reason and continuation/expansion affordance.

## Optional semantic/provider behavior

Exact, lexical, metadata, graph, source exploration and validation are deterministic mandatory paths. Embeddings, reranking, LLM summaries and guided narratives are optional. Their failure never fails an otherwise valid core build; dependent capability becomes `limited`, `failed`, or `unavailable`. Incomplete semantic indexes are never reported ready.

## Incremental indexing

Fingerprints cover raw/normalized content, structure, public API, dependencies, chunks and all producer/rule/model versions. The planner classifies add/delete/move/rename/content/doc/structure/API/dependency/component changes.

Affected sets start with changed files and expand only through allowed typed dependencies, endpoint chains, inheritance, frontend/backend matches and tests. Expansion has node/depth/time/fraction budgets. Exceeding a compatibility/budget threshold triggers a full rebuild; the value is accepted from equivalence/capacity evidence, not invented here.

Unchanged artifacts may be reused only when every producer/input/schema/security dependency is compatible. Full and incremental builds must produce equivalent canonical facts, graph, chunks, readiness and unchanged benchmark results under the declared equivalence rules.

## Failure and cleanup

- File parse failure is recoverable when coverage remains safely `limited`; it produces a file diagnostic.
- Database outage, lease loss, unsafe source, schema-invalid mandatory artifact, critical graph validation, checksum failure, disk exhaustion and activation conflict are fatal for the candidate version.
- Cancellation stops at a safe boundary and never publishes.
- Failed/cancelled builds remain inactive; partial artifacts use failed/debug retention and idempotent cleanup.
- Broker outage stops delivery; provider outage degrades only optional capabilities.

Parser and resolver outcomes are capability-scoped, not controlled by an undocumented global percentage:

- One file failure records a diagnostic; file exploration remains available for safe files and dependent symbol/graph capabilities become `limited` when their required coverage contract still passes.
- Failure of every file for one language profile marks that profile's parser-dependent capabilities `failed`; file metadata and safe lexical source search may still activate when their artifacts validate.
- If a mandatory capability named by the preflight build plan has a failed required artifact/profile, the candidate cannot activate. Optional capability failure never blocks unrelated mandatory capabilities.
- Unresolved references are retained. Count alone never becomes a hidden activation threshold. Invalid same-version references, missing provenance for served confirmed edges, or critical dangling edges block activation; otherwise affected graph/flow/impact capabilities are `limited` with measured coverage. Numeric release thresholds, if later required, come from versioned resolver benchmarks.

Cancellation is checked before and after every stage and inside the activation transaction. Cancellation observed before the activation checks prevents publish. After activation commits it is too late and cannot convert a successful version to cancelled.

Queue-library selection remains an explicit implementation gate: `JOB-002` must choose one adapter through the accepted recovery/cancellation PoC and ADR. Tasks may implement the queue port, data semantics, deterministic fake, and conformance suite before that decision, but may not choose RQ/Dramatiq ad hoc.

## Capacity and evidence

Release evidence establishes repository class limits for files/source/indexable bytes/symbols/edges/chunks/embeddings; job and per-stage p50/p95, peak memory/CPU, write batches, database/artifact growth, concurrent repositories/jobs, query/projection performance and provider tokens/cost. Required tests include duplicate delivery, kill/restart, stale lease, cancel, broker/DB/artifact/provider outage, disk full/OOM/timeout, corruption, atomic preservation, load and full/incremental equivalence.
