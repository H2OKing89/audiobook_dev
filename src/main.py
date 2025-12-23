import asyncio
import contextlib
import contextvars
import ipaddress
import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.config import load_config  # add import for config
from src.db import save_request  # switch to persistent DB store
from src.metadata import fetch_metadata
from src.metadata_coordinator import MetadataCoordinator
from src.notify.discord import send_discord
from src.notify.gotify import send_gotify
from src.notify.ntfy import send_ntfy
from src.notify.pushover import send_pushover
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


load_dotenv()

# Load configuration
config = load_config()
server_cfg = config.get("server", {})
autobrr_endpoint = server_cfg.get("autobrr_webhook_endpoint", "/webhook")

# Context variable for request ID
request_id_ctx_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Logging filter to inject request_id into log records."""

    def filter(self, record):
        record.request_id = request_id_ctx_var.get() or "-"
        return True


# Dynamic logging configuration from config.yaml
log_cfg = config.get("logging", {})
level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
# Create a format that includes request_id without duplicating timestamp
base_fmt = log_cfg.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# Replace the base format to include request_id in the right place
fmt = base_fmt.replace("%(asctime)s", "%(asctime)s - %(request_id)s")
log_path = Path(log_cfg.get("file", "log/audiobook_requests.log"))
# Ensure log directory exists
log_path.parent.mkdir(parents=True, exist_ok=True)

# Create logger and set level
logger = logging.getLogger()
logger.setLevel(level)
formatter = logging.Formatter(fmt)

rotation = log_cfg.get("rotation")
if rotation == "midnight":
    from logging.handlers import TimedRotatingFileHandler

    file_handler = TimedRotatingFileHandler(
        filename=log_path, when="midnight", backupCount=log_cfg.get("backup_count", 5)
    )
else:
    from logging.handlers import RotatingFileHandler

    file_handler = RotatingFileHandler(  # type: ignore[assignment]
        filename=log_path,
        maxBytes=log_cfg.get("max_size", 10) * 1024 * 1024,
        backupCount=log_cfg.get("backup_count", 5),
    )
file_handler.setFormatter(formatter)
file_handler.addFilter(RequestIdFilter())

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.addFilter(RequestIdFilter())

# Apply handlers
logger.handlers.clear()
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# SECURITY: Disable debug logging for httpx/httpcore to prevent cookie/token leakage
# These libraries log full HTTP headers including sensitive cookies at DEBUG level
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpcore.http2").setLevel(logging.WARNING)
logging.getLogger("httpcore.connection").setLevel(logging.WARNING)
logging.getLogger("hpack").setLevel(logging.WARNING)

app = FastAPI(
    title="Audiobook Approval Service",
    description="A secure audiobook approval workflow with notifications",
    version="1.0.0",
)

# Global metadata processing queue
# Increase queue size to avoid transient test flakiness under heavy test load
metadata_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)  # Allow up to 1000 pending requests
metadata_worker_running = False
metadata_coordinator = None  # Single shared coordinator instance

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


# Add startup event to initialize worker
@app.on_event("startup")
async def startup_event():
    """Initialize the metadata worker on app startup"""
    await init_metadata_worker()
    logging.info("🚀 Audiobook service started with queue-based processing")


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
        logging.warning(f"Unauthorized queue status access attempt from {client_ip}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied - internal endpoint")

    return {
        "queue_size": metadata_queue.qsize(),
        "queue_maxsize": metadata_queue.maxsize,
        "queue_full": metadata_queue.full(),
        "worker_running": metadata_worker_running,
        "coordinator_initialized": metadata_coordinator is not None,
        "timestamp": time.time(),
    }


def _create_fallback_metadata(payload: dict[str, Any], log_prefix: str, error: Exception) -> dict[str, Any]:
    """Create fallback metadata when all metadata sources fail.

    Args:
        payload: The webhook payload
        log_prefix: Log prefix for the request
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

    logging.warning(log_prefix + f"Using fallback metadata due to error: {error}")
    return metadata


# Middleware to set request_id from path token or generate new one
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    # Extract token from path parameters if available
    token = None
    try:
        token = request.path_params.get("token")
    except Exception:
        token = None
    if not token:
        # Fallback to header or generate new UUID
        token = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    # Store in contextvar
    request_id_ctx_var.set(token)
    # Get client IP address using centralized function
    client_ip = get_client_ip(request)
    # Log the incoming request with IP and token
    logging.info(f"Incoming request: path={request.url.path} ip={client_ip} token={token}")
    # Proceed with request
    response = await call_next(request)
    # Echo request_id back in response headers
    response.headers["X-Request-ID"] = token
    response.headers["X-Client-IP"] = client_ip
    return response


@app.post(autobrr_endpoint)
async def webhook(request: Request):
    """Webhook endpoint that enqueues requests for background processing"""
    # Get client IP for rate limiting
    client_ip = get_client_ip(request)

    # Rate limit token generation
    if not rate_limit_token_generation(client_ip):
        logging.warning(f"Rate limit exceeded for token generation: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests. Please try again later."
        )

    # Validate Autobrr token
    autobrr_token = os.getenv("AUTOBRR_TOKEN")
    header_token = request.headers.get("X-Autobrr-Token")
    if autobrr_token and header_token != autobrr_token:
        logging.warning(f"Invalid Autobrr token received from {client_ip}")
        request_id = request_id_ctx_var.get() or "-"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid Autobrr token (Request ID: {request_id})"
        )

    payload = await request.json()

    # Validate payload has minimum required fields
    required_fields = ["name", "url", "download_url"]
    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
        logging.warning(f"Missing required fields in payload: {missing_fields}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing required fields: {', '.join(missing_fields)}"
        )

    # Generate one-time-use token for this request
    token = generate_token()
    log_prefix = f"[token={token}] "
    logging.info(log_prefix + f"Received webhook payload: {payload}")

    try:
        # Process request inline (synchronously) to provide immediate feedback in tests
        # Ensure coordinator exists
        global metadata_coordinator  # noqa: PLW0603
        if metadata_coordinator is None:
            metadata_coordinator = MetadataCoordinator()
            logging.info(log_prefix + "Initialized metadata coordinator for inline processing")

        metadata = None
        last_error: Exception | None = None

        # Try 1: Compatibility wrapper (tests often patch fetch_metadata)
        try:
            loop = asyncio.get_running_loop()
            metadata = await loop.run_in_executor(None, fetch_metadata, payload)
            if metadata:
                logging.info(log_prefix + "Metadata obtained from fetch_metadata() wrapper")
                metadata = metadata_coordinator.get_enhanced_metadata(metadata)
        except ValueError as e:
            # Expected when fetch_metadata returns None or finds no metadata
            logging.info(log_prefix + f"fetch_metadata did not provide metadata: {e}")
            last_error = e
        except Exception as e:
            # Unexpected exceptions from fetch_metadata - log and continue to next method
            logging.exception(log_prefix + f"Unexpected error in fetch_metadata: {e}")
            last_error = e

        # Try 2: Coordinator async workflow
        if not metadata:
            try:
                metadata = await metadata_coordinator.get_metadata_from_webhook(payload)
                if metadata:
                    metadata = metadata_coordinator.get_enhanced_metadata(metadata)
                    logging.info(log_prefix + "Metadata obtained from coordinator workflow")
            except ValueError as e:
                # Expected when coordinator finds no metadata
                logging.info(log_prefix + f"Coordinator did not provide metadata: {e}")
                last_error = e
            except Exception as e:
                # Network errors or other issues from coordinator
                logging.exception(log_prefix + f"Coordinator workflow failed: {e}")
                last_error = e

        # Try 3: Fallback metadata
        if not metadata:
            metadata = _create_fallback_metadata(
                payload, log_prefix, last_error or Exception("No metadata sources available")
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

    except asyncio.QueueFull as err:
        logging.error(log_prefix + "Failed to enqueue request - queue is full")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server is busy processing other requests. Please try again later.",
        ) from err


async def init_metadata_worker():
    """Initialize the shared metadata coordinator and start worker if needed"""
    global metadata_coordinator, metadata_worker_running  # noqa: PLW0603

    if metadata_coordinator is None:
        metadata_coordinator = MetadataCoordinator()
        logging.info("Shared metadata coordinator initialized")

    if not metadata_worker_running:
        task = asyncio.create_task(metadata_worker())  # noqa: RUF006, F841
        metadata_worker_running = True
        logging.info("Metadata worker started")


async def metadata_worker():
    """Background worker to process metadata requests sequentially"""
    global metadata_coordinator  # noqa: PLW0603

    logging.info("Metadata worker started - processing requests sequentially")

    while True:
        try:
            # Get next request from queue
            request_data = await metadata_queue.get()

            token = request_data["token"]
            payload = request_data["payload"]
            timestamp = request_data["timestamp"]

            log_prefix = f"[token={token}] "
            wait_time = time.time() - timestamp

            logging.info(log_prefix + f"Processing metadata request (waited {wait_time:.1f}s in queue)")

            # Ensure coordinator exists
            if metadata_coordinator is None:
                metadata_coordinator = MetadataCoordinator()
                logging.info("Created metadata coordinator in worker")

            # Process metadata using shared coordinator
            try:
                metadata = await metadata_coordinator.get_metadata_from_webhook(payload)
                if metadata:
                    # Enhance metadata with additional information
                    metadata = metadata_coordinator.get_enhanced_metadata(metadata)
                    logging.info(log_prefix + "✅ Metadata processed successfully")
                else:
                    raise ValueError("No metadata found from any source")

            except Exception as e:
                logging.exception(log_prefix + f"Metadata fetch failed: {e}")
                # Use helper function to create fallback metadata
                metadata = _create_fallback_metadata(payload, log_prefix, e)

            # Continue with the rest of the processing (notifications, etc.)
            await process_metadata_and_notify(token, metadata, payload)

            # Mark task as done
            metadata_queue.task_done()

        except Exception as e:
            logging.error(f"Error in metadata worker: {e}")
            # Mark task as done even on error to prevent queue blocking
            with contextlib.suppress(ValueError):
                metadata_queue.task_done()


async def process_metadata_and_notify(token: str, metadata: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Process metadata and send notifications (simplified synchronous version)

    Returns a summary dict: {"notifications_sent": int, "notification_errors": list}
    """
    log_prefix = f"[token={token}] "

    # Persist token, metadata, and original payload
    save_request(token, metadata, payload)
    logging.info(log_prefix + f"Saved request with token: {token}")

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
        logging.info(
            log_prefix
            + "DISABLE_WEBHOOK_NOTIFICATIONS is set; skipping notification delivery for webhook-driven processing"
        )
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
                logging.info(log_prefix + "Pushover notification sent successfully.")
                notifications_sent += 1
            else:
                logging.error(log_prefix + f"Pushover notification failed with status {status_code}: {response}")
                notification_errors.append(f"Pushover: HTTP {status_code}")
        except Exception as e:
            logging.error(log_prefix + f"Pushover notification failed: {e}")
            notification_errors.append(f"Pushover: {e}")
    # Send Gotify notification
    if gotify_url and gotify_token:
        try:
            status_code, response = send_gotify(metadata, payload, token, base_url, gotify_url, gotify_token)
            if status_code >= 200 and status_code < 300:
                logging.info(log_prefix + "Gotify notification sent successfully.")
                notifications_sent += 1
            else:
                logging.error(log_prefix + f"Gotify notification failed with status {status_code}: {response}")
                notification_errors.append(f"Gotify: HTTP {status_code}")
        except Exception as e:
            logging.error(log_prefix + f"Gotify notification failed: {e}")
            notification_errors.append(f"Gotify: {e}")

    # Send Discord notification
    if discord_webhook:
        try:
            status_code, response = send_discord(metadata, payload, token, base_url, discord_webhook)
            if status_code >= 200 and status_code < 300:
                logging.info(log_prefix + "Discord notification sent successfully.")
                notifications_sent += 1
            else:
                logging.error(log_prefix + f"Discord notification failed with status {status_code}: {response}")
                notification_errors.append(f"Discord: HTTP {status_code}")
        except Exception as e:
            logging.error(log_prefix + f"Discord notification failed: {e}")
            notification_errors.append(f"Discord: {e}")

    # Send ntfy notification
    if ntfy_enabled and ntfy_topic:
        try:
            status_code, response = send_ntfy(
                metadata, payload, token, base_url, ntfy_topic, ntfy_url, ntfy_user=ntfy_user, ntfy_pass=ntfy_password
            )
            if status_code >= 200 and status_code < 300:
                logging.info(log_prefix + "ntfy notification sent successfully.")
                notifications_sent += 1
            else:
                logging.error(log_prefix + f"ntfy notification failed with status {status_code}: {response}")
                notification_errors.append(f"ntfy: HTTP {status_code}")
        except Exception as e:
            logging.error(log_prefix + f"ntfy notification failed: {e}")
            notification_errors.append(f"ntfy: {e}")

    # Log summary
    if notifications_sent > 0:
        logging.info(log_prefix + f"Sent {notifications_sent} notifications successfully")
    if notification_errors:
        logging.warning(log_prefix + f"Notification errors: {'; '.join(notification_errors)}")

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
