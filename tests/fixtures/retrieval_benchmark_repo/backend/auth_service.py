class AuthService:
    """Authenticate a known user before a token is issued."""

    def authenticate_user(self, username: str, password: str) -> str:
        if username == "demo" and password == "demo-pass":
            return username
        raise ValueError("invalid login")
