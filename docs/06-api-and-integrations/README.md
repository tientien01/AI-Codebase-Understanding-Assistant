# API and Integration Design

The accepted detailed REST contract owns HTTP semantics and minimum wire schemas until `FND-003` generates and validates the first OpenAPI artifact. From that gate onward, OpenAPI is the machine-readable shape authority while Markdown continues to own semantics that schemas cannot express.

Production API requirements:

- Versioned `/api/v1` surface with consistent resource naming.
- Bearer/session authentication appropriate to the accepted single-tenant deployment.
- Idempotency keys for import/index/delete operations where retries are plausible.
- Cursor or stable pagination for large collections.
- Standard error envelope with stable code, safe message, details, request ID, and retryability.
- Async operations return job/resource IDs; clients poll or subscribe to documented status updates.
- Rate/upload limits, cancellation, timeout, and capability-limited states are explicit.
- OpenAPI drift is checked against implementation and generated frontend types.

CLI and MCP are inbound adapters over the same application services. They must not duplicate authorization, retrieval, evidence, or indexing business logic.

## Detailed REST specification

`specifications/detailed-rest-api-contract.md` contains endpoint-level requests, responses, statuses, errors, evidence objects, pagination, import, repository, indexing, exploration, search, chat, graph, impact, evaluation, and settings APIs.

Until `openapi.yaml` is generated and verified, this is the normative target. `14-implementation-baseline/` identifies current coverage. Tasks may not implement missing endpoints unless their plan authorizes them.
