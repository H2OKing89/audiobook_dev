"""
Centralized structured logging configuration for audiobook_dev.

This module configures structlog + stdlib logging for the entire application.
Call configure_logging() once at process start, before creating the FastAPI app.

Environment variables:
    LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
    LOG_FORMAT: json, console (default: json in production, console in dev)
    LOG_FILE: Path to log file (optional, default: logs/audiobook.log)

Usage:
    from src.logging_setup import configure_logging, get_logger

    configure_logging()
    log = get_logger(__name__)

    log.info("event.name", key="value", another_key=123)
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog


if TYPE_CHECKING:
    from structlog.typing import Processor

# Sensitive keys to redact from logs (case-insensitive matching)
REDACT_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "authorization",
        "auth",
        "cookie",
        "mam_id",
        "session",
        "credential",
        "private_key",
        "access_token",
        "refresh_token",
    }
)

# Global flag to prevent double-configuration
_configured = False


def _should_redact(key: str) -> bool:
    """Check if a key should be redacted based on sensitive patterns."""
    key_lower = key.lower()
    return any(sensitive in key_lower for sensitive in REDACT_KEYS)


def _redact_sensitive_data(
    _logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    Processor that redacts sensitive values from log events.

    Replaces values of keys matching REDACT_KEYS with '***REDACTED***'.
    """
    for key in list(event_dict.keys()):
        if _should_redact(key):
            value = event_dict[key]
            if value is not None:
                # Only show suffix for longer values (8+ chars) to avoid revealing too much
                if isinstance(value, str) and len(value) >= 8:
                    event_dict[key] = f"***{value[-4:]}"
                else:
                    event_dict[key] = "***REDACTED***"
    return event_dict  # type: ignore[return-value]


def _add_service_context(
    _logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add service-level context to all log events."""
    event_dict.setdefault("service", "audiobook_dev")
    return event_dict  # type: ignore[return-value]


def _is_dev_environment() -> bool:
    """Detect if running in development environment."""
    # Check common dev indicators
    if os.getenv("LOG_FORMAT", "").lower() == "console":
        return True
    if os.getenv("ENVIRONMENT", "").lower() in ("dev", "development", "local"):
        return True
    if os.getenv("DEBUG", "").lower() in ("1", "true", "yes"):
        return True
    # Check if running under pytest
    return "pytest" in sys.modules


def configure_logging(
    *,
    log_level: str | None = None,
    log_format: str | None = None,
    log_file: str | Path | None = None,
    force: bool = False,
) -> None:
    """
    Configure structured logging for the application.

    Call exactly once at process start, before creating the FastAPI app.
    Subsequent calls are no-ops unless force=True.

    Args:
        log_level: Override LOG_LEVEL env var (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Override LOG_FORMAT env var (json, console)
        log_file: Override LOG_FILE env var (path to log file)
        force: If True, reconfigure even if already configured
    """
    global _configured  # noqa: PLW0603
    if _configured and not force:
        return

    # Resolve configuration from args -> env -> defaults
    level_str = (log_level or os.getenv("LOG_LEVEL") or "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)

    format_str = log_format or os.getenv("LOG_FORMAT") or ""
    if not format_str:
        format_str = "console" if _is_dev_environment() else "json"
    use_json = format_str.lower() == "json"

    file_path_str = log_file or os.getenv("LOG_FILE") or "logs/audiobook.log"
    file_path = Path(file_path_str)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Configure stdlib logging (handles third-party libs) ---
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    # File handler with rotation
    file_handler: logging.Handler
    rotation_type = os.getenv("LOG_ROTATION", "size").lower()
    if rotation_type == "midnight":
        file_handler = TimedRotatingFileHandler(
            filename=file_path,
            when="midnight",
            backupCount=int(os.getenv("LOG_BACKUP_COUNT", "7")),
        )
    else:
        file_handler = RotatingFileHandler(
            filename=file_path,
            maxBytes=int(os.getenv("LOG_MAX_SIZE_MB", "10")) * 1024 * 1024,
            backupCount=int(os.getenv("LOG_BACKUP_COUNT", "5")),
        )

    # For stdlib handler, use simple format - structlog handles the rest
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(console_handler)

    # Quiet down noisy third-party loggers
    # SECURITY: Keep httpx/httpcore at WARNING to prevent credential leakage
    for noisy_logger in (
        "httpx",
        "httpcore",
        "httpcore.http2",
        "httpcore.connection",
        "hpack",
        "urllib3",
        "asyncio",
    ):
        logging.getLogger(noisy_logger).setLevel(
            max(logging.WARNING, level)  # At least WARNING, or higher if app level is higher
        )

    # Uvicorn loggers - keep them somewhat quiet but usable
    logging.getLogger("uvicorn.error").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Access logs can be noisy

    # --- Configure structlog ---
    # Shared processors for all renderers
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        _add_service_context,  # type: ignore[list-item]
        _redact_sensitive_data,  # type: ignore[list-item]
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if use_json:
        # JSON output for production (Loki/ELK/Datadog)
        processors: list[Processor] = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(serializer=_json_serializer),
        ]
    else:
        # Pretty console output for development
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            ),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _configured = True

    # Log that we're configured (using the new system!)
    # Include process identity for debugging multi-worker scenarios
    log = structlog.get_logger("logging_setup")
    log.info(
        "logging.configured",
        level=level_str,
        format=format_str,
        log_file=str(file_path),
        rotation=rotation_type,
        pid=os.getpid(),
        hostname=_get_hostname(),
        version=_get_version(),
    )


def _get_hostname() -> str:
    """Get hostname for log identification."""
    import socket

    try:
        return socket.gethostname()
    except Exception:
        return "unknown"


def _get_version() -> str:
    """Get application version (git sha or package version)."""
    # Try git first
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=1,
            cwd=Path(__file__).parent.parent,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        # Git command failed or not in a git repo, silently fall through to package version
        pass

    # Fall back to package version
    try:
        from importlib.metadata import version

        return version("audiobook_dev")
    except Exception:
        return "dev"


def _json_serializer(obj: Any, **_kwargs: Any) -> str:
    """JSON serializer using orjson for speed."""
    try:
        import orjson

        result: bytes = orjson.dumps(obj, default=_json_default)
        return result.decode("utf-8")
    except ImportError:
        import json

        return json.dumps(obj, default=str)


def _json_default(obj: Any) -> Any:
    """Default handler for JSON serialization of non-standard types."""
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Ensures logging is configured before returning the logger.

    Args:
        name: Logger name (typically __name__). If None, uses root logger.

    Returns:
        A structlog BoundLogger instance.

    Example:
        log = get_logger(__name__)
        log.info("user.login", user_id=123, ip="192.168.1.1")
    """
    if not _configured:
        configure_logging()
    return structlog.get_logger(name)  # type: ignore[no-any-return]


def bind_contextvars(**kwargs: Any) -> None:
    """
    Bind key-value pairs to the current context.

    These values will be included in all subsequent log messages
    within the current async context (or thread).

    Useful for binding request_id, user_id, etc. at the start of a request.

    Example:
        bind_contextvars(request_id="abc123", user_id=456)
        log.info("some.event")  # Will include request_id and user_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_contextvars() -> None:
    """
    Clear all context variables.

    Call at the start of a new request/task to ensure clean context.
    """
    structlog.contextvars.clear_contextvars()


def unbind_contextvars(*keys: str) -> None:
    """
    Remove specific keys from the current context.

    Args:
        *keys: Keys to remove from context.
    """
    structlog.contextvars.unbind_contextvars(*keys)
