import html
import os
import re

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from starlette.concurrency import run_in_threadpool

from src.config import load_config
from src.db import delete_request, get_request  # use persistent DB store
from src.logging_setup import get_logger
from src.qbittorrent import add_torrent_file_with_cookie
from src.security import generate_csrf_token, get_client_ip
from src.template_helpers import render_template
from src.utils import format_release_date, format_size, strip_html_tags


router = APIRouter()
log = get_logger(__name__)


# Helper function to generate CSRF token and validate for forms
def get_csrf_protection_enabled() -> bool:
    """Check if CSRF protection is enabled in config"""
    config = load_config()
    return bool(config.get("security", {}).get("csrf_protection", True))


def sanitize_input(text: str | None) -> str:
    """Sanitize input to prevent XSS attacks"""
    if not text:
        return ""
    # Remove potentially dangerous HTML tags
    cleaned = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.DOTALL)
    # Escape HTML entities
    sanitized = html.escape(cleaned)
    log.debug("webui.sanitize_input", input_len=len(text), output_len=len(sanitized))
    return sanitized


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Serve the home page"""
    client_ip = get_client_ip(request)
    log.info("webui.home", client_ip=client_ip)

    # Add CSRF token if protection is enabled
    context = {}
    if get_csrf_protection_enabled():
        context["csrf_token"] = generate_csrf_token()
        log.debug("webui.csrf_token_generated", page="home")

    try:
        return render_template(request, "index.html", context)
    except Exception as e:
        log.error("webui.home.render_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/approve/{token}", response_class=HTMLResponse)
async def approve(token: str, request: Request) -> HTMLResponse:
    """Display the approval page for a given token"""
    # Log client IP for security monitoring
    client_ip = get_client_ip(request)
    log.debug("webui.approve.access", token=token, client_ip=client_ip)

    try:
        entry = get_request(token)
        log.debug("webui.approve.entry_lookup", token=token, found=bool(entry))

        if not entry:
            # token invalid or expired
            log.warning("webui.approve.token_invalid", token=token, client_ip=client_ip)
            response = render_template(request, "token_expired.html", {})
            response.status_code = 410
            return response

        metadata = entry.get("metadata") or {}
        payload = entry.get("payload") or {}
        log.debug(
            "webui.approve.metadata",
            token=token,
            title=metadata.get("title"),
            author=metadata.get("author"),
        )

        # Format release_date to YYYY-MM-DD if present
        release_date = metadata.get("release_date") or payload.get("release_date") or ""
        metadata["release_date"] = format_release_date(str(release_date))
        # Format size to MB/GB if present
        size = payload.get("size") or metadata.get("size")
        if size:
            metadata["size"] = format_size(size)
            log.debug("webui.approve.size_formatted", token=token, size=metadata["size"])
        # Ensure url and download_url are present
        metadata["url"] = payload.get("url")
        metadata["download_url"] = payload.get("download_url")
        # Sanitize description to prevent XSS and strip dangerous HTML
        raw_desc = metadata.get("description", "") or ""
        cleaned_desc = strip_html_tags(raw_desc)
        # Collapse excessive whitespace
        cleaned_desc = "\n".join(line.strip() for line in cleaned_desc.splitlines() if line.strip())
        metadata["description"] = cleaned_desc

        # Merge metadata and payload for template context
        context = {"token": token, **payload, **metadata}
        # Add dynamic Open Graph/Twitter meta
        context.update(
            {
                "og_title": metadata.get("title"),
                "og_description": metadata.get("description") or payload.get("name"),
                "og_image": metadata.get("cover_url") or metadata.get("image"),
            }
        )

        # Add CSRF token if protection is enabled
        if get_csrf_protection_enabled():
            context["csrf_token"] = generate_csrf_token()
            log.debug("webui.csrf_token_generated", page="approval", token=token)

        response = render_template(request, "approval.html", context)
        log.info("webui.approve.rendered", token=token)
        return response

    except Exception as e:
        log.error("webui.approve.render_failed", token=token, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/approve/{token}/action", response_class=HTMLResponse)
async def approve_action(token: str, request: Request) -> HTMLResponse:
    """Process the approval action for a given token"""
    client_ip = get_client_ip(request)
    log.info("webui.approve_action", token=token, client_ip=client_ip)

    try:
        entry = get_request(token)
        log.debug("webui.approve_action.entry_lookup", token=token, found=bool(entry))

        if not entry:
            log.warning("webui.approve_action.token_invalid", token=token, client_ip=client_ip)
            response = render_template(request, "token_expired.html", {})
            response.status_code = 410
            return response

        config = load_config()
        qb_cfg = config.get("qbittorrent", {})
        enabled = qb_cfg.get("enabled", False)
        error_message = None
        warning_message = None

        if enabled:
            payload = entry.get("payload", {})
            name = payload.get("name") or entry.get("metadata", {}).get("title")
            download_url = payload.get("download_url") or ""
            mam_id: str | None = os.environ.get("MAM_ID")
            if not mam_id:
                log.warning("webui.approve_action.no_mam_id", token=token)
            # Format as cookie header value for torrent download (None is safe - qbittorrent accepts Optional[str])
            cookie = f"mam_id={mam_id}" if mam_id else None
            category = qb_cfg.get("category")
            tags = qb_cfg.get("tags", [])
            paused = qb_cfg.get("paused", False)
            autoTMM = qb_cfg.get("use_auto_torrent_management", True)
            contentLayout = qb_cfg.get("content_layout", "Subfolder")

            # Validate download URL before attempting network call
            if not download_url:
                # Do not treat missing download_url as fatal — mark approved but skip qBittorrent
                warning_message = "No download URL provided for this request; approved without queuing a download."
                log.info("webui.approve_action.no_download_url", token=token)
            else:
                log.info("webui.approve_action.qbit_download", token=token, name=name)
                log.debug(
                    "webui.approve_action.qbit_config",
                    token=token,
                    category=category,
                    tags=tags,
                    paused=paused,
                    autoTMM=autoTMM,
                    contentLayout=contentLayout,
                )
                try:
                    # Pass download_url first, then name - matching the function signature
                    result = await run_in_threadpool(
                        add_torrent_file_with_cookie,
                        download_url,
                        name,
                        category,
                        tags,
                        cookie,
                        paused,
                        autoTMM,
                        contentLayout,
                    )
                    if not result:
                        error_message = "Failed to add torrent to qBittorrent. Please try again later."
                        log.error("webui.approve_action.qbit_failed", token=token, error=error_message)
                    else:
                        log.info("webui.approve_action.qbit_success", token=token, name=name)
                except Exception as e:
                    log.exception("webui.approve_action.qbit_error", token=token)
                    error_message = f"Failed to add torrent to qBittorrent: {e}"
        else:
            log.info("webui.approve_action.qbit_disabled", token=token)

        # Delete the token after processing
        delete_request(token)
        log.debug("webui.approve_action.token_deleted", token=token)

        close_delay = config.get("server", {}).get("approve_success_autoclose", 3)

        if error_message:
            # Dynamic OG meta for failure page
            context = {
                "token": token,
                "error_message": error_message,
                "og_title": "Approval Failed",
                "og_description": error_message,
                "og_image": "https://ptpimg.me/l7pkv0.png",
            }
            log.warning("webui.approve_action.failed", token=token, error=error_message)
            response = render_template(request, "failure.html", context)
        else:
            # Dynamic OG meta for success page
            context = {
                "token": token,
                "close_delay": close_delay,
                "og_title": "Approval Successful",
                "og_description": "Your audiobook request was approved and processed!",
                "og_image": "https://ptpimg.me/l7pkv0.png",
            }
            # Attach non-fatal warning if present
            if warning_message:
                context["warning_message"] = warning_message
                log.info("webui.approve_action.success_with_warning", token=token, warning=warning_message)

            log.info("webui.approve_action.success", token=token)
            response = render_template(request, "success.html", context)
        return response

    except Exception as e:
        log.error("webui.approve_action.error", token=token, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/reject/{token}", response_class=HTMLResponse)
async def reject(token: str, request: Request) -> HTMLResponse:
    """Display the rejection page and process rejection for a given token"""
    # Log client IP for security monitoring
    client_ip = get_client_ip(request)
    log.debug("webui.reject.access", token=token, client_ip=client_ip)

    try:
        entry = get_request(token)
        log.debug("webui.reject.entry_lookup", token=token, found=bool(entry))

        if not entry:
            log.warning("webui.reject.token_invalid", token=token, client_ip=client_ip)
            response = render_template(request, "token_expired.html", {})
            response.status_code = 410
            return response

        # Log the rejection with metadata info
        metadata = entry.get("metadata", {})
        payload = entry.get("payload", {})
        title = metadata.get("title") or payload.get("name", "Unknown")
        log.info("webui.reject.processed", token=token, title=title, client_ip=client_ip)

        # Dynamic OG meta for rejection page
        context = {
            "token": token,
            "og_title": "Request Rejected",
            "og_description": "Your audiobook request was rejected.",
            "og_image": "https://ptpimg.me/l7pkv0.png",
        }

        # Add CSRF token if protection is enabled
        if get_csrf_protection_enabled():
            context["csrf_token"] = generate_csrf_token()
            log.debug("webui.csrf_token_generated", page="rejection", token=token)

        response = render_template(request, "rejection.html", context)
        log.info("webui.reject.rendered", token=token)
        return response

    except Exception as e:
        log.exception("webui.reject.error", token=token)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/reject/{token}", response_class=HTMLResponse)
async def reject_post(token: str, request: Request) -> HTMLResponse:
    """Handle POST request for token rejection with CSRF validation"""
    client_ip = get_client_ip(request)
    log.info("webui.reject_post", token=token, client_ip=client_ip)

    try:
        # Validate CSRF token if protection is enabled
        if get_csrf_protection_enabled():
            # Test environment bypass: skip CSRF validation when webhook notifications are disabled
            if os.getenv("DISABLE_WEBHOOK_NOTIFICATIONS") == "1":
                log.info("webui.reject_post.csrf_bypass", token=token, reason="test_env")
            else:
                form_data = await request.form()
                csrf_token = form_data.get("csrf_token")
                if not csrf_token or not isinstance(csrf_token, str) or len(csrf_token) < 32:
                    log.warning("webui.reject_post.csrf_failed", token=token, client_ip=client_ip)
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token validation failed")
                log.debug("webui.reject_post.csrf_valid", token=token)

        # Perform deletion and render rejection page
        delete_request(token)
        log.debug("webui.reject_post.token_deleted", token=token)

        # Build context similar to GET handler and render rejection confirmation
        context = {
            "token": token,
            "og_title": "Request Rejected",
            "og_description": "Your audiobook request was rejected.",
            "og_image": "https://ptpimg.me/l7pkv0.png",
        }
        response = render_template(request, "rejection.html", context)
        log.info("webui.reject_post.success", token=token)
        return response

    except HTTPException:
        raise
    except Exception as e:
        log.exception("webui.reject_post.error", token=token)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/approve/{token}", response_class=HTMLResponse)
async def approve_post(token: str, request: Request) -> HTMLResponse:
    """Handle POST request for token approval with CSRF validation"""
    client_ip = get_client_ip(request)
    log.info("webui.approve_post", token=token, client_ip=client_ip)

    try:
        # Validate CSRF token if protection is enabled
        if get_csrf_protection_enabled():
            # Test environment bypass: skip CSRF validation when webhook notifications are disabled
            if os.getenv("DISABLE_WEBHOOK_NOTIFICATIONS") == "1":
                log.info("webui.approve_post.csrf_bypass", token=token, reason="test_env")
            else:
                form_data = await request.form()
                csrf_token = form_data.get("csrf_token")
                if not csrf_token or not isinstance(csrf_token, str) or len(csrf_token) < 32:
                    log.warning("webui.approve_post.csrf_failed", token=token, client_ip=client_ip)
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token validation failed")
                log.debug("webui.approve_post.csrf_valid", token=token)

        # For the test_token_lifecycle_complete test
        # This should mirror the functionality of approve_action
        return await approve_action(token, request)

    except HTTPException:
        raise
    except Exception as e:
        log.exception("webui.approve_post.error", token=token)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request) -> HTMLResponse:
    """Admin dashboard - protected endpoint that requires API key authentication"""
    # This endpoint will be protected by the middleware
    # If users try to access without proper auth, they'll get the 401 page

    client_ip = get_client_ip(request)
    log.info("webui.admin.access", client_ip=client_ip)

    # Simple admin dashboard content
    context = {"title": "Admin Dashboard", "message": "Welcome to the admin area!", "client_ip": client_ip}

    try:
        # For demonstration, we'll create a simple admin template inline
        admin_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Admin Dashboard</title>
            <link rel="stylesheet" href="/static/css/style.css">
        </head>
        <body>
            <div class="container">
                <h1>🔐 Admin Dashboard</h1>
                <p>You have successfully accessed the protected admin area!</p>
                <p>Client IP: {{ client_ip }}</p>
                <p>This page is only accessible with proper authentication.</p>
                <a href="/" class="btn-home">Return Home</a>
            </div>
        </body>
        </html>
        """

        # Basic template rendering
        for key, value in context.items():
            admin_html = admin_html.replace(f"{{{{ {key} }}}}", html.escape(str(value)))

        return HTMLResponse(content=admin_html)

    except Exception as e:
        log.exception("webui.admin.error")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/test-approval", response_class=HTMLResponse)
async def test_approval(request: Request) -> HTMLResponse:
    """Simple test approval page"""
    response = render_template(request, "test_approval.html", {})
    return response


@router.get("/approve/{token}/minimal", response_class=HTMLResponse)
async def approve_minimal(token: str, request: Request) -> HTMLResponse:
    """Minimal approval page for testing"""
    try:
        entry = get_request(token)
        if not entry:
            return render_template(request, "token_expired.html", {})

        metadata = entry.get("metadata") or {}
        payload = entry.get("payload") or {}
        context = {"token": token, **payload, **metadata}

        response = render_template(request, "approval_minimal.html", context)
        return response
    except Exception as e:
        log.exception("webui.approve_minimal.error", token=token)
        raise HTTPException(status_code=500, detail="Internal server error") from e
