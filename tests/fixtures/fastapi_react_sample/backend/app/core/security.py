def create_access_token(payload: dict) -> str:
    subject = payload.get("sub", "anonymous")
    return f"fixture-token-for-{subject}"
