from typing import List

def generate_token() -> str:
    import secrets
    return secrets.token_urlsafe(16)

def verify_token(token: str, valid_tokens: List[str]) -> bool:
    return token in valid_tokens