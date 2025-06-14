from typing import Any, Dict, Optional, Tuple
from src.utils import build_notification_message
import os
import tempfile


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
    import requests

    message = build_notification_message(metadata, payload, token, base_url)
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