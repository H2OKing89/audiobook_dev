import logging
import os
import tempfile
from html import escape
from typing import Any

import httpx

from src.utils import get_notification_fields


logger = logging.getLogger(__name__)


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
    logger.info("[token=%s] Preparing Pushover notification", token)

    try:
        fields = get_notification_fields(metadata, payload)
        title = fields.get("title", "Unknown Title")
        logger.debug("[token=%s] Pushover notification for: %s", token, title)

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
            logger.debug("[token=%s] Pushover HTML mode enabled", token)
        if sound is not None:
            payload_data["sound"] = sound
            logger.debug("[token=%s] Pushover sound: %s", token, sound)
        if priority is not None:
            payload_data["priority"] = str(priority)
            logger.debug("[token=%s] Pushover priority: %s", token, priority)

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
        temp_file = None

        if cover_url:
            logger.debug("[token=%s] Downloading cover image: %s", token, cover_url)
            try:
                resp = httpx.get(cover_url, timeout=10)
                resp.raise_for_status()
                # Save to temp file
                suffix = os.path.splitext(cover_url)[-1] or ".jpg"
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                temp_file.write(resp.content)
                temp_file.close()
                files = {"attachment": (os.path.basename(temp_file.name), open(temp_file.name, "rb"), "image/jpeg")}
                logger.debug("[token=%s] Cover image downloaded and prepared for upload", token)
            except httpx.RequestError as e:
                logger.debug("[token=%s] Failed to download cover image: %s", token, e)
                files = None

        try:
            logger.debug("[token=%s] Sending Pushover notification%s", token, "with attachment" if files else "")
            if files:
                response = httpx.post(url, data=payload_data, files=files, timeout=15)
            else:
                response = httpx.post(url, data=payload_data, timeout=15)
            response.raise_for_status()
            logger.info("[token=%s] Pushover notification sent successfully: status=%s", token, response.status_code)
            return response.status_code, response.json()
        except httpx.RequestError:
            logger.exception("[token=%s] Failed to send Pushover notification", token)
            # Propagate network-level exceptions to callers (tests expect this behavior)
            raise
        finally:
            # Cleanup temporary file and file handle
            if files and "attachment" in files and hasattr(files["attachment"][1], "close"):
                try:
                    files["attachment"][1].close()
                except Exception as e:
                    logger.warning("[token=%s] Failed to close file handle: %s", token, e)
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                    logger.debug("[token=%s] Cleaned up temporary cover image file", token)
                except Exception as e:
                    logger.warning("[token=%s] Failed to cleanup temp file: %s", token, e)

    except httpx.RequestError:
        # Re-raise network related exceptions so callers can handle circuit breakers, retries etc.
        logger.exception("[token=%s] Pushover network error during preparation/sending", token)
        raise
    except Exception as e:
        logger.exception("[token=%s] Pushover notification preparation failed", token)
        return 0, {"error": str(e)}
