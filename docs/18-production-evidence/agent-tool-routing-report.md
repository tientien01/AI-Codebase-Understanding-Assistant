# AGT-001 Agent Tool Routing Report

Status: Verified task evidence; not release qualification
Task: `AGT-001`
Verified: 2026-07-13
Environment: local Windows Python 3.11 profile

## Outcome

The compatibility assistant now runs through immutable `assistant-config/v1` and versioned request, plan, tool-input, tool-output, observation, budget and diagnostic contracts. The default configuration identity is `agentcfg_e235e1526f869eff8288324a`; it caps one round, two tool calls, six candidates/evidence blocks, 8000 context tokens, 10000 elapsed milliseconds and zero provider calls/cost.

The immutable registry identity is `toolreg_72fd01c97265295cb1685017` and allowlists only `exact_lookup/v1` and `hybrid_retrieval/v1`. It rejects unknown/duplicate/incompatible tools and repository/index ownership mismatches. Eligible direct questions stop after exact support, exact misses fall back to hybrid once, and current multi-step question types route directly to hybrid. Tool choices are static controlled values and cannot be supplied by imported repository or prompt-like query text.

Every call records controlled identities, candidate IDs/count coverage, truncation, safe diagnostics, duration and retryability without source blocks, absolute paths, prompts, credentials or provider payloads. Equivalent calls are deduplicated; cancellation and tool-call/time limits stop at boundaries. Only ranked output that passes RET-003 context selection is persisted as evidence/citations.

## Verification

| Command | Result |
| --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest tests/assistant/test_bounded_workflow_tools.py -q` | 12 passed |
| `backend\.venv\Scripts\python.exe -m pytest tests/assistant tests/evidence tests/retrieval tests/test_codebase_service.py tests/test_service_boundaries.py -q` | 92 passed; 1 existing duplicate-ZIP warning and 1 dependency deprecation warning |
| `backend\.venv\Scripts\python.exe -m pytest tests -q` | 212 passed, 29 skipped; 1 existing duplicate-ZIP warning and 1 dependency deprecation warning |
| `git diff --check` | Recorded after documentation closure |

The regression covers canonical configuration identity/validation, JSON-serializable contracts, registry order invariance, duplicate/unknown/version/ownership rejection, exact avoidance, one-time fallback, multi-step routing, tool-call and elapsed-time limits, cancellation, equivalent-call deduplication, safe failures and prompt-like input isolation.

## Limitations

- AGT-001 executes one deterministic retrieval round. Sufficiency-driven query/graph repair belongs to AGT-002.
- Existing question-type classification remains the RET-001 controlled compatibility set; expanding it requires an authorized retrieval contract task.
- Provider generation remains outside the tool loop; provider budgets are declared as zero and ChatService retains its existing optional provider boundary.
- Claim extraction, citation-to-claim support validation and bounded claim repair belong to AGT-002.
- Structured persistent traces, retention/redaction and replay read models belong to AGT-003.
- Evaluation datasets, quality/latency/cost thresholds and Phase 5 release qualification remain incomplete.
