# UI-008 production evidence — sixty-second architecture and assistant

Verified: 2026-07-15

## Delivered behavior

- Overview now receives a bounded deterministic architecture read model with repository identity, technologies, typed components, supported relations, primary flows, coverage, and explicit unknowns.
- The C4-lite map renders actor, presentation, backend boundary, API/application/data-access areas, and only infrastructure supported by indexed markers. Confirmed connections are solid; inferred connections are dashed.
- Raw alphabetical folders are no longer presented as the architecture mental model. Recommended Reading and Key Areas are compact and independently justified.
- The assistant uses an IDE-style drawer with a real collapsed rail, fresh-chat/history views, contextual prompts, evidence disclosure, evidence trail, and a multiline composer.
- Unsupported attachment and context actions remain visibly disabled rather than implying unavailable backend behavior.

## Verification

- `python -m pytest ../tests/test_codebase_service.py -q`: 25 passed, 2 warnings.
- `python -m pytest ../tests/test_service_boundaries.py ../tests/test_api_contract.py -q`: 16 passed, 1 warning.
- Targeted frontend suite: 18 passed across UI-008, UI-007 compatibility, UI-004, and App tests.
- Full frontend suite: 61 passed across 12 files.
- `npm run lint`: passed with no warnings.
- `npx tsc -b --pretty false`: passed.
- `npm run build`: passed; Vite production bundle generated.
- `python scripts/export_openapi.py --check`: OpenAPI artifact is up to date.
- `git diff --check -- backend frontend tests docs`: passed.

The warnings are pre-existing dependency/duplicate-ZIP-fixture warnings and are not introduced behavior failures.

## Evidence limits

- Architecture is a static indexed-source view, not a claim about live deployment topology.
- Structural relationships remain labelled `inferred` until graph evidence confirms them.
- The current assistant response contract exposes citations, not a public execution graph. The UI therefore presents an honest evidence trail and does not invent a graph trace.
- Browser-level visual acceptance remains with the project owner; component accessibility interactions and the production build are verified here.

## Acceptance follow-up

On 2026-07-15, the Primary Flows card regression reported during owner review was corrected. Flow buttons now use the intended dark card layout with bounded copy and a separated Graph Explorer action. The UI-008/UI-007 suites (6 tests), lint, typecheck, and production build passed after the correction.

The follow-up interaction review also established that a flow must be understandable without leaving Overview. Primary Flow cards now expand into an accessible, support-aware step diagram; confirmed, inferred, and unknown steps remain explicitly labelled. Graph navigation is a separate action and opens the API-flow projection. Targeted tests (18), the full frontend suite (61), lint, typecheck, and the production build passed after this change.
