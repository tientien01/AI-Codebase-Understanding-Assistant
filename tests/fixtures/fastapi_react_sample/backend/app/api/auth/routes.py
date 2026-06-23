from fastapi import APIRouter, HTTPException, status

from app.core.security import create_access_token
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login")
async def login(payload: dict):
    user = await AuthService.authenticate_user(payload["email"], payload["password"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": user["email"]})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
async def get_current_user():
    return {"email": "demo@example.com"}
