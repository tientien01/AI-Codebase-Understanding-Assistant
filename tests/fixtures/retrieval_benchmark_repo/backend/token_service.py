def create_access_token(username: str) -> str:
    """Create the short-lived access token returned by the login route."""
    return f"token-for-{username}"
