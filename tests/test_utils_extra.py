import time

import pytest

from src.db import delete_request, get_request, save_request
from src.metadata import clean_metadata
from src.utils import (
    _format_sampling_rate,
    build_notification_message,
    clean_author_list,
    format_release_date,
    format_size,
    get_notification_fields,
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
    from unittest.mock import patch

    token = "tok_expire"
    meta = {"foo": "bar"}
    payload = {"baz": 1}

    # Use short TTL and time travel
    with patch("src.db._get_ttl", return_value=1):
        save_request(token, meta, payload)

        # Simulate expiry by advancing time
        old_time = time.time
        monkeypatch.setattr(time, "time", lambda: old_time() + 3600)
        assert get_request(token) is None

    # Clean up
    monkeypatch.setattr(time, "time", old_time)
    delete_request(token)


@pytest.mark.usefixtures("sample_item", "sample_payload")
def test_get_notification_fields(sample_item, sample_payload):
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
    meta = {"title": "Test", "author": "Auth"}
    payload = {"url": "u", "download_url": "d"}  # No size
    fields = get_notification_fields(meta, payload)
    assert fields["size"] == ""
    assert fields["title"] == "Test"
    assert fields["series"] == ""  # Empty series


def test_get_notification_fields_uses_payload_release_date():
    fields = get_notification_fields({"title": "Test"}, {"release_date": "2026-07-20T12:00:00Z"})

    assert fields["release_date"] == "2026-07-20"


def test_format_sampling_rate_below_one_khz_uses_hz():
    assert _format_sampling_rate("800") == "800 Hz"


def test_get_notification_fields_with_mam_enrichment():
    meta = {
        "title": "",
        "mam_enrichment": {
            "title": "Torrent Title",
            "uploader": "UploaderUser",
            "authors": ["MAM Author"],
            "narrators": ["MAM Narrator"],
            "series": "Series Name #1",
            "language": "ENG",
            "filetype": "MP3",
            "asin": "B0TEST1234",
            "isbn": "ASIN:B0TEST1234",
            "tags": "mystery, thriller",
            "upload_notes": "<p>Encoded from CD</p>",
            "added": "2025-12-20T10:30:00+00:00",
            "seeders": 10,
            "leechers": 2,
            "times_completed": 50,
            "comments": 12,
            "free": True,
            "audio": {
                "duration": "12h 30m",
                "codec": "AAC / xHE-AAC / USAC",
                "bitrate": "128000",
                "channels": 2,
                "sampling_rate": "44100",
            },
        },
    }
    payload = {"url": "u", "download_url": "d", "size": 1024 * 1024 * 500}

    fields = get_notification_fields(meta, payload)

    assert fields["title"] == "Torrent Title"
    assert fields["author"] == "MAM Author"
    assert fields["narrators"] == ["MAM Narrator"]
    assert fields["series"] == "Series Name #1"
    assert fields["runtime"] == "12h 30m"
    assert fields["audio_summary"] == "MP3 • AAC / xHE-AAC / USAC • 128 kbps • 2 ch • 44.1 kHz"
    assert fields["torrent_health"] == "10 seeders • 2 leechers • 50 completed"
    assert fields["freeleech_label"] == "Freeleech"
    assert fields["added_date"] == "2025-12-20"
    assert fields["description"] == "Encoded from CD"
    assert fields["tag_list"] == ["mystery", "thriller"]
    assert fields["uploader"] == "UploaderUser"
    assert fields["comment_count_label"] == "12 comments"


def test_get_notification_fields_audible_series_key():
    """Audible scraper uses 'title' inside series items, not 'series'."""
    meta = {
        "title": "The Angel Next Door Spoils Me Rotten, Vol. 3",
        "series": [{"title": "The Angel Next Door Spoils Me Rotten", "sequence": "3"}],
        "releaseDate": "2023-06-27",
        "author": "Saekisan",
        "narrators": ["Greg D. Barnett"],
    }
    payload = {}
    fields = get_notification_fields(meta, payload)
    assert fields["series"] == "The Angel Next Door Spoils Me Rotten (Vol. 3)"
    assert fields["release_date"] == "2023-06-27"


def test_get_notification_fields_audible_series_no_sequence():
    """Audible series item with title but no sequence."""
    meta = {
        "title": "Some Book",
        "series": [{"title": "Some Series", "sequence": ""}],
        "releaseDate": "2024-01-15T00:00:00Z",
    }
    payload = {}
    fields = get_notification_fields(meta, payload)
    assert fields["series"] == "Some Series"
    assert fields["release_date"] == "2024-01-15"
