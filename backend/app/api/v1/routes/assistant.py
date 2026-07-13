from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_assistant_use_cases
from app.core.auth import require_api_auth
from app.schemas.assistant import (
    ChatRequest,
    ChatResponse,
    EvidenceDTO,
    EvidenceValidationRequest,
    EvidenceValidationResponse,
    SearchAskWithEvidenceRequest,
)
from app.services.application.use_cases import AssistantUseCases


router = APIRouter(prefix="/repositories", tags=["repositories"], dependencies=[Depends(require_api_auth)])


@router.post("/{repository_id}/chat", response_model=ChatResponse)
def chat_with_repository(
    repository_id: str,
    request: ChatRequest,
    service: AssistantUseCases = Depends(get_assistant_use_cases),
) -> ChatResponse:
    return service.chat(repository_id, request.message, request.conversation_id)


@router.get("/{repository_id}/evidence/{evidence_id}", response_model=EvidenceDTO)
def get_evidence(
    repository_id: str,
    evidence_id: str,
    service: AssistantUseCases = Depends(get_assistant_use_cases),
) -> EvidenceDTO:
    return service.get_evidence(repository_id, evidence_id)


@router.post("/{repository_id}/evidence/validate", response_model=EvidenceValidationResponse)
def validate_evidence(
    repository_id: str,
    request: EvidenceValidationRequest,
    service: AssistantUseCases = Depends(get_assistant_use_cases),
) -> EvidenceValidationResponse:
    return service.validate_evidence(repository_id, request.evidence_ids)


@router.post("/{repository_id}/search/ask-with-evidence", response_model=ChatResponse)
def ask_with_search_evidence(
    repository_id: str,
    request: SearchAskWithEvidenceRequest,
    service: AssistantUseCases = Depends(get_assistant_use_cases),
) -> ChatResponse:
    return service.ask_with_evidence(repository_id, request.message, request.evidence_ids, request.conversation_id)
