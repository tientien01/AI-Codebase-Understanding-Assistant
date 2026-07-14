# SEC-001 Import Acquisition Security Evidence

Status: Complete for SEC-001 scope
Task: `SEC-001`
Observed: 2026-07-14

## Implemented boundary

- One NFC/case-folded relative-path identity rejects traversal, absolute/drive/control/colon paths, excessive depth and normalized collisions.
- ZIP planning rejects links, special files, duplicate paths, excessive files/bytes/per-file bytes and unsafe compression ratios before extraction; streamed output independently enforces byte ceilings.
- Folder uploads enforce submitted-file count, normalized duplicates, per-file and aggregate bytes and idempotent failed-session cleanup.
- Public Git accepts canonical credential-free HTTPS GitHub owner/repository URLs and safe refs only. Clone execution uses isolated user/config paths, HTTPS-only protocol policy, disabled redirects/prompts/credentials/hooks/submodules/LFS smudging, shallow single-branch/no-tags options and a configured timeout.
- Cloned Git metadata is removed and the resulting tree is checked for links, special files, normalized collisions and file/tree quotas before preview.
- Tests mock Git execution and never access the network or execute imported source.

## Verification

| Gate | Result |
| --- | --- |
| Focused security plus ingestion regression | Passed: 49 tests; 2 existing warnings |
| Backend excluding dataset-owned evaluation tests | Passed: 262 tests; 29 integration-profile tests skipped; 2 existing warnings |
| Mandatory full backend suite | Passed: 294 tests; 29 integration-profile tests skipped; 2 existing warnings |
| Diff whitespace validation | Passed |

The earlier full-suite failure was caused by Windows checkout conversion of the synthetic fixture from Git-index LF to working-tree CRLF. Restoring the tracked fixture files to their canonical LF bytes made every declared content hash validate, including `backend/auth_service.py` at `sha256:e48e8badcfc2059ccdbcb7f1c74efc6d29ae9824725426cca0c0268bb4528e40`. No dataset record, manifest, expected hash, threshold, or test gate was changed or bypassed.

## Remaining boundaries

This report does not prove parser CPU/memory isolation, content secret scanning across every sink, request/rate/provider quotas, authentication/authorization/audit, container or network namespace isolation, accepted capacity classes, dependency/SBOM scanning, deletion drills, or Phase 7/L3 release qualification. Git transfer bytes are contained by shallow/time/post-clone policy here; hard OS/container resource and egress enforcement remains an `OPS-002` gate.
