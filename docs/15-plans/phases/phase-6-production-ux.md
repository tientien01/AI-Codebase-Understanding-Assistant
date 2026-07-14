# Phase 6 — Production Workspace UX

Status: Approved; UI-001 canonical routing/deep-link foundation is verified, while UI-002 through UI-005 and Phase 6 release evidence remain open

## Outcome

Users can complete onboarding, trace, and change-impact jobs through deep-linked, accessible, performant surfaces that disclose readiness, evidence, uncertainty, staleness, and coverage.

## Tasks

`UI-001` through `UI-005`.

## Entry

Versioned API contract and representative read models exist; each page has defined states and E2E acceptance flow.

## Exit gates

- React Router owns navigation; TanStack Query owns server state; feature state does not duplicate authoritative data.
- Shared entity/evidence context connects code, search, graph, API, impact, and assistant surfaces.
- Every page handles loading, empty, error, retry, limited, stale, unavailable, and responsive states as applicable.
- Graph queries are bounded and disclose coverage/truncation; architecture/tour/diff views retain evidence.
- Typecheck, lint, targeted tests, production build, accessibility checks, and critical Playwright flows pass.

## Evidence

Frontend CI reports, navigation/state E2E, accessibility report, performance budget, and large-projection UX test.

`UI-001` establishes React Router browser/history ownership, the accepted canonical route set, reloadable source/line and evidence links, URL-owned search/graph/impact identities, and fail-closed route/repository recovery. Symbol and conversation identities remain explicit unavailable states until their public read models exist. Server-state ownership, the complete async-state matrix, bounded graph UX, later feature surfaces, accessibility automation, critical Playwright flows and accepted performance budgets remain outside this task.
