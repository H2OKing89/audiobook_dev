"""
Request ID correlation middleware for FastAPI.

This middleware ensures every request has a unique identifier that flows
through all log messages, making it possible to trace a request across
the entire system.

The middleware:
1. Reads X-Request-ID from incoming request headers (or generates one)
2. Binds it to structlog context vars (available to all loggers)
3. Returns it in the response X-Request-ID header
4. Logs request start/end with timing information

Usage:
    from fastapi import FastAPI
    from src.request_id_middleware import RequestIdMiddleware

    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

from src.logging_setup import bind_contextvars, clear_contextvars, get_logger


if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.requests import Request
    from starlette.responses import Response

log = get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds request correlation IDs to all requests.

    Features:
    - Accepts X-Request-ID from upstream (load balancer, gateway)
    - Generates UUID if not provided
    - Binds to structlog context for automatic inclusion in all logs
    - Returns request ID in response header
    - Logs request timing and basic info

    Attributes:
        header_name: HTTP header name for request ID (default: X-Request-ID)
        log_requests: Whether to log request start/end (default: True)
    """

    def __init__(
        self,
        app,
        *,
        header_name: str = "X-Request-ID",
        log_requests: bool = True,
    ) -> None:
        super().__init__(app)
        self.header_name = header_name
        self.log_requests = log_requests

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request with correlation ID tracking."""
        # Get or generate request ID
        request_id = request.headers.get(self.header_name) or uuid.uuid4().hex

        # Clear any stale context and bind new values
        clear_contextvars()
        bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        # Store in request state for access by route handlers
        request.state.request_id = request_id

        start_time = time.perf_counter()

        if self.log_requests:
            # Log request start (minimal - just to mark entry)
            log.debug(
                "http.request.start",
                client_ip=self._get_client_ip(request),
                query=str(request.query_params) if request.query_params else None,
            )

        try:
            response = await call_next(request)
        except Exception:
            # Log unhandled exceptions with timing
            duration_ms = (time.perf_counter() - start_time) * 1000
            log.exception(
                "http.request.error",
                duration_ms=round(duration_ms, 2),
                status_code=500,
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Add request ID to response headers
        response.headers[self.header_name] = request_id

        if self.log_requests:
            # Log request completion with timing
            log_method = log.info if response.status_code < 400 else log.warning
            log_method(
                "http.request.complete",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

        return response  # type: ignore[no-any-return]

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check common proxy headers
        for header in ("X-Forwarded-For", "X-Real-IP", "CF-Connecting-IP"):
            if value := request.headers.get(header):
                # X-Forwarded-For can be comma-separated; take first
                return str(value.split(",")[0].strip())

        # Fall back to direct connection
        if request.client:
            return str(request.client.host)
        return "unknown"


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """
    Lightweight middleware that only adds timing without full logging.

    Use this if you want timing headers but handle logging elsewhere.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        return response  # type: ignore[no-any-return]
