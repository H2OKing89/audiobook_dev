import secrets

from src.db import get_request
from src.logging_setup import get_logger


log = get_logger(__name__)


def generate_token() -> str:
    """
    Generate a secure URL-safe token for one-time use.
    """
    token = secrets.token_urlsafe(16)
    log.debug("token.generated", token=token)
    return token


def verify_token(token: str, valid_tokens: list[str] | None = None) -> bool:
    """
    Verify if a token is valid by checking the database.

    Args:
        token: The token to verify
        valid_tokens: Optional list of valid tokens for backwards compatibility

    Returns:
        bool: True if token exists in the database or valid_tokens, False otherwise
    """
    # First check the database
    entry = get_request(token)
    if entry:
        log.debug("token.verified", token=token, source="database")
        return True

    # Fall back to valid_tokens list for backwards compatibility
    if valid_tokens and token in valid_tokens:
        log.debug("token.verified", token=token, source="valid_tokens_list")
        return True

    log.warning("token.verification_failed", token=token)
    return False
