"""
Security module for implementing rate limiting and other security measures.
"""
import time
import logging
import secrets
from typing import Dict, Optional, Tuple, Callable
from fastapi import Request, Response, Depends, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse
from src.config import load_config

# Initialize rate limiter with client IP address as key
limiter = Limiter(key_func=get_remote_address)

# Create an in-memory token bucket for rate limiting token generation
token_buckets: Dict[str, Dict[str, float]] = {}

# Time window for rate limiting (seconds)
TIME_WINDOW = 3600  # 1 hour
# Maximum tokens per time window
MAX_TOKENS = 10

def get_config_rate_limits():
    """Get rate limit settings from config."""
    config = load_config()
    security_cfg = config.get('security', {})
    time_window = security_cfg.get('rate_limit_window', TIME_WINDOW)
    max_tokens = security_cfg.get('max_tokens_per_window', MAX_TOKENS)
    return time_window, max_tokens

def token_bucket_rate_limit(client_ip: str) -> bool:
    """
    Implements token bucket algorithm for rate limiting token generation.
    Returns True if the request is allowed, False otherwise.
    """
    time_window, max_tokens = get_config_rate_limits()
    now = time.time()
    
    # Create a new bucket if the IP doesn't exist
    if client_ip not in token_buckets:
        token_buckets[client_ip] = {
            "tokens": max_tokens,
            "last_refill": now
        }
    
    # Get the bucket for this IP
    bucket = token_buckets[client_ip]
    
    # Calculate time since last refill
    time_passed = now - bucket["last_refill"]
    
    # Refill tokens based on time passed (tokens replenish over time)
    refill_amount = (time_passed / time_window) * max_tokens
    bucket["tokens"] = min(max_tokens, bucket["tokens"] + refill_amount)
    bucket["last_refill"] = now
    
    # Check if we have at least one token left
    if bucket["tokens"] >= 1:
        # Use one token
        bucket["tokens"] -= 1
        return True
    else:
        return False

def rate_limit_token_generation(client_ip: str) -> bool:
    """
    Rate limit token generation to prevent abuse.
    Returns True if the request is allowed, False otherwise.
    """
    allowed = token_bucket_rate_limit(client_ip)
    if not allowed:
        logging.warning(f"Rate limit exceeded for token generation from IP: {client_ip}")
    else:
        logging.debug(f"Rate limit check passed for IP: {client_ip}")
    return allowed

def require_api_key(request: Request) -> None:
    """
    Validate API key for admin endpoints.
    """
    config = load_config()
    security_cfg = config.get('security', {})
    api_key_enabled = security_cfg.get('api_key_enabled', False)
    
    if api_key_enabled:
        logging.debug("API key validation enabled, checking request")
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        configured_api_key = security_cfg.get('api_key')
        
        if not configured_api_key:
            logging.error("API key security is enabled but no key is configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error"
            )
            
        if not api_key or api_key != configured_api_key:
            client_ip = request.client.host if request.client else "unknown"
            logging.warning(f"Invalid or missing API key from IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Invalid or missing API key"
            )
        logging.debug("API key validation successful")
    else:
        logging.debug("API key validation disabled")

def generate_csrf_token() -> str:
    """Generate a secure CSRF token."""
    return secrets.token_hex(32)

def get_csp_header() -> str:
    """
    Get Content Security Policy header based on configuration.
    Returns stricter CSP if external JS files are used.
    """
    config = load_config()
    security_cfg = config.get('security', {})
    use_external_js = security_cfg.get('use_external_js', True)
    
    if use_external_js:
        # Stricter CSP - no inline scripts
        return "default-src 'self'; img-src 'self' https:; style-src 'self' 'unsafe-inline'; script-src 'self';"
    else:
        # Allow inline scripts for legacy support
        return "default-src 'self'; img-src 'self' https:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline';"

# Custom rate limit handler
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom handler for rate limit exceeded errors."""
    client_host = request.client.host if request.client else "unknown"
    logging.warning(f"Rate limit exceeded: {client_host}")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "retry_after": 60
        }
    )
