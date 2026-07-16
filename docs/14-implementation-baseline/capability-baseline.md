# Current Capability Baseline

Status: Source/test verified baseline  
Authority: Current source plus the 251-test suite
Owner: Product and intelligence owners  
Verified: 2026-07-14

States in this document describe the MVP only: `implemented`, `partial`, `placeholder`, `unverified`, and `production-blocked`. They are not the runtime readiness states defined by the target capability contract.

The source now includes a tested internal calculator for the target runtime states `ready`, `limited`, `unavailable`, `failed`, and `stale`. This does not change the MVP baseline states below or claim that the local indexer publishes production readiness records.

| Capability | Baseline state | Evidence and limitation |
| --- | --- | --- |
| Folder/ZIP import session | Implemented hardened local boundary | Preview/confirm/cancel remain compatible; normalized duplicates, file/tree quotas, streamed bytes and failed-session cleanup are adversarially tested |
| ZIP safety | Implemented hardened local boundary | Traversal, links, special files, case/Unicode collisions, nested archives, depth/count/size/ratio limits and actual streamed-byte enforcement are tested; container resource isolation and capacity qualification remain open |
| Public GitHub import | Partial hardened boundary | Canonical credential-free GitHub URL/ref checks, no redirect/prompt/hooks/submodules/LFS, HTTPS-only isolated configuration, shallow timeout, post-clone tree quotas, metadata removal and cleanup are network-free tested; OS/container network and resource isolation remain open |
| Repository persistence | Implemented MVP | SQLite ORM persists repository/index records; production schema/migrations absent |
| Background indexing | Production-blocked | Daemon thread and process-local controls; job status persists but worker execution/control is not recoverable |
| Incremental indexing | Partial | Changed-file behavior and failed-reindex preservation tested; full/incremental equivalence is not benchmarked |
| File scanning/secret paths | Implemented MVP | Dependency/secret skips and example-env allowance tested; content secret scanning before all sinks is not established |
| Python structure | Implemented deep baseline | Canonical AST/IR boundary, typed deterministic import/call outcomes, stable IDs, endpoints, CFG/DFG and compatibility graph tests exist; cross-file symbol/inheritance/dynamic resolver coverage remains partial |
| JS/TS and other languages | Partial structural | Registry declares 18 language/file profiles and Tree-sitter fallbacks; depth/accuracy matrix is not generated |
| Endpoint detection | Partial | FastAPI and Flask decorators plus generic fallback tested; framework coverage and resolution accuracy are unmeasured |
| Graph model/projections | Implemented MVP | Reference-derived Python edges have typed provenance/normalization and zero-critical gating; legacy CFG/DFG/non-Python/global normalization and large bounded server projection contracts remain incomplete |
| Search/retrieval | Implemented typed deterministic baseline with evaluation foundation | Owned typed retrievers feed content-addressed rank-only weighted RRF with explicit filters/limits/dedup/ties and bounded score projection; a six-case versioned synthetic dataset compares keyword, semantic-fixture and hybrid methods, but no persistent BM25/vector index, learned reranker, real provider benchmark or accepted quality/latency threshold exists |
| Evidence/citations | Implemented deterministic baseline | Ranked support is revalidated for owner/current index/source/hash/range/blocked/support eligibility, selected as whole spans under an inspectable token budget, persisted idempotently with content-bound IDs and projected as citations; claim extraction/support validation and benchmark thresholds are absent |
| Assistant | Partial validated stateful baseline | Typed bounded routing, question-specific sufficiency, one controlled repair and selected/current claim-citation validation feed exact validated provider source context plus atomic redacted conversation/claim/citation/structured-trace persistence. Repository-owned bounded list/replay APIs, retained frontend conversation identity, refresh/deep-link replay and an eight-message/1,000-token non-evidentiary memory projection are tested. Optional page/file/line/symbol request context remains visible and validated; graph/API context, Ollama qualification, retention execution and accepted agent thresholds remain absent |
| Real LLM provider | Unverified/optional | Provider receives whole selected source spans with owner/index/hash/range/blocked/budget checks and deterministic fallback; the default fake provider is deliberately not configured and real-provider quality remains unverified |
| Impact analysis | Implemented MVP | Files/endpoints/tests and unresolved-target behavior tested; completeness/confidence benchmark absent |
| Code/file/API/search UI | Implemented MVP | Pages call current APIs through the main controller; deep-link/router/query architecture absent |
| Graph UI | Partial | Multiple projections render, but client silently slices to 18 nodes and 8 edges |
| Evaluation UI/backend | Partial internal backend with CI smoke policy | Deterministic runner validates `evaluation-case/v1`, exports checksummed metrics, and a named CI job applies a content-addressed non-release smoke gate alongside graph/incremental/assistant suites; API/UI, answer judging, provider runs, accepted thresholds and load evidence remain absent |
| Settings UI | Placeholder/partial | Static values; backend exposes read-only safe settings/ignore patterns |
| Authentication/access | Implemented single-operator backend boundary | One-time bootstrap, scrypt password verifier, strict browser sessions, named Bearer tokens, repository path ownership, safe audit and recovery are tested; frontend login UX, rate limiting, TLS/container exposure, RBAC and automated audit retention remain open |
| Observability/operations | Production-blocked | No complete structured telemetry, readiness dependencies, CI/deploy, backup/restore or exercised runbooks |

## Language declaration warning

The language registry contains Python, HTML, CSS, JavaScript, TypeScript, Go, Rust, Java, Kotlin, C, C++, C#, PHP, Ruby, Swift, Markdown, Docker and configuration profiles. Registry presence means files can be recognized/routed; it does **not** mean equal symbol, resolver, CFG/DFG, endpoint, graph, or retrieval quality. UI and marketing must not convert this list into an unqualified “full support” claim.
