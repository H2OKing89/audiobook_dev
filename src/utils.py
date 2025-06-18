from datetime import datetime
from html import escape
from typing import Any, Dict, List, Optional
import re
import logging
import os
from pathlib import Path
from fastapi import Request




def format_metadata(metadata: Dict[str, Any]) -> str:
    formatted = "\n".join(f"{key}: {value}" for key, value in metadata.items())
    return formatted


def validate_payload(payload: Dict[str, Any], required_keys: List[str]) -> bool:
    """Validate that payload contains all required keys"""
    missing_keys = [key for key in required_keys if key not in payload]
    if missing_keys:
        logging.warning(f"Payload validation failed: missing keys {missing_keys}")
        return False
    logging.debug(f"Payload validation successful: all required keys present")
    return True


def format_release_date(date_str: str) -> str:
    if not date_str:
        return ''
    if 'T' in date_str:
        return date_str.split('T')[0]
    return date_str


def format_size(size_bytes: Any) -> str:
    """Format file size in bytes to human readable format"""
    try:
        if size_bytes is None:
            logging.debug("Size formatting: size_bytes is None")
            return "?"
        size = float(size_bytes)
        logging.debug(f"Formatting size: {size} bytes")
        if size < 1024:
            return f"{size:.0f} B"
        elif size < 1024 ** 2:
            return f"{size / 1024:.2f} KB"
        elif size < 1024 ** 3:
            return f"{size / 1024 ** 2:.2f} MB"
        else:
            return f"{size / 1024 ** 3:.2f} GB"
    except Exception as e:
        logging.warning(f"Size formatting failed for {size_bytes}: {e}")
        return "?"


def clean_author_list(authors: List[Dict[str, Any]]) -> List[str]:
    """
    Return only authors, not illustrators or translators.
    """
    if not authors:
        logging.debug("Author list is empty")
        return []
        
    filtered = []
    excluded_count = 0
    for author in authors:
        name = author.get('name', '')
        # Skip illustrators and translators 
        if any(keyword in name.lower() for keyword in ['illustrator', 'translator', 'narrator']):
            excluded_count += 1
            continue
        if name:
            filtered.append(name)
    
    logging.debug(f"Author filtering: {len(filtered)} kept, {excluded_count} excluded")
    return filtered


def clean_light_novel(text: Optional[str]) -> Optional[str]:
    """Remove '(Light Novel)' suffixes from text"""
    if not text:
        return text
    cleaned = text.replace('(Light Novel)', '').replace('(light novel)', '').strip()
    if cleaned != text:
        logging.debug(f"Light novel title cleaned: '{text}' -> '{cleaned}'")
    return cleaned


def strip_html_tags(text: Optional[str]) -> str:
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


def build_notification_message(metadata: Dict[str, Any], payload: Dict[str, Any], token: str, base_url: str) -> str:
    """
    Construct an HTML notification message for Pushover/Discord with approve/reject links.
    """
    # Clean title and series
    title = clean_light_novel(metadata.get('title', '')) or ''
    series_info = metadata.get('series_primary', {})
    series = clean_light_novel(series_info.get('name'))
    if series and series_info.get('position'):
        series = f"{series} (Vol. {series_info['position']})"
    author = metadata.get('author', '')
    publisher = metadata.get('publisher', '')
    narrators = ', '.join(metadata.get('narrators', []))
    # Use format_release_date to strip time
    release_date = format_release_date(metadata.get('release_date', ''))
    runtime = str(metadata.get('runtime_minutes', ''))
    category = payload.get('category', '')
    size = payload.get('size', '')
    # Clean HTML from description
    raw_desc = metadata.get('description', '')
    description = strip_html_tags(raw_desc)

    msg = (
        '<font color="green"><b>🎉 NEW AUDIOBOOK</b></font><br>'
        f'<font color="#30bfff"><b>🎧 Title:</b></font> <b>{escape(title)}</b><br>'
        f'<font color="#e040fb"><b>🔗 Series:</b></font> {escape(series or "")}<br>'
        f'<font color="#ff9500"><b>✍️ Author:</b></font> <i>{escape(author)}</i><br>'
        f'<font color="#30bfff"><b>🏢 Publisher:</b></font> {escape(publisher)}<br>'
        f'<font color="#b889f4"><b>🎤 Narrators:</b></font> {escape(narrators)}<br>'
        f'<font color="#ff9500"><b>📅 Release Date:</b></font> {escape(release_date)}<br>'
        f'<font color="green"><b>⏱️ Runtime:</b></font> {escape(runtime)}<br>'
        f'<font color="#b889f4"><b>📚 Category:</b></font> {escape(category)}<br>'
        f'<font color="#888"><b>💾 Size:</b></font> {format_size(payload.get("size") or metadata.get("size"))}<br>'
        f'<font color="#888"><b>📝 Description:</b></font> {strip_html_tags(metadata.get("summary") or metadata.get("description", ""))}<br>'
    )
    # Add url and download_url if present
    url = payload.get("url") or metadata.get("url")
    download_url = payload.get("download_url") or metadata.get("download_url")
    if url:
        msg += f'<br><font color="#30bfff"><b>🔗 URL:</b></font> <a href="{escape(url)}">{escape(url)}</a>'
    if download_url:
        msg += f'<br><font color="#30bfff"><b>⬇️ Download:</b></font> <a href="{escape(download_url)}">{escape(download_url)}</a>'
    msg += f'<br><br><a href="{base_url}/approve/{token}">✅ Approve</a> <a href="{base_url}/reject/{token}">❌ Reject</a><br>'
    return msg


def get_notification_fields(metadata: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and sanitize common fields for notification formatting.
    """
    title = clean_light_novel(metadata.get('title', '')) or ''
    
    # Series handling - try multiple field names
    series = ''
    if metadata.get('book_series'):
        series_name = metadata.get('book_series')
        series_seq = metadata.get('book_series_sequence', '')
        if series_seq:
            series = f"{series_name} (Vol. {series_seq})"
        else:
            series = series_name
    elif metadata.get('series'):
        # Handle series as array or string
        series_data = metadata.get('series')
        if isinstance(series_data, list) and series_data:
            s = series_data[0]
            if isinstance(s, dict):
                series_name = s.get('series', '')
                series_seq = s.get('sequence', '')
                if series_name and series_seq:
                    series = f"{series_name} (Vol. {series_seq})"
                elif series_name:
                    series = series_name
        elif isinstance(series_data, str):
            series = series_data
    elif metadata.get('series_primary'):
        # Legacy format
        series_info = metadata.get('series_primary', {})
        series_name = clean_light_novel(series_info.get('name', ''))
        if series_name and series_info.get('position'):
            series = f"{series_name} (Vol. {series_info['position']})"
        elif series_name:
            series = series_name
    
    # Clean series name
    series = clean_light_novel(series) or ''
    
    author = metadata.get('author', '') or metadata.get('book_author', '')
    publisher = metadata.get('publisher', '') or metadata.get('book_publisher', '')
    
    # Narrator handling - try multiple field names
    narrators = []
    if metadata.get('narrator_list'):
        narrators = metadata.get('narrator_list', [])
    elif metadata.get('narrator'):
        # Split comma-separated narrator string
        narrator_str = metadata.get('narrator', '')
        if narrator_str:
            narrators = [n.strip() for n in narrator_str.split(',')]
    elif metadata.get('book_narrator'):
        # Split comma-separated narrator string
        narrator_str = metadata.get('book_narrator', '')
        if narrator_str:
            narrators = [n.strip() for n in narrator_str.split(',')]
    elif metadata.get('narrators_raw'):
        # Extract names from raw narrator objects
        narrators_raw = metadata.get('narrators_raw', [])
        narrators = [n.get('name', '') for n in narrators_raw if n.get('name')]
    
    # Fallback to payload if no narrators found
    if not narrators:
        narrators = payload.get('narrators', [])
    
    release_date = format_release_date(metadata.get('release_date', '') or metadata.get('book_release_date', ''))
    runtime = str(metadata.get('runtime_minutes', '') or metadata.get('book_duration', ''))
    category = payload.get('category', '')
    size = format_size(payload.get('size') or metadata.get('size'))
    description = strip_html_tags(
        metadata.get('summary') or 
        metadata.get('description', '') or 
        metadata.get('book_description', '')
    )
    url = payload.get('url') or metadata.get('url')
    download_url = payload.get('download_url') or metadata.get('download_url')
    cover_url = metadata.get('cover_url') or metadata.get('image') or metadata.get('cover') or metadata.get('book_cover')
    
    return {
        'title': title,
        'series': series,
        'author': author,
        'publisher': publisher,
        'narrators': narrators,
        'release_date': release_date,
        'runtime': runtime,
        'category': category,
        'size': size,
        'description': description,
        'url': url,
        'download_url': download_url,
        'cover_url': cover_url,
    }