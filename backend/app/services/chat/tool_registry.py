from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from time import monotonic
from typing import Protocol

from app.services.chat.workflow_contracts import ToolInput, ToolName, ToolOutput
from app.services.index_models import RepositoryState
from app.services.retrieval.contracts import RetrievalRequest
from app.services.retrieval.ranking import RankedCandidate
from app.services.retrieval.retrieval_service import RetrievalService


@dataclass(frozen=True)
class ToolExecution:
    output: ToolOutput
    retrieval_request: RetrievalRequest
    ranked_candidates: tuple[RankedCandidate, ...]


class ToolHandler(Protocol):
    name: ToolName
    version: str

    def execute(self, tool_input: ToolInput, repository: RepositoryState) -> ToolExecution: ...


class ExactLookupTool:
    name = ToolName.EXACT_LOOKUP
    version = "1"

    def __init__(self, retrieval: RetrievalService) -> None:
        self.retrieval = retrieval

    def execute(self, tool_input: ToolInput, repository: RepositoryState) -> ToolExecution:
        started = monotonic()
        classification = self.retrieval.classifier.classify(
            tool_input.classification_query or tool_input.query
        )
        request = RetrievalRequest.for_repository(
            repository,
            tool_input.query,
            tool_input.limit,
            classification,
        )
        if classification.compatibility_label != tool_input.question_type:
            raise ValueError("tool input question type does not match deterministic classification")
        candidates = self.retrieval.exact_retriever.retrieve(request, repository)
        ranked = tuple(self.retrieval.ranker.rank(request, candidates))
        return ToolExecution(
            output=_output(tool_input, ranked, started),
            retrieval_request=request,
            ranked_candidates=ranked,
        )


class HybridRetrievalTool:
    name = ToolName.HYBRID_RETRIEVAL
    version = "1"

    def __init__(self, retrieval: RetrievalService) -> None:
        self.retrieval = retrieval

    def execute(self, tool_input: ToolInput, repository: RepositoryState) -> ToolExecution:
        started = monotonic()
        classification = self.retrieval.classifier.classify(
            tool_input.classification_query or tool_input.query
        )
        if tool_input.classification_query and tool_input.classification_query != tool_input.query:
            request, ranked = self.retrieval.ranked_search(
                repository,
                tool_input.query,
                tool_input.limit,
                classification,
            )
        else:
            request, ranked = self.retrieval.ranked_search(
                repository,
                tool_input.query,
                tool_input.limit,
            )
        if request.classification.compatibility_label != tool_input.question_type:
            raise ValueError("tool input question type does not match deterministic classification")
        ranked_tuple = tuple(ranked)
        return ToolExecution(
            output=_output(tool_input, ranked_tuple, started),
            retrieval_request=request,
            ranked_candidates=ranked_tuple,
        )


class ToolRegistry:
    """Immutable allowlist for versioned assistant tools."""

    def __init__(self, handlers: tuple[ToolHandler, ...]) -> None:
        if not handlers:
            raise ValueError("tool registry requires at least one handler")
        by_key: dict[tuple[ToolName, str], ToolHandler] = {}
        for handler in handlers:
            if not isinstance(handler.name, ToolName) or handler.version != "1":
                raise ValueError("tool registry handler name and version must be controlled")
            key = (handler.name, handler.version)
            if key in by_key:
                raise ValueError("duplicate tool registry handler")
            by_key[key] = handler
        self._handlers = by_key

    @classmethod
    def default(cls, retrieval: RetrievalService) -> ToolRegistry:
        return cls((ExactLookupTool(retrieval), HybridRetrievalTool(retrieval)))

    @property
    def registry_id(self) -> str:
        payload = json.dumps(
            sorted((name.value, version) for name, version in self._handlers),
            ensure_ascii=True,
            separators=(",", ":"),
        )
        return f"toolreg_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"

    @property
    def tool_names(self) -> tuple[ToolName, ...]:
        return tuple(sorted((name for name, _ in self._handlers), key=lambda item: item.value))

    def resolve(self, name: ToolName, version: str) -> ToolHandler:
        if not isinstance(name, ToolName):
            raise ValueError("unknown assistant tool")
        handler = self._handlers.get((name, version))
        if handler is None:
            raise ValueError("unknown assistant tool or incompatible version")
        return handler

    def execute(self, tool_input: ToolInput, repository: RepositoryState) -> ToolExecution:
        expected_index_id = f"idx_compat_{max(repository.current_index_version, 0)}"
        if tool_input.repository_id != repository.id or tool_input.index_version_id != expected_index_id:
            raise ValueError("tool input ownership does not match the active repository index")
        execution = self.resolve(tool_input.tool_name, tool_input.tool_version).execute(
            tool_input,
            repository,
        )
        output = execution.output
        if (
            output.call_id != tool_input.call_id
            or output.tool_name != tool_input.tool_name
            or output.tool_version != tool_input.tool_version
            or output.repository_id != tool_input.repository_id
            or output.index_version_id != tool_input.index_version_id
        ):
            raise ValueError("tool output ownership does not match tool input")
        return execution


def _output(
    tool_input: ToolInput,
    ranked: tuple[RankedCandidate, ...],
    started: float,
) -> ToolOutput:
    candidate_ids = tuple(
        sorted({candidate_id for item in ranked for candidate_id in item.candidate_ids})
    )
    return ToolOutput(
        call_id=tool_input.call_id,
        tool_name=tool_input.tool_name,
        tool_version=tool_input.tool_version,
        repository_id=tool_input.repository_id,
        index_version_id=tool_input.index_version_id,
        candidate_ids=candidate_ids,
        coverage="matched" if candidate_ids else "none",
        truncated=len(ranked) >= tool_input.limit,
        diagnostics=("candidates_found",) if candidate_ids else ("no_candidates",),
        duration_ms=max(0, int((monotonic() - started) * 1_000)),
        retryable=False,
    )
