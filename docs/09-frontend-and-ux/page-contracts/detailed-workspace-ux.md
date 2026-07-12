# Detailed Production Workspace UX

Status: Accepted production v1 specification  
Authority: User journeys, page behavior, shared states, and frontend acceptance  
Owner: Frontend and product owners  
Dependencies: `../interaction-contracts.md`, API/capability/evidence contracts  
Related source: `../../14-implementation-baseline/source-map.md`  
Related tests: component, accessibility, performance, and critical Playwright flows  
Last verified: 2026-07-12

## Product jobs and journeys

### Onboard

```text
/projects → /import → source/limits → preview/security/coverage
→ confirm → durable job status → overview/architecture/tour
→ source/evidence inspection
```

Success: the user imports and understands a repository without hidden local-path/manual steps and can explain why suggested files/modules matter.

### Trace

```text
search or entity deep link → shared entity detail → source/relations/flow
→ provenance/coverage/truncation → evidence → optional grounded explanation
```

Success: every step is inspectable and unsupported hops are explicit.

### Assess change

```text
select entity/version diff → impact → direct/inferred/unknown groups
→ related endpoints/models/tests/docs → evidence and verification actions
```

Success: the UI never converts missing coverage into “no impact.”

## Information architecture

Canonical routes are owned by `../interaction-contracts.md`. Primary surfaces are Projects, Import, Index Jobs, Overview/Architecture/Tours, Code, Search, API, Graph, Impact, Assistant, Evidence, Evaluation, and Settings. React Router owns URL/history; TanStack Query owns server state; feature-local state owns transient interaction only.

The layout may use navigation, main workspace and contextual entity/assistant drawer. It must remain useful when the drawer is closed and responsive when space is limited. Internal IDs, storage paths, chunk/vector counts and graph totals are hidden unless an authorized diagnostic view makes them actionable.

## Shared state contract

Every async surface implements applicable `initial`, `loading`, `refreshing`, `success`, `empty`, `limited`, `stale`, `unavailable`, `permission_denied`, `error_retryable`, `error_terminal`, and `cancelled` states. Payloads show reason, repository/index, coverage/truncation, retryability and next action.

“In development” is documentation/baseline language, not a runtime capability value. An unavailable planned surface may remain visible only when it accurately states the missing accepted prerequisite; it never returns fake data or a generic success.

## Page contracts

| Surface | User decision | Required content/actions | Critical degraded states |
| --- | --- | --- | --- |
| Projects | Which repository needs action? | name/source label, freshness, active index, capability summary, last verified activity; import/open/re-index/delete | empty, unauthorized, deleting, source missing, stale, latest job failed while prior active remains |
| Import | Is this exact source safe/in scope? | folder/ZIP/public Git; enforced limits, canonical preview counts, skips/warnings, duplicates, snapshot identity; cancel/confirm | expired/changed session, quota/security reject, no indexable files, public-Git acquisition failure |
| Index Jobs | Can I trust/use current result? | job vs attempt vs candidate version, server-declared stages, progress basis, warnings/errors, active-version preservation; cancel/retry/open validation | queued/backoff, lost lease/recovery, cancelled, failed candidate, broker/provider degradation |
| Overview | Where should I start? | purpose evidence, capability/coverage, architecture modules/entrypoints/config/tests, justified tour/reading actions | partial language/graph, stale index, optional architecture unavailable |
| Code | What does this source/entity show? | virtualized tree/list, bounded range-loaded source, symbols, related entities/evidence; copy/open/ask/impact | blocked/binary/too-large, range truncated, stale/deleted entity, parser limited |
| Search | Where is the target/support? | exact-first query, filters, typed reason/support, validated evidence action; optional semantic disclosure | no exact result, semantic unavailable, partial coverage, cancelled superseded query |
| API/Flow | How is a route supported? | endpoint/handler/schema/auth hints, bounded supported path, unsupported hops, source/evidence | unsupported framework, partial prefix/handler resolution, truncated path |
| Graph | What relationship is actionable? | task-specific server projection, node/edge provenance/support, filters/expand, coverage/truncation, accessible relation list | too broad request, capped projection, missing source, layout failure with list fallback |
| Impact | What may change? | validated target, direct/inferred/unknown, typed paths, endpoints/models/tests/docs, coverage and checklist | target ambiguous/stale, graph limited, projection truncated, no evidence |
| Assistant | Is the answer supported? | outcome, claims/citations, missing evidence, provider/capability/budget disclosure, trace summary; open source/evidence | insufficient evidence, provider outage, budget/cancel, stale context, citation invalid |
| Evidence | Does support validate? | source/range/hash, support/provenance label, version/freshness, claim links; open bounded source/re-run | forbidden, deleted, stale, range/hash invalid, blocked source |
| Evaluation | Did quality improve? | frozen dataset/config/run identity, baselines, per-case evidence/trace/errors, metrics/threshold decision | missing ground truth, provider outage, partial run, incomparable configuration |
| Settings | What safe preference can change? | effective non-secret profile, provider configured/test status, allowlisted preferences and re-index/restart effect | permission denied, invalid setting, provider degraded; security invariants never toggleable |

## Import and indexing presentation

The UI renders server-provided stage codes/labels and progress units rather than a Python-specific fixed pipeline. It separates repository lifecycle, source freshness, job/attempt, index version and per-capability readiness. A failed new build shows the prior active version remains available.

Status updates use cancellation-aware exponential backoff with jitter, honor server retry hints, pause when the page is hidden where safe, stop on terminal state and deduplicate queries. An event strategy may replace polling after accepted evidence; fixed 1–3 second polling is not a production contract.

## Large-data behavior

- Repository/file/symbol/job/evaluation lists use cursor pagination and virtualization after benchmark-triggered sizes.
- File content uses line/byte range loading, cancellation and stable scroll targets; no mandatory Monaco/editor dependency for a read-only product.
- Search debounces and cancels superseded requests.
- Graph requests server-enforced projections; layout moves off the main thread when measured thresholds require it and always has a grouped-list alternative.
- Query invalidation is entity/version scoped; activation invalidates active-version-dependent keys, not the entire application cache.

Numeric limits and frontend JS/CSS, route-load, interaction, long-task, memory, tree/code/graph budgets are accepted from representative evidence, not invented here.

## Evidence and uncertainty language

User-facing labels distinguish confirmed source/static resolution, framework rule, heuristic inference, AI inference, stale support, limited coverage and truncation. Color is never the only signal. Generic “confidence” or “health” numbers are not shown without a defined calibrated method and decision value.

Graph/impact/assistant wording uses direct, inferred and unknown. Architecture/tour steps explain their reason and link to evidence/signals. Internal metrics such as chunks/embeddings/nodes appear only in diagnostics when they help remediation.

## Accessibility and resilience

All actions, tree navigation, relation alternatives, dialogs/drawers and citation targets are keyboard accessible with visible focus. Focus is trapped/restored correctly; status updates use non-noisy live regions; headings/landmarks and text equivalents support code/graph content; contrast and reduced-motion preferences pass accepted checks.

Feature/page error boundaries preserve repository context and recovery. Refresh may retain last successful data only when visibly stale and safe. Permission failures do not leak repository metadata. Stored source/Markdown/AI output is escaped/sanitized; external links and copied content follow security policy.

## Release acceptance

Typecheck, lint, targeted component/hook/MSW contract tests, production build, accessibility checks and critical Playwright flows must pass. Performance evidence covers representative Small/Medium/Large reference classes. Required E2E includes import/index recovery, deep-linked source, exact search/evidence, endpoint flow, bounded graph, impact/tests, answer/refusal/citation, stale evidence after re-index, permission/capability/provider failure, evaluation and deletion recovery.
