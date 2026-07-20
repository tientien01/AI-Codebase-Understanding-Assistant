"""Bounded, non-evidentiary conversation replay and memory contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.api import CitationDTO


MAX_CONVERSATION_LIST_ITEMS = 50
MAX_TRANSCRIPT_MESSAGES = 200
DEFAULT_MEMORY_MESSAGES = 8
DEFAULT_MEMORY_TOKEN_BUDGET = 1_000


@dataclass(frozen=True)
class ConversationMessageRecord:
    message_id: str
    role: str
    content: str
    index_version: int
    created_at: str
    citations: tuple[CitationDTO, ...] = field(default_factory=tuple)
    evidence_sufficient: bool | None = None


@dataclass(frozen=True)
class ConversationSummaryRecord:
    conversation_id: str
    title: str | None
    status: str
    message_count: int
    latest_index_version: int
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ConversationTranscriptRecord:
    summary: ConversationSummaryRecord
    messages: tuple[ConversationMessageRecord, ...]


@dataclass(frozen=True)
class ConversationMemoryProjection:
    """Untrusted intent context. It is never a source-evidence container."""

    text: str
    messages_used: int
    tokens_used: int
    token_budget: int
    truncated: bool
    stale_history: bool


def project_conversation_memory(
    transcript: ConversationTranscriptRecord,
    current_index_version: int,
    *,
    max_messages: int = DEFAULT_MEMORY_MESSAGES,
    token_budget: int = DEFAULT_MEMORY_TOKEN_BUDGET,
) -> ConversationMemoryProjection:
    """Select recent whole messages deterministically within a conservative budget.

    Assistant messages from an older index are excluded. Prior operator questions may
    still help resolve intent, but the resulting text remains explicitly non-evidence.
    """

    stale_history = transcript.summary.latest_index_version != current_index_version
    candidates = [
        message
        for message in transcript.messages
        if not (stale_history and message.role == "assistant")
    ][-max_messages:]
    selected: list[tuple[str, int]] = []
    used = 0
    truncated = len(candidates) < len(transcript.messages)
    for message in reversed(candidates):
        label = "operator" if message.role in {"operator", "user"} else "assistant"
        rendered = f"{label}: {message.content.strip()}"
        cost = _estimated_tokens(rendered)
        if used + cost > token_budget:
            truncated = True
            continue
        selected.append((rendered, cost))
        used += cost
    selected.reverse()
    return ConversationMemoryProjection(
        text="\n".join(item for item, _ in selected),
        messages_used=len(selected),
        tokens_used=used,
        token_budget=token_budget,
        truncated=truncated,
        stale_history=stale_history,
    )


def _estimated_tokens(value: str) -> int:
    return max(1, (len(value) + 3) // 4)
