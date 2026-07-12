# Success Metrics and Release Threshold Ownership

Status: Accepted metric catalog; numeric thresholds pending benchmark tasks  
Authority: Product outcome measurement  
Owner: Product and evaluation owners  
Dependencies: `10-ai-rag-and-evaluation/`, `18-production-evidence/`  
Last verified: 2026-07-12

This catalog defines what must be measured. Numeric thresholds are versioned with benchmark datasets and accepted in release evidence; they must not be invented before representative runs.

| Area | Metric | Definition | Gate owner |
| --- | --- | --- | --- |
| Import | safe import completion | accepted supported imports completed without boundary violation | Security/import suite |
| Indexing | recovery success | interrupted eligible jobs reach a valid terminal state after recovery | Resilience suite |
| Indexing | active-version preservation | failed build never changes the active version | Index integration suite |
| Incremental | full/incremental equivalence | canonical artifacts match within declared equivalence rules | Intelligence benchmark |
| Parsing | entity coverage | expected fixture entities emitted by language/capability | Parser golden suite |
| Resolution | relation precision/coverage | expected references resolved without invalid edges | Resolver benchmark |
| Retrieval | Recall@k and precision@k | expected evidence/entities present among ranked results | Retrieval benchmark |
| Evidence | citation validity | citation resolves to allowed source and version | Evidence suite |
| Evidence | claim support | technical claims supported by cited spans/relations | Evaluation report |
| Assistant | insufficient-evidence accuracy | unsupported questions are limited or refused correctly | Negative benchmark |
| Assistant | hallucination rate | unsupported factual claims per evaluated answer | Evaluation report |
| Performance | indexing duration/peak memory | measured by repository capacity class | Load report |
| Performance | query p50/p95 | end-to-end latency by deterministic and AI capability | Load report |
| Cost | tokens/provider cost | per question and benchmark run by configuration | Evaluation trace |
| UX | task completion | onboarding, trace, and impact E2E flows complete without hidden steps | Playwright/manual UX evidence |
| Operations | restore consistency | database and required artifacts restore to a valid active version | Restore drill |

## Metric contract

Every release-blocking metric must record dataset/fixture version, index version, ranking/workflow configuration, provider/model when applicable, environment class, formula, threshold, raw results, aggregate result, and report checksum or immutable CI link.

## Baseline rule

Keyword/exact search and naive vector top-k are retained as comparison baselines. A semantic store, reranker, graph algorithm, or agent framework is adopted only when the measured gain justifies its latency, cost, security, and operational impact.
