# Workspace Interaction Contracts

Status: Accepted production v1 UX contract  
Authority: Route state, shared entity context, async/capability states, and performance/accessibility behavior  
Owner: Frontend and product owners  
Dependencies: API, capability, evidence, and detailed workspace specifications  
Last verified: 2026-07-12

## Route model

React Router owns browser history and reloadable deep links. Canonical routes:

```text
/projects
/import
/index-jobs
/repositories/:repositoryId/overview
/repositories/:repositoryId/code?path=<relative-path>&line=<n>
/repositories/:repositoryId/symbols/:symbolKey
/repositories/:repositoryId/api?endpoint=<endpointKey>
/repositories/:repositoryId/graph?view=<view>&root=<key>&depth=<n>
/repositories/:repositoryId/impact?target=<key>&compare=<indexVersionId>
/repositories/:repositoryId/search?q=<query>&types=<csv>
/repositories/:repositoryId/assistant/:conversationId?
/repositories/:repositoryId/evidence/:evidenceId
/repositories/:repositoryId/evaluation
/settings
```

Repository/index/entity/evidence identity in URLs uses opaque IDs or percent-encoded canonical keys, never host paths. Selection/filter state that must survive refresh/share belongs in URL; transient panel size, hover and unsaved input remain local. Invalid/stale URLs show recovery choices rather than silently redirecting to unrelated content.

## Data ownership

```text
UI component → feature query/mutation hook → API data-access method → versioned endpoint
```

TanStack Query owns server state, retry/cancel/cache/staleness/invalidation. React Router owns navigation. Component/feature state owns interaction. A global store, if later justified, may own cross-panel UI selection/layout only and must not duplicate repositories, jobs, evidence, graph results or conversations.

## Shared entity context

Code, search, graph, API, impact and assistant open the same `EntityDetailPanel` contract:

| Tab | Required data |
| --- | --- |
| Overview | type, canonical key, display name, capability/coverage, index version |
| Source | relative path, version, valid line range, content hash/staleness |
| Relations | bounded incoming/outgoing edges with type, support and provenance |
| Flows | bounded named paths/processes and truncation/unknown disclosure |
| Tests | deterministic related-test evidence or explicit none-found result |
| Evidence | support objects/citations and validation status |
| Impact | direct/inferred/unknown impact grouped by relation/path |

Opening an entity updates the URL and preserves the originating view. Closing returns focus to the invoking control. Cross-page links retain repository and explicit index-version context.

## Async state matrix

Every feature declares applicable states: `initial`, `loading`, `refreshing`, `success`, `empty`, `limited`, `stale`, `unavailable`, `permission_denied`, `error_retryable`, `error_terminal`, and `cancelled`. A spinner alone is not an error/limited state.

State payload includes safe reason code, current/requested index version, capability state, coverage/truncation, retryability and next action. Retain last successful data during refresh only when visibly marked stale/refreshing and safe for that action.

## Graph contract

The client requests a projection with repository/index, view, root keys, edge/node types, direction, depth, confidence/support filters and node/edge budgets. Server response returns counts, included counts, coverage, truncation reason, continuation/expand affordance and provenance. The UI never silently slices nodes/edges; the current 18-node/8-edge slice is a baseline defect to remove in `UI-003`.

## Accessibility acceptance

- All actions and graph alternatives are keyboard reachable with visible focus.
- Status changes use appropriate live regions without repeated noisy announcements.
- Dialog/panel focus is trapped/restored correctly; escape behavior is consistent.
- Color is not the only carrier of support, stale, limited or error state.
- Code/evidence line targets have text equivalents and stable headings/landmarks.
- Automated axe-style checks and keyboard/manual checks cover critical Playwright flows; serious violations block L3.

## Performance contract

Lists/trees/code use virtualization when measured size exceeds accepted budgets. Graph layout runs off the main thread for benchmark-triggered sizes. Search input debounces/cancels superseded requests. Route chunks may be lazy-loaded. Phase 6 must record initial JS/CSS, route-load, interaction, long-task, memory and graph-render budgets from representative hardware; numeric release thresholds live in evidence rather than this contract.

## Critical E2E flows

Import/preview/confirm/index; worker status/failure/retry; open repository and deep-linked source; search → entity/evidence; endpoint → flow → source; graph expand with coverage; impact → tests/evidence; assistant answer/refusal → citation; stale evidence after re-index; permission/capability/provider failure; evaluation run/result; and delete confirmation/recovery.
