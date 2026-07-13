from __future__ import annotations

from uuid import uuid4

from app.schemas.api import ChatResponse, CitationDTO, EvidenceDTO
from app.services.chat.agent_workflow_service import AgentWorkflowService
from app.services.chat.llm_client import LLMClient
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
        self.agent = AgentWorkflowService(retrieval, evidence)

    def chat(self, repository_id: str, message: str, conversation_id: str | None = None) -> ChatResponse:
        repository = self.repositories.get_indexed_repository(repository_id)
        result = self.agent.answer(repository, message)
        if not result.citations:
            return ChatResponse(
                conversation_id=conversation_id or f"conv_{uuid4().hex[:8]}",
                message_id=f"msg_{uuid4().hex[:10]}",
                question_type=result.question_type,
                answer=result.answer,
                citations=[],
                evidence_sufficient=False,
                missing_evidence=result.missing_evidence,
            )

        generated = (
            self.llm.generate_grounded_answer(message, result.question_type, result.citations)
            if result.evidence_sufficient
            else None
        )
        if generated and self.agent.validate_generated_answer(
            repository, generated.answer, generated.citation_ids, result.citations
        ).valid:
            return ChatResponse(
                conversation_id=conversation_id or f"conv_{uuid4().hex[:8]}",
                message_id=f"msg_{uuid4().hex[:10]}",
                question_type=result.question_type,
                answer=generated.answer,
                citations=result.citations,
                evidence_sufficient=True,
            )

        return ChatResponse(
            conversation_id=conversation_id or f"conv_{uuid4().hex[:8]}",
            message_id=f"msg_{uuid4().hex[:10]}",
            question_type=result.question_type,
            answer=result.answer,
            citations=result.citations,
            evidence_sufficient=result.evidence_sufficient,
            missing_evidence=result.missing_evidence,
        )

    def ask_with_evidence(
        self,
        repository_id: str,
        message: str,
        evidence_ids: list[str],
        conversation_id: str | None = None,
    ) -> ChatResponse:
        repository = self.repositories.get_indexed_repository(repository_id)
        question_type = self.retrieval.classify_question(message)
        if not evidence_ids:
            return ChatResponse(
                conversation_id=conversation_id or f"conv_{uuid4().hex[:8]}",
                message_id=f"msg_{uuid4().hex[:10]}",
                question_type=question_type,
                answer="Chua du bang chung de tra loi chac chan. Hay chon it nhat mot evidence tu ket qua search.",
                citations=[],
                evidence_sufficient=False,
                missing_evidence=["No selected evidence ids"],
            )

        validation = self.evidence.validate_evidence(repository, evidence_ids)
        invalid_items = [item for item in validation.items if not item.is_valid]
        if invalid_items:
            return ChatResponse(
                conversation_id=conversation_id or f"conv_{uuid4().hex[:8]}",
                message_id=f"msg_{uuid4().hex[:10]}",
                question_type=question_type,
                answer="Chua du bang chung de tra loi chac chan. Mot so evidence da mat, stale, hoac khong con khop voi index hien tai.",
                citations=[],
                evidence_sufficient=False,
                missing_evidence=[f"{item.evidence_id}: {item.reason or 'invalid'}" for item in invalid_items],
            )

        evidences = [self.evidence.get_evidence(repository.id, evidence_id) for evidence_id in evidence_ids]
        citations = [self._citation_from_evidence(evidence) for evidence in evidences]
        agent_result = self.agent.answer_from_citations(repository, message, citations)
        generated = (
            self.llm.generate_grounded_answer(message, question_type, citations)
            if agent_result.evidence_sufficient
            else None
        )
        if generated and self.agent.validate_generated_answer(
            repository, generated.answer, generated.citation_ids, citations
        ).valid:
            return ChatResponse(
                conversation_id=conversation_id or f"conv_{uuid4().hex[:8]}",
                message_id=f"msg_{uuid4().hex[:10]}",
                question_type=question_type,
                answer=generated.answer,
                citations=citations,
                evidence_sufficient=True,
            )

        return ChatResponse(
            conversation_id=conversation_id or f"conv_{uuid4().hex[:8]}",
            message_id=f"msg_{uuid4().hex[:10]}",
            question_type=question_type,
            answer=agent_result.answer,
            citations=citations,
            evidence_sufficient=agent_result.evidence_sufficient,
            missing_evidence=agent_result.missing_evidence,
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
