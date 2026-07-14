# AI Codebase UI Reference

This package is a static HTML/CSS reconstruction of the supplied screenshots.

## Files

- `index.html`: navigation hub
- `pages/overview.html`
- `pages/code-explorer.html`
- `pages/graph-view.html`
- `pages/api-explorer.html`
- `pages/impact-analysis.html`
- `pages/search.html`
- `pages/evidence-viewer.html`
- `pages/evaluation.html`
- `pages/settings.html`
- `css/shared.css`: global shell, sidebar, header, cards, controls
- `css/*.css`: page-specific layout
- `assets/screenshots/`: original screenshots

## Intended use with Codex

Treat screenshots as visual source of truth and HTML as structure/layout reference.
Do not copy the static HTML into one giant React component. Translate it into reusable components that fit the existing frontend architecture.

Recommended shared components:
`AppHeader`, `Sidebar`, `IndexStatusCard`, `Panel`, `Button`, `Badge`, `SearchInput`, `DataTable`, `AssistantPanel`.

The static files use Unicode placeholders for icons. Replace them with the project's existing icon library in production.

## UI-004 concept

`assets/concepts/ui-004-graph-explorer.png` is the approved visual direction for the UI-004 Graph Explorer. It evolves the supplied graph screenshot with an architecture-layer canvas, selected-path focus, projection disclosure, contextual evidence/impact inspection, and an accessible relation-list entry point. The image is a visual target, not a factual API contract; accepted frontend, graph, evidence, and accessibility contracts remain authoritative.
