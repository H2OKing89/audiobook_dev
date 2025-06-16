import re
import requests
from typing import Any, Dict, Optional, Tuple
from src.utils import format_size, format_release_date, strip_html_tags

def escape_md(text: Optional[str]) -> str:
    if not text:
        return ''
    return re.sub(r'([*_`~|>])', r'\\\1', str(text))

def send_gotify(
    metadata: Dict[str, Any],
    payload: Dict[str, Any],
    token: str,
    base_url: str,
    gotify_url: str,
    gotify_token: str
) -> Tuple[int, dict]:
    """
    Send a Gotify notification with Markdown message and big image for Android notifications.
    """
    if not gotify_url or not gotify_token:
        raise ValueError("GOTIFY_URL and GOTIFY_TOKEN must be set.")

    # Emoji for category
    emoji_tbl = {
        'fantasy': '🧙‍♂️',
        'science fiction': '🚀',
        'sci-fi': '🚀',
        'mystery': '🕵️‍♂️',
        'romance': '💘'
    }
    category = (payload.get('category') or '').lower()
    key = re.sub(r'[^a-z]', '', category.split('/')[-1].split('-')[-1].split('&')[0].strip())
    emoji = emoji_tbl.get(key, '📚')

    def clean_light_novel(text):
        if not text:
            return text
        return text.replace('(Light Novel)', '').replace('(light novel)', '').strip()

    title = clean_light_novel(metadata.get('title', ''))
    series_info = metadata.get('series_primary', {})
    series = clean_light_novel(series_info.get('name'))
    if series and series_info.get('position'):
        series = f"{series} (Vol. {series_info['position']})"
    author = metadata.get('author', '')
    publisher = metadata.get('publisher', '')
    narrators = ', '.join(metadata.get('narrators', []))
    release_date = format_release_date(metadata.get('release_date', ''))
    runtime = str(metadata.get('runtime_minutes', ''))
    size = payload.get('size') or metadata.get('size')
    size_fmt = format_size(size)
    raw_desc = metadata.get('description', '')
    description = strip_html_tags(raw_desc)
    view_url = payload.get('url') or metadata.get('url') or f"{base_url}/view/{token}"
    download_url = payload.get('download_url') or metadata.get('download_url') or f"{base_url}/download/{token}"
    approve_url = f"{base_url}/approve/{token}/action"
    reject_url = f"{base_url}/reject/{token}"

    cover_url = metadata.get('cover_url') or metadata.get('image')

    # Message body: Markdown, cover image included if present
    body_lines = [
        f"**{emoji} NEW AUDIOBOOK**",
        f"**🎧 Title:** ***{escape_md(title)}***",
        f"**🔗 Series:** {escape_md(series)}" if series else None,
        f"**✍️ Author:** _{escape_md(author)}_" if author else None,
        f"**🏢 Publisher:** {escape_md(publisher)}" if publisher else None,
        f"**🎤 Narrators:** {escape_md(narrators)}" if narrators else None,
        f"**📅 Release Date:** {escape_md(release_date)}" if release_date else None,
        f"**⏱️ Runtime:** {escape_md(runtime)}" if runtime else None,
        f"**📚 Category:** {escape_md(category)}" if category else None,
        f"**💾 Size:** {escape_md(size_fmt)}" if size_fmt else None,
        f"**📝 Description:** {escape_md(description)}" if description else None,
        f"![cover]({cover_url})" if cover_url else None,  # Markdown image line
        f"[🌐 View]({view_url})",
        f"[📥 Download]({download_url})",
        '',
        f"# [✅ APPROVE]({approve_url}) | [❌ Reject]({reject_url})"
    ]
    body = '\n\n'.join([line for line in body_lines if line])

    # Prepare payload for Gotify
    payload_data = {
        "message": body,
        "title": f"{emoji} {title}",
        "priority": 5,
        "extras": {
            "client::display": {"contentType": "text/markdown"}
        }
    }

    # Add bigImageUrl for Android client if cover exists
    if cover_url:
        if not isinstance(payload_data.get("extras"), dict):
            payload_data["extras"] = {}
        # Ensure "extras" is a dict and not accidentally overwritten elsewhere
        if not isinstance(payload_data["extras"], dict):
            payload_data["extras"] = {}
        payload_data["extras"]["client::notification"] = {"bigImageUrl": cover_url}

    response = requests.post(f"{gotify_url}/message?token={gotify_token}", json=payload_data)
    if response.status_code != 200:
        raise Exception(f"Failed to send notification: {response.text}")
    return response.status_code, response.json()
