import time

import pytest

import src.db as dbmod
from src.db import delete_request, get_request, save_request
from src.metadata import clean_metadata
from src.utils import (
    build_notification_message,
    clean_author_list,
    format_release_date,
    format_size,
    strip_html_tags,
    validate_payload,
)


def test_strip_html_tags_empty():
    assert strip_html_tags("") == ""
    assert strip_html_tags(None) == ""


def test_format_release_date_variants():
    assert format_release_date("") == ""
    assert format_release_date("2020-01-01T00:00:00Z").startswith("2020-01-01")
    assert format_release_date("2020-01-01") == "2020-01-01"


def test_format_size():
    assert format_size(1024 * 1024) == "1.00 MB"
    assert format_size(1024 * 1024 * 1024) == "1.00 GB"
    assert format_size(None) == "?"
    assert format_size("notanumber") == "?"


def test_clean_author_list_edge_cases():
    assert clean_author_list([]) == []
    assert clean_author_list([{"name": "Jane Illustrator"}]) == []
    assert clean_author_list([{"name": "Jane Doe"}]) == ["Jane Doe"]


def test_validate_payload_missing_keys():
    payload = {"name": "A"}
    required = ["name", "url", "download_url"]
    assert not validate_payload(payload, required)


def test_build_notification_message_fields(sample_item, sample_payload):
    md = clean_metadata(sample_item)
    msg = build_notification_message(md, sample_payload, "tok", "http://base")
    assert "🎧 Title:" in msg
    assert "🔗 Series:" in msg
    assert "Test Title" in msg
    assert "http://example.com" in msg


def test_db_token_lifecycle():
    token = "tok123"
    meta = {"foo": "bar"}
    payload = {"baz": 1}
    save_request(token, meta, payload)
    result = get_request(token)
    assert result is not None
    assert result["metadata"] == meta
    assert result["payload"] == payload
    delete_request(token)
    assert get_request(token) is None


def test_db_token_expiry(monkeypatch):
    token = "tok_expire"
    meta = {"foo": "bar"}
    payload = {"baz": 1}
    save_request(token, meta, payload)
    # Simulate expiry by patching time
    old_time = time.time
    dbmod.TTL = 1
    monkeypatch.setattr(time, "time", lambda: old_time() + 3600)
    assert get_request(token) is None
    monkeypatch.setattr(time, "time", old_time)
    delete_request(token)


@pytest.mark.usefixtures("sample_item", "sample_payload")
def test_get_notification_fields(sample_item, sample_payload):
    from src.metadata import clean_metadata
    from src.utils import get_notification_fields

    md = clean_metadata(sample_item)
    # Add size to payload for this test
    payload_with_size = {**sample_payload, "size": 1024 * 1024 * 100}  # 100 MB
    fields = get_notification_fields(md, payload_with_size)
    # Basic keys
    assert fields["title"] == "Test Title"
    assert fields["series"] == "Series Name (Vol. 1)"
    # Date stripped to YYYY-MM-DD
    assert fields["release_date"] == "2020-01-01"
    # URLs preserved
    assert fields["url"] == sample_payload["url"]
    assert fields["download_url"] == sample_payload["download_url"]
    # Size formatted
    assert fields["size"].endswith("MB") or fields["size"].endswith("GB")


def test_get_notification_fields_light_novel():
    from src.utils import get_notification_fields

    # Simulate light novel title
    meta = {
        "title": "My Story (Light Novel)",
        "series_primary": {"name": "Saga (light novel)", "position": "2"},
        "author": "Auth",
        "narrators": ["N1"],
        "release_date": "2021-12-12T05:00:00Z",
        "description": "Desc",
    }
    payload = {"url": "u", "download_url": "d", "size": 2048}
    fields = get_notification_fields(meta, payload)
    assert fields["title"] == "My Story"
    assert fields["series"] == "Saga (Vol. 2)"
    assert fields["release_date"] == "2021-12-12"
    assert fields["size"] == "2.00 KB"


def test_get_notification_fields_no_size():
    from src.utils import get_notification_fields

    meta = {"title": "Test", "author": "Auth"}
    payload = {"url": "u", "download_url": "d"}  # No size
    fields = get_notification_fields(meta, payload)
    assert fields["size"] == "?"
    assert fields["title"] == "Test"
    assert fields["series"] == ""  # Empty series
