# Observability, Capacity, and SLO Contract

Status: Accepted instrumentation contract; numeric L3 thresholds pending load evidence  
Authority: Telemetry names, correlation, SLIs, capacity profiles, alerts, and threshold acceptance  
Owner: Reliability owner  
Dependencies: deployment/capacity design and failure model  
Last verified: 2026-07-12

## Correlation context

Propagate `request_id` on every request and add `repository_id`, `job_id`, `index_version_id`, `trace_id`, and `evaluation_run_id` only where applicable. Accept a valid external request ID or generate one; return it in the response/error envelope. IDs are opaque and safe for logs, but source paths, query text and user prompts are not default metric labels.

## Structured event families

| Event | Required fields beyond correlation |
| --- | --- |
| `http.request.completed` | method, route template, status class, duration, response bytes, error code |
| `import.session.transitioned` | source type, from/to state, reason code, scanned bytes/files |
| `index.job.transitioned` | attempt, from/to state, worker ID, reason code |
| `index.stage.completed` | stage, duration, input/output counts, warning/error counts, artifact type |
| `index.version.activated` | previous/new version, validation status, capability summary |
| `retrieval.completed` | retriever/config version, candidate/selected counts, duration, truncated |
| `assistant.completed` | workflow/model class, rounds/tools, evidence count, citation result, tokens/cost, duration, outcome |
| `artifact.operation` | operation/type, bytes, duration, result/checksum result |
| `security.control` | control ID, allow/reject/quarantine, safe reason code |

Logs use an allowlist schema and redact before serialization/export. Never log raw secrets, authorization headers, provider keys, full source chunks, raw archives, or unrestricted prompts.

## Metric namespace

Use `aca_` prefix and base units:

```text
aca_http_requests_total{route,method,status_class}
aca_http_request_duration_seconds{route,method}
aca_jobs{state}
aca_job_attempts_total{result,stage}
aca_index_stage_duration_seconds{stage,result}
aca_index_files_total{stage,result,language_profile}
aca_index_artifact_bytes{artifact_type}
aca_queue_depth{queue}
aca_worker_lease_expirations_total{reason}
aca_retrieval_duration_seconds{retriever,result}
aca_retrieval_candidates_total{retriever,result}
aca_citation_validations_total{result,reason}
aca_provider_requests_total{provider_class,operation,result}
aca_provider_duration_seconds{provider_class,operation}
aca_provider_tokens_total{provider_class,direction}
aca_storage_bytes{store,retention_class}
```

Do not label metrics by repository, job, request, file, symbol, question, user text or error message; those are high-cardinality trace/log fields. `provider_class` is a controlled adapter class, not a credential/account ID.

## Trace spans

Top-level spans: `http.request`, `import.session`, `index.job`, `evaluation.run`. Index child spans follow declared stages; retrieval child spans follow classifier/retriever/fusion/evidence/context; assistant spans expose tool/provider/citation-validation summaries. Sampling never removes error/security/activation audit records; tracing can be sampled but authoritative job/audit state cannot.

## SLIs

| SLI | Measurement |
| --- | --- |
| API availability | eligible non-maintenance requests without server/internal dependency failure divided by eligible requests |
| Deterministic query latency | p50/p95 by route and capacity class, excluding optional provider time only when the endpoint contract separates it |
| Job completion | accepted jobs reaching successful terminal state within class budget |
| Recovery correctness | interrupted/redelivered jobs recovered without invalid activation or duplicate authoritative effects |
| Index activation safety | failed/invalid builds that changed active version; target is always zero |
| Evidence validity | valid current citations divided by citations expected to be current |
| Restore integrity | restore drills yielding database/artifact/active-version consistency |
| Assistant quality/cost | groundedness, insufficient-evidence accuracy, latency, tokens and cost from versioned evaluation runs |

## Capacity classes

Classify by source files, source bytes, indexable bytes, symbols, graph edges, chunks and language mix. `Small`, `Medium`, and `Large` thresholds remain `TBD` until `REL-001`-compatible benchmark evidence; no release or UI may invent them. Each accepted class records maximum input limits, index p50/p95/peak memory/artifact size, deterministic query p50/p95, graph projection/render limits, concurrent jobs/queries and provider budget.

## Threshold acceptance

Numeric SLOs are proposed from at least three repeatable production-like runs per reference class, then accepted in a versioned release evidence file with environment, dataset, revision and confidence/variance. Changing an accepted threshold requires rationale and release-owner approval; lowering it cannot hide a regression.

## Minimum alerts and runbooks

Alert on readiness failure, queue backlog age, lost/stale leases, repeated job failure, validation/activation failure, database/broker/artifact outage, storage exhaustion forecast, restore-check failure, security-control surge, provider error/cost budget and citation/AI regression. Every paging alert links an exercised runbook, owner, severity, deduplication key and clear condition; dashboards alone are not alerts.
