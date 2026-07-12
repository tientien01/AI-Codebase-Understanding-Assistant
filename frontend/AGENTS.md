# Frontend Agent Rules

- Read the selected `ready` or `in_progress` task, linked page/API/capability contracts, and current frontend baseline before editing. Root `AGENTS.md` rules continue to apply.
- Preserve the approved main pages and visual language unless the task changes a page contract.
- React Router owns navigation; TanStack Query owns server state; local/feature state owns interactions.
- Do not duplicate API data in a global store or invent response fields absent from the API contract.
- Every asynchronous surface declares applicable `initial`, `loading`, `refreshing`, `success`, `empty`, `limited`, `stale`, `unavailable`, `permission_denied`, `error_retryable`, `error_terminal`, and `cancelled` states.
- Keep repository, opaque index-version, entity, evidence, capability, coverage, and truncation context explicit across routes and cross-page links.
- Graph views consume bounded server projections and display coverage/truncation/provenance.
- Never silently slice graph nodes/edges client-side. Expansion issues a new bounded server request; provide an accessible grouped-list fallback when canvas/layout is limited.
- Large lists and file trees use stable cursor pagination and virtualization when the accepted performance budget requires it. Code uses bounded line/byte range loading rather than fetching an unbounded file.
- Search and navigation cancel superseded requests. Status polling honors server retry hints, uses backoff, stops at terminal states, and does not invalidate unrelated repository/version data.
- Keep citations and source paths deep-linkable and keyboard accessible.
- Escape/sanitize imported source, Markdown, graph labels, and AI output; never render raw secrets, unsafe HTML, host paths, or unrestricted provider payloads.
- Do not show generic confidence/health scores or internal chunk/vector/node counts unless a defined method and actionable diagnostic consumer exist.
- Dependency additions require explicit permission in the selected `ready` or `in_progress` task, plus lockfile update, tests, and bundle/performance review.
- Run typecheck, lint, targeted tests, and production build for frontend behavior changes.
