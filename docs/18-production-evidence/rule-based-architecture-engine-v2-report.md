# ARCH-001 Production Evidence

Verified: 2026-07-15

## Delivered behavior

- Added a bounded, deterministic architecture detector registry for common JavaScript/TypeScript, Python, JVM, C#, and Go conventions.
- Normalized presentation, API, application, domain, data-access, messaging, integration, entrypoint, infrastructure, and fallback package roles.
- Selected repository-specific layered web, backend API, MVC, modular, event-driven, library, CLI, or package-map layouts without LLM classification.
- Grouped operational endpoints away from business APIs and preserved full component labels.
- Rendered directional confirmed, inferred, and unknown connections without inventing an infrastructure owner.
- Excluded secret-like paths and blocked build/dependency directories from architecture source inspection.

## Verification

- Architecture and repository tests: `33 passed`.
- Service-boundary and API-contract tests: `16 passed`.
- Targeted frontend tests: `18 passed`.
- Full frontend tests: `61 passed`.
- ESLint: passed.
- TypeScript project typecheck: passed.
- Production Vite build: passed (`145 modules transformed`).
- OpenAPI artifact check: passed after authorized contract export.
- `git diff --check -- backend frontend tests docs`: passed.

Two existing non-failing Python warnings remain: an OpenTelemetry importlib deprecation and the intentional duplicate-ZIP fixture warning.

## Safety and limitations

- Imported source is read as bounded text only; it is never executed, imported, installed, built, or followed as instructions.
- Rule-based output remains an evidence-backed projection rather than proof of runtime topology.
- Missing graph or ownership evidence is disclosed through inferred support or `unknowns` rather than replaced with a generic edge.
