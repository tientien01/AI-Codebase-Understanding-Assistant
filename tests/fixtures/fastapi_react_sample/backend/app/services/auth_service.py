class AuthService:
    @staticmethod
    async def authenticate_user(email: str, password: str):
        if email == "demo@example.com" and password == "password":
            return {"email": email, "role": "admin"}
        return None
