"""Single-operator authentication API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class BootstrapRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=1024)


class LoginRequest(BaseModel):
    password: str = Field(min_length=12, max_length=1024)


class SessionIssuedResponse(BaseModel):
    principal_id: str
    display_name: str
    csrf_token: str
    expires_at: datetime


class SessionResponse(BaseModel):
    principal_id: str
    display_name: str
    credential_kind: str


class ApiTokenCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    expires_in_seconds: int = Field(ge=1)


class ApiTokenIssuedResponse(BaseModel):
    token_id: str
    name: str
    token: str
    expires_at: datetime


class AccessOperationResponse(BaseModel):
    status: str
