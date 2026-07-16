from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.routes.assistant import chat_with_repository
from app.schemas.assistant import AssistantRequestContext, ChatRequest
from app.services.chat.agent_workflow_service import AgentWorkflowService
from app.services.chat.chat_service import ChatService
from app.services.chat.request_context import (
    AssistantContextValidationError,
    AssistantRequestContextValidator,
)
from app.services.chat.tool_registry import ToolRegistry
from app.services.evidence.evidence_service import EvidenceService
from app.services.index_models import ChunkRecord, FileRecord, RepositoryState, SymbolRecord
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.text_utils import content_hash


class MemoryEvidenceStore:
    def __init__(self) -> None:
        self.evidence = {}

    def save_evidence(self, evidence) -> None:
        self.evidence[evidence.evidence_id] = evidence

    def get_evidence(self, evidence_id):
        return self.evidence.get(evidence_id)


class RecordingRegistry:
    def __init__(self, retrieval: RetrievalService) -> None:
        self.delegate = ToolRegistry.default(retrieval)
        self.inputs = []

    def execute(self, tool_input, repository):
        self.inputs.append(tool_input)
        return self.delegate.execute(tool_input, repository)


def repository(tmp_path: Path) -> RepositoryState:
    relative_path = "src/service.py"
    source = "def calculate(value):\n    return value + 1\n"
    absolute_path = tmp_path / relative_path
    absolute_path.parent.mkdir(parents=True)
    absolute_path.write_text(source, encoding="utf-8", newline="\n")
    source_bytes = absolute_path.read_bytes()
    chunk_content = source.strip()
    return RepositoryState(
        id="repo_context",
        name="context",
        source_type="local",
        source_uri=None,
        source_path=tmp_path,
        status="ready",
        current_index_version=3,
        files=[FileRecord(
            path=relative_path,
            absolute_path=absolute_path,
            language="python",
            file_type="source",
            size_bytes=len(source_bytes),
            content_hash=hashlib.sha256(source_bytes).hexdigest(),
        )],
        symbols=[SymbolRecord(
            id="symbol_calculate",
            name="calculate",
            symbol_type="function",
            file_path=relative_path,
            start_line=1,
            end_line=2,
        )],
        chunks=[ChunkRecord(
            id="chunk_calculate",
            file_path=relative_path,
            chunk_type="function",
            content=chunk_content,
            start_line=1,
            end_line=2,
            symbol_name="calculate",
            content_hash=content_hash(f"{relative_path}:1:2:{chunk_content}"),
        )],
    )


def request_context(**changes) -> AssistantRequestContext:
    values = {
        "page": "code",
        "file_path": "src/service.py",
        "start_line": 1,
        "end_line": 1,
        "symbol_name": "calculate",
    }
    values.update(changes)
    return AssistantRequestContext(**values)


def test_public_context_is_bounded_and_never_accepts_source_content() -> None:
    assert AssistantRequestContext(page="overview").model_dump(exclude_none=True) == {"page": "overview"}
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AssistantRequestContext.model_validate({
            "page": "code",
            "file_path": "src/service.py",
            "source": "do not trust this text",
        })
    with pytest.raises(ValidationError, match="canonical repository-relative"):
        request_context(file_path="../outside.py")
    with pytest.raises(ValidationError, match="supplied together"):
        request_context(end_line=None)
    with pytest.raises(ValidationError, match="only valid for the code page"):
        request_context(page="overview")


def test_validator_binds_file_range_symbol_and_source_hash_to_active_repository(tmp_path: Path) -> None:
    state = repository(tmp_path)
    validator = AssistantRequestContextValidator()

    validated = validator.validate(state, request_context())

    assert validated is not None
    assert validated.retrieval_anchor == (
        "workspace-page:code workspace-file:src/service.py "
        "workspace-lines:1-1 workspace-symbol:calculate"
    )
    with pytest.raises(AssistantContextValidationError, match="context_file_not_indexed"):
        validator.validate(state, request_context(file_path="src/other.py"))
    with pytest.raises(AssistantContextValidationError, match="context_range_invalid"):
        validator.validate(state, request_context(start_line=9, end_line=9, symbol_name=None))
    with pytest.raises(AssistantContextValidationError, match="context_symbol_not_indexed"):
        validator.validate(state, request_context(symbol_name="missing"))

    state.files[0].absolute_path.write_text("changed\n", encoding="utf-8")
    with pytest.raises(AssistantContextValidationError, match="context_source_changed"):
        validator.validate(state, request_context())


def test_valid_context_anchors_retrieval_without_changing_question_classification(tmp_path: Path) -> None:
    state = repository(tmp_path)
    retrieval = RetrievalService()
    registry = RecordingRegistry(retrieval)
    workflow = AgentWorkflowService(
        retrieval,
        EvidenceService(MemoryEvidenceStore()),  # type: ignore[arg-type]
        registry=registry,  # type: ignore[arg-type]
    )
    context = AssistantRequestContextValidator().validate(state, request_context())

    result = workflow.answer(state, "What does this do?", context_anchor=context.retrieval_anchor)

    assert result.question_type == "code_question"
    assert result.citations[0].file_path == "src/service.py"
    assert registry.inputs[0].classification_query == "What does this do?"
    assert "workspace-file:src/service.py" in registry.inputs[0].query
    assert "workspace-symbol:calculate" in registry.inputs[0].query


def test_route_returns_stable_422_when_context_validation_fails() -> None:
    class RejectingService:
        def chat(self, *_args, **_kwargs):
            raise AssistantContextValidationError("context_file_not_indexed")

    request = ChatRequest(message="Explain this", context=request_context())
    with pytest.raises(HTTPException) as raised:
        chat_with_repository("repo_context", request, RejectingService())  # type: ignore[arg-type]

    assert raised.value.status_code == 422
    assert raised.value.detail == {
        "code": "context_file_not_indexed",
        "message": "Workspace context is invalid.",
    }


def test_chat_rejects_invalid_context_before_retrieval(tmp_path: Path) -> None:
    state = repository(tmp_path)

    class Repositories:
        def get_indexed_repository(self, _repository_id):
            return state

    class NeverCalledAgent:
        def answer(self, *_args, **_kwargs):
            raise AssertionError("retrieval must not run")

    service = ChatService(
        Repositories(),  # type: ignore[arg-type]
        RetrievalService(),
        EvidenceService(MemoryEvidenceStore()),  # type: ignore[arg-type]
    )
    service.agent = NeverCalledAgent()  # type: ignore[assignment]

    with pytest.raises(AssistantContextValidationError, match="context_file_not_indexed"):
        service.chat(state.id, "Explain this", context=request_context(file_path="src/missing.py"))
