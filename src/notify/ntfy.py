import logging
import os
from typing import Any

import httpx

from src.config import load_config
from src.utils import get_notification_fields


def send_ntfy(
    metadata: dict[str, Any],
    payload: dict[str, Any],
    token: str,
    base_url: str,
    ntfy_topic: str,
    ntfy_url: str,
    ntfy_user: str | None = None,
    ntfy_pass: str | None = None,
) -> tuple[int, dict]:
    """
    Send a notification to ntfy.sh with Markdown, cover image, and action buttons.
    Logs all attempts and errors.
    Tries JSON publish first, then falls back to topic endpoint.
    Uses NTFY_TOKEN from environment as Bearer token if set.
    """
    logging.info(f"Preparing ntfy notification for topic={ntfy_topic} at {ntfy_url}")

    config = load_config()
    icon_url = config.get("notifications", {}).get("ntfy", {}).get("icon_url", "https://ptpimg.me/4larvz.jpg")

    # Build message body (Markdown)
    fields = get_notification_fields(metadata, payload)
    title = fields["title"]
    series = fields["series"]
    author = fields["author"]
    publisher = fields["publisher"]
    narrators = ", ".join(fields["narrators"])
    release_date = fields["release_date"]
    runtime = fields["runtime"]
    category = fields["category"]
    size_fmt = fields["size"]
    description = fields["description"]
    url = fields["url"]
    download_url = fields["download_url"]
    cover_url = fields["cover_url"]
    approve_url = f"{base_url}/approve/{token}/action"
    reject_url = f"{base_url}/reject/{token}"
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
        " ---\n",
        "> 📝 **Description:**\n```\n" + description + "\n```" if description else None,
        (f"[🌐 View]({url})" if url else "") + (f" | [📥 Download]({download_url})" if download_url else ""),
    ]
    if cover_url:
        msg_lines.append(f"![cover]({cover_url})")
    message = "\n".join([line for line in msg_lines if line])

    # Actions (JSON array)
    actions: list[dict] = [
        {"action": "view", "label": "Approve", "url": approve_url, "clear": True},
        {"action": "view", "label": "Reject", "url": reject_url, "clear": True},
    ]

    headers = {
        "Title": f"{title}",
        "Markdown": "true",
        "Icon": icon_url,
    }
    # Add Bearer token if present
    ntfy_token = os.getenv("NTFY_TOKEN")
    if ntfy_token:
        headers["Authorization"] = f"Bearer {ntfy_token}"
    if ntfy_user and ntfy_pass:
        auth = (ntfy_user, ntfy_pass)
    else:
        auth = None

    data = {"topic": ntfy_topic, "message": message, "actions": actions}
    # Send as JSON for Markdown and actions
    base = ntfy_url.rstrip("/")
    logging.info(f"Sending ntfy JSON to {base}")
    try:
        resp = httpx.post(base, json=data, headers=headers, auth=auth)
        resp.raise_for_status()
        logging.info(f"ntfy JSON publish succeeded: status={resp.status_code}")
        return resp.status_code, resp.json()
    except httpx.RequestError as e:
        logging.error(f"ntfy JSON publish failed: {e}")
        # Fallback to topic endpoint
        fallback_url = f"{base}/{ntfy_topic}"
        logging.info(f"Falling back to ntfy topic endpoint: {fallback_url}")
        try:
            resp2 = httpx.post(fallback_url, data=message.encode("utf-8"), headers=headers, auth=auth, timeout=15)
            resp2.raise_for_status()
            logging.info(f"ntfy fallback publish succeeded: status={resp2.status_code}")
            return resp2.status_code, resp2.json()
        except httpx.RequestError as e2:
            error_msg = f"ntfy fallback publish also failed: {e2}"
            logging.error(error_msg)
            # Return the original error plus the fallback error
            return 0, {"error": f"Primary: {e}, Fallback: {e2}"}
