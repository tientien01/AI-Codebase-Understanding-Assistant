# Evaluation Plan

## Document Purpose

This document defines how AI Codebase Assistant will be evaluated. It focuses on measuring retrieval quality, citation quality, grounded answer generation, hallucination behavior, and the benefit of the adaptive agentic retrieval workflow compared with simpler baselines.

This file is separate from `17_testing_plan.md`. Testing verifies whether the system works correctly. Evaluation measures whether the AI/retrieval approach is better than simpler alternatives.

## Evaluation Goal

Evaluation must prove that the system:

- retrieves more relevant evidence than keyword search and naive vector RAG;
- produces more grounded answers;
- cites real files, symbols, and line ranges correctly;
- refuses or marks answers as insufficient when evidence is weak;
- reduces hallucination compared with direct top-k RAG;
- provides useful agent traces for multi-step codebase questions.

## Methods to Compare

### Method 1: Keyword Search Baseline

Behavior:

- Search chunks/files by literal terms.
- No embeddings.
- No graph traversal.
- Optional LLM answer generation from keyword results.

Purpose:

- Represents simple grep-like or text-match search.

### Method 2: Naive RAG Baseline

Behavior:

- Chunk repository.
- Embed query.
- Retrieve vector top-k chunks.
- Generate answer directly from retrieved chunks.
- No explicit metadata lookup, graph traversal, evidence sufficiency check, or citation validation.

Purpose:

- Represents the common beginner RAG approach.

### Method 3: Adaptive Agentic Retrieval

Behavior:

- Classify question type.
- Extract entities.
- Plan retrieval.
- Retrieve from vector store, metadata, graph, docs, config, files, endpoints, symbols, and tests depending on question type.
- Evaluate evidence.
- Rewrite/retrieve again when evidence is weak.
- Generate answer only with selected evidence.
- Validate citations.
- Return insufficient-evidence response when evidence is not enough.

Purpose:

- Represents the proposed method of this project.

## Benchmark Categories

Each serious benchmark should include at least 10 questions per category. A small local smoke benchmark may use 2-3 questions per category.

Categories:

- Architecture overview.
- API flow.
- Database/model usage.
- Debugging and error tracing.
- Onboarding and suggested reading path.
- Impact analysis.
- Configuration and environment.
- Testing and related tests.
- Insufficient evidence / nonexistent target.

## Benchmark Dataset Format

### `benchmark/questions.json`

```json
[
  {
    "id": "q001",
    "category": "api_flow",
    "question": "How does the login flow work?",
    "repository_fixture": "fastapi_react_sample",
    "tags": ["auth", "frontend", "backend"]
  }
]
```

### `benchmark/ground_truth.json`

```json
[
  {
    "question_id": "q001",
    "expected_answer_summary": "Frontend login form calls backend login endpoint, backend authenticates credentials and returns a token.",
    "expected_files": [
      "frontend/src/pages/LoginPage.tsx",
      "frontend/src/services/authApi.ts",
      "backend/app/api/auth/routes.py",
      "backend/app/services/auth_service.py",
      "backend/app/core/security.py"
    ],
    "expected_symbols": ["LoginPage", "login", "authenticate_user", "create_access_token"],
    "expected_relations": ["calls_api", "exposes_endpoint", "calls"],
    "acceptable_alternative_files": [],
    "notes": "Exact service file names may vary by fixture version."
  }
]
```

## Metrics

### Retrieval Precision

Relevant retrieved evidence divided by total retrieved evidence.

```text
relevant_retrieved / total_retrieved
```

### Retrieval Recall

Expected evidence found divided by total expected evidence.

```text
expected_found / expected_total
```

### Citation Accuracy

Valid citations divided by total citations.

```text
valid_citations / total_citations
```

A citation is valid only when:

- the cited file exists in the current or referenced index version;
- the line range is valid;
- the citation overlaps expected evidence or clearly supports the claim;
- the citation is not stale, or is explicitly marked as stale.

### Answer Correctness

Manual score:

- `0`: incorrect or no useful answer.
- `1`: partially correct.
- `2`: correct but incomplete.
- `3`: correct and complete.

### Groundedness

Manual or semi-automatic score:

- `0`: many unsupported claims.
- `1`: some unsupported claims.
- `2`: all key technical claims are supported by citations.

### Hallucination Rate

Percentage of answers containing unsupported invented claims.

```text
answers_with_hallucination / total_answers
```

Hallucination includes invented files, functions, endpoints, config keys, database tables, tests, or graph relations.

### Completeness

Manual score:

- `0`: misses key components.
- `1`: covers one major component.
- `2`: covers most components.
- `3`: covers all expected components.

### Insufficient-Evidence Accuracy

Measures whether the system correctly refuses or marks answers insufficient when the target does not exist or evidence is weak.

```text
correct_insufficient_responses / insufficient_evidence_questions
```

### Agent Trace Quality

Measures whether the adaptive agent selected appropriate tools for the question type.

Example checks:

- API flow questions used endpoint lookup and graph traversal.
- Impact questions used symbol lookup, graph traversal, and related test lookup.
- Debugging questions used error keyword search, config retrieval, and related code retrieval.

### Latency

Measure:

- mean latency;
- median latency;
- p95 latency;
- retrieval rounds per answer;
- tool calls per answer.

## Pass Criteria

The complete product should meet:

- Adaptive method has higher citation accuracy than naive RAG.
- Adaptive method has lower hallucination rate than naive RAG.
- Adaptive method retrieves graph or metadata evidence for flow and impact questions.
- Adaptive method correctly returns insufficient evidence for nonexistent targets.
- Citation viewer can open all non-stale citations from evaluation answers.
- Agent trace shows appropriate tool usage for multi-step questions.
- Evaluation run results can be exported as JSON.

## Evaluation Page Requirements

The Evaluation page must show:

- dataset name;
- run method;
- run status;
- aggregate metrics;
- question-level result table;
- expected files/symbols/relations;
- retrieved evidence;
- generated answer;
- citations and citation validity;
- agent trace summary when available;
- manual score controls;
- export JSON action.

## Test Fixtures

Minimum fixture repository:

- FastAPI backend.
- React frontend.
- Login flow.
- Auth service.
- Security/token helper.
- SQLAlchemy model or Pydantic schema.
- README.
- `.env.example`.
- Dockerfile or docker-compose.
- At least one test file.

Do not include:

- `.env`;
- real credentials;
- dependency folders;
- build outputs.

## Notes for AI Coding Agents

- Evaluation logic must be deterministic where possible.
- Use fake LLM and fake embedding providers for automated evaluation tests.
- Store evaluation runs and results in the evaluation tables defined by the data model.
- Do not block normal product usage if evaluation is not configured.

## Production Indexing Evaluation

Evaluation must measure indexing quality, not only answer quality.

### Parser Coverage Metrics

Measure:

- file coverage;
- symbol precision;
- symbol recall;
- endpoint precision;
- endpoint recall;
- import extraction accuracy;
- import resolution accuracy;
- call-edge precision;
- test linkage accuracy.

Example:

```text
parsed_indexable_files / total_indexable_files
resolved_imports / total_imports
correct_endpoint_records / expected_endpoint_records
```

### Graph Quality Metrics

Measure:

- dangling edge rate;
- orphan node rate;
- duplicate node rate;
- resolved-reference rate;
- edge provenance coverage;
- graph path validity;
- graph validation critical issue count.

Pass expectation:

- no critical validation issue in active index;
- every graph edge has provenance;
- dangling edge rate is zero after normalization.

### Architecture And Guided Tour Metrics

For fixtures with ground truth, measure:

- layer assignment accuracy;
- entrypoint detection accuracy;
- module grouping quality;
- guided tour step validity;
- guided tour usefulness by manual review.

Tour validity is automatic:

- every target node/file exists;
- every step has evidence or explicit signal;
- no step references deleted files after re-index.

### Incremental Correctness Metrics

Compare full rebuild with incremental rebuild:

```text
full_rebuild(index N)
vs
incremental_rebuild(index N)
```

Expected equivalence:

- same canonical graph for unchanged areas;
- same active endpoints;
- same chunks for unchanged files;
- same retrieval answers for unchanged benchmark questions;
- changed files and affected dependents are updated.

### Capability Readiness Metrics

Measure:

- percentage of repositories with code explorer ready;
- percentage with graph ready;
- percentage with semantic search ready;
- number of limited/failed capabilities per index;
- mean time from build start to active index.

These metrics help avoid hiding partial failures behind one generic indexed status.
