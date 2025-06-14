from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from src.metadata import fetch_metadata
from src.token_gen import generate_token, verify_token
from src.notify.pushover import send_pushover
from src.notify.gotify import send_gotify
from src.notify.discord import send_discord
from src.qbittorrent import add_torrent
from src.db import save_request  # switch to persistent DB store
from src.webui import router as webui_router  # add web UI router import
from src.config import load_config  # add import for config
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

load_dotenv()

# Load configuration
config = load_config()
server_cfg = config.get('server', {})
autobrr_endpoint = server_cfg.get('autobrr_webhook_endpoint', '/webhook')

# Dynamic logging configuration from config.yaml
log_cfg = config.get('logging', {})
level = getattr(logging, log_cfg.get('level', 'INFO').upper(), logging.INFO)
fmt = log_cfg.get('format', '%(asctime)s [%(levelname)s] %(message)s')
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

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Apply handlers
logger.handlers.clear()
logger.addHandler(file_handler)
logger.addHandler(console_handler)

app = FastAPI()
app.include_router(webui_router)  # mount web UI routes

# Use dynamic autobrr endpoint from config
@app.post(autobrr_endpoint)
async def webhook(request: Request):
    # Validate Autobrr token
    autobrr_token = os.getenv('AUTOBRR_TOKEN')
    header_token = request.headers.get('X-Autobrr-Token')
    if autobrr_token and header_token != autobrr_token:
        logging.warning(f"Invalid Autobrr token: {header_token}")
        raise HTTPException(status_code=401, detail="Invalid Autobrr token")
    payload = await request.json()
    logging.info(f"Received webhook payload: {payload}")

    token = generate_token()
    # Fetch and validate metadata
    try:
        metadata = fetch_metadata(payload)
    except Exception as e:
        logging.error(f"Metadata fetch failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    logging.info(f"Fetched metadata: {metadata}")

    # Persist token, metadata, and original payload
    save_request(token, metadata, payload)
    logging.info(f"Saved request with token: {token}")

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

    # Send notifications with granular error handling
    notification_errors = []
    if pushover_enabled:
        if pushover_user is None or pushover_token is None:
            error_msg = "Pushover user key or token is not set in environment variables."
            logging.error(error_msg)
            notification_errors.append(f"Pushover: {error_msg}")
        else:
            try:
                send_pushover(
                    metadata, payload, token, base_url,
                    pushover_user, pushover_token,
                    pushover_sound, pushover_html, pushover_priority
                )
                logging.info("Pushover notification sent successfully.")
            except Exception as e:
                logging.error(f"Pushover notification failed: {e}")
                notification_errors.append(f"Pushover: {e}")
    try:
        send_gotify(metadata, payload, token, base_url, gotify_url, gotify_token)
        logging.info("Gotify notification sent successfully.")
    except Exception as e:
        logging.error(f"Gotify notification failed: {e}")
        notification_errors.append(f"Gotify: {e}")
    try:
        send_discord(metadata, payload, token, base_url, discord_webhook)
        logging.info("Discord notification sent successfully.")
    except Exception as e:
        logging.error(f"Discord notification failed: {e}")
        notification_errors.append(f"Discord: {e}")

    if notification_errors:
        return {"message": "Webhook received, but some notifications failed.", "errors": notification_errors}
    return {"message": "Webhook received and notifications sent."}

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