from src.utils import build_notification_message, format_size, format_release_date, strip_html_tags
import os
import requests
import re
import tempfile

def escape_md(text):
    if not text:
        return ''
    return re.sub(r'([*_`~|>])', r'\\\1', str(text))

def send_gotify(metadata, payload, token, base_url, gotify_url, gotify_token):
    """
    Send a Gotify notification with Markdown message and cover image attachment.
    """
    if not gotify_url or not gotify_token:
        raise ValueError("GOTIFY_URL and GOTIFY_TOKEN must be set in the environment variables.")

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

    # Clean title/series
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
    # Use token-based view/download URLs
    view_url = f"{base_url}/view/{token}"
    download_url = f"{base_url}/download/{token}"
    approve_url = f"{base_url}/approve/{token}/action"
    reject_url = f"{base_url}/reject/{token}"

    # Markdown body
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
        f"[🌐 View]({view_url})",
        f"[📥 Download]({download_url})",
        '',
        f"# [✅ APPROVE]({approve_url}) | [❌ Reject]({reject_url})"
    ]
    body = '\n\n'.join([line for line in body_lines if line])

    payload_data = {
        "message": body,
        "title": f"{emoji} {title}",
        "priority": 5,
        "extras": {
            "client::display": {
                "contentType": "text/markdown"
            }
        }
    }

    # Add cover image as bigImageUrl in extras if available
    cover_url = metadata.get('cover_url') or metadata.get('image')
    # Defensive: ensure 'extras' is always a dict
    if not isinstance(payload_data.get('extras'), dict):
        payload_data['extras'] = {
            "client::display": {
                "contentType": "text/markdown"
            }
        }
    # Defensive: always overwrite 'client::notification' to avoid type errors
    if cover_url:
        if not isinstance(payload_data['extras'], dict):
            payload_data['extras'] = {}
        payload_data['extras']['client::notification'] = {'bigImageUrl': cover_url}

    # Download cover image if available and attach
    files = None
    temp_file = None
    if cover_url:
        try:
            resp = requests.get(cover_url, timeout=10)
            resp.raise_for_status()
            suffix = os.path.splitext(cover_url)[-1] or '.jpg'
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(resp.content)
            temp_file.close()
            files = {'image': (os.path.basename(temp_file.name), open(temp_file.name, 'rb'), 'image/jpeg')}
        except Exception as e:
            files = None
    try:
        # Send as JSON for markdown support (no image if using JSON)
        if files:
            # If you want to send an image, Gotify only supports multipart/form-data, but markdown is only supported with JSON.
            # So, you must choose: image OR markdown. We'll prefer markdown as requested.
            response = requests.post(f"{gotify_url}/message?token={gotify_token}", json=payload_data)
        else:
            response = requests.post(f"{gotify_url}/message?token={gotify_token}", json=payload_data)
    finally:
        if temp_file:
            os.unlink(temp_file.name)
    if response.status_code != 200:
        raise Exception(f"Failed to send notification: {response.text}")
    return response.status_code, response.json()