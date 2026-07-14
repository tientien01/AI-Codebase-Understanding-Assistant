# BUG-001 Robust GitHub Import Report

Status: Focused verification passed; full-suite evaluation prerequisite unresolved
Date: 2026-07-14

## Defect

On Windows, Git pack index files can be read-only. Public GitHub import cloned the repository successfully but returned HTTP 500 when direct `shutil.rmtree` could not remove `.git`.

## Change

The ingestion boundary retries a permission-denied removal only after making the denied path writable. The existing path-containment and invalid-symlink checks remain authoritative. The Git acquisition test now creates a read-only pack index before verifying metadata removal.

Post-clone validation continues to reject unsafe paths, links, special files, excessive file counts and excessive aggregate bytes. It no longer rejects the entire repository solely because one file exceeds the indexing content limit; the existing scanner skips that file and exposes the reason and coverage in preview.

## Production incident reproduction

Metadata-only inspection of `Hoang-Sang/recommend_hotel` found 63 files totaling 122.37 MiB. Nine assets exceed 1 MiB: four CSV datasets, one SQLite database and four images. The repository is far below the aggregate acquisition limit; the former per-file fail-fast behavior caused the HTTP 413.

## Verification

- Focused acquisition/service suite: `49 passed`.
- Backend suite excluding the unrelated evaluation fixture: `270 passed, 31 skipped`.
- Mandatory full backend suite: `284 passed, 31 skipped, 18 failed`. Every failure is under `tests/evaluation/` and starts from the pre-existing checkout checksum mismatch for `tests/fixtures/retrieval_benchmark_repo/backend/auth_service.py` (`index 2980a498...`, worktree `40b22c9b...`). The hotfix does not modify or refresh the frozen evaluation fixture.
- `git diff --check`: passed.

The focused regression creates a read-only `.git/objects/pack/pack-test.idx` and verifies that import preview succeeds with all Git metadata removed. It also proves an oversized file is disclosed as skipped while a supported file remains indexable, and that aggregate overflow still fails closed with staging cleanup.

After the partial-import change, the focused acquisition/service suite remains `49 passed`, the backend suite excluding the unrelated frozen evaluation fixture remains `270 passed, 31 skipped`, and `git diff --check` passes.
