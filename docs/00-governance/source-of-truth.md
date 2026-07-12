# Source of Truth

## Normative authorities

- Product behavior: accepted requirements in `01-product/`.
- Architecture and topology: accepted documents in `02-system-architecture/` and ADRs.
- Approved technology: `03-technology/stack-overview.md` plus accepted ADRs.
- Data semantics: `04-domain-and-data/`; physical schema is verified against migrations.
- Domain behavior: `05-domain-contracts/`.
- HTTP semantics and minimum wire schemas: the accepted detailed REST contract under `06-api-and-integrations/` until `FND-003` produces a generated, validated OpenAPI artifact. After that gate, OpenAPI is the machine-readable shape authority and must remain drift-checked against the semantic contract and generated client types.
- Release readiness: `18-production-evidence/`.
- Delivery phase order and gates: `15-plans/master-roadmap.md` and `15-plans/phases/`.
- Executable change scope: the selected `ready` or `in_progress` file under `16-agent-tasks/`.

## Detailed specification authority

Detailed specifications promoted from the original design are canonical domain detail when linked by the owning section README. They preserve field definitions, use cases, flows, examples, error cases, and acceptance criteria that the concise overview intentionally does not repeat.

When a detailed specification contains an older technology recommendation, `03-technology/` and accepted ADRs take precedence. When it describes behavior not yet implemented, it remains the production target; `14-implementation-baseline/` records the implementation gap. Target, baseline, and delivery plan are separate document classes.

## Conflict resolution

An accepted contract overrides a baseline description. A task may migrate source toward a contract but may not silently change the contract. Research and archive never override accepted documents.

## Implementation authorization

Only a task with status `ready` or `in_progress` under `16-agent-tasks/` authorizes source changes. The task must link requirements, contracts, decisions, paths, tests, and rollback.

The master task register is an index and dependency graph; it is not implementation authorization. `project-status.md` reports progress but cannot override any authority above.
