# AGT-004 Provider Evidence Context Report

Status: Verified local implementation evidence

Owner: Assistant owner

Task: `../16-agent-tasks/retrieval-agent/AGT-004-grounded-provider-evidence-context.md`

Verified: 2026-07-16

## Delivered behavior

- The optional provider receives immutable evidence blocks containing repository/index binding, evidence ID, safe file/range/symbol/support metadata, exact selected content and token estimate.
- The normal assistant path projects only RET-003 selected whole spans and revalidates their current source hash and exact range before the provider boundary.
- The selected-evidence path re-reads only the requested current source ranges and rejects stale, changed, blocked, invalid, duplicate or over-budget context as an all-or-nothing provider input.
- Source content is serialized inside explicit untrusted-data delimiters. Provider citation IDs remain restricted to supplied evidence and provider failures retain the deterministic grounded response.
- Provider context is internal and is not added to public responses, persisted messages, claims, diagnostics or structured trace events.
- No edit, terminal, dependency, commit or pull-request capability was added.

## Verification

| Gate | Result |
| --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest tests/assistant/test_provider_evidence_context.py -q` | Passed: 7 |
| `backend\.venv\Scripts\python.exe -m pytest tests/assistant tests/evidence tests/retrieval tests/test_codebase_service.py tests/test_service_boundaries.py -q` | Passed: 121 |
| `backend\.venv\Scripts\python.exe -m pytest tests -q` in canonical-LF local checkout | Passed: 342; skipped: 31 declared integration-profile tests |
| `git diff --check -- backend/app/services/chat tests/assistant tests/test_service_boundaries.py docs` | Passed |

The main Windows checkout has system-wide `core.autocrlf=true`; its full-suite evaluation cases fail the pre-existing fixture SHA-256 gate after CRLF conversion. The same revision and AGT-004 files were therefore verified in a disposable local clone checked out with `core.autocrlf=false`; the fixture worktree blob matched the Git blob and all 342 runnable tests passed. No fixture, dataset, manifest, golden value or threshold was changed.

## Remaining limits

- The default provider is still `fake` and deliberately unconfigured.
- This evidence does not establish real-provider answer quality, semantic entailment, latency, cost, load behavior or release thresholds.
- Frontend conversation replay and current page/file/symbol/endpoint context remain separate future tasks.
- Provider context is bounded source evidence for read-only explanation; production v1 still forbids source modification and command execution.
