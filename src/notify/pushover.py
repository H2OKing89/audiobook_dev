import requests
from typing import Any, Dict, Optional, Tuple
from src.utils import build_notification_message, get_notification_fields
import os
import tempfile
from html import escape


def send_pushover(
    metadata: Dict[str, Any],
    payload: Dict[str, Any],
    token: str,
    base_url: str,
    user_key: str,
    api_token: str,
    sound: Optional[str] = None,
    html: Optional[int] = None,
    priority: Optional[int] = None
) -> Tuple[int, dict]:
    """
    Send a Pushover notification with optional cover image attachment.
    Returns (status_code, response_json).
    Raises requests.RequestException for network errors.
    """
    fields = get_notification_fields(metadata, payload)
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
    if fields['url']:
        message += f'<br><font color="#30bfff"><b>🔗 URL:</b></font> <a href="{escape(fields["url"])}">{escape(fields["url"])}</a>'
    if fields['download_url']:
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
    if sound is not None:
        payload_data["sound"] = sound
    if priority is not None:
        payload_data["priority"] = str(priority)
    # Include the approval page link in the notification
    approve_url = f"{base_url}/approve/{token}"
    payload_data['url'] = approve_url
    # Use torrent name or title as the link title
    url_title = metadata.get('title') or payload.get('name')
    if url_title:
        payload_data['url_title'] = url_title

    # Download cover image if available and attach
    cover_url = metadata.get('cover_url') or metadata.get('image')
    files = None
    temp_file = None
    if cover_url:
        try:
            resp = requests.get(cover_url, timeout=10)
            resp.raise_for_status()
            # Save to temp file
            suffix = os.path.splitext(cover_url)[-1] or '.jpg'
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(resp.content)
            temp_file.close()
            files = {'attachment': (os.path.basename(temp_file.name), open(temp_file.name, 'rb'), 'image/jpeg')}
        except requests.RequestException:
            files = None
    try:
        if files:
            response = requests.post(url, data=payload_data, files=files)
        else:
            response = requests.post(url, data=payload_data)
    finally:
        if temp_file:
            os.unlink(temp_file.name)
    return response.status_code, response.json()