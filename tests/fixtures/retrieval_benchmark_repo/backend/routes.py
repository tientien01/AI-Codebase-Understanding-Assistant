from backend.auth_service import AuthService
from backend.token_service import create_access_token


def login(username: str, password: str) -> str:
    user = AuthService().authenticate_user(username, password)
    return create_access_token(user)
