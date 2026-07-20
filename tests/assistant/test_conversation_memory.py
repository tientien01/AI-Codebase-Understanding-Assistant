from app.services.chat.conversation_memory import (
    ConversationMessageRecord,
    ConversationSummaryRecord,
    ConversationTranscriptRecord,
    project_conversation_memory,
)
from app.services.chat.agent_workflow_service import AgentWorkflowResult
from app.services.chat.chat_service import ChatService, ConversationNotFoundError
from app.services.evidence.evidence_service import EvidenceService
from app.services.index_models import RepositoryState
from app.services.retrieval.retrieval_service import RetrievalService
import pytest


def transcript(*, latest_index: int = 2, contents: tuple[str, ...] = ("first", "answer", "follow up")):
    summary = ConversationSummaryRecord(
        "conversation_test", "test", "active", len(contents), latest_index, "start", "end"
    )
    messages = tuple(
        ConversationMessageRecord(
            f"message_{index}",
            "user" if index % 2 == 0 else "assistant",
            content,
            latest_index,
            str(index),
        )
        for index, content in enumerate(contents)
    )
    return ConversationTranscriptRecord(summary, messages)


def test_memory_projection_is_recent_bounded_and_chronological() -> None:
    projected = project_conversation_memory(
        transcript(contents=("old", "old answer", "recent question", "recent answer")),
        2,
        max_messages=2,
        token_budget=100,
    )

    assert projected.text == "operator: recent question\nassistant: recent answer"
    assert projected.messages_used == 2
    assert projected.truncated is True
    assert projected.tokens_used <= projected.token_budget


def test_stale_memory_excludes_prior_assistant_claims() -> None:
    projected = project_conversation_memory(transcript(latest_index=1), 2, token_budget=100)

    assert "operator: first" in projected.text
    assert "operator: follow up" in projected.text
    assert "answer" not in projected.text
    assert projected.stale_history is True


def test_over_budget_memory_drops_messages_without_exceeding_budget() -> None:
    projected = project_conversation_memory(
        transcript(contents=("x" * 80, "y" * 80, "short")),
        2,
        token_budget=5,
    )

    assert projected.tokens_used <= 5
    assert projected.truncated is True


class MemoryStore:
    def __init__(self, value):
        self.value = value
        self.turns = []

    def get_conversation_transcript(self, repository_id, conversation_id, limit):
        if repository_id != "repo_test" or conversation_id != "conversation_test":
            return None
        return self.value

    def save_assistant_turn(self, turn):
        self.turns.append(turn)


class Repositories:
    def __init__(self, store):
        self.store = store
        self.state = RepositoryState(
            id="repo_test",
            name="test",
            source_type="folder",
            source_uri=None,
            source_path=None,
            status="indexed",
            current_index_version=2,
        )

    def get_indexed_repository(self, repository_id):
        return self.state


class EmptyEvidenceStore:
    def get_evidence(self, evidence_id):
        return None


class CapturingAgent:
    def __init__(self):
        self.context_anchor = None

    def answer(self, repository, message, context_anchor=None):
        self.context_anchor = context_anchor
        return AgentWorkflowResult("code_question", "limited", [], False, ["missing"])


def test_follow_up_uses_owned_memory_and_retains_conversation_identity() -> None:
    store = MemoryStore(transcript())
    service = ChatService(
        Repositories(store),
        RetrievalService(),
        EvidenceService(EmptyEvidenceStore()),
    )
    agent = CapturingAgent()
    service.agent = agent

    response = service.chat("repo_test", "Where is that used?", "conversation_test")

    assert response.conversation_id == "conversation_test"
    assert "operator: first" in agent.context_anchor
    assert store.turns[0].conversation_id == "conversation_test"
    budget = store.turns[0].budget_json
    assert '"memory_messages_used":3' in budget


def test_unknown_conversation_fails_before_answering() -> None:
    service = ChatService(
        Repositories(MemoryStore(transcript())),
        RetrievalService(),
        EvidenceService(EmptyEvidenceStore()),
    )

    with pytest.raises(ConversationNotFoundError):
        service.chat("repo_test", "question", "conversation_missing")
