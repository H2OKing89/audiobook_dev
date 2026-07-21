import re
from html import escape, unescape
from typing import Any

from src.logging_setup import get_logger


log = get_logger(__name__)


def format_metadata(metadata: dict[str, Any]) -> str:
    formatted = "\n".join(f"{key}: {value}" for key, value in metadata.items())
    return formatted


def validate_payload(payload: dict[str, Any], required_keys: list[str]) -> bool:
    """Validate that payload contains all required keys"""
    missing_keys = [key for key in required_keys if key not in payload]
    if missing_keys:
        log.warning("payload.validation_failed", missing_keys=missing_keys)
        return False
    log.debug("payload.validation_success")
    return True


def format_release_date(date_str: str) -> str:
    if not date_str:
        return ""
    if "T" in date_str:
        return date_str.split("T", maxsplit=1)[0]
    return date_str


def format_size(size_bytes: Any) -> str:
    """Format file size in bytes to human readable format"""
    try:
        if size_bytes is None:
            log.debug("format_size.null_input")
            return "?"
        size = float(size_bytes)
        log.debug("format_size", size_bytes=size)
        if size < 1024:
            return f"{size:.0f} B"
        elif size < 1024**2:
            return f"{size / 1024:.2f} KB"
        elif size < 1024**3:
            return f"{size / 1024**2:.2f} MB"
        else:
            return f"{size / 1024**3:.2f} GB"
    except Exception as e:
        log.warning("format_size.failed", size_bytes=size_bytes, error=str(e))
        return "?"


def clean_author_list(authors: list[dict[str, Any]]) -> list[str]:
    """
    Return only authors, not illustrators or translators.
    """
    if not authors:
        log.debug("clean_author_list.empty_input")
        return []

    filtered = []
    excluded_count = 0
    for author in authors:
        name = author.get("name", "")
        # Skip illustrators and translators
        if any(keyword in name.lower() for keyword in ["illustrator", "translator", "narrator"]):
            excluded_count += 1
            continue
        if name:
            filtered.append(name)

    log.debug("clean_author_list", kept=len(filtered), excluded=excluded_count)
    return filtered


def clean_light_novel(text: str | None) -> str | None:
    """Remove '(Light Novel)' suffixes from text"""
    if not text:
        return text
    cleaned = text.replace("(Light Novel)", "").replace("(light novel)", "").strip()
    if cleaned != text:
        log.debug("clean_light_novel", original=text, cleaned=cleaned)
    return cleaned


def strip_html_tags(text: str | None) -> str:
    """
    Strips all HTML tags from a string, preserving paragraph breaks.
    Converts <p> and <br> tags into newlines, removes other tags,
    decodes basic HTML entities, and collapses excess whitespace.
    """
    if not text:
        return ""
    # Decode HTML entities FIRST (so &#60;script&#62; becomes <script> which can then be stripped)
    text = unescape(text)
    # Convert <p> and <br> to newlines
    text = re.sub(r"</?(p|br)[^>]*>", "\n", text, flags=re.IGNORECASE)
    # Remove other HTML tags
    text = re.sub(r"<.*?>", "", text)
    # Collapse multiple paragraph breaks
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    # Collapse spaces/tabs
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def build_notification_message(metadata: dict[str, Any], payload: dict[str, Any], token: str, base_url: str) -> str:
    """
    Construct an HTML notification message for Pushover/Discord with approve/reject links.
    """
    # Clean title and series
    title = clean_light_novel(metadata.get("title", "")) or ""
    series_info = metadata.get("series_primary", {})
    series = clean_light_novel(series_info.get("name"))
    if series and series_info.get("position"):
        series = f"{series} (Vol. {series_info['position']})"
    author = metadata.get("author", "")
    publisher = metadata.get("publisher", "")
    narrators = ", ".join(metadata.get("narrators", []))
    # Use format_release_date to strip time
    release_date = format_release_date(metadata.get("release_date", ""))
    runtime = str(metadata.get("runtime_minutes", ""))
    category = payload.get("category", "")
    payload.get("size", "")
    # Clean HTML from description
    raw_desc = metadata.get("description", "")
    strip_html_tags(raw_desc)

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


def _get_mam_enrichment(metadata: dict[str, Any]) -> dict[str, Any]:
    mam_enrichment = metadata.get("mam_enrichment")
    return mam_enrichment if isinstance(mam_enrichment, dict) else {}


def _clean_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _split_tags(value: Any) -> list[str]:
    if not value:
        return []
    return [tag.strip() for tag in re.split(r",\s*", str(value)) if tag.strip()]


def _coerce_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _format_bitrate(value: Any) -> str:
    if value is None or value == "":
        return ""
    text = str(value).strip()
    if not text:
        return ""
    try:
        numeric = float(text)
    except ValueError:
        return text

    if numeric >= 1000:
        kbps = numeric / 1000
        formatted = f"{kbps:.1f}".rstrip("0").rstrip(".")
        return f"{formatted} kbps"
    return f"{int(numeric)} bps"


def _format_sampling_rate(value: Any) -> str:
    if value is None or value == "":
        return ""
    text = str(value).strip()
    if not text:
        return ""
    try:
        numeric = float(text)
    except ValueError:
        return text

    if numeric >= 1000:
        khz = numeric / 1000
        formatted = f"{khz:.1f}".rstrip("0").rstrip(".")
        return f"{formatted} kHz"
    return text


def _format_channels(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        channels = int(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{channels} ch"


def get_notification_fields(metadata: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """
    Extract and sanitize common fields for notification formatting.
    """
    mam_enrichment = _get_mam_enrichment(metadata)
    audio_data = mam_enrichment.get("audio")
    mam_audio = audio_data if isinstance(audio_data, dict) else {}

    title = clean_light_novel(metadata.get("title") or mam_enrichment.get("title") or "") or ""

    # Series handling - try multiple field names
    series = ""
    if metadata.get("book_series"):
        series_name = metadata.get("book_series")
        series_seq = metadata.get("book_series_sequence", "")
        if series_seq:
            series = f"{series_name} (Vol. {series_seq})"
        else:
            series = str(series_name) if series_name else ""
    elif metadata.get("series"):
        # Handle series as array or string.
        # Audnex uses key "series"; Audible scraper uses key "title".
        series_data = metadata.get("series")
        if isinstance(series_data, list) and series_data:
            s = series_data[0]
            if isinstance(s, dict):
                series_name = s.get("series") or s.get("title") or s.get("name") or ""
                series_seq = s.get("sequence") or s.get("position") or ""
                if series_name and series_seq:
                    series = f"{series_name} (Vol. {series_seq})"
                elif series_name:
                    series = series_name
        elif isinstance(series_data, str):
            series = series_data
    elif metadata.get("series_primary"):
        # Legacy format
        series_info = metadata.get("series_primary", {})
        series_name = clean_light_novel(series_info.get("name", ""))
        if series_name and series_info.get("position"):
            series = f"{series_name} (Vol. {series_info['position']})"
        elif series_name:
            series = series_name
    elif mam_enrichment.get("series"):
        series = str(mam_enrichment.get("series") or "")

    # Clean series name
    series = clean_light_novel(series) or ""

    author = metadata.get("author", "") or metadata.get("book_author", "")
    if not author:
        author = ", ".join(_clean_list(mam_enrichment.get("authors")))
    publisher = metadata.get("publisher", "") or metadata.get("book_publisher", "")

    # Narrator handling - try multiple field names
    narrators = []
    if metadata.get("narrator_list"):
        narrators = metadata.get("narrator_list", [])
    elif metadata.get("narrator"):
        # Split comma-separated narrator string
        narrator_str = metadata.get("narrator", "")
        if narrator_str:
            narrators = [n.strip() for n in narrator_str.split(",")]
    elif metadata.get("book_narrator"):
        # Split comma-separated narrator string
        narrator_str = metadata.get("book_narrator", "")
        if narrator_str:
            narrators = [n.strip() for n in narrator_str.split(",")]
    elif metadata.get("narrators_raw"):
        # Extract names from raw narrator objects
        narrators_raw = metadata.get("narrators_raw", [])
        narrators = [n.get("name", "") for n in narrators_raw if n.get("name")]

    if not narrators:
        narrators = _clean_list(mam_enrichment.get("narrators"))

    # Fallback to payload if no narrators found
    if not narrators:
        narrators = payload.get("narrators", [])

    release_date = format_release_date(
        metadata.get("release_date") or metadata.get("releaseDate") or metadata.get("book_release_date") or ""
    )
    runtime = str(
        metadata.get("runtime_minutes", "") or metadata.get("book_duration", "") or mam_audio.get("duration") or ""
    )
    category = payload.get("category", "") or metadata.get("category", "") or mam_enrichment.get("category", "")
    size = format_size(payload.get("size") or metadata.get("size") or mam_enrichment.get("size"))
    book_description = strip_html_tags(
        metadata.get("summary") or metadata.get("description", "") or metadata.get("book_description", "")
    )
    upload_notes = strip_html_tags(mam_enrichment.get("upload_notes"))
    description = book_description or upload_notes
    url = payload.get("url") or metadata.get("url")
    download_url = payload.get("download_url") or metadata.get("download_url")
    cover_url = (
        metadata.get("cover_url") or metadata.get("image") or metadata.get("cover") or metadata.get("book_cover")
    )

    language = str(metadata.get("language") or mam_enrichment.get("language") or "")
    filetype = str(mam_enrichment.get("filetype") or metadata.get("format") or "")
    isbn = str(mam_enrichment.get("isbn") or metadata.get("isbn") or "")
    asin = str(metadata.get("asin") or mam_enrichment.get("asin") or "")
    tags = str(mam_enrichment.get("tags") or metadata.get("tags") or "")
    tag_list = _split_tags(tags)
    uploader = str(mam_enrichment.get("uploader") or metadata.get("uploader") or payload.get("uploader") or "")

    audio_codec = str(mam_audio.get("codec") or "")
    audio_bitrate = _format_bitrate(mam_audio.get("bitrate"))
    audio_channels = _format_channels(mam_audio.get("channels"))
    audio_sampling_rate = _format_sampling_rate(mam_audio.get("sampling_rate"))
    audio_container = str(mam_audio.get("container") or "")

    audio_summary_parts = []
    if filetype:
        audio_summary_parts.append(filetype)
    if audio_codec and audio_codec.lower() != filetype.lower():
        audio_summary_parts.append(audio_codec)
    if audio_bitrate:
        audio_summary_parts.append(audio_bitrate)
    if audio_channels:
        audio_summary_parts.append(audio_channels)
    if audio_sampling_rate:
        audio_summary_parts.append(audio_sampling_rate)
    audio_summary = " • ".join(audio_summary_parts)

    seeders = _coerce_optional_int(mam_enrichment.get("seeders"))
    leechers = _coerce_optional_int(mam_enrichment.get("leechers"))
    times_completed = _coerce_optional_int(mam_enrichment.get("times_completed"))
    comments = _coerce_optional_int(mam_enrichment.get("comments"))
    torrent_health_parts = []
    if seeders is not None:
        torrent_health_parts.append(f"{seeders} seeders")
    if leechers is not None:
        torrent_health_parts.append(f"{leechers} leechers")
    if times_completed is not None:
        torrent_health_parts.append(f"{times_completed} completed")
    torrent_health = " • ".join(torrent_health_parts)
    comment_count_label = f"{comments} comments" if comments is not None else ""

    freeleech_flags = []
    if mam_enrichment.get("fl_vip"):
        freeleech_flags.append("VIP Freeleech")
    else:
        if mam_enrichment.get("free") or payload.get("freeleech"):
            freeleech_flags.append("Freeleech")
        if mam_enrichment.get("vip"):
            freeleech_flags.append("VIP")
    freeleech_label = " • ".join(freeleech_flags)
    added_date = format_release_date(str(mam_enrichment.get("added") or ""))

    return {
        "title": title,
        "series": series,
        "author": author,
        "publisher": publisher,
        "narrators": narrators,
        "narrator_text": ", ".join(narrators),
        "release_date": release_date,
        "runtime": runtime,
        "category": category,
        "size": size,
        "description": description,
        "url": url,
        "download_url": download_url,
        "cover_url": cover_url,
        "language": language,
        "filetype": filetype,
        "asin": asin,
        "isbn": isbn,
        "tags": tags,
        "tag_list": tag_list,
        "uploader": uploader,
        "audio_summary": audio_summary,
        "audio_codec": audio_codec,
        "audio_bitrate": audio_bitrate,
        "audio_channels": audio_channels,
        "audio_sampling_rate": audio_sampling_rate,
        "audio_container": audio_container,
        "torrent_health": torrent_health,
        "seeders": seeders,
        "leechers": leechers,
        "times_completed": times_completed,
        "comments": comments,
        "comment_count_label": comment_count_label,
        "freeleech_label": freeleech_label,
        "freeleech_flags": freeleech_flags,
        "added_date": added_date,
        "upload_notes": upload_notes,
        "has_mam_enrichment": bool(mam_enrichment),
    }
