# Import and Graph Refactor Summary

## Backend

- Added streaming upload support so large ZIP/folder uploads are written in chunks instead of being fully loaded into memory.
- Raised import configuration for larger repositories and added separate limits for upload size, extracted size, ZIP entries, path depth, and compression ratio.
- Hardened ZIP handling with duplicate-path detection, nested archive skipping, path-depth checks, entry-count checks, and ZIP bomb protection.
- Added graph coverage metadata:
  - `mapped` for repository-map level areas.
  - `deep_indexed` for files/symbols/endpoints with parsed code evidence.
  - edge `evidence_level` to distinguish map-level and deep relationships.
- Added folder/project-area graph nodes so the graph can show a high-level repository map before users inspect detailed code relationships.
- Added a graph expansion endpoint as a foundation for `Analyze this area`. The MVP refreshes the project graph; this can later enqueue scoped RQ jobs.

## Frontend

- Added upload progress for ZIP/folder import using `XMLHttpRequest`.
- Updated Graph View into a simpler Project Map UI with user-facing statuses:
  - `Ready`
  - `Analyzing`
  - `Needs analysis`
  - `Skipped`
  - `Issue found`
- Added an `Analyze this area` action for graph areas that need deeper analysis.
- Updated graph side panel to show analysis coverage instead of internal graph implementation details.

## Notes

- RQ/Redis is not wired yet. The new graph expansion endpoint and job/status fields are prepared so a real background worker can replace the current synchronous refresh path.
- The UI avoids internal terms such as chunks, vectors, graph node IDs, and scope internals by default.

## Follow-up: HTML and CSS Support

- Added HTML (`.html`, `.htm`) and CSS (`.css`) to the language registry.
- HTML/CSS files are now treated as UI source files instead of unsupported files.
- Import Preview can show HTML and CSS under Detected Languages.
- Added tests so HTML/CSS support does not regress.
