# AGT-002 Assistant Sufficiency and Citation Report

Status: Verified task evidence; not release qualification
Task: `AGT-002`
Verified: 2026-07-14
Environment: local Windows Python 3.11 profile

## Outcome

The assistant now evaluates selected RET-003 evidence with deterministic requirements by current controlled question type. Direct/code/debug/database questions require strong exact/static support; flow/API/impact require two strong blocks plus graph/endpoint coverage; architecture/onboarding require two distinct strong sources. Heuristic-only support cannot confirm a claim.

Only repairable multi-step/architecture undercoverage may run one controlled hybrid repair. The default `assistant-config/v1` identity is now `agentcfg_6b15697e76ce968055eae2ba`, capped at two rounds and three calls while retaining the six-candidate/evidence, 8000-token and 10000-millisecond limits. Repair candidates remain repository/index/ranking bound, merge by stable entity/source/span keys and pass RET-003 reselection. Direct missing questions do not broaden into generic unrelated repair.

Answers are represented internally as structured claims with controlled support and citation IDs. Validation requires every citation to be selected, present in the response, current, owned, range/scope-identical to persisted evidence and non-duplicated. Optional provider output must parse as a controlled JSON answer plus allowed citation IDs, and ChatService invokes it only after deterministic evidence sufficiency; invalid declarations fall back to the deterministic result.

## Verification

| Command | Result |
| --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest tests/assistant/test_sufficiency_citation_repair.py -q` | 10 passed |
| `backend\.venv\Scripts\python.exe -m pytest tests/assistant tests/evidence tests/retrieval tests/test_codebase_service.py tests/test_service_boundaries.py -q` | 102 passed; 1 existing duplicate-ZIP warning and 1 dependency deprecation warning |
| `backend\.venv\Scripts\python.exe -m pytest tests -q` | 222 passed, 29 skipped; 1 existing duplicate-ZIP warning and 1 dependency deprecation warning |
| `git diff --check` | Recorded after documentation closure |

## Limitations

- Claim validation is structural/static scope validation; semantic entailment quality still requires EVA datasets and thresholds.
- Repair uses controlled query expansion and no dynamic/LLM planner; only one repair round is permitted.
- Existing controlled question types remain unchanged.
- Provider integration is optional/unverified in the local profile; malformed, undeclared or foreign citations fail closed.
- Persistent trace/conversation events, retention/redaction and replay belong to AGT-003.
- This report is task evidence, not Phase 5 exit or release qualification.
