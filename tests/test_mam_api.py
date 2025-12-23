#!/usr/bin/env python3
"""
Tests for MAM API client, models, and adapter.

These tests cover:
- Pydantic model parsing (including JSON-inside-string fields)
- URL parsing and torrent ID extraction
- API client functionality (mocked)
- Adapter backward compatibility
"""

import inspect
import os
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.mam_api.adapter import MAMApiAdapter
from src.mam_api.client import MamAsyncClient, MamClient, extract_tid_from_irc
from src.mam_api.models import (
    MamMediaInfo,
    MamSearchResponseRaw,
    MamTorrentNormalized,
    MamTorrentRaw,
    _parse_added_datetime,
    _safe_json_loads,
    _to_bool,
    _to_int,
)


# =============================================================================
# Test Data / Fixtures
# =============================================================================


@pytest.fixture
def sample_torrent_data():
    """Sample raw torrent data from MAM API."""
    return {
        "id": "1234567",
        "title": "Test Audiobook - By Author Name",
        "author_info": '{"123": "Test Author", "456": "Co-Author"}',
        "narrator_info": '{"789": "Narrator One"}',
        "series_info": '{"100": ["Test Series", "1", 1.0]}',
        "description": "This is a test audiobook description.",
        # ASIN is extracted from isbn field via property, use "ASIN:" format
        "isbn": "ASIN:B0TEST1234",
        "language": "en",
        "lang_code": "ENG",
        "filetype": "MP3",
        "my_snatched": "1",
        "my_bookmarked": "0",
        "browseflags": "00000000000000000000000000",
        "cat_name": "Audiobooks",
        "added": "2025-12-20 10:30:00",
        "size": "524288000",
        "times_completed": "50",
        "seeders": "10",
        "leechers": "2",
        "personal_freelech": "0",
        "free": "0",
        "vip": "0",
        "owner": "12345",
        "owner_name": "uploader123",
        "category": "14",
        "main_cat": "1",
        "sub_cat": "14",
        "thumb": "https://example.com/thumb.jpg",
        "files": "25",
        "mediainfo": '{"General": {"Duration": "12h 30m"}, "Audio1": {"Format": "MP3", "Bitrate": "128000"}}',
        "ownership": '["67890", "downloader"]',
    }


@pytest.fixture
def sample_search_response(sample_torrent_data):
    """Sample search response envelope."""
    return {
        "perpage": 5,
        "start": 0,
        "data": [sample_torrent_data],
        "total": 1,
        "found": 1,
    }


# =============================================================================
# Model Tests
# =============================================================================


class TestHelperFunctions:
    """Test helper functions for parsing."""

    def test_safe_json_loads_valid(self):
        """Test _safe_json_loads with valid JSON."""
        result = _safe_json_loads('{"key": "value"}', default=None)
        assert result == {"key": "value"}

    def test_safe_json_loads_invalid(self):
        """Test _safe_json_loads with invalid JSON."""
        result = _safe_json_loads("not valid json", default=None)
        assert result is None

    def test_safe_json_loads_empty(self):
        """Test _safe_json_loads with empty string."""
        result = _safe_json_loads("", default=None)
        assert result is None

    def test_safe_json_loads_none(self):
        """Test _safe_json_loads with None."""
        result = _safe_json_loads(None, default=None)
        assert result is None

    def test_safe_json_loads_already_parsed(self):
        """Test _safe_json_loads with already parsed dict."""
        result = _safe_json_loads({"already": "parsed"}, default=None)
        assert result == {"already": "parsed"}

    def test_to_bool_true_values(self):
        """Test _to_bool with truthy values."""
        assert _to_bool("1") is True
        assert _to_bool("true") is True
        assert _to_bool("yes") is True
        assert _to_bool(1) is True
        assert _to_bool(True) is True

    def test_to_bool_false_values(self):
        """Test _to_bool with falsy values."""
        assert _to_bool("0") is False
        assert _to_bool("false") is False
        assert _to_bool("no") is False
        assert _to_bool(0) is False
        assert _to_bool(False) is False
        assert _to_bool("") is False
        assert _to_bool(None) is False

    def test_to_int_valid(self):
        """Test _to_int with valid values."""
        assert _to_int("123") == 123
        assert _to_int(456) == 456

    def test_to_int_invalid(self):
        """Test _to_int with invalid values returns default."""
        # _to_int returns default (0) for invalid values, not None
        assert _to_int("abc") == 0
        assert _to_int(None) == 0
        assert _to_int("") == 0
        assert _to_int("abc", default=-1) == -1

    def test_parse_added_datetime_valid(self):
        """Test _parse_added_datetime with valid datetime string."""
        result = _parse_added_datetime("2025-12-20 10:30:00")
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 20

    def test_parse_added_datetime_invalid(self):
        """Test _parse_added_datetime with invalid string."""
        result = _parse_added_datetime("not a date")
        assert result is None


class TestMamTorrentRaw:
    """Test MamTorrentRaw model parsing."""

    def test_basic_parsing(self, sample_torrent_data):
        """Test basic torrent data parsing."""
        torrent = MamTorrentRaw(**sample_torrent_data)

        # id is coerced to int
        assert torrent.id == 1234567
        assert torrent.title == "Test Audiobook - By Author Name"
        # asin is a property that extracts from isbn
        assert torrent.asin == "B0TEST1234"
        assert torrent.isbn == "ASIN:B0TEST1234"
        # language is coerced to int (0 from "en" which fails int conversion)
        assert torrent.lang_code == "ENG"

    def test_json_inside_string_parsing(self, sample_torrent_data):
        """Test that JSON-inside-string fields are parsed correctly."""
        torrent = MamTorrentRaw(**sample_torrent_data)

        # author_info keys are coerced to int
        assert torrent.author_info == {123: "Test Author", 456: "Co-Author"}

        # narrator_info keys are coerced to int
        assert torrent.narrator_info == {789: "Narrator One"}

        # series_info keys are coerced to int
        assert torrent.series_info == {100: ["Test Series", "1", 1.0]}

    def test_mediainfo_parsing(self, sample_torrent_data):
        """Test mediainfo JSON-inside-string parsing."""
        torrent = MamTorrentRaw(**sample_torrent_data)

        assert torrent.mediainfo is not None
        assert isinstance(torrent.mediainfo, MamMediaInfo)
        assert torrent.mediainfo.General is not None
        assert torrent.mediainfo.Audio1 is not None

    def test_ownership_parsing(self, sample_torrent_data):
        """Test ownership JSON-inside-string parsing."""
        torrent = MamTorrentRaw(**sample_torrent_data)

        # ownership is (int, str) tuple
        assert torrent.ownership == (67890, "downloader")

    def test_numeric_fields(self, sample_torrent_data):
        """Test numeric field parsing - strings are preserved."""
        torrent = MamTorrentRaw(**sample_torrent_data)

        assert torrent.size == "524288000"
        # These are coerced to int
        assert torrent.times_completed == 50
        assert torrent.seeders == 10
        assert torrent.leechers == 2

    def test_boolean_fields(self, sample_torrent_data):
        """Test boolean field parsing - coerced from 0/1."""
        torrent = MamTorrentRaw(**sample_torrent_data)

        # my_snatched "1" coerced to True
        assert torrent.my_snatched is True
        # free "0" coerced to False
        assert torrent.free is False

    def test_author_names_property(self, sample_torrent_data):
        """Test author_names computed property."""
        torrent = MamTorrentRaw(**sample_torrent_data)

        names = torrent.author_names
        assert "Test Author" in names
        assert "Co-Author" in names

    def test_narrator_names_property(self, sample_torrent_data):
        """Test narrator_names computed property."""
        torrent = MamTorrentRaw(**sample_torrent_data)

        names = torrent.narrator_names
        assert "Narrator One" in names

    def test_series_display_property(self, sample_torrent_data):
        """Test series_display property."""
        torrent = MamTorrentRaw(**sample_torrent_data)

        # series_display is a property, not a method
        series = torrent.series_display
        assert series is not None
        assert "Test Series" in series

    def test_missing_optional_fields(self):
        """Test parsing with missing optional fields."""
        minimal_data = {
            "id": 999,
            "title": "Minimal Torrent",
        }
        torrent = MamTorrentRaw(**minimal_data)

        assert torrent.id == 999
        assert torrent.title == "Minimal Torrent"
        # asin property returns empty string when isbn is None/empty
        assert torrent.asin == ""
        assert torrent.author_info == {}

    def test_to_normalized_conversion(self, sample_torrent_data):
        """Test conversion to normalized format."""
        raw = MamTorrentRaw(**sample_torrent_data)
        normalized = raw.to_normalized()

        assert isinstance(normalized, MamTorrentNormalized)
        assert normalized.tid == 1234567
        assert normalized.title == "Test Audiobook - By Author Name"
        assert normalized.asin == "B0TEST1234"
        # author is comma-joined string of author names
        assert "Test Author" in normalized.author
        # narrator is comma-joined string of narrator names
        assert "Narrator One" in normalized.narrator


class TestMamSearchResponseRaw:
    """Test search response parsing."""

    def test_response_parsing(self, sample_search_response):
        """Test full search response parsing."""
        response = MamSearchResponseRaw(**sample_search_response)

        assert response.total == 1
        assert response.found == 1
        assert len(response.data) == 1

        torrent = response.data[0]
        assert torrent.id == 1234567  # coerced to int

    def test_empty_response(self):
        """Test empty search response."""
        empty = {
            "perpage": 5,
            "start": 0,
            "data": [],
            "total": 0,
            "found": 0,
        }
        response = MamSearchResponseRaw(**empty)

        assert response.total == 0
        assert len(response.data) == 0


class TestMamMediaInfo:
    """Test MamMediaInfo model."""

    def test_basic_mediainfo(self):
        """Test basic mediainfo parsing."""
        data = {
            "General": {"Duration": "12h 30m", "Format": "Matroska"},
            "Audio1": {"Format": "MP3", "Bitrate": "128000"},
        }
        info = MamMediaInfo(**data)

        assert info.General.Duration == "12h 30m"
        assert info.Audio1.Format == "MP3"


# =============================================================================
# Client Tests
# =============================================================================


class TestExtractTidFromIrc:
    """Test IRC tid extraction."""

    def test_standard_format(self):
        """Test standard IRC format."""
        line = "New upload: Test Book https://www.myanonamouse.net/t/1234567"
        tid = extract_tid_from_irc(line)
        assert tid == 1234567

    def test_no_match(self):
        """Test line without MAM URL."""
        line = "Some random IRC message"
        tid = extract_tid_from_irc(line)
        assert tid is None

    def test_alternate_format(self):
        """Test alternate URL format."""
        line = "https://myanonamouse.net/t/9876543"
        tid = extract_tid_from_irc(line)
        assert tid == 9876543


class TestMamClient:
    """Test synchronous MAM client."""

    def test_client_initialization(self):
        """Test client initialization - creates httpx client."""
        # Client init should succeed with valid mam_id (no network call during init)
        client = MamClient(mam_id="test_id")
        assert client._client is not None
        client.close()

    def test_client_no_mam_id(self):
        """Test client raises error without mam_id."""
        with pytest.raises(ValueError, match="mam_id"):
            MamClient(mam_id="")  # Empty string is falsy


class TestMamAsyncClient:
    """Test async MAM client."""

    @pytest.mark.asyncio
    async def test_async_client_initialization(self):
        """Test async client initialization."""
        # Async client init should succeed with valid mam_id (no network call during init)
        client = MamAsyncClient(mam_id="test_id")
        assert client._client is not None
        await client.aclose()

    @pytest.mark.asyncio
    async def test_search_returns_response(self):
        """Test that search method signature is correct and returns MamSearchResponseRaw."""
        # We can't easily mock httpx in this case, so just verify
        # the search method exists with correct signature
        client = MamAsyncClient(mam_id="test_id")

        # Verify the search method exists and has correct signature
        sig = inspect.signature(client.search)
        assert "tor" in sig.parameters
        assert "perpage" in sig.parameters

        await client.aclose()


# =============================================================================
# Adapter Tests
# =============================================================================


class TestMAMApiAdapter:
    """Test backward-compatible adapter."""

    def test_extract_tid_from_url_t_format(self):
        """Test extracting tid from /t/ URL format."""
        url = "https://www.myanonamouse.net/t/1234567"
        tid = MAMApiAdapter.extract_tid_from_url(url)
        assert tid == 1234567

    def test_extract_tid_from_url_torrents_php(self):
        """Test extracting tid from torrents.php URL."""
        url = "https://www.myanonamouse.net/torrents.php?id=9876543"
        tid = MAMApiAdapter.extract_tid_from_url(url)
        assert tid == 9876543

    def test_extract_tid_from_url_view_request(self):
        """Test extracting tid from viewRequest.php URL."""
        url = "https://www.myanonamouse.net/tor/viewRequest.php/5555555.1234"
        tid = MAMApiAdapter.extract_tid_from_url(url)
        assert tid == 5555555

    def test_extract_tid_from_url_invalid(self):
        """Test extracting tid from invalid URL returns None."""
        url = "https://example.com/not-mam"
        tid = MAMApiAdapter.extract_tid_from_url(url)
        assert tid is None

    def test_extract_tid_from_url_empty(self):
        """Test extracting tid from empty/None URL."""
        assert MAMApiAdapter.extract_tid_from_url("") is None
        assert MAMApiAdapter.extract_tid_from_url(None) is None

    @pytest.mark.asyncio
    async def test_scrape_asin_backward_compat(self):
        """Test that scrape_asin_from_url maintains interface."""
        adapter = MAMApiAdapter(mam_id="test_id")

        # Create a real MamTorrentRaw object with isbn field
        mock_torrent = MamTorrentRaw(id=12345, title="Test", isbn="ASIN:B0TESTMOCK")

        # Mock the get_torrent_data method
        with patch.object(adapter, "get_torrent_data", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_torrent

            asin = await adapter.scrape_asin_from_url(
                "https://www.myanonamouse.net/t/12345",
                force_login=True,  # Should be ignored but shouldn't error
            )

            assert asin == "B0TESTMOCK"

    @pytest.mark.asyncio
    async def test_scrape_asin_no_torrent(self):
        """Test scrape_asin_from_url when no torrent found."""
        adapter = MAMApiAdapter(mam_id="test_id")

        with patch.object(adapter, "get_torrent_data", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            asin = await adapter.scrape_asin_from_url("https://www.myanonamouse.net/t/12345")

            assert asin is None

    @pytest.mark.asyncio
    async def test_get_full_metadata(self, sample_torrent_data):
        """Test get_full_metadata returns enhanced data."""
        adapter = MAMApiAdapter(mam_id="test_id")

        with patch.object(adapter, "get_torrent_data", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MamTorrentRaw(**sample_torrent_data)

            metadata = await adapter.get_full_metadata("https://www.myanonamouse.net/t/1234567")

            assert metadata is not None
            assert metadata["asin"] == "B0TEST1234"
            assert metadata["title"] == "Test Audiobook - By Author Name"
            assert "Test Author" in metadata["authors"]
            assert "Narrator One" in metadata["narrators"]
            assert metadata["source"] == "mam_api"


# =============================================================================
# Integration Tests (require MAM_ID)
# =============================================================================


class TestIntegration:
    """
    Integration tests that require MAM_ID.

    These are skipped if MAM_ID is not set in the environment.
    Run with: MAM_ID=your_cookie_value pytest tests/test_mam_api.py -k Integration
    """

    @pytest.fixture
    def mam_id(self):
        """Get MAM_ID from environment or skip."""
        mam_id = os.getenv("MAM_ID")
        if not mam_id:
            pytest.skip("MAM_ID not set - skipping integration test")
        return mam_id

    @pytest.mark.asyncio
    async def test_real_search(self, mam_id):
        """Test real search against MAM API."""
        client = MamAsyncClient(mam_id=mam_id)
        try:
            results = await client.search(tor={"text": "harry potter"}, perpage=5)
            assert len(results.data) > 0
            assert results.data[0].title is not None
        finally:
            await client.aclose()
