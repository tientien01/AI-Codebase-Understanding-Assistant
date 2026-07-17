# RET-004 Ollama Dense Embedding Benchmark Report

Status: Completed locally; RET-005 prototype adoption accepted
Date: 2026-07-17

## Frozen identity and method

- Dataset: `retrieval-v1`, revision
  `sha256:734b850ed37fcc2a7fa5aaf6f6903c2c1cbc3a5b85db68ecfa1cc024546ecc49`.
- Provider: loopback-only local Ollama.
- Model: `embeddinggemma:latest`, digest
  `85462619ee721b466c5927d109d4cb765861907d5417b9109caebc4e614679f1`.
- Dimension: 768; exact UTF-8 case questions and candidate `chunk_content`,
  `truncate=false`, cosine similarity.
- Methods: EVA-001 exact/keyword sparse, naive dense cosine top-k, and weighted
  reciprocal-rank fusion with sparse weight 2, dense weight 1 and `rrf_k=60`.
- Repetitions: three sequential runs, concurrency one, local provider cost zero.

Every method receives the same sorted per-case candidate IDs. The checked-in raw
result retains all per-case rankings, metrics, durations, configuration IDs,
capacity identity, checks and checksums.

## Results

| Metric at k=3 | Sparse | Ollama dense | Sparse+dense hybrid |
| --- | ---: | ---: | ---: |
| Recall | 0.6667 | 1.0000 | 1.0000 |
| Reciprocal rank | 0.8000 | 0.9000 | 0.9000 |
| nDCG | 0.6939 | 0.9262 | 0.9262 |
| Precision | 0.3333 | 0.6667 | 0.5333 |
| Insufficient-evidence accuracy | 0.5000 | 0.5000 | 0.5000 |

- Corpus embedding times: 1,142.95 ms, 1,372.30 ms and 1,231.40 ms.
- Overall query latency p95: 334.48 ms.
- Observed Ollama model memory: 680,379,023 bytes.
- Raw-results checksum:
  `sha256:876078fe4f3575f96a590e4e6e129d68336eb1c6230aa70e1bba90ae7759bfe1`.
- Report checksum:
  `sha256:2bec4e6394c2b14a9bb383b934168262d5078c955acfb6d10574f7daa90d303a`.

The first generated observation exposed that duplicate relevant spans could inflate
entity-level nDCG above 1.0. RET-004 corrected the evaluator to count the first rank
per relevant entity, added a regression, discarded the invalid observation and
reran the complete benchmark and full gate. Final nDCG values are bounded.

## Adoption decision

All reviewed checks pass: hybrid recall, reciprocal rank and insufficient-evidence
accuracy do not regress; quality gain exceeds 0.01; query p95 is below 2,000 ms;
corpus embedding is below 30,000 ms; and observed model memory is below 2 GiB.
Decision: `adopt_for_ret_005`.

This authorizes a separately promoted RET-005 prototype with versioned model,
dimension and preprocessing compatibility plus sparse fallback. It does not claim
production-scale load, answer/citation quality, universal repository quality or
release readiness.

## Verification

- Focused fake-provider RET-004 gate: 10 passed.
- Metric correction plus focused RET-004 gate: 15 passed.
- Evaluation/retrieval combined gate: 76 passed.
- Canonical-LF full backend gate after the final real benchmark: 384 passed,
  31 declared integration-profile skips and three existing warnings.
