# Product Positioning

Status: Accepted  
Authority: Production v1 product positioning  
Owner: Product owner  
Dependencies: `specifications/product-brief-and-capabilities.md`  
Last verified: 2026-07-12

## Position

AI Codebase Assistant is a local-first, evidence-first code intelligence workspace for understanding unfamiliar repositories and assessing change impact. It creates a versioned model of code facts and relationships, then lets humans and bounded AI workflows explore that model with verifiable source evidence.

It is not a generic chat interface over code chunks, an autonomous coding agent, or a replacement for an IDE/compiler/runtime debugger.

## Primary jobs

Production v1 optimizes three end-to-end jobs:

1. **Onboard:** identify architecture, entry points, important modules, configuration, tests, and a defensible reading path.
2. **Trace:** follow an endpoint, symbol, dependency, or configuration flow through evidence-backed relations.
3. **Assess change:** estimate the blast radius of a file/symbol/API change and identify related callers, models, tests, docs, and uncertainty.

Search, graph, code exploration, assistant, evidence, and evaluation exist to support these jobs rather than become isolated products.

## Differentiation

| Alternative | Useful strength | Product difference |
| --- | --- | --- |
| Text/IDE search | Fast exact location | Adds typed entities, relations, versions, provenance, flows, and impact |
| Naive code RAG | Natural-language access | Validates evidence and can refuse when support is insufficient |
| Repository map | Token-efficient overview | Maintains a durable queryable model and detailed evidence |
| Graph viewer | Relationship exploration | Uses bounded task-specific projections with coverage and provenance |
| Autonomous coding agent | Executes changes | Production v1 remains read-only and focuses on understanding and risk |

## Trust promise

Every technical claim is either supported by validated evidence, clearly labeled as an inference, or reported as unsupported. Static facts cannot be overwritten by LLM output. The UI discloses index version, capability limitations, stale evidence, inferred relations, and truncated projections.
