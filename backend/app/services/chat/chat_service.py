from __future__ import annotations

from uuid import uuid4

from app.schemas.api import (
    AssistantRequestContext,
    ChatResponse,
    CitationDTO,
    ConversationListResponse,
    ConversationMessageDTO,
    ConversationSummaryDTO,
    ConversationTranscriptResponse,
    EvidenceDTO,
)
from app.services.chat.agent_workflow_service import AgentWorkflowResult, AgentWorkflowService
from app.services.chat.conversation_memory import (
    MAX_CONVERSATION_LIST_ITEMS,
    MAX_TRANSCRIPT_MESSAGES,
    ConversationMemoryProjection,
    ConversationSummaryRecord,
    ConversationTranscriptRecord,
    project_conversation_memory,
)
from app.services.chat.llm_client import LLMClient, LLMResult
from app.services.chat.provider_context import ProviderEvidenceContext, ProviderEvidenceContextBuilder
from app.services.chat.request_context import AssistantRequestContextValidator
from app.services.chat.trace_persistence import build_persisted_turn, normalize_conversation_id
from app.services.evidence.evidence_service import EvidenceService
from app.services.repositories.repository_service import RepositoryService
from app.services.retrieval.retrieval_service import RetrievalService


class ChatService:
    def __init__(
        self,
        repositories: RepositoryService,
        retrieval: RetrievalService,
        evidence: EvidenceService,
        llm: LLMClient | None = None,
    ) -> None:
        self.repositories = repositories
        self.retrieval = retrieval
        self.evidence = evidence
        self.llm = llm or LLMClient()
        self.provider_context_builder = ProviderEvidenceContextBuilder()
        self.request_context_validator = AssistantRequestContextValidator()
        self.agent = AgentWorkflowService(
            retrieval,
            evidence,
            provider_context_builder=self.provider_context_builder,
        )

    def chat(
        self,
        repository_id: str,
        message: str,
        conversation_id: str | None = None,
        context: AssistantRequestContext | None = None,
    ) -> ChatResponse:
        repository = self.repositories.get_indexed_repository(repository_id)
        memory = self._load_memory(repository.id, repository.current_index_version, conversation_id)
        validated_context = self.request_context_validator.validate(repository, context)
        intent_context = self._intent_context(
            validated_context.retrieval_anchor if validated_context else None, memory
        )
        result = (
            self.agent.answer(repository, message, context_anchor=intent_context)
            if intent_context
            else self.agent.answer(repository, message)
        )
        if not result.citations:
            response = ChatResponse(
                conversation_id=conversation_id or normalize_conversation_id(None),
                message_id=f"message_{uuid4().hex}",
                question_type=result.question_type,
                answer=result.answer,
                citations=[],
                evidence_sufficient=False,
                missing_evidence=result.missing_evidence,
                retrieval_mode=self._retrieval_mode(),
            )
            return self._persist(
                repository.id, repository.current_index_version, message, response, result, memory=memory
            )

        generated = (
            self._generate_with_memory(
                message, result.question_type, result.provider_context, memory
            )
            if result.evidence_sufficient and result.provider_context is not None
            else None
        )
        if generated and self.agent.validate_generated_answer(
            repository, generated.answer, generated.citation_ids, result.citations
        ).valid:
            response = ChatResponse(
                conversation_id=conversation_id or normalize_conversation_id(None),
                message_id=f"message_{uuid4().hex}",
                question_type=result.question_type,
                answer=generated.answer,
                citations=result.citations,
                evidence_sufficient=True,
                generation_mode="ollama" if generated.provider == "ollama" else "provider",
                provider_state="ready",
                retrieval_mode=self._retrieval_mode(),
            )
            return self._persist(
                repository.id,
                repository.current_index_version,
                message,
                response,
                result,
                provider_accepted=True,
                memory=memory,
            )

        response = ChatResponse(
            conversation_id=conversation_id or normalize_conversation_id(None),
            message_id=f"message_{uuid4().hex}",
            question_type=result.question_type,
            answer=result.answer,
            citations=result.citations,
            evidence_sufficient=result.evidence_sufficient,
            missing_evidence=result.missing_evidence,
            generation_mode=(
                "deterministic_fallback" if self._provider_configured() else "deterministic"
            ),
            provider_state="degraded" if self._provider_configured() else "unavailable",
            retrieval_mode=self._retrieval_mode(),
        )
        return self._persist(
            repository.id, repository.current_index_version, message, response, result, memory=memory
        )

    def ask_with_evidence(
        self,
        repository_id: str,
        message: str,
        evidence_ids: list[str],
        conversation_id: str | None = None,
    ) -> ChatResponse:
        repository = self.repositories.get_indexed_repository(repository_id)
        memory = self._load_memory(repository.id, repository.current_index_version, conversation_id)
        question_type = self.retrieval.classify_question(message)
        if not evidence_ids:
            response = ChatResponse(
                conversation_id=conversation_id or normalize_conversation_id(None),
                message_id=f"message_{uuid4().hex}",
                question_type=question_type,
                answer="There is not enough evidence to answer confidently. Select at least one evidence item from the search results.",
                citations=[],
                evidence_sufficient=False,
                missing_evidence=["No selected evidence ids"],
                retrieval_mode=self._retrieval_mode(),
            )
            return self._persist(
                repository.id, repository.current_index_version, message, response, None, memory=memory
            )

        validation = self.evidence.validate_evidence(repository, evidence_ids)
        invalid_items = [item for item in validation.items if not item.is_valid]
        if invalid_items:
            response = ChatResponse(
                conversation_id=conversation_id or normalize_conversation_id(None),
                message_id=f"message_{uuid4().hex}",
                question_type=question_type,
                answer="There is not enough evidence to answer confidently. Some evidence is missing, stale, or no longer matches the current index.",
                citations=[],
                evidence_sufficient=False,
                missing_evidence=[f"{item.evidence_id}: {item.reason or 'invalid'}" for item in invalid_items],
                retrieval_mode=self._retrieval_mode(),
            )
            return self._persist(
                repository.id, repository.current_index_version, message, response, None, memory=memory
            )

        evidences = [self.evidence.get_evidence(repository.id, evidence_id) for evidence_id in evidence_ids]
        citations = [self._citation_from_evidence(evidence) for evidence in evidences]
        agent_result = self.agent.answer_from_citations(repository, message, citations)
        provider_context = self.provider_context_builder.from_saved(
            repository,
            evidences,
            self.agent.configuration.context_token_budget,
        )
        generated = (
            self._generate_with_memory(message, question_type, provider_context, memory)
            if agent_result.evidence_sufficient and provider_context is not None
            else None
        )
        if generated and self.agent.validate_generated_answer(
            repository, generated.answer, generated.citation_ids, citations
        ).valid:
            response = ChatResponse(
                conversation_id=conversation_id or normalize_conversation_id(None),
                message_id=f"message_{uuid4().hex}",
                question_type=question_type,
                answer=generated.answer,
                citations=citations,
                evidence_sufficient=True,
                generation_mode="ollama" if generated.provider == "ollama" else "provider",
                provider_state="ready",
                retrieval_mode=self._retrieval_mode(),
            )
            return self._persist(
                repository.id,
                repository.current_index_version,
                message,
                response,
                agent_result,
                provider_accepted=True,
                memory=memory,
            )

        response = ChatResponse(
            conversation_id=conversation_id or normalize_conversation_id(None),
            message_id=f"message_{uuid4().hex}",
            question_type=question_type,
            answer=agent_result.answer,
            citations=citations,
            evidence_sufficient=agent_result.evidence_sufficient,
            missing_evidence=agent_result.missing_evidence,
            generation_mode=(
                "deterministic_fallback" if self._provider_configured() else "deterministic"
            ),
            provider_state="degraded" if self._provider_configured() else "unavailable",
            retrieval_mode=self._retrieval_mode(),
        )
        return self._persist(
            repository.id,
            repository.current_index_version,
            message,
            response,
            agent_result,
            memory=memory,
        )

    def list_conversations(self, repository_id: str, limit: int) -> ConversationListResponse:
        repository = self.repositories.get_repository(repository_id)
        bounded = min(max(limit, 1), MAX_CONVERSATION_LIST_ITEMS)
        records = self.repositories.store.list_conversations(repository_id, bounded)
        return ConversationListResponse(
            items=[self._summary_dto(item, repository.current_index_version) for item in records]
        )

    def get_conversation(
        self, repository_id: str, conversation_id: str, limit: int
    ) -> ConversationTranscriptResponse:
        repository = self.repositories.get_repository(repository_id)
        transcript = self.repositories.store.get_conversation_transcript(
            repository_id, conversation_id, min(max(limit, 1), MAX_TRANSCRIPT_MESSAGES)
        )
        if transcript is None:
            raise ConversationNotFoundError
        return self._transcript_dto(transcript, repository.current_index_version)

    def delete_conversation(self, repository_id: str, conversation_id: str) -> None:
        self.repositories.get_repository(repository_id)
        if not self.repositories.store.delete_conversation(repository_id, conversation_id):
            raise ConversationNotFoundError

    def _persist(
        self,
        repository_id: str,
        index_version: int,
        operator_message: str,
        response: ChatResponse,
        result: AgentWorkflowResult | None,
        *,
        provider_accepted: bool = False,
        memory: ConversationMemoryProjection | None = None,
    ) -> ChatResponse:
        turn = build_persisted_turn(
            repository_id,
            index_version,
            operator_message,
            response,
            result,
            provider_accepted=provider_accepted,
            memory=memory,
        )
        self.repositories.store.save_assistant_turn(turn)
        return response

    def _load_memory(
        self, repository_id: str, index_version: int, conversation_id: str | None
    ) -> ConversationMemoryProjection | None:
        if conversation_id is None:
            return None
        transcript = self.repositories.store.get_conversation_transcript(
            repository_id, conversation_id, MAX_TRANSCRIPT_MESSAGES
        )
        if transcript is None:
            raise ConversationNotFoundError
        return project_conversation_memory(transcript, index_version)

    @staticmethod
    def _intent_context(
        workspace_context: str | None, memory: ConversationMemoryProjection | None
    ) -> str | None:
        memory_context = (
            f"CONVERSATION_INTENT_CONTEXT (untrusted, not evidence):\n{memory.text}"
            if memory and memory.text
            else None
        )
        parts = [item for item in (workspace_context, memory_context) if item]
        return "\n".join(parts) or None

    def _generate_with_memory(
        self,
        message: str,
        question_type: str,
        provider_context: ProviderEvidenceContext,
        memory: ConversationMemoryProjection | None,
    ) -> LLMResult | None:
        if memory and memory.text:
            return self.llm.generate_grounded_answer(
                message,
                question_type,
                provider_context,
                conversation_context=memory.text,
            )
        return self.llm.generate_grounded_answer(message, question_type, provider_context)

    def _retrieval_mode(self) -> str:
        return "hybrid" if self.retrieval.vector_search.__class__.__name__ == "DenseVectorSearchService" else "sparse"

    def _provider_configured(self) -> bool:
        return bool(getattr(self.llm, "is_configured", False))

    @staticmethod
    def _summary_dto(
        record: ConversationSummaryRecord, current_index_version: int
    ) -> ConversationSummaryDTO:
        return ConversationSummaryDTO(
            conversation_id=record.conversation_id,
            title=record.title,
            status=record.status,
            message_count=record.message_count,
            latest_index_version=record.latest_index_version,
            is_stale=record.latest_index_version != current_index_version,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _transcript_dto(
        self, transcript: ConversationTranscriptRecord, current_index_version: int
    ) -> ConversationTranscriptResponse:
        return ConversationTranscriptResponse(
            conversation=self._summary_dto(transcript.summary, current_index_version),
            messages=[
                ConversationMessageDTO(
                    message_id=item.message_id,
                    role="user" if item.role in {"operator", "user"} else "assistant",
                    content=item.content,
                    index_version=item.index_version,
                    created_at=item.created_at,
                    citations=list(item.citations),
                    evidence_sufficient=item.evidence_sufficient,
                )
                for item in transcript.messages
            ],
        )

    def _citation_from_evidence(self, evidence: EvidenceDTO) -> CitationDTO:
        return CitationDTO(
            evidence_id=evidence.evidence_id,
            file_path=evidence.file_path,
            symbol_name=evidence.symbol_name,
            start_line=evidence.start_line,
            end_line=evidence.end_line,
            index_version=evidence.index_version,
            is_stale=evidence.is_stale,
        )


class ConversationNotFoundError(LookupError):
    """Safe owned-conversation lookup failure."""
