# Security Architecture

`threat-model.md` owns production v1 assets, trust boundaries, threat/control IDs, import/provider/access rules, and required release evidence. The detailed risk register expands failure likelihood and mitigation context.

Imported repositories, archives, Git metadata, source comments, Markdown, generated prompts, and provider responses are untrusted.

## Primary threats

- ZIP bomb, traversal, symlink escape, nested archive, oversized/deep trees.
- Git URL SSRF, malicious redirects, submodules/hooks, excessive clone size/time.
- Parser CPU/memory denial of service and malformed grammar input.
- Secret ingestion, embedding, logging, citation, or export.
- Prompt injection embedded in repository content.
- Unauthorized repository/evidence access and insecure deletion.
- Provider data exposure, dependency compromise, and unsafe operational commands.

## Required controls

- Never execute imported source or repository instructions during indexing/Q&A.
- Disable Git hooks/submodules and restrict protocols, redirects, time, size, and network destinations.
- Isolate workers with CPU, memory, time, filesystem, and preferably network limits.
- Filter secret-like paths and scan content before parsing, embedding, export, or LLM transmission.
- Store credential references, not raw credentials in domain records; redact logs/traces.
- Enforce repository ownership boundary in every query and tool.
- Apply upload quotas, rate limits, safe errors, dependency scanning, SBOM, non-root containers, and TLS.
- Security tests and threat mitigations are mandatory release evidence.

`specifications/risks-and-constraints.md` provides the detailed risk register for secrets, imports, large repositories, parser accuracy, stale indexes/citations, hallucination, over-planning, providers, graph complexity, evaluation bias, technical debt, ID drift, incremental divergence, provenance loss, and partial activation.
