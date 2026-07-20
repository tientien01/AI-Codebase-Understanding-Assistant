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

The static reconstruction under `references/ai-codebase-ui-reference/` records the supplied visual direction for workspace density, hierarchy, dark-theme tokens and page composition. Its screenshots are visual references and its HTML/CSS are structural examples only; accepted interaction/page contracts and current typed React boundaries remain authoritative. `assets/concepts/ui-004-graph-explorer.png` captures the UI-004 graph direction.

UI-004 browser qualification lives under `frontend/e2e/`: deterministic owned fixtures exercise the architecture tour into source, complete graph focus/relations with reduced motion, and honest current-impact disclosure. Axe serious/critical checks and 12/80/220-node Chromium observations are part of the named CI gate; they do not create a Phase 6 release-performance threshold.

UI-005 replaces the remaining fabricated Evaluation/Settings content. Settings reads only the existing non-secret allowlist and effective ignore patterns; Evaluation preserves repository/index context while explicitly disclosing that interactive dataset/run/result APIs are unavailable. The UI never presents offline CI evidence as a user-triggered run or exposes a control for an unsupported settings mutation.

UI-025 adds an optimistic user turn and visible evidence-checking state while a chat request is pending, a line-numbered wrapping Evidence Viewer, and confirmed per-conversation removal backed by repository-owned soft deletion. The generic Evidence “in development” card is removed. Impact, Search, and Evaluation keep their canonical deep links but are intentionally omitted from workspace navigation until the owner resumes those surfaces. Grounded provider prompts now request direct natural-language explanations in the question's language; citation validation and deterministic fallback remain unchanged.

## Quality

Keyboard navigation, color contrast, focus management, accessible status messages, virtualization for large lists/code, performance budgets, error boundaries, and critical Playwright flows are release requirements.

## Detailed page specification

`page-contracts/detailed-workspace-ux.md` preserves the complete design for navigation, project/import/indexing/workspace/code/graph/API/assistant/impact/search/evidence/evaluation/settings pages, component states, interactions, data requirements, responsive behavior, index quality, readiness, provenance, architecture views, guided tours, and incremental summaries.

The current main surfaces and visual direction remain. Ideas adapted from other repositories enhance these pages; they do not replace the designed information architecture.
