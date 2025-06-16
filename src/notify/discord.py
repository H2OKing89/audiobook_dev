import re
from typing import Any, Dict, Optional, Tuple
from src.config import load_config
from src.utils import format_size, format_release_date, strip_html_tags


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
    import requests
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

    # Compose fields using cleaned info
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
    # Clean HTML from description
    raw_desc = metadata.get('description', '')
    description = strip_html_tags(raw_desc)
    url = payload.get('url') or metadata.get('url')
    download_url = payload.get('download_url') or metadata.get('download_url')

    # Build description block
    desc_lines = [
        f"🎧 **Title:** {escape_md(title)}",
        f"🔗 **Series:** {escape_md(series)}" if series else None,
        f"✍️ **Author:** {escape_md(author)}" if author else None,
        f"🏢 **Publisher:** {escape_md(publisher)}" if publisher else None,
        f"🎤 **Narrators:** {escape_md(narrators)}" if narrators else None,
        f"📅 **Release Date:** {escape_md(release_date)}" if release_date else None,
        f"⏱️ **Runtime:** {escape_md(runtime)}" if runtime else None,
        f"📚 **Category:** {escape_md(category)}" if category else None,
        f"💾 **Size:** {escape_md(size_fmt)}" if size_fmt else None,
        f"📝 **Description:** {escape_md(description)}" if description else None,
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
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
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