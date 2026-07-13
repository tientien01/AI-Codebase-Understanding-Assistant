from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from math import isfinite

from app.services.index_models import ChunkRecord, RepositoryState


class QuestionType(str, Enum):
    ARCHITECTURE_OVERVIEW = "architecture_overview"
    FLOW_TRACING = "flow_tracing"
    API_QUESTION = "api_question"
    DATABASE_QUESTION = "database_question"
    DEBUGGING = "debugging"
    ONBOARDING = "onboarding"
    IMPACT_ANALYSIS = "impact_analysis"
    CODE_QUESTION = "code_question"


class RetrieverName(str, Enum):
    EXACT = "exact"
    LEXICAL = "lexical"
    SYMBOL = "symbol"
    ENDPOINT = "endpoint"
    METADATA = "metadata"
    GRAPH = "graph"
    SEMANTIC = "semantic"


class SupportType(str, Enum):
    SOURCE_EXACT = "source_exact"
    STATIC_RESOLVED = "static_resolved"
    HEURISTIC = "heuristic"


@dataclass(frozen=True)
class QueryClassification:
    question_type: QuestionType
    confidence: float
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("classification confidence must be finite and between zero and one")
        if not self.reason_codes or any(not reason.strip() for reason in self.reason_codes):
            raise ValueError("classification must contain non-empty reason codes")

    @property
    def compatibility_label(self) -> str:
        return self.question_type.value


@dataclass(frozen=True)
class RetrievalRequest:
    repository_id: str
    index_version_id: str
    query: str
    limit: int
    classification: QueryClassification

    def __post_init__(self) -> None:
        if not self.repository_id.strip():
            raise ValueError("repository_id must not be blank")
        if not self.index_version_id.startswith("idx_"):
            raise ValueError("index_version_id must use the idx_ identity prefix")
        if self.limit <= 0:
            raise ValueError("retrieval limit must be positive")

    @classmethod
    def for_repository(
        cls,
        repository: RepositoryState,
        query: str,
        limit: int,
        classification: QueryClassification,
    ) -> RetrievalRequest:
        return cls(
            repository_id=repository.id,
            index_version_id=f"idx_compat_{max(repository.current_index_version, 0)}",
            query=query,
            limit=limit,
            classification=classification,
        )


@dataclass(frozen=True)
class RetrievalCandidate:
    candidate_id: str
    repository_id: str
    index_version_id: str
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
    chunk: ChunkRecord
    result_type: str
    title: str
    compatibility_source: str

    def __post_init__(self) -> None:
        if not self.candidate_id.startswith("cand_"):
            raise ValueError("candidate_id must use the cand_ identity prefix")
        if not self.repository_id.strip() or not self.index_version_id.startswith("idx_"):
            raise ValueError("candidate ownership must be explicit")
        if not self.retriever_version.strip() or self.rank <= 0:
            raise ValueError("candidate retriever version and rank are required")
        if not isfinite(self.raw_score) or self.raw_score <= 0:
            raise ValueError("candidate raw_score must be finite and positive")
        if not self.entity_key.strip() or not self.source_key.strip():
            raise ValueError("candidate entity and source keys are required")
        if not self.reason_codes or any(not reason.strip() for reason in self.reason_codes):
            raise ValueError("candidate reason codes must be non-empty")

    def validate_ownership(self, request: RetrievalRequest) -> None:
        if self.repository_id != request.repository_id or self.index_version_id != request.index_version_id:
            raise ValueError("candidate ownership does not match the retrieval request")


def candidate_id(request: RetrievalRequest, retriever: RetrieverName, chunk: ChunkRecord) -> str:
    identity = "|".join(
        (request.repository_id, request.index_version_id, retriever.value, chunk.id, chunk.file_path)
    )
    return f"cand_{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]}"
