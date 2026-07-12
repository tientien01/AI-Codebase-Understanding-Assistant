# Current Capability Baseline

Status: Source/test verified baseline  
Authority: Current source plus the 52-test suite  
Owner: Product and intelligence owners  
Verified: 2026-07-12

States in this document describe the MVP only: `implemented`, `partial`, `placeholder`, `unverified`, and `production-blocked`. They are not the runtime readiness states defined by the target capability contract.

| Capability | Baseline state | Evidence and limitation |
| --- | --- | --- |
| Folder/ZIP import session | Implemented | Preview, cache, fingerprint duplicate candidate, confirm, cancel and upload tests exist |
| ZIP safety | Implemented MVP | Traversal/duplicate rejection, nested archive skip and unsafe-content filtering tested; full adversarial/DoS suite absent |
| Public GitHub import | Partial | URL validation, shallow clone implementation and network-free preview test exist; SSRF/redirect/protocol/submodule/hook/size hardening is not production verified |
| Repository persistence | Implemented MVP | SQLite ORM persists repository/index records; production schema/migrations absent |
| Background indexing | Production-blocked | Daemon thread and process-local controls; job status persists but worker execution/control is not recoverable |
| Incremental indexing | Partial | Changed-file behavior and failed-reindex preservation tested; full/incremental equivalence is not benchmarked |
| File scanning/secret paths | Implemented MVP | Dependency/secret skips and example-env allowance tested; content secret scanning before all sinks is not established |
| Python structure | Implemented deep baseline | AST/adapter, stable IDs, endpoints, imports, calls, CFG/DFG and graph tests exist |
| JS/TS and other languages | Partial structural | Registry declares 18 language/file profiles and Tree-sitter fallbacks; depth/accuracy matrix is not generated |
| Endpoint detection | Partial | FastAPI and Flask decorators plus generic fallback tested; framework coverage and resolution accuracy are unmeasured |
| Graph model/projections | Implemented MVP | Normalization and project/dependency/API/function/data projections exist; large bounded server projection contract is incomplete |
| Search/retrieval | Implemented deterministic baseline | Exact/fuzzy/metadata/graph context and local sparse token-vector retrieval tested; no persistent BM25/vector index or versioned ranking benchmark |
| Evidence/citations | Implemented MVP | Repository lookup, source existence, index version, staleness and line range validation exist; claim-level benchmark absent |
| Assistant | Partial | Heuristic classifier, selected tools, evidence sufficiency and grounded fallback exist; no bounded multi-round repair or persistent structured trace |
| Real LLM provider | Unverified/optional | Provider boundary exists; default fake provider is deliberately not configured |
| Impact analysis | Implemented MVP | Files/endpoints/tests and unresolved-target behavior tested; completeness/confidence benchmark absent |
| Code/file/API/search UI | Implemented MVP | Pages call current APIs through the main controller; deep-link/router/query architecture absent |
| Graph UI | Partial | Multiple projections render, but client silently slices to 18 nodes and 8 edges |
| Evaluation UI/backend | Placeholder | Static questions and empty metrics explicitly say runner is pending |
| Settings UI | Placeholder/partial | Static values; backend exposes read-only safe settings/ignore patterns |
| Authentication/access | Production-blocked | Optional shared token only; blank token bypasses auth; no identity/ownership/audit model |
| Observability/operations | Production-blocked | No complete structured telemetry, readiness dependencies, CI/deploy, backup/restore or exercised runbooks |

## Language declaration warning

The language registry contains Python, HTML, CSS, JavaScript, TypeScript, Go, Rust, Java, Kotlin, C, C++, C#, PHP, Ruby, Swift, Markdown, Docker and configuration profiles. Registry presence means files can be recognized/routed; it does **not** mean equal symbol, resolver, CFG/DFG, endpoint, graph, or retrieval quality. UI and marketing must not convert this list into an unqualified “full support” claim.
