import re
from typing import Any

import httpx

from src.logging_setup import get_logger
from src.utils import get_notification_fields


log = get_logger(__name__)


def escape_md(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"([*_`~|>])", r"\\\1", str(text))


def send_gotify(
    metadata: dict[str, Any], payload: dict[str, Any], token: str, base_url: str, gotify_url: str, gotify_token: str
) -> tuple[int, dict]:
    """
    Send a Gotify notification with Markdown message and big image for Android notifications.
    """
    if not gotify_url or not gotify_token:
        raise ValueError("GOTIFY_URL and GOTIFY_TOKEN must be set.")

    # Emoji for category and sanitized fields
    fields = get_notification_fields(metadata, payload)
    emoji_tbl = {"fantasy": "🧙‍♂️", "science fiction": "🚀", "sci-fi": "🚀", "mystery": "🕵️‍♂️", "romance": "💘"}
    category = (payload.get("category") or "").lower()
    key = re.sub(r"[^a-z]", "", category.split("/")[-1].split("-")[-1].split("&")[0].strip())
    emoji = emoji_tbl.get(key, "📚")

    # Escape markdown
    title = escape_md(fields["title"])
    series = escape_md(fields["series"])
    author = escape_md(fields["author"])
    publisher = escape_md(fields["publisher"])
    narrators = escape_md(", ".join(fields["narrators"]))
    release_date = escape_md(fields["release_date"])
    runtime = escape_md(fields["runtime"])
    size_fmt = escape_md(fields["size"])
    description = escape_md(fields["description"])
    view_url = fields["url"] or f"{base_url}/view/{token}"
    download_url = fields["download_url"] or f"{base_url}/download/{token}"
    approve_url = f"{base_url}/approve/{token}/action"
    reject_url = f"{base_url}/reject/{token}"

    cover_url = metadata.get("cover_url") or metadata.get("image")

    # Message body: Markdown, cover image included if present
    body_lines = [
        f"**{emoji} NEW AUDIOBOOK**",
        f"**🎧 Title:** ***{title}***",
        f"**🔗 Series:** {series}" if series else None,
        f"**✍️ Author:** _{author}_" if author else None,
        f"**🏢 Publisher:** {publisher}" if publisher else None,
        f"**🎤 Narrators:** {narrators}" if narrators else None,
        f"**📅 Release Date:** {release_date}" if release_date else None,
        f"**⏱️ Runtime:** {runtime}" if runtime else None,
        f"**📚 Category:** {category}" if category else None,
        f"**💾 Size:** {size_fmt}" if size_fmt else None,
        f"**🎛️ Audio:** {escape_md(fields['audio_summary'])}" if fields["audio_summary"] else None,
        f"**📈 Torrent:** {escape_md(fields['torrent_health'])}" if fields["torrent_health"] else None,
        f"**🎟️ Access:** {escape_md(fields['freeleech_label'])}" if fields["freeleech_label"] else None,
        f"**🕒 Added:** {escape_md(fields['added_date'])}" if fields["added_date"] else None,
        f"**🆔 ID:** {escape_md(fields['asin'] or fields['isbn'])}" if (fields["asin"] or fields["isbn"]) else None,
        f"**📝 Description:** {description}" if description else None,
        f"![cover]({cover_url})" if cover_url else None,  # Markdown image line
        f"[🌐 View]({view_url})",
        f"[📥 Download]({download_url})",
        "",
        f"# [✅ APPROVE]({approve_url}) | [❌ Reject]({reject_url})",
    ]
    body = "\n\n".join([line for line in body_lines if line])

    # Prepare payload for Gotify
    payload_data = {
        "message": body,
        "title": f"{emoji} {title}",
        "priority": 5,
        "extras": {"client::display": {"contentType": "text/markdown"}},
    }

    # Add bigImageUrl for Android client if cover exists
    if cover_url:
        if not isinstance(payload_data.get("extras"), dict):
            payload_data["extras"] = {}
        # Ensure "extras" is a dict and not accidentally overwritten elsewhere
        if not isinstance(payload_data["extras"], dict):
            payload_data["extras"] = {}
        payload_data["extras"]["client::notification"] = {"bigImageUrl": cover_url}  # type: ignore[index]

    try:
        response = httpx.post(f"{gotify_url}/message?token={gotify_token}", json=payload_data, timeout=15)
        response.raise_for_status()
        log.info("notify.gotify.success", status_code=response.status_code)
        return response.status_code, response.json()
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        log.exception("notify.gotify.failed", error=str(e))
        return 0, {"error": f"Failed to send Gotify notification: {e}"}
