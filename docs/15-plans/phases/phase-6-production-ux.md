# Phase 6 — Production Workspace UX

Status: Approved; UI-001 routing, UI-002 server-state ownership and UI-003 bounded graph projections are verified, while UI-004, UI-005 and Phase 6 release evidence remain open

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

`UI-002` establishes one TanStack Query client, repository/index-version-owned query keys, cancellable typed reads, bounded classified retry, terminal/hidden polling, scoped mutations and explicit active-surface async/recovery states while preserving UI-001 URL ownership. Bounded graph UX, architecture/tour/diff and real evaluation/settings/status surfaces, accessibility automation, critical Playwright flows and accepted performance budgets remain open.

`UI-003` replaces silent client graph slicing with deterministic server-enforced projections, additive count/coverage/truncation/provenance metadata, normalized version-owned query identities, bounded focus/expand controls and a keyboard-native relation-list fallback. The compatibility API still uses active integer version sequences and existing GET routes; canonical opaque-version POST projection/path APIs, architecture/tour/diff UX, later surfaces, accessibility automation, Playwright and accepted release performance budgets remain open.
