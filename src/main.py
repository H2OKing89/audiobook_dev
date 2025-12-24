import asyncio
import contextlib
import ipaddress
import os
import re
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.config import load_config  # add import for config
from src.db import save_request  # switch to persistent DB store
from src.http_client import AsyncHttpClient, close_default_client
from src.logging_setup import clear_contextvars, configure_logging, get_logger
from src.metadata import fetch_metadata
from src.metadata_coordinator import MetadataCoordinator
from src.notify.discord import send_discord
from src.notify.gotify import send_gotify
from src.notify.ntfy import send_ntfy
from src.notify.pushover import send_pushover
from src.request_id_middleware import RequestIdMiddleware
from src.security import (
    RateLimitExceeded,
    check_endpoint_authorization,
    get_client_ip,
    get_csp_header,
    rate_limit_exceeded_handler,
    rate_limit_token_generation,
)
from src.token_gen import generate_token
from src.webui import router as webui_router  # add web UI router import


# Configure structured logging FIRST, before anything else
configure_logging()
log = get_logger(__name__)

load_dotenv()

# Load configuration
config = load_config()
server_cfg = config.get("server", {})
autobrr_endpoint = server_cfg.get("autobrr_webhook_endpoint", "/webhook")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown.

    Creates shared resources on startup and cleans them up on shutdown.
    This replaces the deprecated @app.on_event("startup") pattern.
    """
    # Startup: Initialize shared HTTP client and metadata coordinator
    app.state.http_client = AsyncHttpClient()
    app.state.metadata_coordinator = MetadataCoordinator()
    log.info("app.startup", component="http_client", status="initialized")
    log.info("app.startup", component="metadata_coordinator", status="initialized")

    # Start the metadata worker
    app.state.metadata_worker_task = asyncio.create_task(_metadata_worker_loop(app))
    app.state.metadata_worker_running = True
    log.info("app.startup.complete", worker="metadata_queue", queue_maxsize=metadata_queue.maxsize)

    yield  # App runs here

    # Shutdown: Clean up resources
    log.info("app.shutdown.start")

    # Cancel metadata worker
    app.state.metadata_worker_running = False
    if hasattr(app.state, "metadata_worker_task"):
        app.state.metadata_worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await app.state.metadata_worker_task

    # Close the shared HTTP client (releases connection pool)
    if hasattr(app.state, "http_client") and app.state.http_client:
        await app.state.http_client.aclose()
        log.info("app.shutdown", component="http_client", status="closed")

    # Also close any default client that may have been created
    await close_default_client()
    log.info("app.shutdown.complete")


app = FastAPI(
    title="Audiobook Approval Service",
    description="A secure audiobook approval workflow with notifications",
    version="1.0.0",
    lifespan=lifespan,
)

# Global metadata processing queue
# Increase queue size to avoid transient test flakiness under heavy test load
metadata_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)  # Allow up to 1000 pending requests

# Add HTTPS enforcement middleware (must be first)
security_config = config.get("security", {})
if security_config.get("force_https", False):
    from src.security import HTTPSRedirectMiddleware

    app.add_middleware(HTTPSRedirectMiddleware, force_https=True)

# Add CORS middleware with secure defaults
app.add_middleware(
    CORSMiddleware,
    allow_origins=[server_cfg.get("base_url", "*")],  # Restrict origins to base_url if set, otherwise allow all
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-Request-ID", "X-API-Key", "Content-Type"],
    expose_headers=["X-Request-ID"],
)


# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = get_csp_header()
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Add endpoint authorization middleware
@app.middleware("http")
async def endpoint_authorization_middleware(request: Request, call_next):
    # Check if the endpoint requires authorization
    auth_response = await check_endpoint_authorization(request)
    if auth_response:
        return auth_response

    # If authorization passes, continue with the request
    response = await call_next(request)
    return response


@app.exception_handler(429)
async def too_many_requests_handler(request: Request, exc: RateLimitExceeded):
    return await rate_limit_exceeded_handler(request, exc)


app.include_router(webui_router)  # mount web UI routes

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# Queue status endpoint for monitoring (internal use only)
@app.get("/queue/status")
async def queue_status(request: Request):
    """Get current queue status for monitoring - INTERNAL USE ONLY"""
    # Check if request is from local network or has API key
    client_ip = get_client_ip(request)

    # Define private/internal network ranges
    private_networks = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),  # IPv4 loopback
        ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ]

    # Get additional allowed IPs from environment (comma-separated)
    extra_allowed = os.getenv("INTERNAL_ALLOWED_IPS", "").strip()
    allowed_ips = {ip.strip() for ip in extra_allowed.split(",") if ip.strip()}

    # Check if IP is internal/allowed
    is_local = False
    if client_ip in ("localhost", "::1"):
        is_local = True
    else:
        try:
            ip_obj = ipaddress.ip_address(client_ip)
            is_local = any(ip_obj in network for network in private_networks) or client_ip in allowed_ips
        except ValueError:
            # Invalid IP format - treat as external
            is_local = False

    # Check for API key (optional additional security)
    api_key = request.headers.get("X-API-Key")
    internal_api_key = os.getenv("INTERNAL_API_KEY")  # Set this for additional security

    if not is_local and (not internal_api_key or api_key != internal_api_key):
        log.warning("queue.status.unauthorized", client_ip=client_ip)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied - internal endpoint")

    worker_running = getattr(request.app.state, "metadata_worker_running", False)
    coordinator = getattr(request.app.state, "metadata_coordinator", None)

    return {
        "queue_size": metadata_queue.qsize(),
        "queue_maxsize": metadata_queue.maxsize,
        "queue_full": metadata_queue.full(),
        "worker_running": worker_running,
        "coordinator_initialized": coordinator is not None,
        "timestamp": time.time(),
    }


def _create_fallback_metadata(payload: dict[str, Any], token: str, error: Exception) -> dict[str, Any]:
    """Create fallback metadata when all metadata sources fail.

    Args:
        payload: The webhook payload
        token: Request token for logging context
        error: The original error that triggered fallback

    Returns:
        Dict containing fallback metadata
    """
    name = payload.get("name", "Unknown Title")
    title = name
    # Remove trailing format tags like [English / m4b]
    if re.search(r"\[[A-Z0-9]+\]$", name):
        title = re.sub(r"\s*\[[A-Z0-9]+\]$", "", name)

    metadata = {
        "title": title,
        "author": "Unknown Author",
        "asin": "B000000000",
        "description": f"Fallback metadata for {title}",
        "cover": "",
        "publisher": "Unknown Publisher",
        "publishedYear": "",
        "duration": 0,
        "narrator": "Unknown Narrator",
        "series": None,
        "genres": None,
        "tags": None,
        "language": "English",
        "rating": None,
        "abridged": False,
        "source": "fallback",
        "workflow_path": "fallback",
    }

    log.warning("metadata.fallback", token=token, title=title, error=str(error))
    return metadata


# Add request ID middleware for correlation (replaces manual request_id handling)
app.add_middleware(RequestIdMiddleware, log_requests=True)


@app.post(autobrr_endpoint)
async def webhook(request: Request):
    """Webhook endpoint that enqueues requests for background processing"""
    # Get client IP for rate limiting
    client_ip = get_client_ip(request)

    # Rate limit token generation
    if not rate_limit_token_generation(client_ip):
        log.warning("webhook.rate_limit_exceeded", client_ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests. Please try again later."
        )

    # Validate Autobrr token
    autobrr_token = os.getenv("AUTOBRR_TOKEN")
    header_token = request.headers.get("X-Autobrr-Token")
    if autobrr_token and header_token != autobrr_token:
        log.warning("webhook.invalid_token", client_ip=client_ip)
        request_id = getattr(request.state, "request_id", "-")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid Autobrr token (Request ID: {request_id})"
        )

    payload = await request.json()

    # Validate payload has minimum required fields
    required_fields = ["name", "url", "download_url"]
    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
        log.warning("webhook.missing_fields", missing_fields=missing_fields)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing required fields: {', '.join(missing_fields)}"
        )

    # Generate one-time-use token for this request
    token = generate_token()

    # Bind only a fingerprint (last 4 chars) to context - not the full token
    token_fingerprint = token[-4:] if len(token) > 4 else token

    log.info("webhook.received", name=payload.get("name"), url=payload.get("url"), token_id=token_fingerprint)

    try:
        # Get coordinator from app state (initialized by lifespan handler)
        coordinator = request.app.state.metadata_coordinator

        metadata = None
        last_error: Exception | None = None

        # Try 1: Compatibility wrapper (tests often patch fetch_metadata)
        try:
            metadata = await fetch_metadata(payload)
            if metadata:
                log.info("metadata.fetch.success", source="fetch_metadata_wrapper")
                metadata = await coordinator.get_enhanced_metadata(metadata)
        except ValueError as e:
            # Expected when fetch_metadata returns None or finds no metadata
            log.debug("metadata.fetch.no_result", source="fetch_metadata", reason=str(e))
            last_error = e
        except Exception as e:
            # Unexpected exceptions from fetch_metadata - log and continue to next method
            log.exception("metadata.fetch.error", source="fetch_metadata")
            last_error = e

        # Try 2: Coordinator async workflow
        if not metadata:
            try:
                metadata = await coordinator.get_metadata_from_webhook(payload)
                if metadata:
                    metadata = await coordinator.get_enhanced_metadata(metadata)
                    log.info("metadata.fetch.success", source="coordinator")
            except ValueError as e:
                # Expected when coordinator finds no metadata
                log.debug("metadata.fetch.no_result", source="coordinator", reason=str(e))
                last_error = e
            except Exception as e:
                # Network errors or other issues from coordinator
                log.exception("metadata.fetch.error", source="coordinator")
                last_error = e

        # Try 3: Fallback metadata
        if not metadata:
            metadata = _create_fallback_metadata(
                payload, token, last_error or Exception("No metadata sources available")
            )

        # Process notifications synchronously and return a summary
        summary = await process_metadata_and_notify(token, metadata, payload)

        # Build response message based on notification outcomes
        notifications_sent = summary.get("notifications_sent", 0)
        notification_errors = summary.get("notification_errors", [])

        if notification_errors:
            if notifications_sent > 0:
                message = "Webhook received, but some notifications failed."
            else:
                message = "Webhook received but notification delivery failed."
        elif notifications_sent > 0:
            message = "Webhook received and notifications sent."
        else:
            message = "Webhook received and queued for processing"

        return {
            "message": message,
            "token": token,
            "queue_size": metadata_queue.qsize(),
            "notifications_sent": notifications_sent,
            "notification_errors": notification_errors,
        }

    except asyncio.QueueFull:
        log.error("webhook.queue_full", queue_size=metadata_queue.qsize())
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server is busy processing other requests. Please try again later.",
        ) from None


async def _metadata_worker_loop(app: FastAPI) -> None:
    """Background worker loop to process metadata requests sequentially.

    This worker is started by the lifespan handler and uses app.state
    for the coordinator and running flag.
    """
    log.info("worker.started", worker="metadata_queue")

    while getattr(app.state, "metadata_worker_running", False):
        try:
            # Get next request from queue with timeout to check running flag
            try:
                request_data = await asyncio.wait_for(metadata_queue.get(), timeout=1.0)
            except TimeoutError:
                continue  # Check running flag again

            token = request_data["token"]
            payload = request_data["payload"]
            timestamp = request_data["timestamp"]

            wait_time = time.time() - timestamp

            # Clear stale context but don't bind token - use fingerprint only where needed
            clear_contextvars()
            token_fingerprint = token[-4:] if len(token) > 4 else token

            log.info("worker.processing", wait_time_s=round(wait_time, 1), token_id=token_fingerprint)

            # Get coordinator from app state
            coordinator = app.state.metadata_coordinator

            # Process metadata using shared coordinator
            try:
                metadata = await coordinator.get_metadata_from_webhook(payload)
                if metadata:
                    # Enhance metadata with additional information
                    metadata = await coordinator.get_enhanced_metadata(metadata)
                    log.info("worker.metadata.success")
                else:
                    raise ValueError("No metadata found from any source")

            except Exception as e:
                log.exception("worker.metadata.failed")
                # Use helper function to create fallback metadata
                metadata = _create_fallback_metadata(payload, token, e)

            # Continue with the rest of the processing (notifications, etc.)
            await process_metadata_and_notify(token, metadata, payload)

            # Mark task as done
            metadata_queue.task_done()

        except asyncio.CancelledError:
            log.info("worker.cancelled")
            break
        except Exception as e:
            log.error("worker.error", error=str(e))
            # Mark task as done even on error to prevent queue blocking
            with contextlib.suppress(ValueError):
                metadata_queue.task_done()


async def process_metadata_and_notify(token: str, metadata: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Process metadata and send notifications (simplified synchronous version)

    Returns a summary dict: {"notifications_sent": int, "notification_errors": list}
    """
    # Use token fingerprint for logging (never log full token)
    token_fingerprint = token[-4:] if len(token) > 4 else token

    # Persist token, metadata, and original payload
    save_request(token, metadata, payload)
    log.info("request.saved", title=metadata.get("title"), token_id=token_fingerprint)

    # Get notification settings
    base_url = server_cfg.get("base_url")
    notif_cfg = config.get("notifications", {})

    # Get environment variables for notification services
    pushover_token = os.getenv("PUSHOVER_TOKEN")
    pushover_user = os.getenv("PUSHOVER_USER")
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
    gotify_url = os.getenv("GOTIFY_URL")
    gotify_token = os.getenv("GOTIFY_TOKEN")
    ntfy_cfg = notif_cfg.get("ntfy", {})
    ntfy_enabled = ntfy_cfg.get("enabled", False)
    ntfy_topic = ntfy_cfg.get("topic")
    ntfy_url = ntfy_cfg.get("url", "https://ntfy.sh")
    ntfy_user = os.getenv("NTFY_USER")
    ntfy_password = os.getenv("NTFY_PASS")

    # Allow tests or CI to skip external notifications to avoid spamming/ratelimiting
    if os.getenv("DISABLE_WEBHOOK_NOTIFICATIONS") == "1":
        log.info("notify.skipped", reason="DISABLE_WEBHOOK_NOTIFICATIONS")
        return {"notifications_sent": 0, "notification_errors": []}

    notifications_sent = 0
    notification_errors = []

    # Send Pushover notification
    pushover_cfg = notif_cfg.get("pushover", {})
    pushover_enabled = pushover_cfg.get("enabled", False)
    if pushover_enabled and pushover_token and pushover_user:
        try:
            status_code, response = send_pushover(
                metadata,
                payload,
                token,
                base_url,
                pushover_user,
                pushover_token,
                sound=pushover_cfg.get("sound"),
                html=pushover_cfg.get("html"),
                priority=pushover_cfg.get("priority"),
            )
            if status_code >= 200 and status_code < 300:
                log.info("notify.success", channel="pushover", status_code=status_code)
                notifications_sent += 1
            else:
                log.error("notify.failed", channel="pushover", status_code=status_code)
                notification_errors.append(f"Pushover: HTTP {status_code}")
        except Exception as e:
            log.error("notify.error", channel="pushover", error=str(e))
            notification_errors.append(f"Pushover: {e}")
    # Send Gotify notification
    if gotify_url and gotify_token:
        try:
            status_code, response = send_gotify(metadata, payload, token, base_url, gotify_url, gotify_token)
            if status_code >= 200 and status_code < 300:
                log.info("notify.success", channel="gotify", status_code=status_code)
                notifications_sent += 1
            else:
                log.error("notify.failed", channel="gotify", status_code=status_code)
                notification_errors.append(f"Gotify: HTTP {status_code}")
        except Exception as e:
            log.error("notify.error", channel="gotify", error=str(e))
            notification_errors.append(f"Gotify: {e}")

    # Send Discord notification
    if discord_webhook:
        try:
            status_code, response = send_discord(metadata, payload, token, base_url, discord_webhook)
            if status_code >= 200 and status_code < 300:
                log.info("notify.success", channel="discord", status_code=status_code)
                notifications_sent += 1
            else:
                log.error("notify.failed", channel="discord", status_code=status_code)
                notification_errors.append(f"Discord: HTTP {status_code}")
        except Exception as e:
            log.error("notify.error", channel="discord", error=str(e))
            notification_errors.append(f"Discord: {e}")

    # Send ntfy notification
    if ntfy_enabled and ntfy_topic:
        try:
            status_code, response = send_ntfy(
                metadata, payload, token, base_url, ntfy_topic, ntfy_url, ntfy_user=ntfy_user, ntfy_pass=ntfy_password
            )
            if status_code >= 200 and status_code < 300:
                log.info("notify.success", channel="ntfy", status_code=status_code)
                notifications_sent += 1
            else:
                log.error("notify.failed", channel="ntfy", status_code=status_code)
                notification_errors.append(f"ntfy: HTTP {status_code}")
        except Exception as e:
            log.error("notify.error", channel="ntfy", error=str(e))
            notification_errors.append(f"ntfy: {e}")

    # Log summary
    if notifications_sent > 0:
        log.info("notify.summary", sent=notifications_sent)
    if notification_errors:
        log.warning("notify.summary.errors", errors=notification_errors)

    # Return a summary for callers
    return {"notifications_sent": notifications_sent, "notification_errors": notification_errors}


# Commented out legacy handlers; using webui router instead


# Public health check endpoint (safe for monitoring)
@app.get("/health")
async def health_check():
    """Basic health check - safe for public access"""
    return {"status": "healthy", "service": "audiobook-approval-service", "timestamp": time.time()}


# CSS test endpoint for developers (not for production)
@app.get("/css-test", response_class=HTMLResponse)
async def css_test():
    """Test page for CSS light/dark mode - for development only"""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Light/Dark Mode CSS Test</title>
    <link rel="stylesheet" href="/static/css/pages/approval.css">
    <style>
        .test-container {
            padding: 20px;
            margin: 20px;
            border: 2px solid var(--border-primary);
            background: var(--bg-secondary);
            color: var(--text-primary);
            border-radius: 8px;
        }
        .test-section {
            margin: 10px 0;
            padding: 10px;
            background: var(--bg-tertiary);
            border-left: 3px solid var(--accent-cyan);
        }
        .color-swatch {
            display: inline-block;
            width: 20px;
            height: 20px;
            margin-right: 10px;
            border: 1px solid var(--border-secondary);
        }
        .mode-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px;
            background: var(--bg-panel);
            border: 1px solid var(--border-primary);
            border-radius: 5px;
            color: var(--text-accent);
            font-weight: bold;
        }
    </style>
</head>
<body class="approval-page">
    <div class="mode-indicator">
        Color Scheme: <span id="scheme">Auto</span>
    </div>

    <div class="test-container">
        <h1 style="color: var(--text-accent);">🎨 Light/Dark Mode CSS Test</h1>
        <p>This page tests the CSS variables for both light and dark modes.</p>

        <div class="test-section">
            <h3>Background Colors</h3>
            <p><span class="color-swatch" style="background: var(--bg-primary);"></span>Primary Background</p>
            <p><span class="color-swatch" style="background: var(--bg-secondary);"></span>Secondary Background</p>
            <p><span class="color-swatch" style="background: var(--bg-tertiary);"></span>Tertiary Background</p>
        </div>

        <div class="test-section">
            <h3>Text Colors</h3>
            <p style="color: var(--text-primary);">Primary Text Color</p>
            <p style="color: var(--text-secondary);">Secondary Text Color</p>
            <p style="color: var(--text-muted);">Muted Text Color</p>
            <p style="color: var(--text-accent);">Accent Text Color</p>
            <p style="color: var(--text-author);">Author Text Color</p>
            <p style="color: var(--text-narrator);">Narrator Text Color</p>
        </div>

        <div class="test-section">
            <h3>Accent Colors</h3>
            <p><span class="color-swatch" style="background: var(--accent-cyan);"></span>Cyan Accent</p>
            <p><span class="color-swatch" style="background: var(--accent-pink);"></span>Pink Accent</p>
            <p><span class="color-swatch" style="background: var(--accent-green);"></span>Green Accent</p>
            <p><span class="color-swatch" style="background: var(--accent-yellow);"></span>Yellow Accent</p>
            <p><span class="color-swatch" style="background: var(--accent-red);"></span>Red Accent</p>
        </div>

        <div class="test-section">
            <h3>Instructions</h3>
            <p>To test the light/dark mode functionality:</p>
            <ol>
                <li>Open this page in a browser</li>
                <li>Change your system's color scheme preference (dark/light mode)</li>
                <li>Refresh the page or toggle the preference</li>
                <li>Observe how the colors adapt automatically</li>
            </ol>
            <p><strong>Dark Mode:</strong> Should show dark backgrounds with bright text and cyan accents</p>
            <p><strong>Light Mode:</strong> Should show light backgrounds with dark text and blue accents</p>
        </div>
    </div>

    <script>
        // Detect and display current color scheme
        function updateSchemeIndicator() {
            const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const isLight = window.matchMedia('(prefers-color-scheme: light)').matches;
            const schemeElement = document.getElementById('scheme');

            if (isDark) {
                schemeElement.textContent = 'Dark';
            } else if (isLight) {
                schemeElement.textContent = 'Light';
            } else {
                schemeElement.textContent = 'Auto';
            }
        }

        // Update on load
        updateSchemeIndicator();

        // Listen for changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updateSchemeIndicator);
        window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', updateSchemeIndicator);
    </script>
</body>
</html>"""


# Rejection CSS test endpoint for developers
@app.get("/rejection-css-test", response_class=HTMLResponse)
async def rejection_css_test():
    """Test page for rejection CSS light/dark mode - for development only"""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rejection Light/Dark Mode CSS Test</title>
    <link rel="stylesheet" href="/static/css/pages/rejection.css">
    <style>
        .test-container {
            padding: 20px;
            margin: 20px;
            border: 2px solid var(--border-error);
            background: var(--bg-secondary);
            color: var(--text-primary);
            border-radius: 8px;
        }
        .test-section {
            margin: 10px 0;
            padding: 10px;
            background: var(--bg-tertiary);
            border-left: 3px solid var(--error-primary);
        }
        .color-swatch {
            display: inline-block;
            width: 20px;
            height: 20px;
            margin-right: 10px;
            border: 1px solid var(--border-secondary);
        }
        .mode-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px;
            background: var(--bg-panel);
            border: 1px solid var(--border-error);
            border-radius: 5px;
            color: var(--error-primary);
            font-weight: bold;
        }
    </style>
</head>
<body class="rejection-page">
    <div class="mode-indicator">
        Color Scheme: <span id="scheme">Auto</span>
    </div>

    <div class="test-container">
        <h1 style="color: var(--error-primary);">🚫 Rejection Light/Dark Mode CSS Test</h1>
        <p>This page tests the CSS variables for the rejection page in both light and dark modes.</p>

        <div class="test-section">
            <h3>Background Colors</h3>
            <p><span class="color-swatch" style="background: var(--bg-primary);"></span>Primary Background</p>
            <p><span class="color-swatch" style="background: var(--bg-secondary);"></span>Secondary Background</p>
            <p><span class="color-swatch" style="background: var(--bg-tertiary);"></span>Tertiary Background</p>
        </div>

        <div class="test-section">
            <h3>Text Colors</h3>
            <p style="color: var(--text-primary);">Primary Text Color</p>
            <p style="color: var(--text-secondary);">Secondary Text Color</p>
            <p style="color: var(--text-muted);">Muted Text Color</p>
            <p style="color: var(--text-footer);">Footer Text Color</p>
        </div>

        <div class="test-section">
            <h3>Error & Accent Colors</h3>
            <p><span class="color-swatch" style="background: var(--error-primary);"></span>Error Primary</p>
            <p><span class="color-swatch" style="background: var(--error-secondary);"></span>Error Secondary</p>
            <p><span class="color-swatch" style="background: var(--accent-cyan);"></span>Cyan Accent</p>
            <p><span class="color-swatch" style="background: var(--accent-green);"></span>Green Accent</p>
            <p><span class="color-swatch" style="background: var(--accent-yellow);"></span>Yellow Accent</p>
            <p><span class="color-swatch" style="background: var(--accent-pink);"></span>Pink Accent</p>
        </div>

        <div class="test-section">
            <h3>Instructions</h3>
            <p>To test the light/dark mode functionality:</p>
            <ol>
                <li>Open this page in a browser</li>
                <li>Change your system's color scheme preference (dark/light mode)</li>
                <li>Refresh the page or toggle the preference</li>
                <li>Observe how the colors adapt automatically</li>
            </ol>
            <p><strong>Dark Mode:</strong> Should show dark backgrounds with red errors and bright accents</p>
            <p><strong>Light Mode:</strong> Should show light backgrounds with darker red errors and muted accents</p>
        </div>
    </div>

    <script>
        // Detect and display current color scheme
        function updateSchemeIndicator() {
            const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const isLight = window.matchMedia('(prefers-color-scheme: light)').matches;
            const schemeElement = document.getElementById('scheme');

            if (isDark) {
                schemeElement.textContent = 'Dark';
            } else if (isLight) {
                schemeElement.textContent = 'Light';
            } else {
                schemeElement.textContent = 'Auto';
            }
        }

        // Update on load
        updateSchemeIndicator();

        // Listen for changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updateSchemeIndicator);
        window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', updateSchemeIndicator);
    </script>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn

    server_config = load_config().get("server", {})
    uvicorn.run(
        "src.main:app",
        host=server_config.get("host", "0.0.0.0"),
        port=server_config.get("port", 8000),
        reload=server_config.get("reload", True),
    )
