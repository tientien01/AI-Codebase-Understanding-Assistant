# Frontend and UX Architecture

`interaction-contracts.md` owns canonical routes, server/UI state ownership, shared entity context, async/capability states, graph projection disclosure, accessibility, performance evidence, and critical E2E flows.

The existing main surfaces remain: Projects, Import, Index Jobs, Overview, Code Explorer, Graph, API Explorer, Assistant, Impact, Search, Evidence, Evaluation, and Settings.

## Architecture target

- React/TypeScript/Vite remains the foundation.
- React Router owns deep links and browser navigation.
- TanStack Query owns server state, retry, cancellation, cache, staleness, and invalidation.
- Feature-local hooks/stores own UI state; Zustand is optional for complex graph interaction, not duplicated server data.
- API types are generated or checked against OpenAPI.
- Each page defines loading, empty, error, retry, stale, permission, limited-capability, and responsive states.

## Graph UX

Learn from Understand-Anything without replacing the designed workspace: use architecture layers, guided tours, evidence on nodes/edges, expand-on-demand, diff impact overlay, explicit coverage/truncation, and worker-based layout for large projections. Start with XYFlow + Dagre; adopt heavier layout/algorithm libraries only after benchmark.

## Quality

Keyboard navigation, color contrast, focus management, accessible status messages, virtualization for large lists/code, performance budgets, error boundaries, and critical Playwright flows are release requirements.

## Detailed page specification

`page-contracts/detailed-workspace-ux.md` preserves the complete design for navigation, project/import/indexing/workspace/code/graph/API/assistant/impact/search/evidence/evaluation/settings pages, component states, interactions, data requirements, responsive behavior, index quality, readiness, provenance, architecture views, guided tours, and incremental summaries.

The current main surfaces and visual direction remain. Ideas adapted from other repositories enhance these pages; they do not replace the designed information architecture.
