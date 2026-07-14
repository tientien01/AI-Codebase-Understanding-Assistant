# SEC-001 Import Acquisition Security Evidence

Status: Implementation evidence incomplete; mandatory full-suite prerequisite failed
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
| Mandatory full backend suite | Incomplete: 276 passed, 29 skipped, 18 evaluation failures |
| Diff whitespace validation | Passed |

The full-suite failures all originate in the evaluation fixture integrity check before method execution: the checked-out `tests/fixtures/retrieval_benchmark_repo/backend/auth_service.py` bytes do not match the declared content hash. The file remains Git-clean, and this SEC-001 change does not allow reading or modifying the dataset. The fixture/hash prerequisite must be restored by its owner and the exact full command rerun; no threshold or test was weakened.

## Remaining boundaries

This report does not prove parser CPU/memory isolation, content secret scanning across every sink, request/rate/provider quotas, authentication/authorization/audit, container or network namespace isolation, accepted capacity classes, dependency/SBOM scanning, deletion drills, or Phase 7/L3 release qualification. Git transfer bytes are contained by shallow/time/post-clone policy here; hard OS/container resource and egress enforcement remains an `OPS-002` gate.
