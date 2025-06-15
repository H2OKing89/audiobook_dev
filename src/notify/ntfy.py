import os
import requests
import logging
from typing import Any, Dict, Optional, List
from src.utils import clean_light_novel, format_release_date, format_size
# from src.utils import build_notification_message
def send_ntfy(
    metadata: Dict[str, Any],
    payload: Dict[str, Any],
    token: str,
    base_url: str,
    ntfy_topic: str,
    ntfy_url: str,
    ntfy_user: Optional[str] = None,
    ntfy_pass: Optional[str] = None
) -> requests.Response:
    """
    Send a notification to ntfy.sh with Markdown, cover image, and action buttons.
    Logs all attempts and errors.
    Tries JSON publish first, then falls back to topic endpoint.
    Uses NTFY_TOKEN from environment as Bearer token if set.
    """
    logging.info(f"Preparing ntfy notification for topic={ntfy_topic} at {ntfy_url}")
    # Build message body (Markdown)
    title = clean_light_novel(metadata.get('title', 'New Audiobook'))
    series_info = metadata.get('series_primary', {})
    series = clean_light_novel(series_info.get('name'))
    if series and series_info.get('position'):
        series = f"{series} (Vol. {series_info['position']})"
    author = metadata.get('author', '')
    publisher = metadata.get('publisher', '')
    narrators = ', '.join(metadata.get('narrators', []))
    release_date = format_release_date(metadata.get('release_date', ''))
    runtime = str(metadata.get('runtime_minutes', ''))
    category = payload.get('category', '')
    size = payload.get('size') or metadata.get('size')
    size_fmt = format_size(size)
    description = metadata.get('description', '')
    approve_url = f"{base_url}/approve/{token}/action"
    reject_url = f"{base_url}/reject/{token}"
    cover_url = metadata.get('cover_url') or metadata.get('image')
    msg_lines = [
        f"- 🎧 **Title:** {title}",
        f"- 🔗 **Series:** {series}" if series else None,
        f"- ✍️ **Author:** {author}" if author else None,
        f"- 🏢 **Publisher:** {publisher}" if publisher else None,
        f"- 🎤 **Narrators:** {narrators}" if narrators else None,
        f"- 📅 **Release Date:** {release_date}" if release_date else None,
        f"- ⏱️ **Runtime:** {runtime}" if runtime else None,
        f"- 📚 **Category:** {category}" if category else None,
        f"- 💾 **Size:** {size_fmt}" if size_fmt else None,
        f" ---\n",
        f"> 📝 **Description:** {description}" if description else None,
    ]
    if cover_url:
        msg_lines.append(f"![cover]({cover_url})")
    message = '\n'.join([line for line in msg_lines if line])

    # Actions (JSON array)
    actions: List[dict] = [
        {"action": "view", "label": "Approve", "url": approve_url, "clear": True},
        {"action": "view", "label": "Reject", "url": reject_url, "clear": True}
    ]

    headers = {
        "Title": f"{title}",
        "Markdown": "true",
        "Icon": "https://picsur.kingpaging.com/i/f1eb91c4-1fc4-40a3-a258-e41448b1f3d9.jpg",
    }
    # Add Bearer token if present
    ntfy_token = os.getenv("NTFY_TOKEN")
    if ntfy_token:
        headers["Authorization"] = f"Bearer {ntfy_token}"
    if ntfy_user and ntfy_pass:
        auth = (ntfy_user, ntfy_pass)
    else:
        auth = None

    data = {
        "topic": ntfy_topic,
        "message": message,
        "actions": actions
    }
    # Send as JSON for Markdown and actions
    base = ntfy_url.rstrip('/')
    logging.info(f"Sending ntfy JSON to {base}")
    try:
        resp = requests.post(
            base,
            json=data,
            headers=headers,
            auth=auth
        )
        resp.raise_for_status()
        logging.info(f"ntfy JSON publish succeeded: status={resp.status_code}")
        return resp
    except Exception as e:
        logging.error(f"ntfy JSON publish failed: {e}")
        # Fallback to topic endpoint
        fallback_url = f"{base}/{ntfy_topic}"
        logging.info(f"Falling back to ntfy topic endpoint: {fallback_url}")
        resp2 = requests.post(
            fallback_url,
            data=message.encode('utf-8'),
            headers=headers,
            auth=auth
        )
        resp2.raise_for_status()
        logging.info(f"ntfy fallback publish succeeded: status={resp2.status_code}")
        return resp2
