# UI-006 Background Import UX Report

Status: Completed by owner-authorized documentation closure; UX implementation verified
Date: 2026-07-17

The accepted target is an explicit Prepare Preview action, immediate session acknowledgement, server-owned acquisition stages, truthful elapsed time, retained Import context, safe cancellation, and unchanged background indexing semantics.

## Verification

- Frontend production build/typecheck: passed.
- Frontend lint: passed.
- Frontend Vitest: 55 passed across 10 files, including source-aware preparation, explicit Folder/ZIP confirmation, local generated-folder filtering, bounded folder batching and safe multipart error disclosure.
- Focused backend acquisition/service and API/OpenAPI contract: 68 passed; committed artifact updated for the additive status and batched-folder endpoints.
- Real Chromium Prepare Preview: POST/status polling/preview all returned 200; 63 total, 34 indexable, 29 skipped; no console/page errors.
- Real Chromium Start Indexing: completed 34/34 in 0.7 seconds with 55 symbols, 9 endpoints, 134 chunks and 3,700 graph nodes; test repository deletion returned 200; no console/page errors after the activity-key fix.
- Full backend: 288 passed, 31 skipped, 18 failed only under the pre-existing frozen evaluation fixture CRLF/checksum mismatch.

On 2026-07-17 the project owner confirmed that the unrelated frozen-fixture issue
had been handled and authorized closing UI-006 through a documentation-only update.
AGT-007 verification subsequently confirmed the expected tracked LF hash in a
canonical clone and passed all 373 backend tests there; the main Windows checkout
still converts that file to CRLF and reproduces the same 18 failures. The earlier
counts remain the exact UI-006 run record, and this closure does not misattribute
the line-ending condition to UI-006.

The first blank-page report was caused by `useImportPreviewQuery` and `useImportSessionStatusQuery` receiving each other's `enabled` expression. The TypeScript build caught the undefined variable; the corrected hooks now build and render `/import` in Chromium.

The follow-up UI pass now presents only the implemented standard indexing pipeline, uses a three-step page wizard, groups acquisition into four readable preparation steps, and keeps raw activity under a collapsed technical-details disclosure. Production build/typecheck, lint and automated component tests passed; visual UX acceptance remains with the owner as requested.

Folder and ZIP selection no longer starts network activity automatically. GitHub, ZIP and folder imports share one source-specific preparation component; upload percentage appears only inside the active upload step. Browser folders exclude common generated directories before transfer and use 200-file batches under a manifest-backed import session, avoiding the multipart parser failure caused by tens of thousands of files in one request. FastAPI `detail` errors are preserved for safe, actionable user messages.

ZIP extraction now separates archive-envelope safety from per-file indexing eligibility. Entry count, declared expanded bytes, compression ratio, path/type validation and actual streamed-byte checks remain fail-closed. A correctly declared source file above the indexing limit is recorded as `file_too_large` and skipped, allowing remaining supported files to reach preview.
