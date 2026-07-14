Use the files in this reference package as implementation guidance.

Source priority:
1. Original screenshots in `assets/screenshots/` are the visual source of truth.
2. HTML files in `pages/` define page hierarchy and content grouping.
3. CSS files define approximate sizing, spacing, colors, borders, and responsive behavior.

Before coding:
- Inspect the current frontend framework, router, component library, icon library, and design tokens.
- Reuse existing project conventions and dependencies.
- Do not create a separate standalone application.

Implementation rules:
- Build reusable React components rather than copying each HTML page verbatim.
- Extract shared shell components: top header, project selector, branch selector, status badge, sidebar, index status card, cards, buttons, tables, search fields, and AI assistant.
- Store repeated mock data in typed arrays/objects and render with mapping.
- Replace all Unicode placeholder icons with the existing icon package.
- Preserve the desktop information density shown in the screenshots.
- Keep the center content independently scrollable where appropriate.
- Implement selected navigation states and basic interactions.
- Match the screenshots before adding any new features.
- Run lint, typecheck, tests, and production build after implementation.
- Report changed files and remaining visual differences.
