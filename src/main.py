from fastapi import FastAPI, HTTPException, Request, Depends, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from src.metadata_coordinator import MetadataCoordinator
from src.token_gen import generate_token, verify_token
from src.notify.pushover import send_pushover
from src.notify.gotify import send_gotify
from src.notify.discord import send_discord
from src.notify.ntfy import send_ntfy
from src.qbittorrent import add_torrent
from src.db import save_request  # switch to persistent DB store
from src.webui import router as webui_router  # add web UI router import
from src.config import load_config  # add import for config
from src.security import require_api_key, rate_limit_token_generation, rate_limit_exceeded_handler, get_csp_header, check_endpoint_authorization, get_client_ip
from src.utils import validate_payload, format_size
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import uuid
import contextvars
from typing import Optional

load_dotenv()

# Load configuration
config = load_config()
server_cfg = config.get('server', {})
autobrr_endpoint = server_cfg.get('autobrr_webhook_endpoint', '/webhook')

# Context variable for request ID
request_id_ctx_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)

class RequestIdFilter(logging.Filter):
    """Logging filter to inject request_id into log records."""
    def filter(self, record):
        record.request_id = request_id_ctx_var.get() or '-'
        return True

# Dynamic logging configuration from config.yaml
log_cfg = config.get('logging', {})
level = getattr(logging, log_cfg.get('level', 'INFO').upper(), logging.INFO)
# Create a format that includes request_id without duplicating timestamp
base_fmt = log_cfg.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Replace the base format to include request_id in the right place
fmt = base_fmt.replace('%(asctime)s', '%(asctime)s - %(request_id)s')
log_path = Path(log_cfg.get('file', 'log/audiobook_requests.log'))
# Ensure log directory exists
log_path.parent.mkdir(parents=True, exist_ok=True)

# Create logger and set level
logger = logging.getLogger()
logger.setLevel(level)
formatter = logging.Formatter(fmt)

rotation = log_cfg.get('rotation')
if rotation == 'midnight':
    from logging.handlers import TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        filename=log_path,
        when='midnight',
        backupCount=log_cfg.get('backup_count', 5)
    )
else:
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        filename=log_path,
        maxBytes=log_cfg.get('max_size', 10) * 1024 * 1024,
        backupCount=log_cfg.get('backup_count', 5)
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

app = FastAPI(
    title="Audiobook Approval Service",
    description="A secure audiobook approval workflow with notifications",
    version="1.0.0"
)

# Add HTTPS enforcement middleware (must be first)
security_config = config.get('security', {})
if security_config.get('force_https', False):
    from src.security import HTTPSRedirectMiddleware
    app.add_middleware(HTTPSRedirectMiddleware, force_https=True)

# Add CORS middleware with secure defaults
app.add_middleware(
    CORSMiddleware,
    allow_origins=[server_cfg.get('base_url', '*')],  # Restrict origins to base_url if set, otherwise allow all
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-Request-ID", "X-API-Key", "Content-Type"],
    expose_headers=["X-Request-ID"]
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

# Exception handler for too many requests
from src.security import RateLimitExceeded  # Ensure this import exists

@app.exception_handler(429)
async def too_many_requests_handler(request: Request, exc: RateLimitExceeded):
    return await rate_limit_exceeded_handler(request, exc)

app.include_router(webui_router)  # mount web UI routes

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Middleware to set request_id from path token or generate new one
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    # Extract token from path parameters if available
    token = None
    try:
        token = request.path_params.get('token')
    except Exception:
        token = None
    if not token:
        # Fallback to header or generate new UUID
        token = request.headers.get('X-Request-ID') or uuid.uuid4().hex
    # Store in contextvar
    request_id_ctx_var.set(token)
    # Get client IP address using centralized function
    client_ip = get_client_ip(request)
    # Log the incoming request with IP and token
    logging.info(f"Incoming request: path={request.url.path} ip={client_ip} token={token}")
    # Proceed with request
    response = await call_next(request)
    # Echo request_id back in response headers
    response.headers['X-Request-ID'] = token
    response.headers['X-Client-IP'] = client_ip
    return response

@app.post(autobrr_endpoint)
async def webhook(request: Request):
    # Get client IP for rate limiting
    client_ip = get_client_ip(request)
    
    # Rate limit token generation
    if not rate_limit_token_generation(client_ip):
        logging.warning(f"Rate limit exceeded for token generation: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later."
        )
    
    # Validate Autobrr token
    autobrr_token = os.getenv('AUTOBRR_TOKEN')
    header_token = request.headers.get('X-Autobrr-Token')
    if autobrr_token and header_token != autobrr_token:
        logging.warning(f"Invalid Autobrr token received from {client_ip}")
        request_id = request_id_ctx_var.get() or '-'
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid Autobrr token (Request ID: {request_id})")
    
    payload = await request.json()
    
    # Validate payload has minimum required fields
    required_fields = ["name", "url", "download_url"]
    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
        logging.warning(f"Missing required fields in payload: {missing_fields}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required fields: {', '.join(missing_fields)}"
        )
    
    # Generate one-time-use token and use as request ID for logs
    token = generate_token()
    log_prefix = f"[token={token}] "
    logging.info(log_prefix + f"Received webhook payload: {payload}")

    # Fetch and validate metadata using the new modular coordinator
    coordinator = MetadataCoordinator()
    try:
        metadata = await coordinator.get_metadata_from_webhook(payload)
        if metadata:
            # Enhance metadata with additional information
            metadata = coordinator.get_enhanced_metadata(metadata)
        else:
            raise ValueError("No metadata found from any source")
    except Exception as e:
        logging.error(log_prefix + f"Metadata fetch failed: {e}")
        # Don't raise an exception, just continue with empty metadata for testing
        name = payload.get("name", "Unknown Title")
        # Extract the title without ASIN suffix if present
        import re
        title = name
        if re.search(r'\[[A-Z0-9]+\]$', name):
            title = re.sub(r'\s*\[[A-Z0-9]+\]$', '', name)
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
            "workflow_path": "fallback"
        }
        logging.warning(log_prefix + f"Using fallback metadata due to fetch error: {metadata}")
    logging.info(log_prefix + f"Fetched metadata: {metadata}")

    # Persist token, metadata, and original payload
    save_request(token, metadata, payload)
    logging.info(log_prefix + f"Saved request with token: {token}")

    # Prepare notification settings
    base_url = server_cfg.get('base_url')
    notif_cfg = config.get('notifications', {})
    pushover_cfg = notif_cfg.get('pushover', {})
    pushover_enabled = pushover_cfg.get('enabled', False)
    pushover_sound = pushover_cfg.get('sound')
    pushover_html = pushover_cfg.get('html')
    pushover_priority = pushover_cfg.get('priority')

    pushover_token = os.getenv('PUSHOVER_TOKEN')
    pushover_user = os.getenv('PUSHOVER_USER')
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    gotify_url = os.getenv('GOTIFY_URL')
    gotify_token = os.getenv('GOTIFY_TOKEN')
    ntfy_cfg = notif_cfg.get('ntfy', {})
    ntfy_enabled = ntfy_cfg.get('enabled', False)
    ntfy_topic = ntfy_cfg.get('topic')
    ntfy_url = ntfy_cfg.get('url', 'https://ntfy.sh')
    ntfy_user = os.getenv('NTFY_USER')
    ntfy_pass = os.getenv('NTFY_PASS')

    # Send notifications with granular error handling
    notification_errors = []
    notifications_sent = 0
    
    logging.info(log_prefix + f"Sending notifications: pushover={'enabled' if pushover_enabled else 'disabled'}, gotify={'enabled' if gotify_url and gotify_token else 'disabled'}, discord={'enabled' if discord_webhook else 'disabled'}, ntfy={'enabled' if ntfy_enabled else 'disabled'}")
    
    if pushover_enabled:
        if pushover_user is None or pushover_token is None:
            error_msg = "Pushover user key or token is not set in environment variables."
            logging.error(log_prefix + error_msg)
            notification_errors.append(f"Pushover: {error_msg}")
        else:
            try:
                status_code, response = send_pushover(
                    metadata, payload, token, base_url,
                    pushover_user, pushover_token,
                    pushover_sound, pushover_html, pushover_priority
                )
                if status_code >= 200 and status_code < 300:
                    logging.info(log_prefix + "Pushover notification sent successfully.")
                    notifications_sent += 1
                else:
                    logging.error(log_prefix + f"Pushover notification failed with status {status_code}: {response}")
                    notification_errors.append(f"Pushover: HTTP {status_code}")
            except Exception as e:
                logging.error(log_prefix + f"Pushover notification failed: {e}")
                logging.exception(log_prefix + "Full Pushover exception traceback:")
                notification_errors.append(f"Pushover: {e}")
    
    if gotify_url and gotify_token:
        try:
            status_code, response = send_gotify(
                metadata,
                payload,
                token,
                base_url,
                gotify_url,  # type: ignore
                gotify_token  # type: ignore
            )
            if status_code >= 200 and status_code < 300:
                logging.info(log_prefix + "Gotify notification sent successfully.")
                notifications_sent += 1
            else:
                logging.error(log_prefix + f"Gotify notification failed with status {status_code}: {response}")
                notification_errors.append(f"Gotify: HTTP {status_code}")
        except Exception as e:
            logging.error(log_prefix + f"Gotify notification failed: {e}")
            logging.exception(log_prefix + "Full Gotify exception traceback:")
            notification_errors.append(f"Gotify: {e}")
    elif notif_cfg.get('gotify', {}).get('enabled', False):
        error_msg = "Gotify: URL or token not set in environment/config."
        logging.warning(log_prefix + error_msg)
        notification_errors.append(error_msg)

    if discord_webhook:
        try:
            status_code, response = send_discord(
                metadata,
                payload,
                token,
                base_url,
                discord_webhook  # type: ignore
            )
            if status_code >= 200 and status_code < 300:
                logging.info(log_prefix + "Discord notification sent successfully.")
                notifications_sent += 1
            else:
                logging.error(log_prefix + f"Discord notification failed with status {status_code}: {response}")
                notification_errors.append(f"Discord: HTTP {status_code}")
        except Exception as e:
            logging.error(log_prefix + f"Discord notification failed: {e}")
            logging.exception(log_prefix + "Full Discord exception traceback:")
            notification_errors.append(f"Discord: {e}")
    elif notif_cfg.get('discord', {}).get('enabled', False):
        error_msg = "Discord: webhook URL not set in environment/config."
        logging.warning(log_prefix + error_msg)
        notification_errors.append(error_msg)
    try:
        if ntfy_enabled:
            if not ntfy_topic:
                error_msg = "ntfy topic is not set in config.yaml."
                logging.error(log_prefix + error_msg)
                notification_errors.append(f"ntfy: {error_msg}")
            else:
                status_code, response = send_ntfy(
                    metadata, payload, token, base_url,
                    ntfy_topic, ntfy_url, ntfy_user, ntfy_pass
                )
                if status_code >= 200 and status_code < 300:
                    logging.info(log_prefix + "ntfy notification sent successfully.")
                    notifications_sent += 1
                else:
                    logging.error(log_prefix + f"ntfy notification failed with status {status_code}: {response}")
                    notification_errors.append(f"ntfy: HTTP {status_code}")
    except Exception as e:
        logging.error(log_prefix + f"ntfy notification failed: {e}")
        logging.exception(log_prefix + "Full ntfy exception traceback:")
        notification_errors.append(f"ntfy: {e}")

    # Log summary of notification results
    logging.info(log_prefix + f"Notification summary: {notifications_sent} sent successfully, {len(notification_errors)} failed")
    
    if notification_errors:
        logging.warning(log_prefix + f"Notification errors: {'; '.join(notification_errors)}")
        return {"message": "Webhook received, but some notifications failed.", "errors": notification_errors, "sent": notifications_sent}
    return {"message": "Webhook received and all notifications sent successfully.", "sent": notifications_sent}

# Commented out legacy handlers; using webui router instead
# @app.get("/approve/{token}", response_class=HTMLResponse)
# async def approve(token: str):
#     valid_tokens = []  # TODO: Replace with actual valid tokens source
#     if not verify_token(token, valid_tokens):
#         logging.warning(f"Approval attempt with invalid/expired token: {token}")
#         raise HTTPException(status_code=404, detail="Token not found or expired.")
#     logging.info(f"Token approved: {token}")
#     # Load metadata and render approval page (to be implemented)
#     return f"<h1>Approve Audiobook</h1><p>Token: {token}</p>"

# @app.get("/reject/{token}", response_class=HTMLResponse)
# async def reject(token: str):
#     valid_tokens = []  # TODO: Replace with actual valid tokens source
#     if not verify_token(token, valid_tokens):
#         logging.warning(f"Rejection attempt with invalid/expired token: {token}")
#         raise HTTPException(status_code=404, detail="Token not found or expired.")
#     logging.info(f"Token rejected: {token}")
#     # Handle rejection logic (to be implemented)
#     return f"<h1>Rejected Audiobook</h1><p>Token: {token}</p>"

if __name__ == "__main__":
    import uvicorn
    config = load_config().get('server', {})
    uvicorn.run(
        "src.main:app",
        host=config.get('host', '0.0.0.0'),
        port=config.get('port', 8000),
        reload=config.get('reload', True)
    )