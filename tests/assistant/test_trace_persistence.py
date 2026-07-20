from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.models import (
    AgentTraceORM,
    ConversationORM,
    EvidenceORM,
    MessageORM,
    RepositoryORM,
)
from app.db.session import Base
from app.db.production_base import ProductionBase
import app.db.production_models  # noqa: F401 - register accepted production tables
from app.schemas.api import ChatResponse, CitationDTO
from app.services.chat.agent_workflow_service import AgentWorkflowResult
from app.services.chat.chat_service import ChatService
from app.services.chat.trace_persistence import (
    REDACTION_MARKER,
    TraceEventRecord,
    TraceEventType,
    build_persisted_turn,
)
from app.services.evidence.evidence_service import EvidenceService
from app.services.index_models import RepositoryState
from app.services.repositories import repository_store as local_store_module
from app.services.repositories.repository_store import RepositoryStore
from app.services.retrieval.retrieval_service import RetrievalService


def citation(evidence_id: str = "evidence_trace") -> CitationDTO:
    return CitationDTO(
        evidence_id=evidence_id,
        file_path="app/service.py",
        symbol_name="run",
        start_line=4,
        end_line=8,
        index_version=1,
        is_stale=False,
    )


def response(*, sufficient: bool = True) -> ChatResponse:
    citations = [citation()] if sufficient else []
    return ChatResponse(
        conversation_id="conversation_trace",
        message_id="message_trace_response",
        question_type="code_question",
        answer="The service is grounded. password=hunter2",
        citations=citations,
        evidence_sufficient=sufficient,
        missing_evidence=[] if sufficient else ["required_strong_evidence_count:1"],
    )


@pytest.fixture
def local_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'trace.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(local_store_module, "SessionLocal", session_factory)
    monkeypatch.setattr(local_store_module, "init_db", lambda: None)
    store = RepositoryStore()
    with session_factory.begin() as session:
        session.add(
            RepositoryORM(
                id="repo_trace",
                name="trace",
                source_type="folder",
                source_path=str(tmp_path),
                status="indexed",
                current_index_version=1,
                logs_json="[]",
                warnings_json="[]",
            )
        )
        session.add(
            EvidenceORM(
                evidence_id="evidence_trace",
                repository_id="repo_trace",
                index_version=1,
                source_type="code",
                file_path="app/service.py",
                symbol_name="run",
                start_line=4,
                end_line=8,
                content_preview="safe source",
                relevance_reason="selected",
                confidence_score=1.0,
                retrieval_source="exact",
                is_stale=0,
                metadata_json="{}",
            )
        )
    return store, session_factory


def test_local_turn_is_atomic_owned_redacted_and_replayable(local_store) -> None:
    store, session_factory = local_store
    turn = build_persisted_turn(
        "repo_trace",
        1,
        "Explain it with api_key=top-secret and ghp_1234567890ABCDEF",
        response(),
        None,
    )

    store.save_assistant_turn(turn)
    replay = store.get_agent_trace("repo_trace", turn.trace_id)

    assert replay is not None
    assert replay.turn.operator_message.count(REDACTION_MARKER) == 2
    assert REDACTION_MARKER in replay.turn.assistant_message
    assert replay.turn.claims[0].citation_ids == ("evidence_trace",)
    assert replay.turn.citations[0].evidence_id == "evidence_trace"
    assert [event.sequence for event in replay.turn.events] == list(
        range(1, len(replay.turn.events) + 1)
    )
    assert replay.turn.events[-1].event_type is TraceEventType.WORKFLOW_COMPLETED
    serialized_events = "".join(event.payload_json for event in replay.turn.events)
    assert "top-secret" not in serialized_events
    assert "safe source" not in serialized_events
    assert store.get_agent_trace("repo_other", turn.trace_id) is None

    with session_factory() as session:
        assert session.scalar(select(ConversationORM.id)) == "conversation_trace"
        assert session.scalars(select(MessageORM).order_by(MessageORM.role)).all()


def test_local_conversation_history_is_owned_bounded_and_replayable(local_store) -> None:
    store, _ = local_store
    first = build_persisted_turn("repo_trace", 1, "Where is the service?", response(), None)
    store.save_assistant_turn(first)
    follow_up_response = response(sufficient=False)
    follow_up_response.message_id = "message_trace_follow_up"
    second = build_persisted_turn(
        "repo_trace", 1, "What calls it?", follow_up_response, None
    )
    store.save_assistant_turn(second)

    summaries = store.list_conversations("repo_trace", 10)
    transcript = store.get_conversation_transcript("repo_trace", "conversation_trace", 200)

    assert len(summaries) == 1
    assert summaries[0].message_count == 4
    assert summaries[0].title == "Where is the service?"
    assert transcript is not None
    assert [item.content for item in transcript.messages[::2]] == [
        "Where is the service?",
        "What calls it?",
    ]
    assert transcript.messages[1].citations[0].evidence_id == "evidence_trace"
    assert store.get_conversation_transcript("repo_other", "conversation_trace", 200) is None


def test_failed_citation_rolls_back_the_entire_local_turn(local_store) -> None:
    store, session_factory = local_store
    bad_response = response()
    bad_response.citations[0].evidence_id = "evidence_missing"
    turn = build_persisted_turn("repo_trace", 1, "question", bad_response, None)

    with pytest.raises(ValueError, match="Citation does not belong"):
        store.save_assistant_turn(turn)

    with session_factory() as session:
        assert session.scalar(select(AgentTraceORM.id)) is None
        assert session.scalar(select(ConversationORM.id)) is None
        assert session.scalar(select(MessageORM.id)) is None


class CapturingStore:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.turns = []

    def save_assistant_turn(self, turn) -> None:
        if self.fail:
            raise RuntimeError("trace write failed")
        self.turns.append(turn)


class Repositories:
    def __init__(self, state: RepositoryState, store: CapturingStore) -> None:
        self.state = state
        self.store = store

    def get_indexed_repository(self, repository_id: str) -> RepositoryState:
        return self.state


class NoopEvidenceStore:
    def get_evidence(self, evidence_id):
        return None


class InsufficientAgent:
    def answer(self, repository, message):
        return AgentWorkflowResult(
            question_type="code_question",
            answer="No grounded answer",
            citations=[],
            evidence_sufficient=False,
            missing_evidence=["required_strong_evidence_count:1"],
        )


def chat_service(tmp_path: Path, store: CapturingStore) -> ChatService:
    state = RepositoryState(
        id="repo_trace",
        name="trace",
        source_type="folder",
        source_uri=None,
        source_path=tmp_path,
        status="indexed",
        current_index_version=1,
    )
    service = ChatService(
        Repositories(state, store),  # type: ignore[arg-type]
        RetrievalService(),
        EvidenceService(NoopEvidenceStore()),  # type: ignore[arg-type]
    )
    service.agent = InsufficientAgent()  # type: ignore[assignment]
    return service


def test_chat_returns_only_after_trace_store_accepts_turn(tmp_path: Path) -> None:
    store = CapturingStore()
    result = chat_service(tmp_path, store).chat("repo_trace", "password=private")

    assert result.conversation_id.startswith("conversation_")
    assert result.message_id.startswith("message_")
    assert len(store.turns) == 1
    assert store.turns[0].response_message_id == result.message_id


def test_chat_fails_closed_when_trace_persistence_fails(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="trace write failed"):
        chat_service(tmp_path, CapturingStore(fail=True)).chat("repo_trace", "question")


def test_production_trace_adapter_targets_the_accepted_schema() -> None:
    tables = ProductionBase.metadata.tables

    assert {
        "conversations",
        "messages",
        "claims",
        "citations",
        "agent_traces",
        "agent_trace_events",
    }.issubset(tables)
    assert {"repository_id", "index_version_id", "conversation_id"}.issubset(
        tables["agent_traces"].c.keys()
    )
    assert {"sequence", "event_type", "status", "payload"}.issubset(
        tables["agent_trace_events"].c.keys()
    )


def test_trace_contract_rejects_non_allowlisted_payload_fields() -> None:
    with pytest.raises(ValueError, match="non-allowlisted"):
        TraceEventRecord(
            event_id="traceevent_invalid",
            sequence=1,
            event_type=TraceEventType.QUESTION_CLASSIFIED,
            status="completed",
            payload_json='{"question_type":"code_question","raw_prompt":"do not store"}',
        )
