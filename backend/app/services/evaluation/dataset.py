from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from math import isfinite
from pathlib import Path, PurePosixPath
from typing import Any

from app.services.index_models import ChunkRecord
from app.services.retrieval.contracts import RetrievalCandidate, RetrieverName, SupportType


DATASET_SCHEMA = "evaluation-dataset/v1"
CASE_SCHEMA = "evaluation-case/v1"
CASE_CATEGORIES = frozenset({"exact", "lexical", "semantic", "graph_path", "negative", "ambiguous"})
MAX_DATASET_JSON_BYTES = 5_000_000
MAX_FIXTURE_FILES = 100
MAX_FIXTURE_FILE_BYTES = 1_000_000
MAX_CASES = 1_000
MAX_CANDIDATES_PER_CASE = 500


def canonical_json(value: Any) -> str:
    """Serialize contract data in the one form used for content identities."""

    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def content_digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()}"


def file_digest(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _non_empty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _controlled_path(value: Any, field: str) -> str:
    path = PurePosixPath(_non_empty(value, field))
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError(f"{field} must be a normalized fixture-relative path")
    return path.as_posix()


def _string_tuple(value: Any, field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{field} must be a list of non-empty strings")
    if not allow_empty and not value:
        raise ValueError(f"{field} must not be empty")
    return tuple(value)


@dataclass(frozen=True)
class FixtureFile:
    path: str
    sha256: str


@dataclass(frozen=True)
class EvidenceSpan:
    source_path: str
    content_hash: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class ExpectedResult:
    entity_keys: tuple[str, ...]
    evidence_spans: tuple[EvidenceSpan, ...]
    relation_paths: tuple[tuple[str, ...], ...]
    answer_facts: tuple[str, ...]
    allowed_alternatives: tuple[tuple[str, ...], ...]

    @property
    def relevant_entity_keys(self) -> frozenset[str]:
        alternatives = {item for group in self.allowed_alternatives for item in group}
        return frozenset(self.entity_keys) | frozenset(alternatives)


@dataclass(frozen=True)
class EvaluationPolicy:
    should_answer: bool
    required_source_types: tuple[str, ...]
    forbidden_claims: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationBudgets:
    max_results: int
    max_latency_ms: int | None
    max_input_tokens: int | None


@dataclass(frozen=True)
class CandidateObservation:
    candidate_id: str
    retriever: RetrieverName
    retriever_version: str
    entity_key: str
    source_key: str
    raw_score: float
    rank: int
    matched_terms: tuple[str, ...]
    reason_codes: tuple[str, ...]
    support_type: SupportType
    provenance_refs: tuple[str, ...]
    source_path: str
    content_hash: str
    start_line: int
    end_line: int
    chunk_type: str
    chunk_content: str
    title: str
    result_type: str

    def to_candidate(self, repository_id: str, index_version_id: str) -> RetrievalCandidate:
        chunk = ChunkRecord(
            id=f"chunk_{self.candidate_id.removeprefix('cand_')}",
            file_path=self.source_path,
            chunk_type=self.chunk_type,
            content=self.chunk_content,
            start_line=self.start_line,
            end_line=self.end_line,
            symbol_name=self.title,
            content_hash=self.content_hash.removeprefix("sha256:"),
        )
        return RetrievalCandidate(
            candidate_id=self.candidate_id,
            repository_id=repository_id,
            index_version_id=index_version_id,
            retriever=self.retriever,
            retriever_version=self.retriever_version,
            entity_key=self.entity_key,
            source_key=self.source_key,
            raw_score=self.raw_score,
            rank=self.rank,
            matched_terms=self.matched_terms,
            reason_codes=self.reason_codes,
            support_type=self.support_type,
            provenance_refs=self.provenance_refs,
            chunk=chunk,
            result_type=self.result_type,
            title=self.title,
            compatibility_source=self.retriever.value,
        )


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    schema_version: str
    fixture_id: str
    fixture_revision: str
    category: str
    question: str
    expected: ExpectedResult
    policy: EvaluationPolicy
    budgets: EvaluationBudgets
    capability_preconditions: tuple[str, ...]
    tags: tuple[str, ...]
    candidates: tuple[CandidateObservation, ...]


@dataclass(frozen=True)
class EvaluationDataset:
    dataset_id: str
    schema_version: str
    dataset_revision: str
    fixture_id: str
    fixture_revision: str
    repository_id: str
    files: tuple[FixtureFile, ...]
    cases: tuple[EvaluationCase, ...]
    k_values: tuple[int, ...]
    method_names: tuple[str, ...]


def _load_json(path: Path) -> Any:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ValueError(f"invalid evaluation JSON: {path}") from exc
    if size > MAX_DATASET_JSON_BYTES:
        raise ValueError(f"evaluation JSON exceeds {MAX_DATASET_JSON_BYTES} bytes: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid evaluation JSON: {path}") from exc


def _parse_span(raw: Any) -> EvidenceSpan:
    if not isinstance(raw, dict):
        raise ValueError("evidence span must be an object")
    start_line = raw.get("start_line")
    end_line = raw.get("end_line")
    if not isinstance(start_line, int) or not isinstance(end_line, int) or start_line <= 0 or end_line < start_line:
        raise ValueError("evidence span line range is invalid")
    return EvidenceSpan(
        source_path=_controlled_path(raw.get("source_path"), "evidence source_path"),
        content_hash=_non_empty(raw.get("content_hash"), "evidence content_hash"),
        start_line=start_line,
        end_line=end_line,
    )


def _parse_expected(raw: Any) -> ExpectedResult:
    if not isinstance(raw, dict):
        raise ValueError("case expected must be an object")
    relation_paths = raw.get("relation_paths")
    alternatives = raw.get("allowed_alternatives")
    if not isinstance(relation_paths, list) or any(not isinstance(item, list) for item in relation_paths):
        raise ValueError("expected relation_paths must be a list of paths")
    if not isinstance(alternatives, list) or any(not isinstance(item, list) for item in alternatives):
        raise ValueError("expected allowed_alternatives must be a list of groups")
    return ExpectedResult(
        entity_keys=_string_tuple(raw.get("entity_keys"), "expected entity_keys"),
        evidence_spans=tuple(_parse_span(item) for item in raw.get("evidence_spans", [])),
        relation_paths=tuple(_string_tuple(item, "relation path", allow_empty=False) for item in relation_paths),
        answer_facts=_string_tuple(raw.get("answer_facts"), "expected answer_facts"),
        allowed_alternatives=tuple(
            _string_tuple(item, "allowed alternative", allow_empty=False) for item in alternatives
        ),
    )


def _parse_candidate(raw: Any) -> CandidateObservation:
    if not isinstance(raw, dict):
        raise ValueError("candidate observation must be an object")
    try:
        retriever = RetrieverName(raw.get("retriever"))
        support_type = SupportType(raw.get("support_type"))
    except ValueError as exc:
        raise ValueError("candidate retriever and support_type must be controlled") from exc
    raw_score = raw.get("raw_score")
    rank = raw.get("rank")
    start_line = raw.get("start_line")
    end_line = raw.get("end_line")
    if not isinstance(raw_score, (int, float)) or isinstance(raw_score, bool) or not isfinite(raw_score) or raw_score <= 0:
        raise ValueError("candidate raw_score must be finite and positive")
    if not isinstance(rank, int) or rank <= 0:
        raise ValueError("candidate rank must be positive")
    if not isinstance(start_line, int) or not isinstance(end_line, int) or start_line <= 0 or end_line < start_line:
        raise ValueError("candidate line range is invalid")
    candidate_id = _non_empty(raw.get("candidate_id"), "candidate_id")
    if not candidate_id.startswith("cand_"):
        raise ValueError("candidate_id must use the cand_ prefix")
    return CandidateObservation(
        candidate_id=candidate_id,
        retriever=retriever,
        retriever_version=_non_empty(raw.get("retriever_version"), "retriever_version"),
        entity_key=_non_empty(raw.get("entity_key"), "candidate entity_key"),
        source_key=_non_empty(raw.get("source_key"), "candidate source_key"),
        raw_score=float(raw_score),
        rank=rank,
        matched_terms=_string_tuple(raw.get("matched_terms"), "candidate matched_terms"),
        reason_codes=_string_tuple(raw.get("reason_codes"), "candidate reason_codes", allow_empty=False),
        support_type=support_type,
        provenance_refs=_string_tuple(raw.get("provenance_refs"), "candidate provenance_refs"),
        source_path=_controlled_path(raw.get("source_path"), "candidate source_path"),
        content_hash=_non_empty(raw.get("content_hash"), "candidate content_hash"),
        start_line=start_line,
        end_line=end_line,
        chunk_type=_non_empty(raw.get("chunk_type"), "candidate chunk_type"),
        chunk_content=_non_empty(raw.get("chunk_content"), "candidate chunk_content"),
        title=_non_empty(raw.get("title"), "candidate title"),
        result_type=_non_empty(raw.get("result_type"), "candidate result_type"),
    )


def _parse_case(raw: Any) -> EvaluationCase:
    if not isinstance(raw, dict):
        raise ValueError("evaluation case must be an object")
    if raw.get("schema_version") != CASE_SCHEMA:
        raise ValueError("unsupported evaluation case schema")
    policy = raw.get("policy")
    budgets = raw.get("budgets")
    if not isinstance(policy, dict) or not isinstance(policy.get("should_answer"), bool):
        raise ValueError("case policy and should_answer are required")
    if not isinstance(budgets, dict) or not isinstance(budgets.get("max_results"), int) or budgets["max_results"] <= 0:
        raise ValueError("case budgets.max_results must be positive")
    for optional_budget in ("max_latency_ms", "max_input_tokens"):
        value = budgets.get(optional_budget)
        if value is not None and (not isinstance(value, int) or value <= 0):
            raise ValueError(f"case budgets.{optional_budget} must be null or positive")
    raw_candidates = raw.get("candidates", [])
    if not isinstance(raw_candidates, list) or len(raw_candidates) > MAX_CANDIDATES_PER_CASE:
        raise ValueError(f"case candidates must be a list bounded to {MAX_CANDIDATES_PER_CASE} items")
    candidates = tuple(_parse_candidate(item) for item in raw_candidates)
    candidate_ids = [item.candidate_id for item in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("case contains duplicate candidate IDs")
    retriever_ranks = [(item.retriever, item.rank) for item in candidates]
    if len(retriever_ranks) != len(set(retriever_ranks)):
        raise ValueError("case contains duplicate ranks for one retriever")
    for retriever in {item.retriever for item in candidates}:
        ranks = sorted(item.rank for item in candidates if item.retriever is retriever)
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("candidate ranks must be contiguous per retriever")
    category = _non_empty(raw.get("category"), "case category")
    if category not in CASE_CATEGORIES:
        raise ValueError("case category is not controlled")
    expected = _parse_expected(raw.get("expected"))
    if policy["should_answer"] and (not expected.relevant_entity_keys or not expected.evidence_spans):
        raise ValueError("answerable cases require canonical entities and evidence spans")
    return EvaluationCase(
        id=_non_empty(raw.get("id"), "case id"),
        schema_version=CASE_SCHEMA,
        fixture_id=_non_empty(raw.get("fixture_id"), "case fixture_id"),
        fixture_revision=_non_empty(raw.get("fixture_revision"), "case fixture_revision"),
        category=category,
        question=_non_empty(raw.get("question"), "case question"),
        expected=expected,
        policy=EvaluationPolicy(
            should_answer=policy["should_answer"],
            required_source_types=_string_tuple(policy.get("required_source_types"), "required_source_types"),
            forbidden_claims=_string_tuple(policy.get("forbidden_claims"), "forbidden_claims"),
        ),
        budgets=EvaluationBudgets(
            max_results=budgets["max_results"],
            max_latency_ms=budgets.get("max_latency_ms"),
            max_input_tokens=budgets.get("max_input_tokens"),
        ),
        capability_preconditions=_string_tuple(raw.get("capability_preconditions"), "capability_preconditions"),
        tags=_string_tuple(raw.get("tags"), "case tags"),
        candidates=candidates,
    )


def _validate_fixture(dataset: EvaluationDataset, fixture_root: Path) -> None:
    fixture_root = fixture_root.resolve()
    file_hashes = {item.path: item.sha256 for item in dataset.files}
    if len(file_hashes) != len(dataset.files):
        raise ValueError("fixture manifest contains duplicate paths")
    for item in dataset.files:
        target = (fixture_root / item.path).resolve()
        if not target.is_relative_to(fixture_root) or not target.is_file():
            raise ValueError(f"fixture path is missing or escapes the fixture root: {item.path}")
        if target.stat().st_size > MAX_FIXTURE_FILE_BYTES:
            raise ValueError(f"fixture file exceeds {MAX_FIXTURE_FILE_BYTES} bytes: {item.path}")
        if file_digest(target) != item.sha256:
            raise ValueError(f"fixture content hash mismatch: {item.path}")

    expected_revision = content_digest([{"path": item.path, "sha256": item.sha256} for item in dataset.files])
    if dataset.fixture_revision != expected_revision:
        raise ValueError("fixture revision does not match its file manifest")

    for case in dataset.cases:
        if case.fixture_id != dataset.fixture_id or case.fixture_revision != dataset.fixture_revision:
            raise ValueError(f"case {case.id} fixture identity does not match the dataset")
        spans = list(case.expected.evidence_spans) + [
            EvidenceSpan(item.source_path, item.content_hash, item.start_line, item.end_line)
            for item in case.candidates
        ]
        for span in spans:
            if not span.content_hash.startswith("sha256:"):
                raise ValueError(f"case {case.id} source hash must use the sha256 prefix")
            if span.source_path not in file_hashes or file_hashes[span.source_path] != span.content_hash:
                raise ValueError(f"case {case.id} references an undeclared or stale source hash")
            lines = (fixture_root / span.source_path).read_text(encoding="utf-8").splitlines()
            if span.end_line > len(lines):
                raise ValueError(f"case {case.id} source range is outside the fixture")
        for candidate in case.candidates:
            if candidate.source_key != f"file:v1:{candidate.source_path}":
                raise ValueError(f"case {case.id} candidate source key does not match its path")
            lines = (fixture_root / candidate.source_path).read_text(encoding="utf-8").splitlines()
            expected_content = "\n".join(lines[candidate.start_line - 1 : candidate.end_line])
            if candidate.chunk_content != expected_content:
                raise ValueError(f"case {case.id} candidate content does not match its source range")


def load_dataset(dataset_dir: Path, fixture_root: Path) -> EvaluationDataset:
    """Load and fail-closed validate one immutable evaluation dataset."""

    dataset_dir = dataset_dir.resolve()
    manifest_path = dataset_dir / "manifest.json"
    manifest = _load_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != DATASET_SCHEMA:
        raise ValueError("unsupported evaluation dataset schema")
    case_file = _controlled_path(manifest.get("case_file"), "case_file")
    cases_path = (dataset_dir / case_file).resolve()
    if not cases_path.is_relative_to(dataset_dir) or not cases_path.is_file():
        raise ValueError("case_file is missing or escapes the dataset root")
    raw_cases = _load_json(cases_path)
    if not isinstance(raw_cases, list) or len(raw_cases) > MAX_CASES:
        raise ValueError(f"evaluation cases must be a JSON list bounded to {MAX_CASES} items")
    cases = tuple(_parse_case(item) for item in raw_cases)
    if not cases:
        raise ValueError("evaluation dataset must contain cases")
    case_ids = [case.id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("evaluation dataset contains duplicate case IDs")

    raw_files = manifest.get("fixture_files")
    if not isinstance(raw_files, list) or not raw_files or len(raw_files) > MAX_FIXTURE_FILES:
        raise ValueError(f"fixture_files must contain between 1 and {MAX_FIXTURE_FILES} items")
    files = tuple(
        FixtureFile(
            path=_controlled_path(item.get("path"), "fixture file path"),
            sha256=_non_empty(item.get("sha256"), "fixture file sha256"),
        )
        for item in raw_files
        if isinstance(item, dict)
    )
    if len(files) != len(raw_files):
        raise ValueError("fixture file entries must be objects")
    k_values = manifest.get("k_values")
    if not isinstance(k_values, list) or not k_values or any(not isinstance(k, int) or k <= 0 for k in k_values):
        raise ValueError("k_values must contain positive integers")
    if len(k_values) != len(set(k_values)):
        raise ValueError("k_values must be unique")

    revision_payload = {"manifest": manifest, "cases": raw_cases}
    dataset = EvaluationDataset(
        dataset_id=_non_empty(manifest.get("dataset_id"), "dataset_id"),
        schema_version=DATASET_SCHEMA,
        dataset_revision=content_digest(revision_payload),
        fixture_id=_non_empty(manifest.get("fixture_id"), "fixture_id"),
        fixture_revision=_non_empty(manifest.get("fixture_revision"), "fixture_revision"),
        repository_id=_non_empty(manifest.get("repository_id"), "repository_id"),
        files=files,
        cases=cases,
        k_values=tuple(sorted(k_values)),
        method_names=_string_tuple(manifest.get("methods"), "methods", allow_empty=False),
    )
    if dataset.method_names != ("exact_keyword", "naive_semantic", "deterministic_hybrid"):
        raise ValueError("dataset must declare the three EVA-001 comparison methods in canonical order")
    _validate_fixture(dataset, fixture_root)
    return dataset
