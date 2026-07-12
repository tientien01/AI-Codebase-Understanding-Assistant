# Phase 6 — Production Workspace UX

Status: Approved; may begin after required API/read-model dependencies

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
