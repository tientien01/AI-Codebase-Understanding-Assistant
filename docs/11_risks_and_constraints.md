# Risks and Constraints

## Document Purpose

This document identifies major risks, constraints, mitigations, and acceptance criteria for AI Codebase Assistant. It complements the architecture, indexing, evidence, error-handling, and testing documents by explaining why certain safety and reliability rules exist.

## Secret Leakage

Risk:

- The system reads, embeds, logs, stores, or displays secret values.

Mitigation:

- Never read real `.env` files.
- Ignore `.env.*` except `.env.example`.
- Ignore `secrets.*`, `credentials.*`, `*.pem`, `*.key`, private key files, and known credential files.
- Never log raw file content from config-like files unless explicitly safe.
- Add tests that create blocked files and verify they are absent from scanned output, chunks, vectors, logs, UI, and evidence records.

Acceptance:

- No blocked secret file appears in `FileRecord`, `ChunkRecord`, vector metadata, graph evidence, logs, evaluation results, or UI.

## Source Import Security

Risk:

- Uploaded archives or folder uploads include unintended files or unsafe paths.

Mitigation:

- Reject archive path traversal.
- Reject absolute uploaded paths.
- Reject paths containing `..`.
- Resolve paths before writing.
- Reject paths outside managed repository storage.
- Apply ignore rules before indexing and preferably during copy/extraction.

Acceptance:

- Import cannot read from or write to paths outside managed storage.

## Large Repositories

Risk:

- Indexing becomes slow, expensive, or memory-heavy.

Mitigation:

- Ignore dependencies and build outputs.
- Apply max repository size and max file size.
- Batch parsing and embeddings.
- Add indexing profile modes: Fast, Balanced, Deep.
- Use job progress, warnings, and partial parser failure handling.
- Add future incremental indexing by content hash.

Acceptance:

- Medium repositories can be indexed locally without freezing the UI.
- Status page shows progress, warnings, skipped files, and failed files.

## Parser Inaccuracy

Risk:

- Symbols, endpoints, API calls, or graph relations are incomplete or wrong.

Mitigation:

- Use AST/parser libraries when possible.
- Use confidence scores for best-effort extraction.
- Store parser warnings and parser errors.
- Use fallback retrieval when graph evidence is weak.
- Do not state low-confidence relation as fact.

Acceptance:

- Parser failure in one file does not fail the whole job.
- Low-confidence evidence is visible as such.
- Graph relations can be traced back to parser evidence when possible.

## Stale Index and Stale Citation

Risk:

- Source code changes after indexing, causing search results or old citations to point to outdated files or line ranges.

Mitigation:

- Use `index_version` on file, chunk, evidence, message, and project mental model records.
- Detect source changes through content hashes, modified timestamps, or Git commit changes when available.
- Mark repository as stale when source changes are detected.
- Mark old citations as stale after re-index when they reference an older index version.

Acceptance:

- UI can warn users when a repository index or citation may be outdated.
- Old chat history remains viewable but not presented as current evidence without a warning.

## LLM Hallucination

Risk:

- LLM invents files, functions, endpoints, relations, database tables, config keys, tests, or business logic.

Mitigation:

- Evidence-first prompts.
- Citation validator.
- Reflection/verification step.
- Insufficient-evidence response.
- Strict anti-hallucination rules.
- LLM receives selected evidence, not unrestricted repository claims.

Acceptance:

- Technical answers without valid citations are rejected or marked insufficient.

## Agent Over-Planning

Risk:

- The agent calls too many tools, retrieves too much evidence, becomes slow, or makes the answer harder to explain.

Mitigation:

- Set max retrieval rounds.
- Set max tool calls per question.
- Cap evidence count before LLM generation.
- Log agent trace for debugging.
- Use deterministic routing rules before LLM-based planning when possible.

Acceptance:

- Agent trace remains understandable.
- Common questions complete within acceptable latency.

## Provider Failures

Risk:

- LLM or embedding provider times out, rate-limits, rejects credentials, or becomes unavailable.

Mitigation:

- Provider abstraction.
- Timeouts.
- Retries for transient failures.
- Clear error mapping.
- Offline fake providers for tests.
- Optional local providers such as Ollama.

Acceptance:

- Provider failures return actionable API errors and UI states.
- Tests do not require paid provider keys.

## Graph Complexity

Risk:

- Graph becomes noisy, unreadable, or misleading.

Mitigation:

- Store relation confidence.
- Filter by node type and relation type.
- Limit depth.
- Build focused graph queries.
- UI shows subset around selected node.
- Separate graph view from practical relationship panels such as Depends on, Used by, Calls, Called by, Related endpoints.

Acceptance:

- Graph view remains usable for flow tracing and impact analysis.

## UI Scope Creep

Risk:

- UI becomes broad but shallow.

Mitigation:

- Implement page shells first.
- Show stable in-development states.
- Prioritize complete workflows over decorative panels.
- Reuse layout and components.
- Keep the main workspace readable and avoid information overload.

Acceptance:

- Full user flow exists even if advanced panels are initially marked in development.
- No known route renders a blank page.

## Evaluation Bias

Risk:

- The benchmark fixture is too small, too easy, or too close to the implementation, making the adaptive method appear better than it really is.

Mitigation:

- Use a curated fixture but include multiple categories and negative questions.
- Compare against keyword search and naive RAG.
- Store expected files, symbols, relations, and acceptable alternatives.
- Use transparent manual scoring.

Acceptance:

- Evaluation can show both strengths and failure cases.

## Technical Debt

Risk:

- The service becomes one large class that is hard to maintain.

Mitigation:

- Split scanner, parser, chunker, storage, graph, retrieval, evidence, evaluation, and agent services.
- Add tests per service.
- Keep routes thin.
- Keep domain logic testable without FastAPI or LangGraph runtime.

Acceptance:

- New parsers/providers can be added without modifying unrelated services.

## Constraints

- The first implementation is local-first.
- SQLite is the initial metadata store.
- Vector store is behind a provider abstraction.
- LLM and embedding providers are configurable.
- GitHub private import requires safe token handling and may be implemented after local upload flows.
- Multi-user authentication and cloud deployment are future extensions.
