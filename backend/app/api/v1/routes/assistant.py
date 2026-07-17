from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_assistant_use_cases
from app.core.auth import require_api_auth
from app.schemas.assistant import (
    ChatRequest,
    ChatResponse,
    ConversationListResponse,
    ConversationTranscriptResponse,
    EvidenceDTO,
    EvidenceValidationRequest,
    EvidenceValidationResponse,
    SearchAskWithEvidenceRequest,
)
from app.services.application.use_cases import AssistantUseCases
from app.services.chat.request_context import AssistantContextValidationError
from app.services.chat.chat_service import ConversationNotFoundError


router = APIRouter(prefix="/repositories", tags=["repositories"], dependencies=[Depends(require_api_auth)])


@router.post("/{repository_id}/chat", response_model=ChatResponse)
def chat_with_repository(
    repository_id: str,
    request: ChatRequest,
    service: AssistantUseCases = Depends(get_assistant_use_cases),
) -> ChatResponse:
    try:
        return service.chat(repository_id, request.message, request.conversation_id, request.context)
    except AssistantContextValidationError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": error.code, "message": "Workspace context is invalid."},
        ) from error
    except ConversationNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail={"code": "conversation_not_found", "message": "Conversation was not found."},
        ) from error


@router.get("/{repository_id}/conversations", response_model=ConversationListResponse)
def list_conversations(
    repository_id: str,
    limit: int = Query(default=20, ge=1, le=50),
    service: AssistantUseCases = Depends(get_assistant_use_cases),
) -> ConversationListResponse:
    return service.list_conversations(repository_id, limit)


@router.get(
    "/{repository_id}/conversations/{conversation_id}",
    response_model=ConversationTranscriptResponse,
)
def get_conversation(
    repository_id: str,
    conversation_id: str,
    limit: int = Query(default=200, ge=1, le=200),
    service: AssistantUseCases = Depends(get_assistant_use_cases),
) -> ConversationTranscriptResponse:
    try:
        return service.get_conversation(repository_id, conversation_id, limit)
    except ConversationNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail={"code": "conversation_not_found", "message": "Conversation was not found."},
        ) from error


@router.delete(
    "/{repository_id}/conversations/{conversation_id}",
)
def delete_conversation(
    repository_id: str,
    conversation_id: str,
    service: AssistantUseCases = Depends(get_assistant_use_cases),
) -> dict[str, bool]:
    try:
        service.delete_conversation(repository_id, conversation_id)
    except ConversationNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail={"code": "conversation_not_found", "message": "Conversation was not found."},
        ) from error
    return {"deleted": True}


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
    try:
        return service.ask_with_evidence(
            repository_id, request.message, request.evidence_ids, request.conversation_id
        )
    except ConversationNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail={"code": "conversation_not_found", "message": "Conversation was not found."},
        ) from error
