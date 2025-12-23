"""
Security module for implementing rate limiting and other security measures.
"""

import logging
import secrets
import time
from typing import Any

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

from src.config import load_config
from src.template_helpers import render_template


# Initialize rate limiter with client IP address as key
limiter = Limiter(key_func=get_remote_address)

# Create an in-memory token bucket for rate limiting token generation
token_buckets: dict[str, dict[str, float]] = {}

# Time window for rate limiting (seconds)
TIME_WINDOW = 3600  # 1 hour
# Maximum tokens per time window
MAX_TOKENS = 10

# Define protected endpoints that should require authentication
PROTECTED_ENDPOINTS: set[str] = {"/admin", "/api/admin", "/config", "/logs", "/stats", "/health/detailed", "/debug"}

# Define public endpoints that should be accessible without authentication
PUBLIC_ENDPOINTS: set[str] = {"/", "/static", "/approve", "/reject", "/health"}


def reset_rate_limit_buckets() -> None:
    """
    Reset all rate limit buckets - for testing purposes only.
    """
    token_buckets.clear()


def get_config_rate_limits():
    """Get rate limit settings from config."""
    config = load_config()
    security_cfg = config.get("security", {})
    time_window = security_cfg.get("rate_limit_window", TIME_WINDOW)
    max_tokens = security_cfg.get("max_tokens_per_window", MAX_TOKENS)
    return time_window, max_tokens


def get_config_auth_settings() -> dict[str, Any]:
    """Get authentication settings from config."""
    config = load_config()
    security_cfg = config.get("security", {})

    # Safely get list values and convert to sets
    protected_list = security_cfg.get("protected_endpoints", [])
    public_list = security_cfg.get("public_endpoints", [])

    if not isinstance(protected_list, list):
        protected_list = []
    if not isinstance(public_list, list):
        public_list = []

    return {
        "endpoint_protection_enabled": bool(security_cfg.get("endpoint_protection_enabled", True)),
        "protected_endpoints": set(protected_list) | PROTECTED_ENDPOINTS,
        "public_endpoints": set(public_list) | PUBLIC_ENDPOINTS,
        "require_auth_for_unknown": bool(security_cfg.get("require_auth_for_unknown_endpoints", False)),
    }


def token_bucket_rate_limit(client_ip: str) -> bool:
    """
    Implements token bucket algorithm for rate limiting token generation.
    Returns True if the request is allowed, False otherwise.
    """
    time_window, max_tokens = get_config_rate_limits()
    now = time.time()

    # Create a new bucket if the IP doesn't exist
    if client_ip not in token_buckets:
        token_buckets[client_ip] = {"tokens": max_tokens, "last_refill": now}

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
    security_cfg = config.get("security", {})
    api_key_enabled = security_cfg.get("api_key_enabled", False)

    if api_key_enabled:
        logging.debug("API key validation enabled, checking request")
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        configured_api_key = security_cfg.get("api_key")

        if not configured_api_key:
            logging.error("API key security is enabled but no key is configured")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server configuration error")

        if not api_key or api_key != configured_api_key:
            client_ip = get_client_ip(request)
            logging.warning(f"Invalid or missing API key from IP: {client_ip}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing API key")
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
    frontend_cfg = config.get("frontend", {})
    use_external_js = frontend_cfg.get("use_external_js", True)

    if use_external_js:
        # CSP with Alpine.js CDN support
        return "default-src 'self'; img-src 'self' https://ptpimg.me https: data:; style-src 'self' 'unsafe-inline'; style-src-attr 'unsafe-inline'; font-src 'self'; script-src 'self' https://unpkg.com https://*.unpkg.com 'unsafe-eval'; connect-src 'self';"
    else:
        # Stricter CSP for self-hosted JS (no external CDNs)
        return "default-src 'self'; img-src 'self' https://ptpimg.me https: data:; style-src 'self' 'unsafe-inline'; style-src-attr 'unsafe-inline'; font-src 'self'; script-src 'self' 'unsafe-eval'; connect-src 'self';"


# Custom rate limit handler
async def rate_limit_exceeded_handler(request: Request, _exc: RateLimitExceeded) -> Response:
    """Custom handler for rate limit exceeded errors."""
    client_host = request.client.host if request.client else "unknown"
    logging.warning(f"Rate limit exceeded: {client_host}")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded. Please try again later.", "retry_after": 60},
    )


def is_endpoint_protected(path: str) -> bool:
    """
    Check if an endpoint should be protected based on configuration.
    Returns True if the endpoint requires authentication.
    """
    auth_settings = get_config_auth_settings()

    if not auth_settings["endpoint_protection_enabled"]:
        return False

    # Check if path matches any public endpoint pattern
    for public_pattern in auth_settings["public_endpoints"]:
        # Handle exact matches and prefix matches
        if path == public_pattern or path.startswith(public_pattern + "/"):
            return False

    # Check if path matches any protected endpoint pattern
    for protected_pattern in auth_settings["protected_endpoints"]:
        # Handle exact matches and prefix matches
        if path == protected_pattern or path.startswith(protected_pattern + "/"):
            return True

    # Default behavior for unknown endpoints
    return auth_settings["require_auth_for_unknown"]


def is_valid_token_request(path: str) -> bool:
    """
    Check if the request is for a valid token-based endpoint (approve/reject).
    These endpoints use tokens for authentication instead of API keys.
    """
    token_patterns = ["/approve/", "/reject/"]
    return any(path.startswith(pattern) for pattern in token_patterns)


def has_valid_authentication(request: Request) -> bool:
    """
    Check if the request has valid authentication (API key or valid token).
    """
    config = load_config()
    security_cfg = config.get("security", {})

    # Check API key authentication
    api_key_enabled = security_cfg.get("api_key_enabled", False)
    if api_key_enabled:
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        configured_api_key = security_cfg.get("api_key")

        if api_key and configured_api_key and api_key == configured_api_key:
            return True

    # For token-based endpoints, we'll validate the token separately in the route handlers
    # This function is primarily for API key authentication
    return False


async def check_endpoint_authorization(request: Request) -> Response | None:
    """
    Middleware function to check if endpoint access is authorized.
    Returns None if authorized, or a 401 response if not.
    """
    path = request.url.path

    # Skip authorization for non-protected endpoints
    if not is_endpoint_protected(path):
        return None

    # Skip authorization for token-based endpoints (they handle their own validation)
    if is_valid_token_request(path):
        return None

    # Check if user has valid authentication
    if has_valid_authentication(request):
        return None

    # Log unauthorized access attempt
    client_ip = get_client_ip(request)
    logging.warning(f"Unauthorized access attempt to {path} from IP: {client_ip}")

    # Return 401 response with HTML template
    try:
        response = render_template(request, "401_page.html", {"requested_path": path, "client_ip": client_ip})
        response.status_code = 401
        return response
    except Exception as e:
        logging.error(f"Failed to render 401 page: {e}")
        # Fallback to simple JSON response
        return JSONResponse(status_code=401, content={"detail": "Unauthorized access"})


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce HTTPS in production"""

    def __init__(self, app, force_https: bool = False):
        super().__init__(app)
        self.force_https = force_https
    async def dispatch(self, request, call_next):
        if self.force_https and request.url.scheme != "https":
            # Check for forwarded headers (reverse proxy)
            forwarded_proto = request.headers.get("x-forwarded-proto")
            forwarded_ssl = request.headers.get("x-forwarded-ssl")

            if forwarded_proto != "https" and forwarded_ssl != "on":
                # Redirect to HTTPS
                url = request.url.replace(scheme="https")
                return RedirectResponse(url=str(url), status_code=301)

        response = await call_next(request)
        return response


def get_secure_cookie_settings() -> dict:
    """Get secure cookie settings based on configuration"""
    config = load_config()
    security_config = config.get("security", {})
    server_config = config.get("server", {})

    # Determine if we're in production (HTTPS should be enforced)
    force_https = security_config.get("force_https", False)
    base_url = server_config.get("base_url", "")
    is_https = base_url.startswith("https://") or force_https

    return {
        "secure": is_https,  # Only send cookies over HTTPS
        "httponly": True,  # Prevent JavaScript access
        "samesite": "lax",  # CSRF protection
    }


def get_client_ip(request: Request) -> str:
    """
    Get the real client IP address, respecting reverse proxy headers.

    This function checks for common reverse proxy headers in order of preference:
    1. X-Forwarded-For (most common, can contain multiple IPs)
    2. X-Real-IP (Nginx specific)
    3. X-Forwarded-Host (some configurations)
    4. CF-Connecting-IP (Cloudflare)
    5. X-Client-IP (custom headers)
    6. Falls back to direct connection IP

    Args:
        request: FastAPI Request object

    Returns:
        str: The client IP address
    """
    # Priority order of headers to check
    proxy_headers = ["x-forwarded-for", "x-real-ip", "cf-connecting-ip", "x-client-ip"]

    for header in proxy_headers:
        header_value = request.headers.get(header)
        if header_value:
            # X-Forwarded-For can contain multiple IPs (client, proxy1, proxy2)
            # We want the first one (original client)
            if header == "x-forwarded-for":
                client_ip = header_value.split(",")[0].strip()
            else:
                client_ip = header_value.strip()

            # Validate IP format (basic check)
            if client_ip and client_ip != "unknown":
                # Log which header was used for debugging
                logging.debug(f"Client IP determined from {header}: {client_ip}")
                return client_ip

    # Fallback to direct connection
    direct_ip = request.client.host if request.client else "unknown"
    logging.debug(f"Client IP determined from direct connection: {direct_ip}")
    return direct_ip
