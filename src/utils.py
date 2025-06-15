from datetime import datetime
import re
from html import escape

def log_message(message: str) -> None:
    """
    Deprecated: Use the central logger instead of writing to app.log.
    """
    # Deprecated: remove this function or redirect to logging
    import logging

    logging.warning('log_message is deprecated; use logging module instead')
    with open("app.log", "a") as log_file:
        log_file.write(f"{message}\n")


def format_metadata(metadata: dict) -> str:
    formatted = "\n".join(f"{key}: {value}" for key, value in metadata.items())
    return formatted


def validate_payload(payload: dict, required_keys: list) -> bool:
    return all(key in payload for key in required_keys)


def format_release_date(date_str: str) -> str:
    if not date_str:
        return ''
    if 'T' in date_str:
        return date_str.split('T')[0]
    return date_str


def format_size(size_bytes) -> str:
    try:
        size_bytes = int(size_bytes)
        if size_bytes >= 1024 ** 3:
            return f"{size_bytes / (1024 ** 3):.2f} GB"
        elif size_bytes >= 1024 ** 2:
            return f"{size_bytes / (1024 ** 2):.2f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.2f} KB"
        else:
            return f"{size_bytes} B"
    except Exception:
        return str(size_bytes)


def clean_author_list(authors):
    """
    Return only authors, not illustrators or translators.
    """
    filtered = []
    for author in authors:
        name = author.get('name', '')
        if not any(term in name.lower() for term in (
            'illustrator', 'translator', 'adapter', 'contributor', 'editor'
        )):
            filtered.append(name)
    return filtered


def clean_light_novel(text: str) -> str:
    if not text:
        return text
    return text.replace('(Light Novel)', '').replace('(light novel)', '').strip()


def strip_html_tags(text: str) -> str:
    """
    Strips all HTML tags from a string, preserving paragraph breaks.
    Converts <p> and <br> tags into newlines, removes other tags,
    decodes basic HTML entities, and collapses excess whitespace.
    """
    if not text:
        return ''
    # Convert <p> and <br> to newlines
    text = re.sub(r'</?(p|br)[^>]*>', '\n', text, flags=re.IGNORECASE)
    # Remove other HTML tags
    text = re.sub(r'<.*?>', '', text)
    # Decode HTML entities
    text = (text.replace('&quot;', '"')
                .replace('&amp;', '&')
                .replace('&lt;', '<')
                .replace('&gt;', '>')
                .replace('&apos;', "'"))
    # Collapse multiple paragraph breaks
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    # Collapse spaces/tabs
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def build_notification_message(metadata: dict, payload: dict, token: str, base_url: str) -> str:
    """
    Construct an HTML notification message for Pushover/Discord with approve/reject links.
    """
    title = clean_light_novel(metadata.get('title', ''))
    # Series with volume number if available
    series_info = metadata.get('series_primary', {})
    series = clean_light_novel(series_info.get('name'))
    if series and series_info.get('position'):
        series = f"{series} (Vol. {series_info['position']})"
    author = metadata.get('author', '')
    publisher = metadata.get('publisher', '')
    narrators = ', '.join(metadata.get('narrators', []))
    release_date = metadata.get('release_date', '')
    runtime = str(metadata.get('runtime_minutes', ''))
    category = payload.get('category', '')
    size = payload.get('size', '')
    # Clean HTML from description
    raw_desc = metadata.get('description', '')
    description = strip_html_tags(raw_desc)

    parts = [
        f"<font color=\"green\"><b>🎉 NEW AUDIOBOOK</b></font><br>",
        f"<font color=\"#30bfff\"><b>🎧 Title:</b></font> <b>{escape(title)}</b><br>",
        f"<font color=\"#e040fb\"><b>🔗 Series:</b></font> {escape(series)}<br>" if series else "",
        f"<font color=\"#ff9500\"><b>✍️ Author:</b></font> <i>{escape(author)}</i><br>",
        f"<font color=\"#30bfff\"><b>🏢 Publisher:</b></font> {escape(publisher)}<br>" if publisher else "",
        f"<font color=\"#b889f4\"><b>🎤 Narrators:</b></font> {escape(narrators)}<br>" if narrators else "",
        f"<font color=\"#ff9500\"><b>📅 Release Date:</b></font> {escape(format_release_date(release_date))}<br>" if release_date else "",
        f"<font color=\"green\"><b>⏱️ Runtime:</b></font> {escape(runtime)}<br>" if runtime else "",
        f"<font color=\"#b889f4\"><b>📚 Category:</b></font> {escape(category)}<br>",
        f"<font color=\"#888\"><b>💾 Size:</b></font> {escape(format_size(size))}<br>",
        f"<font color=\"#888\"><b>📝 Description:</b></font> {escape(description)}<br>" if description else "",
        # Approval/reject links
        f"<br><a href=\"{base_url}/approve/{token}\">✅ Approve</a> "
        f"<a href=\"{base_url}/reject/{token}\">❌ Reject</a><br>"
    ]
    # filter out empty parts
    return ''.join([part for part in parts if part])