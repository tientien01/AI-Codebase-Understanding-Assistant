# Current Capability Baseline

Status: Source/test verified baseline  
Authority: Current source plus the 251-test suite
Owner: Product and intelligence owners  
Verified: 2026-07-14

States in this document describe the MVP only: `implemented`, `partial`, `placeholder`, `unverified`, and `production-blocked`. They are not the runtime readiness states defined by the target capability contract.

The source now includes a tested internal calculator for the target runtime states `ready`, `limited`, `unavailable`, `failed`, and `stale`. This does not change the MVP baseline states below or claim that the local indexer publishes production readiness records.

| Capability | Baseline state | Evidence and limitation |
| --- | --- | --- |
| Folder/ZIP import session | Implemented | Preview, cache, fingerprint duplicate candidate, confirm, cancel and upload tests exist |
| ZIP safety | Implemented MVP | Traversal/duplicate rejection, nested archive skip and unsafe-content filtering tested; full adversarial/DoS suite absent |
| Public GitHub import | Partial | URL validation, shallow clone implementation and network-free preview test exist; SSRF/redirect/protocol/submodule/hook/size hardening is not production verified |
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
| Assistant | Partial validated baseline | Typed bounded routing, question-specific sufficiency, one controlled repair and selected/current claim-citation validation now feed atomic redacted conversation/claim/citation/structured-trace persistence with owned replay; no semantic entailment benchmark, public history API, automated retention executor or accepted agent threshold |
| Real LLM provider | Unverified/optional | Provider boundary exists; default fake provider is deliberately not configured |
| Impact analysis | Implemented MVP | Files/endpoints/tests and unresolved-target behavior tested; completeness/confidence benchmark absent |
| Code/file/API/search UI | Implemented MVP | Pages call current APIs through the main controller; deep-link/router/query architecture absent |
| Graph UI | Partial | Multiple projections render, but client silently slices to 18 nodes and 8 edges |
| Evaluation UI/backend | Partial internal backend with CI smoke policy | Deterministic runner validates `evaluation-case/v1`, exports checksummed metrics, and a named CI job applies a content-addressed non-release smoke gate alongside graph/incremental/assistant suites; API/UI, answer judging, provider runs, accepted thresholds and load evidence remain absent |
| Settings UI | Placeholder/partial | Static values; backend exposes read-only safe settings/ignore patterns |
| Authentication/access | Production-blocked | Optional shared token only; blank token bypasses auth; no identity/ownership/audit model |
| Observability/operations | Production-blocked | No complete structured telemetry, readiness dependencies, CI/deploy, backup/restore or exercised runbooks |

## Language declaration warning

The language registry contains Python, HTML, CSS, JavaScript, TypeScript, Go, Rust, Java, Kotlin, C, C++, C#, PHP, Ruby, Swift, Markdown, Docker and configuration profiles. Registry presence means files can be recognized/routed; it does **not** mean equal symbol, resolver, CFG/DFG, endpoint, graph, or retrieval quality. UI and marketing must not convert this list into an unqualified “full support” claim.
