# AGT-006 Stateful Conversation Evidence

Status: Verified local implementation evidence  
Verified: 2026-07-16  
Scope: AGT-006 only; this is not a provider, embedding or release-readiness claim.

## Delivered behavior

- Added authenticated repository-owned conversation list and replay reads bounded to 50 summaries and 200 recent ordered messages.
- Unknown and cross-repository conversation identities return the same safe not-found state; supplied chat IDs must already exist for that repository.
- Replay returns only redacted message content, citation locators, index identity and safe outcome fields. It does not expose traces, prompts, provider payloads, source excerpts or hidden reasoning.
- Follow-ups project at most eight recent messages within a deterministic 1,000-token estimate. The projection is untrusted intent context, never evidence.
- When history belongs to an older index, prior assistant text is excluded from memory and the frontend discloses the stale conversation. Current answers still require current-index evidence and citation validation.
- The frontend retains the server-issued ID, sends it on later turns, deep-links `/repositories/:repositoryId/assistant/:conversationId`, replays after refresh, lists server history and starts a new chat by clearing active identity without deleting history.

## Regression evidence

| Gate | Result |
| --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest tests/assistant tests/persistence tests/test_api_contract.py -q` | 61 passed, 6 skipped |
| Canonical-LF `backend\.venv\Scripts\python.exe -m pytest tests -q` | 354 passed, 31 skipped |
| `backend\.venv\Scripts\python.exe backend/scripts/export_openapi.py --check` | Passed; artifact current |
| `Set-Location frontend; npx.cmd tsc -b` | Passed |
| `Set-Location frontend; npm.cmd run lint` | Passed |
| `Set-Location frontend; npm.cmd test -- --run` | 114 passed across 16 files |
| `Set-Location frontend; npm.cmd run build` | Passed; existing >500 kB chunk warning remains |

The normal Windows checkout still converts the frozen retrieval-evaluation fixture to CRLF, causing the pre-existing content-hash failures. The same complete working diff applied to a canonical-LF archive passed the full backend collection without changing fixtures, manifests or evaluation thresholds.

## Remaining boundaries

Ollama chat/health/fallback is AGT-007. Dense embedding measurement/adoption is RET-004/RET-005. Provider/readiness UX is UI-024. All remain draft and were not implemented by AGT-006.
