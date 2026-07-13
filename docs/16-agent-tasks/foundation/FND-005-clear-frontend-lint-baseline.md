---
id: FND-005
title: Establish a green frontend targeted-test and lint baseline
status: completed
priority: P0
phase: 0
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [DOC-003]
requirements: []
contracts:
  - docs/12-engineering/README.md
decisions:
  - docs/13-decisions/ADR-0002-reproducible-development-toolchain.md
technology_docs:
  - docs/03-technology/stack-overview.md
allowed_paths:
  - frontend/package.json
  - frontend/package-lock.json
  - frontend/vitest.config.ts
  - frontend/src/api/client.ts
  - frontend/src/api/client.test.ts
  - frontend/src/hooks/useImportController.ts
  - frontend/src/hooks/useImportController.test.tsx
  - docs/14-implementation-baseline/verification-report.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/18-production-evidence/frontend-lint-baseline-report.md
  - docs/16-agent-tasks/foundation/FND-005-clear-frontend-lint-baseline.md
  - docs/project-status.md
forbidden_paths:
  - backend/**
  - frontend/src/pages/**
  - frontend/src/components/**
  - tests/fixtures/**
  - storage/**
dependency_changes:
  allowed: true
  add:
    - vitest==4.1.10
    - jsdom==29.1.1
    - "@testing-library/dom==10.4.1"
    - "@testing-library/react==16.3.2"
  remove: []
production_gates:
  - Frontend lint reports zero errors without suppressing additional rules.
  - Targeted frontend tests cover the touched timeout and import-preview behavior.
  - The existing frontend production build remains successful.
  - Import request behavior and visible error messages remain unchanged.
evidence_outputs:
  - docs/18-production-evidence/frontend-lint-baseline-report.md
---

# Task FND-005 — Establish a Green Frontend Targeted-Test and Lint Baseline

## Context

The verified frontend build passes, but lint reports four errors in two files. One timeout wrapper drops the caught error cause. Three import preview effects call upload functions before their declarations, which the React hooks lint rules reject. The repository also lacks the targeted frontend test harness required to verify those source changes. These coupled gaps block `FND-002` from introducing mandatory green CI, so they must become green in one atomic foundation task.

## Objective

Establish a minimal targeted frontend test harness and clear the four verified lint errors with behavior-preserving changes so the reproducible metadata and CI task can require green test, lint, typecheck, and build gates.

## In scope

- Add the exact approved Vitest, Testing Library, and jsdom development dependencies and a standalone Vitest configuration.
- Add targeted tests for timeout error causality and the folder/ZIP/GitHub automatic import-preview effects.
- Preserve the caught `AbortError` as the `cause` of the existing timeout error.
- Reorder the three existing import preview effects below the upload/helper declarations they call while keeping every hook unconditional and in a stable order.
- Update only the named baseline and evidence documents with observed command results.

## Out of scope

- Changing API endpoints, request payloads, import timing, debounce duration, user-visible messages, or page behavior.
- Disabling lint rules, adding suppression comments, or broad controller refactoring.
- Adding MSW, Playwright, coverage tooling, routing, server-state libraries, CI, or unrelated formatting.
- Expanding tests beyond the two touched behaviors or changing product dependencies.

## Existing code to reuse

- The existing error mapping in `frontend/src/api/client.ts`.
- The existing upload functions, preview effects, and state in `frontend/src/hooks/useImportController.ts`.
- The accepted Vitest and Testing Library direction in `docs/03-technology/stack-overview.md`.
- The four-error snapshot in `docs/14-implementation-baseline/verification-report.md`.

## Implementation sequence

1. Reproduce the four-error and missing-test baseline with Node 24 and npm 11.
2. Install the four exact development dependencies and add the `test` script plus jsdom Vitest configuration.
3. Add targeted tests that initially expose the lost timeout cause and protect all three automatic preview paths.
4. Attach the caught abort exception as the cause of the current timeout error.
5. Move the three existing preview effects after the functions they call without changing their bodies, dependency arrays, or ordering relative to one another.
6. Run clean install, targeted test, full test, lint, typecheck/build, and lock-stability gates and record their versions/results.
7. Update the baseline, evidence, task status, and project status only after every gate passes.

## Data/API compatibility and migration

No API, persisted data, request, response, route, or product dependency change is permitted. The timeout message and all import behavior remain compatible. Four test-only development dependencies are added to the npm lock; no runtime migration is required.

## Failure, security, performance, and observability requirements

- Error wrapping retains causal debugging information without exposing it in the user-visible message.
- Effects remain unconditional and preserve the existing folder/ZIP/GitHub preview triggering and GitHub debounce behavior.
- No imported repository content is executed or inspected during this task.
- No new logging, telemetry, network target, or credential handling is introduced.

The four added packages are MIT-licensed, support Node 24, and are already within the accepted frontend-test direction. They are test-only and absent from the production bundle. `vitest@4.1.10` supplies the runner, `jsdom@29.1.1` supplies the browser-like environment, and Testing Library DOM/React `10.4.1`/`16.3.2` supplies user-facing hook/component test utilities compatible with React 19. Rollback removes the packages, script, config, tests, and their lock entries.

## Required tests and commands

Run from `frontend/` on Node `>=24,<25` and npm `>=11,<12`:

```powershell
node --version
npm.cmd --version
npm.cmd install --save-dev --save-exact vitest@4.1.10 jsdom@29.1.1 @testing-library/dom@10.4.1 @testing-library/react@16.3.2
$lockHash = (Get-FileHash package-lock.json -Algorithm SHA256).Hash
npm.cmd ci
if ((Get-FileHash package-lock.json -Algorithm SHA256).Hash -ne $lockHash) { throw 'npm ci mutated package-lock.json.' }
npm.cmd run test -- src/api/client.test.ts src/hooks/useImportController.test.tsx
npm.cmd run test
npm.cmd run lint
npm.cmd run build
```

Run from the repository root:

```powershell
git diff --check -- frontend/src/api/client.ts frontend/src/hooks/useImportController.ts docs
```

Expected results: exact dependency installation updates only the approved manifest/lock entries; clean install does not mutate the lock; targeted and full tests pass; lint reports zero errors; TypeScript and the production build pass; diff whitespace validation passes.

## Acceptance criteria

- `npm.cmd run lint` reports zero errors and no new lint suppression is present.
- The authorized targeted frontend tests for both touched behaviors pass.
- `npm.cmd run build` succeeds under the declared Node/npm range.
- The abort timeout retains the caught error as `cause` and preserves the existing message.
- The three preview effects retain their existing bodies, dependency arrays, relative ordering, and unconditional hook execution.
- `package.json` and `package-lock.json` contain only the approved test dependencies/script and their deterministic transitive lock changes.
- The evidence report records tool versions, commands, results, and the tested revision.

## Rollback

Restore the original two source files and documentation updates; remove the Vitest configuration, targeted tests, `test` script, and the four development dependencies through npm so the lockfile is updated consistently. No data or schema rollback is required.

## Documentation and evidence updates

Update the Phase 0 verification report, frontend test inventory, project status, this task, and `docs/18-production-evidence/frontend-lint-baseline-report.md` with observed results.

## Completion evidence

Verified on 2026-07-13 with Node 24.14.0 and npm 11.9.0: clean `npm ci` preserved the lock hash; 4 targeted tests passed; lint reported zero errors; TypeScript/Vite production build passed with 85 modules; and diff whitespace validation passed. Detailed evidence is recorded in `docs/18-production-evidence/frontend-lint-baseline-report.md`.
