from typing import List, Optional
import secrets
import logging
from src.db import get_request

def generate_token() -> str:
    """
    Generate a secure URL-safe token for one-time use.
    """
    token = secrets.token_urlsafe(16)
    logging.debug(f"Generated new token: {token}")
    return token

def verify_token(token: str, valid_tokens: Optional[List[str]] = None) -> bool:
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
        logging.debug(f"Token {token} verified from database")
        return True
    
    # Fall back to valid_tokens list for backwards compatibility
    if valid_tokens and token in valid_tokens:
        logging.debug(f"Token {token} verified from provided valid_tokens list")
        return True
        
    logging.warning(f"Token verification failed for {token}")
    return False