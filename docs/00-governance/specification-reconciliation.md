# Specification Reconciliation Register

This register prevents promoted detailed documents from reintroducing ambiguity.

| Detailed specification | Canonical content retained | Override authority |
| --- | --- | --- |
| Product brief and use cases | Intent, actors, flows, acceptance | Product scope/priority index |
| Detailed architecture | Domain layers and flows | Production topology + ADRs |
| Detailed data model/storage | Entity semantics and lifecycle | PostgreSQL physical design + migrations |
| Detailed REST API | Endpoint behavior/examples | Verified OpenAPI and API ADRs |
| Indexing/parser specs | Stages, schemas, validation | Typed production contracts |
| Agent/evidence specs | Workflow, guardrails, citations | Bounded Agentic RAG/evidence contract |
| Detailed UX | Page behavior and designed surfaces | Frontend production architecture |
| Evaluation/testing | Metrics and test coverage | Release thresholds/evidence |
| Environment/coding standards | Config groups and conventions | Accepted stack profiles and agent rules |
| Roadmap | Feature scope and milestones | Dependency-aware task register |

The current promoted production specifications are rewritten target documents. Their pre-production originals remain under `99-archive/original-docs/`; do not append a second “Production Update” section or restore superseded SQLite/Chroma/LangGraph/private-Git defaults into the current files.

## Reconciliation rule

Do not delete useful detail merely because its technology or current status changed. Preserve the behavior/schema/acceptance detail, replace only the superseded decision, and record that replacement in the owning README or an ADR.
