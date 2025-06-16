import re
import requests
from datetime import datetime, UTC
from typing import Any, Dict, Optional, Tuple
from src.config import load_config
from src.utils import get_notification_fields


def escape_md(text: Optional[str]) -> str:
    # Escape Discord markdown
    if not text:
        return ''
    return re.sub(r'([*_`~|>])', r'\\\1', str(text))


def send_discord(
    metadata: Dict[str, Any],
    payload: Dict[str, Any],
    token: str,
    base_url: str,
    webhook_url: str
) -> Tuple[int, Any]:
    config = load_config()
    server_cfg = config.get('server', {})
    discord_cfg = config.get('notifications', {}).get('discord', {})
    # Build Approve/Reject URLs
    approve_url = f"{server_cfg.get('base_url', base_url)}/approve/{token}/action"
    reject_url = f"{server_cfg.get('base_url', base_url)}/reject/{token}"

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

    # Sanitize and extract common fields
    fields = get_notification_fields(metadata, payload)
    title = escape_md(fields['title'])
    series = escape_md(fields['series'])
    author = escape_md(fields['author'])
    publisher = escape_md(fields['publisher'])
    narrators = escape_md(', '.join(fields['narrators']))
    release_date = escape_md(fields['release_date'])
    runtime = escape_md(fields['runtime'])
    size_fmt = escape_md(fields['size'])
    description = escape_md(fields['description'])
    url = fields['url']
    download_url = fields['download_url']

    # Build description block
    desc_lines = [
        f"🎧 **Title:** {title}",
        f"🔗 **Series:** {series}" if series else None,
        f"✍️ **Author:** {author}" if author else None,
        f"🏢 **Publisher:** {publisher}" if publisher else None,
        f"🎤 **Narrators:** {narrators}" if narrators else None,
        f"📅 **Release Date:** {release_date}" if release_date else None,
        f"⏱️ **Runtime:** {runtime}" if runtime else None,
        f"📚 **Category:** {category}" if category else None,
        f"💾 **Size:** {size_fmt}" if size_fmt else None,
        f"📝 **Description:** {description}" if description else None,
        '',
        (f"[🌐 View]({url})" if url else "") + (f" | [📥 Download]({download_url})" if download_url else ""),
        f"[✅ APPROVE]({approve_url}) | [❌ Reject]({reject_url})"
    ]
    desc = '\n'.join([line for line in desc_lines if line])

    cover_url = metadata.get('cover_url') or metadata.get('image')
    icon_url = discord_cfg.get('icon_url', "https://ptpimg.me/44pi19.png")
    author_url = discord_cfg.get('author_url', "https://audiobookshelf.kingpaging.com/")
    footer_icon_url = discord_cfg.get('footer_icon_url', "https://ptpimg.me/44pi19.png")
    footer_text = discord_cfg.get('footer_text', "Powered by Autobrr")
    embed = {
        "color": 12074727,
        "title": f"{emoji} NEW AUDIOBOOK",
        "author": {
            "name": "Audiobook Notifier",
            "icon_url": icon_url,
            "url": author_url
        },
        "description": desc,
        "thumbnail": {
            "url": icon_url
        },
        "image": {"url": cover_url} if cover_url else None,
        "footer": {"text": footer_text, "icon_url": footer_icon_url},
        "timestamp": datetime.now(UTC).isoformat()
    }
    # Remove None values (Discord API does not accept them)
    embed = {k: v for k, v in embed.items() if v is not None}
    data = {"embeds": [embed]}
    response = requests.post(webhook_url, json=data)
    try:
        resp_json = response.json()
    except Exception:
        resp_json = {"text": response.text}
    return response.status_code, resp_json