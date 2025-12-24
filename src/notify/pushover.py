import tempfile
from html import escape
from pathlib import Path
from typing import Any

import httpx

from src.logging_setup import get_logger
from src.utils import get_notification_fields


log = get_logger(__name__)


def send_pushover(
    metadata: dict[str, Any],
    payload: dict[str, Any],
    token: str,
    base_url: str,
    user_key: str,
    api_token: str,
    sound: str | None = None,
    html: int | None = None,
    priority: int | None = None,
) -> tuple[int, dict]:
    """
    Send a Pushover notification with optional cover image attachment.
    Returns (status_code, response_json).
    Raises httpx.RequestError for network errors.
    """
    log.info("notify.pushover.prepare", token=token)

    try:
        fields = get_notification_fields(metadata, payload)
        title = fields.get("title", "Unknown Title")
        log.debug("notify.pushover.title", token=token, title=title)

        message = (
            '<font color="green"><b>🎉 NEW AUDIOBOOK</b></font><br>'
            f'<font color="#30bfff"><b>🎧 Title:</b></font> <b>{escape(fields["title"])}</b><br>'
            f'<font color="#e040fb"><b>🔗 Series:</b></font> {escape(fields["series"])}<br>'
            f'<font color="#ff9500"><b>✍️ Author:</b></font> <i>{escape(fields["author"])}</i><br>'
            f'<font color="#30bfff"><b>🏢 Publisher:</b></font> {escape(fields["publisher"])}<br>'
            f'<font color="#b889f4"><b>🎤 Narrators:</b></font> {escape(", ".join(fields["narrators"]))}<br>'
            f'<font color="#ff9500"><b>📅 Release Date:</b></font> {escape(fields["release_date"])}<br>'
            f'<font color="green"><b>⏱️ Runtime:</b></font> {escape(fields["runtime"])}<br>'
            f'<font color="#b889f4"><b>📚 Category:</b></font> {escape(fields["category"])}<br>'
            f'<font color="#888"><b>💾 Size:</b></font> {fields["size"]}<br>'
            f'<font color="#888"><b>📝 Description:</b></font> {fields["description"]}<br>'
        )
        # Add url and download_url
        if fields["url"]:
            message += f'<br><font color="#30bfff"><b>🔗 URL:</b></font> <a href="{escape(fields["url"])}">{escape(fields["url"])}</a>'
        if fields["download_url"]:
            message += f'<br><font color="#30bfff"><b>⬇️ Download:</b></font> <a href="{escape(fields["download_url"])}">{escape(fields["download_url"])}</a>'
        message += f'<br><br><a href="{base_url}/approve/{token}">✅ Approve</a> <a href="{base_url}/reject/{token}">❌ Reject</a><br>'

        url = "https://api.pushover.net/1/messages.json"
        payload_data = {
            "token": api_token,
            "user": user_key,
            "message": message,
        }
        # Add optional settings
        if html is not None:
            payload_data["html"] = str(html)
            log.debug("notify.pushover.html_enabled", token=token)
        if sound is not None:
            payload_data["sound"] = sound
            log.debug("notify.pushover.sound", token=token, sound=sound)
        if priority is not None:
            payload_data["priority"] = str(priority)
            log.debug("notify.pushover.priority", token=token, priority=priority)

        # Include the approval page link in the notification
        approve_url = f"{base_url}/approve/{token}"
        payload_data["url"] = approve_url
        # Use torrent name or title as the link title
        url_title = metadata.get("title") or payload.get("name")
        if url_title:
            payload_data["url_title"] = url_title

        # Download cover image if available and attach
        cover_url = metadata.get("cover_url") or metadata.get("image")
        files = None
        temp_file_path = None

        if cover_url:
            log.debug("notify.pushover.download_cover", token=token, cover_url=cover_url)
            try:
                resp = httpx.get(cover_url, timeout=10)
                resp.raise_for_status()
                # Save to temp file
                suffix = Path(cover_url).suffix or ".jpg"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                    temp_file.write(resp.content)
                    temp_file_path = temp_file.name
                log.debug("notify.pushover.cover_downloaded", token=token)
            except httpx.RequestError as e:
                log.debug("notify.pushover.cover_failed", token=token, error=str(e))

        try:
            log.debug("notify.pushover.send", token=token, has_attachment=bool(temp_file_path))
            if temp_file_path:
                # Use context manager to ensure file handle is closed after request
                with Path(temp_file_path).open("rb") as f:
                    files = {"attachment": (Path(temp_file_path).name, f, "image/jpeg")}
                    response = httpx.post(url, data=payload_data, files=files, timeout=15)
            else:
                response = httpx.post(url, data=payload_data, timeout=15)
            response.raise_for_status()
            token_fp = token[-4:] if len(token) > 4 else token if token else None
            log.info(
                "notify.pushover.success", token_id=token_fp, status_code=response.status_code
            )
            return response.status_code, response.json()
        except httpx.RequestError:
            log.exception("notify.pushover.send_failed", token=token)
            # Propagate network-level exceptions to callers (tests expect this behavior)
            raise
        finally:
            # Cleanup temporary file
            if temp_file_path and Path(temp_file_path).exists():
                try:
                    Path(temp_file_path).unlink()
                    log.debug("notify.pushover.cleanup", token=token)
                except Exception as e:
                    log.warning("notify.pushover.cleanup_failed", token=token, error=str(e))

    except httpx.RequestError:
        # Re-raise network related exceptions so callers can handle circuit breakers, retries etc.
        log.exception("notify.pushover.network_error", token=token)
        raise
    except Exception as e:
        log.exception("notify.pushover.preparation_failed", token=token)
        return 0, {"error": str(e)}
