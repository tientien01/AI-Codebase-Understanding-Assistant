# AI, RAG, and Evaluation

`runtime-and-dataset-contracts.md` owns the normalized candidate schema, deterministic ranking/fusion rules, evidence/context selection record, privacy-safe agent trace, evaluation case, and run identity.

RAG and Agentic AI are separate cooperating layers: retrieval gathers candidates; evidence validates support; the bounded agent chooses workflows/tools and may repair retrieval; the LLM communicates; citation validation enforces grounding.

## Evaluation baselines

- Keyword/exact search.
- Naive vector top-k RAG.
- Production hybrid graph-aware/agentic method.

## Mandatory metrics

- Retrieval precision/recall and Recall@k.
- Citation syntactic validity and claim support.
- Answer correctness, completeness, and groundedness.
- Hallucination rate and insufficient-evidence accuracy.
- Graph path validity, provenance coverage, parser/resolver coverage.
- Full/incremental equivalence.
- Tool selection, retrieval rounds, latency, tokens, and cost.

## Quality rules

- Benchmark datasets and expected evidence are versioned.
- Automated tests use deterministic/fake providers; provider evaluations are separate reproducible runs.
- A model, embedding, reranker, vector DB, or agent framework is adopted only when it improves an accepted metric enough to justify latency, cost, security, and operations.
- Regression thresholds block release and are stored in production evidence.

`specifications/detailed-evaluation-plan.md` defines benchmark categories, dataset formats, keyword/naive-RAG/adaptive baselines, formulas, manual scoring, pass criteria, evaluation UI, fixtures, and parser/graph/architecture/incremental/readiness metrics.
