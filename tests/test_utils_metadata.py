import pytest

from src.utils import (
    strip_html_tags,
    clean_author_list,
    validate_payload,
    build_notification_message
)
from src.metadata import clean_metadata, fetch_metadata


def test_strip_html_tags(sample_html):
    cleaned = strip_html_tags(sample_html)
    # Paragraphs should be separated by blank line
    assert "First paragraph." in cleaned
    assert "Second" in cleaned
    assert "<p>" not in cleaned
    # Ensure one blank line (two newlines) between paragraphs
    assert cleaned.count("\n\n") == 1


def test_clean_author_list(sample_authors):
    result = clean_author_list(sample_authors)
    assert result == ["John Doe"]


def test_validate_payload(sample_payload):
    # Required keys are name, url, download_url
    req = ["name", "url", "download_url"]
    assert validate_payload(sample_payload, req)
    assert not validate_payload({}, req)


def test_clean_metadata(sample_item):
    md = clean_metadata(sample_item)
    # Author cleaned (translators/illustrators removed)
    assert md['author'] == "Author One"
    assert md['authors_raw'] == sample_item['authors']
    # Narrator fields
    assert md['narrator'] == "Narrator A"
    assert md['narrators'] == ["Narrator A"]
    # Series display and raw
    assert md['series'] == "Series Name (Vol. 1)"
    assert md['series_primary'] == sample_item['seriesPrimary']
    # Cover URLs
    assert md['cover'] == sample_item['image']
    assert md['cover_url'] == sample_item['image']
    # Genres and tags
    assert md['genres'] == ["Fantasy"]
    assert md['tags'] == "Epic"


def test_build_notification_message(sample_item, sample_payload):
    md = clean_metadata(sample_item)
    msg = build_notification_message(md, sample_payload, "token123", "http://base")
    # Basic fields
    assert "🎧 Title:" in msg
    assert "Test Title" in msg
    assert "🔗 Series:" in msg
    # Description should be stripped of HTML and show summary (summary takes priority over description)
    assert "<p>" not in msg
    assert "Summary paragraph." in msg
    # Approve link present
    assert "/approve/token123" in msg


def test_fetch_metadata_invalid():
    with pytest.raises(ValueError):
        fetch_metadata({})
