"""
Comprehensive tests for AudnexMetadata module.
Tests all API methods, validation, cleaning functions, and CLI.
"""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.audnex_metadata import AudnexMetadata, async_main, main
from src.http_client import AsyncHttpClient


# Mark all tests in this module to skip the autouse mock_external_apis fixture
# so we can actually test the AudnexMetadata implementation
pytestmark = pytest.mark.no_mock_external_apis


# Sample API responses matching Audnex API v1.8.0 schema
SAMPLE_BOOK_RESPONSE: dict[str, Any] = {
    "asin": "B08G9PRS1K",
    "title": "Project Hail Mary",
    "subtitle": "A Novel",
    "authors": [{"asin": "B00G0WYW92", "name": "Andy Weir"}],
    "narrators": [{"name": "Ray Porter"}],
    "publisherName": "Audible Studios",
    "summary": "<p>A lone astronaut must save the earth...</p>",
    "releaseDate": "2021-05-04T00:00:00.000Z",
    "image": "https://m.media-amazon.com/images/I/91vS2L5YfEL.jpg",
    "genres": [
        {"asin": "18580606011", "name": "Science Fiction & Fantasy", "type": "genre"},
        {"asin": "18580628011", "name": "Science Fiction", "type": "tag"},
        {"asin": "18580639011", "name": "Hard Science Fiction", "type": "tag"},
    ],
    "seriesPrimary": {"asin": "B08G9TBQLD", "name": "Project Hail Mary", "position": "1"},
    "seriesSecondary": None,
    "language": "english",
    "runtimeLengthMin": 970,
    "formatType": "unabridged",
    "isbn": "9781603935470",
    "copyright": 2021,
    "isAdult": False,
    "literatureType": "fiction",
    "rating": "4.9",
    "region": "us",
}

SAMPLE_CHAPTERS_RESPONSE: dict[str, Any] = {
    "asin": "B08G9PRS1K",
    "brandIntroDurationMs": 2043,
    "brandOutroDurationMs": 5061,
    "chapters": [
        {"lengthMs": 13307, "startOffsetMs": 0, "startOffsetSec": 0, "title": "Opening Credits"},
        {"lengthMs": 5909, "startOffsetMs": 13307, "startOffsetSec": 13, "title": "Dedication"},
        {"lengthMs": 2203908, "startOffsetMs": 19216, "startOffsetSec": 19, "title": "Chapter 1"},
    ],
    "isAccurate": True,
    "region": "us",
    "runtimeLengthMs": 58252995,
    "runtimeLengthSec": 58253,
}

SAMPLE_AUTHOR_RESPONSE: dict[str, Any] = {
    "asin": "B00G0WYW92",
    "name": "Andy Weir",
    "description": "ANDY WEIR built a two-decade career as a software engineer...",
    "image": "https://images-na.ssl-images-amazon.com/images/S/amzn-author-media-prod/test.jpg",
    "region": "us",
    "genres": [
        {"asin": "18580606011", "name": "Science Fiction & Fantasy", "type": "genre"},
        {"asin": "18574597011", "name": "Mystery, Thriller & Suspense", "type": "genre"},
    ],
    "similar": [
        {"asin": "B002XLHS8Q", "name": "Adrian Tchaikovsky"},
        {"asin": "B001H6U8X0", "name": "Blake Crouch"},
    ],
}


@pytest.fixture
def mock_config():
    """Mock configuration for tests."""
    return {
        "metadata": {
            "audnex": {
                "base_url": "https://api.audnex.us",
                "regions": ["us", "uk", "ca"],
                "try_all_regions_on_error": True,
                "max_regions_to_try": 3,
                "seed_authors": False,
                "force_update": False,
            }
        }
    }


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    client = AsyncMock(spec=AsyncHttpClient)
    client.get_json = AsyncMock()
    client.fetch_first_success = AsyncMock()
    return client


class TestAudnexMetadataInit:
    """Test AudnexMetadata initialization."""

    @patch("src.audnex_metadata.load_config")
    def test_init_with_defaults(self, mock_load_config, mock_config):
        """Test initialization with default config."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        assert audnex.base_url == "https://api.audnex.us"
        assert audnex.try_all_regions is True
        assert audnex.max_regions == 3
        assert audnex.seed_authors is False
        assert audnex.force_update is False

    @patch("src.audnex_metadata.load_config")
    def test_init_with_custom_client(self, mock_load_config, mock_config, mock_http_client):
        """Test initialization with custom HTTP client."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata(client=mock_http_client)

        assert audnex._client is mock_http_client

    @patch("src.audnex_metadata.load_config")
    def test_init_with_empty_config(self, mock_load_config):
        """Test initialization with empty config uses defaults."""
        mock_load_config.return_value = {}
        audnex = AudnexMetadata()

        assert audnex.base_url == "https://api.audnex.us"
        assert audnex.try_all_regions is True
        assert audnex.max_regions == 10


class TestAudnexMetadataContextManager:
    """Test async context manager functionality."""

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    @patch("src.audnex_metadata.get_default_client")
    async def test_context_manager_entry(self, mock_get_client, mock_load_config, mock_config, mock_http_client):
        """Test async context manager entry."""
        mock_load_config.return_value = mock_config
        mock_get_client.return_value = mock_http_client

        async with AudnexMetadata() as audnex:
            assert audnex._client is mock_http_client

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    @patch("src.audnex_metadata.get_default_client")
    async def test_context_manager_exit(self, mock_get_client, mock_load_config, mock_config, mock_http_client):
        """Test async context manager exit doesn't close shared client."""
        mock_load_config.return_value = mock_config
        mock_get_client.return_value = mock_http_client

        async with AudnexMetadata():
            pass

        # Client should not be closed (managed by app lifespan)
        mock_http_client.aclose.assert_not_called()


class TestAsinValidation:
    """Test ASIN validation."""

    @patch("src.audnex_metadata.load_config")
    def test_valid_asin(self, mock_load_config, mock_config):
        """Test valid ASIN passes validation."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        result = audnex._validate_asin("B08G9PRS1K", "book")
        assert result == "B08G9PRS1K"

    @patch("src.audnex_metadata.load_config")
    def test_lowercase_asin_normalized(self, mock_load_config, mock_config):
        """Test lowercase ASIN is normalized to uppercase."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        result = audnex._validate_asin("b08g9prs1k", "book")
        assert result == "B08G9PRS1K"

    @patch("src.audnex_metadata.load_config")
    def test_asin_with_whitespace(self, mock_load_config, mock_config):
        """Test ASIN with whitespace is trimmed."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        result = audnex._validate_asin("  B08G9PRS1K  ", "book")
        assert result == "B08G9PRS1K"

    @patch("src.audnex_metadata.load_config")
    def test_empty_asin(self, mock_load_config, mock_config):
        """Test empty ASIN returns None."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        result = audnex._validate_asin("", "book")
        assert result is None

    @patch("src.audnex_metadata.load_config")
    def test_none_asin(self, mock_load_config, mock_config):
        """Test None ASIN returns None."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        result = audnex._validate_asin(None, "book")
        assert result is None

    @patch("src.audnex_metadata.load_config")
    def test_short_asin(self, mock_load_config, mock_config):
        """Test short ASIN returns None."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        result = audnex._validate_asin("B08G9PRS", "book")
        assert result is None

    @patch("src.audnex_metadata.load_config")
    def test_long_asin(self, mock_load_config, mock_config):
        """Test long ASIN returns None."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        result = audnex._validate_asin("B08G9PRS1K123", "book")
        assert result is None

    @patch("src.audnex_metadata.load_config")
    def test_non_alphanumeric_asin(self, mock_load_config, mock_config):
        """Test non-alphanumeric ASIN returns None."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        result = audnex._validate_asin("B08G9-RS1K", "book")
        assert result is None


class TestRegionValidation:
    """Test region validation."""

    @patch("src.audnex_metadata.load_config")
    def test_valid_region(self, mock_load_config, mock_config):
        """Test valid region passes."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        assert audnex._validate_region("us") == "us"
        assert audnex._validate_region("uk") == "uk"
        assert audnex._validate_region("de") == "de"

    @patch("src.audnex_metadata.load_config")
    def test_uppercase_region_normalized(self, mock_load_config, mock_config):
        """Test uppercase region is normalized."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        assert audnex._validate_region("US") == "us"
        assert audnex._validate_region("UK") == "uk"

    @patch("src.audnex_metadata.load_config")
    def test_invalid_region_defaults_to_us(self, mock_load_config, mock_config):
        """Test invalid region defaults to 'us'."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        assert audnex._validate_region("invalid") == "us"
        assert audnex._validate_region("xyz") == "us"


class TestGetBookByAsin:
    """Test get_book_by_asin method."""

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_get_book_success(self, mock_load_config, mock_config, mock_http_client):
        """Test successful book fetch."""
        mock_load_config.return_value = mock_config
        mock_http_client.fetch_first_success.return_value = (SAMPLE_BOOK_RESPONSE, "us")

        audnex = AudnexMetadata(client=mock_http_client)
        result = await audnex.get_book_by_asin("B08G9PRS1K")

        assert result is not None
        assert result["asin"] == "B08G9PRS1K"
        assert result["title"] == "Project Hail Mary"
        assert result["audnex_region"] == "us"

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_get_book_not_found(self, mock_load_config, mock_config, mock_http_client):
        """Test book not found."""
        mock_load_config.return_value = mock_config
        mock_http_client.fetch_first_success.return_value = (None, None)

        audnex = AudnexMetadata(client=mock_http_client)
        result = await audnex.get_book_by_asin("B000000000")

        assert result is None

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_get_book_invalid_asin(self, mock_load_config, mock_config, mock_http_client):
        """Test with invalid ASIN."""
        mock_load_config.return_value = mock_config

        audnex = AudnexMetadata(client=mock_http_client)
        result = await audnex.get_book_by_asin("invalid")

        assert result is None
        mock_http_client.fetch_first_success.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_get_book_with_seed_authors(self, mock_load_config, mock_config, mock_http_client):
        """Test book fetch with seed_authors parameter."""
        mock_load_config.return_value = mock_config
        mock_http_client.fetch_first_success.return_value = (SAMPLE_BOOK_RESPONSE, "us")

        audnex = AudnexMetadata(client=mock_http_client)
        await audnex.get_book_by_asin("B08G9PRS1K", seed_authors=True)

        # Check that URL factory includes seedAuthors=1
        call_args = mock_http_client.fetch_first_success.call_args
        url_factory = call_args.kwargs["url_factory"]
        url = url_factory("us")
        assert "seedAuthors=1" in url

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_get_book_with_update(self, mock_load_config, mock_config, mock_http_client):
        """Test book fetch with update parameter."""
        mock_load_config.return_value = mock_config
        mock_http_client.fetch_first_success.return_value = (SAMPLE_BOOK_RESPONSE, "us")

        audnex = AudnexMetadata(client=mock_http_client)
        await audnex.get_book_by_asin("B08G9PRS1K", update=True)

        # Check that URL factory includes update=1
        call_args = mock_http_client.fetch_first_success.call_args
        url_factory = call_args.kwargs["url_factory"]
        url = url_factory("us")
        assert "update=1" in url

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_get_book_uses_config_defaults(self, mock_load_config, mock_http_client):
        """Test book fetch uses config defaults when params not specified."""
        config = {
            "metadata": {
                "audnex": {
                    "base_url": "https://api.audnex.us",
                    "regions": ["us"],
                    "try_all_regions_on_error": False,
                    "max_regions_to_try": 1,
                    "seed_authors": True,
                    "force_update": True,
                }
            }
        }
        mock_load_config.return_value = config
        mock_http_client.fetch_first_success.return_value = (SAMPLE_BOOK_RESPONSE, "us")

        audnex = AudnexMetadata(client=mock_http_client)
        await audnex.get_book_by_asin("B08G9PRS1K")

        # Check that URL factory includes both from config
        call_args = mock_http_client.fetch_first_success.call_args
        url_factory = call_args.kwargs["url_factory"]
        url = url_factory("us")
        assert "seedAuthors=1" in url
        assert "update=1" in url


class TestGetChaptersByAsin:
    """Test get_chapters_by_asin method."""

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_get_chapters_success(self, mock_load_config, mock_config, mock_http_client):
        """Test successful chapters fetch."""
        mock_load_config.return_value = mock_config
        mock_http_client.fetch_first_success.return_value = (SAMPLE_CHAPTERS_RESPONSE, "us")

        audnex = AudnexMetadata(client=mock_http_client)
        result = await audnex.get_chapters_by_asin("B08G9PRS1K")

        assert result is not None
        assert result["asin"] == "B08G9PRS1K"
        assert result["chapter_count"] == 3
        assert result["audnex_region"] == "us"

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_get_chapters_not_found(self, mock_load_config, mock_config, mock_http_client):
        """Test chapters not found."""
        mock_load_config.return_value = mock_config
        mock_http_client.fetch_first_success.return_value = (None, None)

        audnex = AudnexMetadata(client=mock_http_client)
        result = await audnex.get_chapters_by_asin("B000000000")

        assert result is None

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_get_chapters_invalid_asin(self, mock_load_config, mock_config, mock_http_client):
        """Test with invalid ASIN."""
        mock_load_config.return_value = mock_config

        audnex = AudnexMetadata(client=mock_http_client)
        result = await audnex.get_chapters_by_asin("bad")

        assert result is None

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_get_chapters_with_update(self, mock_load_config, mock_config, mock_http_client):
        """Test chapters fetch with update parameter."""
        mock_load_config.return_value = mock_config
        mock_http_client.fetch_first_success.return_value = (SAMPLE_CHAPTERS_RESPONSE, "us")

        audnex = AudnexMetadata(client=mock_http_client)
        result = await audnex.get_chapters_by_asin("B08G9PRS1K", update=True)
        assert result is not None

        # Verify the url_factory was passed with update
        call_args = mock_http_client.fetch_first_success.call_args
        url_factory = call_args.kwargs["url_factory"]
        url = url_factory("us")
        assert "update=1" in url


class TestUrlFactoryBranches:
    """Tests specifically for url_factory branch coverage.

    These tests use a custom client implementation that actually executes
    url_factory to ensure branch coverage of the nested function.
    """

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_chapters_url_factory_with_update_true(self, mock_load_config, mock_config):
        """Test that url_factory in get_chapters_by_asin is called with update=True."""
        mock_load_config.return_value = mock_config

        # Track what URL was generated
        captured_urls = []

        class TestClient:
            """Minimal client that actually calls url_factory."""

            async def fetch_first_success(self, regions, url_factory, validator=None):
                # Actually call url_factory - this is executed within the coverage context
                url = url_factory(regions[0])
                captured_urls.append(url)
                return (SAMPLE_CHAPTERS_RESPONSE, regions[0])

        audnex = AudnexMetadata(client=TestClient())
        result = await audnex.get_chapters_by_asin("B08G9PRS1K", update=True)

        assert result is not None
        assert len(captured_urls) == 1
        assert "update=1" in captured_urls[0]

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_author_url_factory_with_update_true(self, mock_load_config, mock_config):
        """Test that url_factory in get_author_by_asin is called with update=True."""
        mock_load_config.return_value = mock_config

        captured_urls = []

        class TestClient:
            """Minimal client that actually calls url_factory."""

            async def fetch_first_success(self, regions, url_factory, validator=None):
                url = url_factory(regions[0])
                captured_urls.append(url)
                return (SAMPLE_AUTHOR_RESPONSE, regions[0])

        audnex = AudnexMetadata(client=TestClient())
        result = await audnex.get_author_by_asin("B00G0WYW92", update=True)

        assert result is not None
        assert len(captured_urls) == 1
        assert "update=1" in captured_urls[0]

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_chapters_url_factory_with_update_false(self, mock_load_config, mock_config):
        """Test that url_factory in get_chapters_by_asin works with update=False (default)."""
        mock_load_config.return_value = mock_config

        captured_urls = []

        class TestClient:
            """Minimal client that actually calls url_factory."""

            async def fetch_first_success(self, regions, url_factory, validator=None):
                url = url_factory(regions[0])
                captured_urls.append(url)
                return (SAMPLE_CHAPTERS_RESPONSE, regions[0])

        audnex = AudnexMetadata(client=TestClient())
        # No update parameter - use_update will be False
        result = await audnex.get_chapters_by_asin("B08G9PRS1K")

        assert result is not None
        assert len(captured_urls) == 1
        assert "update=1" not in captured_urls[0]  # Verify update NOT in URL

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_author_url_factory_with_update_false(self, mock_load_config, mock_config):
        """Test that url_factory in get_author_by_asin works with update=False (default)."""
        mock_load_config.return_value = mock_config

        captured_urls = []

        class TestClient:
            """Minimal client that actually calls url_factory."""

            async def fetch_first_success(self, regions, url_factory, validator=None):
                url = url_factory(regions[0])
                captured_urls.append(url)
                return (SAMPLE_AUTHOR_RESPONSE, regions[0])

        audnex = AudnexMetadata(client=TestClient())
        # No update parameter - use_update will be False
        result = await audnex.get_author_by_asin("B00G0WYW92")

        assert result is not None
        assert len(captured_urls) == 1
        assert "update=1" not in captured_urls[0]  # Verify update NOT in URL


class TestSearchAuthorByName:
    """Test search_author_by_name method."""

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_search_author_success_list(self, mock_load_config, mock_config, mock_http_client):
        """Test successful author search returning list."""
        mock_load_config.return_value = mock_config
        mock_http_client.fetch_first_success.return_value = ([SAMPLE_AUTHOR_RESPONSE], "us")

        audnex = AudnexMetadata(client=mock_http_client)
        result = await audnex.search_author_by_name("Andy Weir")

        assert len(result) == 1
        assert result[0]["name"] == "Andy Weir"

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_search_author_success_single(self, mock_load_config, mock_config, mock_http_client):
        """Test successful author search returning single result."""
        mock_load_config.return_value = mock_config
        mock_http_client.fetch_first_success.return_value = (SAMPLE_AUTHOR_RESPONSE, "us")

        audnex = AudnexMetadata(client=mock_http_client)
        result = await audnex.search_author_by_name("Andy Weir")

        assert len(result) == 1
        assert result[0]["name"] == "Andy Weir"

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_search_author_not_found(self, mock_load_config, mock_config, mock_http_client):
        """Test author search with no results."""
        mock_load_config.return_value = mock_config
        mock_http_client.fetch_first_success.return_value = (None, None)

        audnex = AudnexMetadata(client=mock_http_client)
        result = await audnex.search_author_by_name("Unknown Author")

        assert result == []

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_search_author_empty_name(self, mock_load_config, mock_config, mock_http_client):
        """Test author search with empty name."""
        mock_load_config.return_value = mock_config

        audnex = AudnexMetadata(client=mock_http_client)
        result = await audnex.search_author_by_name("")

        assert result == []
        mock_http_client.fetch_first_success.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_search_author_whitespace_name(self, mock_load_config, mock_config, mock_http_client):
        """Test author search with whitespace-only name."""
        mock_load_config.return_value = mock_config

        audnex = AudnexMetadata(client=mock_http_client)
        result = await audnex.search_author_by_name("   ")

        assert result == []


class TestGetAuthorByAsin:
    """Test get_author_by_asin method."""

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_get_author_success(self, mock_load_config, mock_config, mock_http_client):
        """Test successful author fetch."""
        mock_load_config.return_value = mock_config
        mock_http_client.fetch_first_success.return_value = (SAMPLE_AUTHOR_RESPONSE, "us")

        audnex = AudnexMetadata(client=mock_http_client)
        result = await audnex.get_author_by_asin("B00G0WYW92")

        assert result is not None
        assert result["name"] == "Andy Weir"
        assert result["audnex_region"] == "us"

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_get_author_not_found(self, mock_load_config, mock_config, mock_http_client):
        """Test author not found."""
        mock_load_config.return_value = mock_config
        mock_http_client.fetch_first_success.return_value = (None, None)

        audnex = AudnexMetadata(client=mock_http_client)
        result = await audnex.get_author_by_asin("B000000000")

        assert result is None

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_get_author_invalid_asin(self, mock_load_config, mock_config, mock_http_client):
        """Test with invalid ASIN."""
        mock_load_config.return_value = mock_config

        audnex = AudnexMetadata(client=mock_http_client)
        result = await audnex.get_author_by_asin("x")

        assert result is None

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_get_author_with_update(self, mock_load_config, mock_config, mock_http_client):
        """Test author fetch with update parameter - actually exercises url_factory."""
        mock_load_config.return_value = mock_config

        # Create a side_effect that calls url_factory to exercise the branch
        async def mock_fetch_first_success(regions, url_factory, validator):
            # Actually call url_factory to trigger coverage of if use_update branch
            url = url_factory(regions[0])
            assert "update=1" in url  # Verify update param is present
            return (SAMPLE_AUTHOR_RESPONSE, "us")

        mock_http_client.fetch_first_success.side_effect = mock_fetch_first_success

        audnex = AudnexMetadata(client=mock_http_client)
        result = await audnex.get_author_by_asin("B00G0WYW92", update=True)
        assert result is not None


class TestCleanBookMetadata:
    """Test _clean_book_metadata method."""

    @patch("src.audnex_metadata.load_config")
    def test_clean_book_metadata_full(self, mock_load_config, mock_config):
        """Test cleaning full book metadata."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        result = audnex._clean_book_metadata(SAMPLE_BOOK_RESPONSE)

        # Primary fields
        assert result["title"] == "Project Hail Mary"
        assert result["subtitle"] == "A Novel"
        assert result["author"] == "Andy Weir"
        assert result["narrator"] == "Ray Porter"
        assert result["publisher"] == "Audible Studios"
        assert result["asin"] == "B08G9PRS1K"
        assert result["isbn"] == "9781603935470"
        assert result["language"] == "English"
        assert result["duration"] == 970
        assert result["rating"] == "4.9"
        assert result["abridged"] is False

        # New API fields
        assert result["copyright"] == 2021
        assert result["isAdult"] is False
        assert result["literatureType"] == "fiction"

        # Series
        assert result["series"] is not None
        assert len(result["series"]) == 1
        assert result["series"][0]["series"] == "Project Hail Mary"
        assert result["series"][0]["sequence"] == "1"

        # Genres and tags
        assert "Science Fiction & Fantasy" in result["genres"]
        assert "Science Fiction" in result["tags"]

    @patch("src.audnex_metadata.load_config")
    def test_clean_book_metadata_minimal(self, mock_load_config, mock_config):
        """Test cleaning minimal book metadata."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        minimal_response = {
            "asin": "B000000000",
            "title": "Test Book",
            "authors": [],
            "narrators": [],
        }

        result = audnex._clean_book_metadata(minimal_response)

        assert result["title"] == "Test Book"
        assert result["author"] is None
        assert result["narrator"] is None
        assert result["series"] is None
        assert result["duration"] == 0

    @patch("src.audnex_metadata.load_config")
    def test_clean_book_metadata_with_secondary_series(self, mock_load_config, mock_config):
        """Test cleaning book with secondary series."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        response = SAMPLE_BOOK_RESPONSE.copy()
        response["seriesSecondary"] = {"name": "Sci-Fi Collection", "position": "Book 5"}

        result = audnex._clean_book_metadata(response)

        assert len(result["series"]) == 2
        assert result["series"][1]["series"] == "Sci-Fi Collection"
        assert result["series"][1]["sequence"] == "5"


class TestCleanChaptersMetadata:
    """Test _clean_chapters_metadata method."""

    @patch("src.audnex_metadata.load_config")
    def test_clean_chapters_metadata(self, mock_load_config, mock_config):
        """Test cleaning chapters metadata."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        result = audnex._clean_chapters_metadata(SAMPLE_CHAPTERS_RESPONSE)

        assert result["asin"] == "B08G9PRS1K"
        assert result["chapter_count"] == 3
        assert result["isAccurate"] is True
        assert result["brandIntroDurationMs"] == 2043
        assert result["brandIntroDurationSec"] == 2
        assert result["runtimeLengthSec"] == 58253
        assert result["runtimeLengthMin"] == 971

        # Check chapter cleaning
        assert len(result["chapters"]) == 3
        assert result["chapters"][0]["title"] == "Opening Credits"
        assert result["chapters"][0]["lengthSec"] == 13

    @patch("src.audnex_metadata.load_config")
    def test_clean_chapters_metadata_empty(self, mock_load_config, mock_config):
        """Test cleaning empty chapters."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        result = audnex._clean_chapters_metadata({"asin": "B000000000", "chapters": []})

        assert result["chapter_count"] == 0
        assert result["chapters"] == []


class TestCleanAuthorMetadata:
    """Test _clean_author_metadata method."""

    @patch("src.audnex_metadata.load_config")
    def test_clean_author_metadata(self, mock_load_config, mock_config):
        """Test cleaning author metadata."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        result = audnex._clean_author_metadata(SAMPLE_AUTHOR_RESPONSE)

        assert result["asin"] == "B00G0WYW92"
        assert result["name"] == "Andy Weir"
        assert result["description"] == "ANDY WEIR built a two-decade career as a software engineer..."
        assert result["similar_count"] == 2
        assert "Science Fiction & Fantasy" in result["genres"]
        assert result["author_name"] == "Andy Weir"

    @patch("src.audnex_metadata.load_config")
    def test_clean_author_metadata_minimal(self, mock_load_config, mock_config):
        """Test cleaning minimal author metadata."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        result = audnex._clean_author_metadata({"asin": "B000000000", "name": "Unknown"})

        assert result["name"] == "Unknown"
        assert result["similar"] is None
        assert result["genres"] is None


class TestCleanSeriesSequence:
    """Test _clean_series_sequence method."""

    @patch("src.audnex_metadata.load_config")
    def test_clean_series_sequence_integer(self, mock_load_config, mock_config):
        """Test cleaning integer sequence."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        assert audnex._clean_series_sequence("Test Series", "1") == "1"
        assert audnex._clean_series_sequence("Test Series", "10") == "10"

    @patch("src.audnex_metadata.load_config")
    def test_clean_series_sequence_decimal(self, mock_load_config, mock_config):
        """Test cleaning decimal sequence."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        assert audnex._clean_series_sequence("Test Series", "1.5") == "1.5"
        assert audnex._clean_series_sequence("Test Series", ".5") == ".5"

    @patch("src.audnex_metadata.load_config")
    def test_clean_series_sequence_with_text(self, mock_load_config, mock_config):
        """Test cleaning sequence with text."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        assert audnex._clean_series_sequence("Test Series", "Book 1") == "1"
        assert audnex._clean_series_sequence("Test Series", "Volume 2.5") == "2.5"

    @patch("src.audnex_metadata.load_config")
    def test_clean_series_sequence_empty(self, mock_load_config, mock_config):
        """Test cleaning empty sequence."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        assert audnex._clean_series_sequence("Test Series", "") == ""
        assert audnex._clean_series_sequence("Test Series", None) == ""


class TestSingleRegionMode:
    """Test single region mode (try_all_regions=False)."""

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_single_region_book_fetch(self, mock_load_config, mock_http_client):
        """Test book fetch with single region mode."""
        config = {
            "metadata": {
                "audnex": {
                    "base_url": "https://api.audnex.us",
                    "regions": ["us"],
                    "try_all_regions_on_error": False,
                    "max_regions_to_try": 1,
                    "seed_authors": False,
                    "force_update": False,
                }
            }
        }
        mock_load_config.return_value = config
        mock_http_client.fetch_first_success.return_value = (SAMPLE_BOOK_RESPONSE, "us")

        audnex = AudnexMetadata(client=mock_http_client)
        await audnex.get_book_by_asin("B08G9PRS1K", region="uk")

        # Should only try single region (uk)
        call_args = mock_http_client.fetch_first_success.call_args
        regions = call_args.kwargs["regions"]
        assert regions == ["uk"]


class TestCLI:
    """Test command line interface."""

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.AudnexMetadata")
    async def test_cli_book_lookup(self, MockAudnex):
        """Test CLI book lookup."""
        mock_instance = AsyncMock()
        mock_instance.get_book_by_asin.return_value = SAMPLE_BOOK_RESPONSE.copy()
        mock_instance.get_book_by_asin.return_value["audnex_region"] = "us"
        mock_instance.get_book_by_asin.return_value["series"] = [{"series": "Test", "sequence": "1"}]
        MockAudnex.return_value.__aenter__.return_value = mock_instance
        MockAudnex.return_value.__aexit__.return_value = None

        with patch("sys.argv", ["audnex", "B08G9PRS1K"]), patch("builtins.print"):
            await async_main()

        mock_instance.get_book_by_asin.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.AudnexMetadata")
    async def test_cli_book_with_chapters(self, MockAudnex):
        """Test CLI book lookup with chapters."""
        mock_instance = AsyncMock()
        mock_instance.get_book_by_asin.return_value = SAMPLE_BOOK_RESPONSE.copy()
        mock_instance.get_book_by_asin.return_value["audnex_region"] = "us"
        mock_instance.get_book_by_asin.return_value["series"] = None
        mock_instance.get_chapters_by_asin.return_value = {
            "chapter_count": 3,
            "runtimeLengthMin": 60,
            "isAccurate": True,
            "chapters": [
                {"title": "Ch 1", "lengthSec": 100},
                {"title": "Ch 2", "lengthSec": 100},
                {"title": "Ch 3", "lengthSec": 100},
            ],
        }
        MockAudnex.return_value.__aenter__.return_value = mock_instance
        MockAudnex.return_value.__aexit__.return_value = None

        with patch("sys.argv", ["audnex", "B08G9PRS1K", "--chapters"]), patch("builtins.print"):
            await async_main()

        mock_instance.get_chapters_by_asin.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.AudnexMetadata")
    async def test_cli_book_with_chapters_not_found(self, MockAudnex):
        """Test CLI book lookup with chapters that return None (covers 686->exit branch)."""
        mock_instance = AsyncMock()
        mock_instance.get_book_by_asin.return_value = SAMPLE_BOOK_RESPONSE.copy()
        mock_instance.get_book_by_asin.return_value["audnex_region"] = "us"
        mock_instance.get_book_by_asin.return_value["series"] = None
        # Chapters returns None - this exercises the 686->exit branch
        mock_instance.get_chapters_by_asin.return_value = None
        MockAudnex.return_value.__aenter__.return_value = mock_instance
        MockAudnex.return_value.__aexit__.return_value = None

        with patch("sys.argv", ["audnex", "B08G9PRS1K", "--chapters"]), patch("builtins.print") as mock_print:
            await async_main()

        mock_instance.get_chapters_by_asin.assert_called_once()
        # Should NOT print chapter info since chapters was None
        calls = [str(call) for call in mock_print.call_args_list]
        assert not any("Chapters" in c for c in calls)

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.AudnexMetadata")
    async def test_cli_author_search(self, MockAudnex):
        """Test CLI author search."""
        mock_instance = AsyncMock()
        mock_instance.search_author_by_name.return_value = [SAMPLE_AUTHOR_RESPONSE]
        MockAudnex.return_value.__aenter__.return_value = mock_instance
        MockAudnex.return_value.__aexit__.return_value = None

        with patch("sys.argv", ["audnex", "--search-author", "Andy Weir"]), patch("builtins.print"):
            await async_main()

        mock_instance.search_author_by_name.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.AudnexMetadata")
    async def test_cli_author_search_not_found(self, MockAudnex):
        """Test CLI author search with no results."""
        mock_instance = AsyncMock()
        mock_instance.search_author_by_name.return_value = []
        MockAudnex.return_value.__aenter__.return_value = mock_instance
        MockAudnex.return_value.__aexit__.return_value = None

        with patch("sys.argv", ["audnex", "--search-author", "Unknown"]), patch("builtins.print"):
            await async_main()

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.AudnexMetadata")
    async def test_cli_author_by_asin(self, MockAudnex):
        """Test CLI author lookup by ASIN."""
        mock_instance = AsyncMock()
        author_result = SAMPLE_AUTHOR_RESPONSE.copy()
        author_result["audnex_region"] = "us"
        author_result["genres"] = ["Science Fiction"]
        author_result["similar"] = [{"name": "Test Author"}]
        mock_instance.get_author_by_asin.return_value = author_result
        MockAudnex.return_value.__aenter__.return_value = mock_instance
        MockAudnex.return_value.__aexit__.return_value = None

        with patch("sys.argv", ["audnex", "--author", "B00G0WYW92"]), patch("builtins.print"):
            await async_main()

        mock_instance.get_author_by_asin.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.AudnexMetadata")
    async def test_cli_author_not_found(self, MockAudnex):
        """Test CLI author lookup not found."""
        mock_instance = AsyncMock()
        mock_instance.get_author_by_asin.return_value = None
        MockAudnex.return_value.__aenter__.return_value = mock_instance
        MockAudnex.return_value.__aexit__.return_value = None

        with patch("sys.argv", ["audnex", "--author", "B000000000"]), patch("builtins.print"):
            await async_main()

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.AudnexMetadata")
    async def test_cli_book_not_found(self, MockAudnex):
        """Test CLI book lookup not found."""
        mock_instance = AsyncMock()
        mock_instance.get_book_by_asin.return_value = None
        MockAudnex.return_value.__aenter__.return_value = mock_instance
        MockAudnex.return_value.__aexit__.return_value = None

        with patch("sys.argv", ["audnex", "B000000000"]), patch("builtins.print"):
            await async_main()

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.AudnexMetadata")
    async def test_cli_with_all_options(self, MockAudnex):
        """Test CLI with all options."""
        mock_instance = AsyncMock()
        mock_instance.get_book_by_asin.return_value = SAMPLE_BOOK_RESPONSE.copy()
        mock_instance.get_book_by_asin.return_value["audnex_region"] = "uk"
        mock_instance.get_book_by_asin.return_value["series"] = None
        MockAudnex.return_value.__aenter__.return_value = mock_instance
        MockAudnex.return_value.__aexit__.return_value = None

        with (
            patch("sys.argv", ["audnex", "B08G9PRS1K", "--region", "uk", "--seed-authors", "--update"]),
            patch("builtins.print"),
        ):
            await async_main()

        mock_instance.get_book_by_asin.assert_called_with(
            "B08G9PRS1K",
            region="uk",
            seed_authors=True,
            update=True,
        )

    def test_main_entry_point(self):
        """Test main() entry point."""
        with patch("src.audnex_metadata.asyncio.run") as mock_run:
            main()
            mock_run.assert_called_once()
            # Close the unawaited coroutine to avoid RuntimeWarning
            coro = mock_run.call_args[0][0]
            coro.close()

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.AudnexMetadata")
    async def test_cli_no_asin_no_author_error(self, MockAudnex):
        """Test CLI error when no ASIN or author provided."""
        mock_instance = AsyncMock()
        MockAudnex.return_value.__aenter__.return_value = mock_instance
        MockAudnex.return_value.__aexit__.return_value = None

        with patch("sys.argv", ["audnex"]), pytest.raises(SystemExit):
            await async_main()

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.AudnexMetadata")
    async def test_cli_book_with_many_chapters(self, MockAudnex):
        """Test CLI book with more than 5 chapters (tests truncation)."""
        mock_instance = AsyncMock()
        mock_instance.get_book_by_asin.return_value = SAMPLE_BOOK_RESPONSE.copy()
        mock_instance.get_book_by_asin.return_value["audnex_region"] = "us"
        mock_instance.get_book_by_asin.return_value["series"] = None
        mock_instance.get_chapters_by_asin.return_value = {
            "chapter_count": 10,
            "runtimeLengthMin": 600,
            "isAccurate": True,
            "chapters": [{"title": f"Ch {i}", "lengthSec": 100} for i in range(10)],
        }
        MockAudnex.return_value.__aenter__.return_value = mock_instance
        MockAudnex.return_value.__aexit__.return_value = None

        with patch("sys.argv", ["audnex", "B08G9PRS1K", "--chapters"]), patch("builtins.print"):
            await async_main()


class TestGetClient:
    """Test _get_client method."""

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    @patch("src.audnex_metadata.get_default_client")
    async def test_get_client_creates_default(self, mock_get_default, mock_load_config, mock_config):
        """Test _get_client creates default client when none provided."""
        mock_load_config.return_value = mock_config
        mock_client = AsyncMock()
        mock_get_default.return_value = mock_client

        audnex = AudnexMetadata()
        client = await audnex._get_client()

        assert client is mock_client
        mock_get_default.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_get_client_returns_provided(self, mock_load_config, mock_config, mock_http_client):
        """Test _get_client returns provided client."""
        mock_load_config.return_value = mock_config

        audnex = AudnexMetadata(client=mock_http_client)
        client = await audnex._get_client()

        assert client is mock_http_client


class TestValidRegions:
    """Test VALID_REGIONS class variable."""

    def test_valid_regions_contains_all_expected(self):
        """Test VALID_REGIONS contains all expected regions."""
        expected = {"au", "ca", "de", "es", "fr", "in", "it", "jp", "us", "uk"}
        assert expected == AudnexMetadata.VALID_REGIONS


class TestSingleRegionModeChapters:
    """Test single region mode for chapters."""

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_single_region_chapters_fetch(self, mock_load_config, mock_http_client):
        """Test chapters fetch with single region mode."""
        config = {
            "metadata": {
                "audnex": {
                    "base_url": "https://api.audnex.us",
                    "regions": ["us"],
                    "try_all_regions_on_error": False,
                    "max_regions_to_try": 1,
                    "seed_authors": False,
                    "force_update": False,
                }
            }
        }
        mock_load_config.return_value = config
        mock_http_client.fetch_first_success.return_value = (SAMPLE_CHAPTERS_RESPONSE, "us")

        audnex = AudnexMetadata(client=mock_http_client)
        await audnex.get_chapters_by_asin("B08G9PRS1K", region="uk")

        # Should only try single region (uk)
        call_args = mock_http_client.fetch_first_success.call_args
        regions = call_args.kwargs["regions"]
        assert regions == ["uk"]

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_single_region_chapters_with_update(self, mock_load_config, mock_http_client):
        """Test chapters fetch with update parameter in single region mode."""
        config = {
            "metadata": {
                "audnex": {
                    "base_url": "https://api.audnex.us",
                    "regions": ["us"],
                    "try_all_regions_on_error": False,
                    "max_regions_to_try": 1,
                    "seed_authors": False,
                    "force_update": False,
                }
            }
        }
        mock_load_config.return_value = config
        mock_http_client.fetch_first_success.return_value = (SAMPLE_CHAPTERS_RESPONSE, "us")

        audnex = AudnexMetadata(client=mock_http_client)
        await audnex.get_chapters_by_asin("B08G9PRS1K", update=True)

        # Verify url_factory includes update=1
        call_args = mock_http_client.fetch_first_success.call_args
        url_factory = call_args.kwargs["url_factory"]
        url = url_factory("us")
        assert "update=1" in url


class TestSingleRegionModeAuthorSearch:
    """Test single region mode for author search."""

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_single_region_author_search(self, mock_load_config, mock_http_client):
        """Test author search with single region mode."""
        config = {
            "metadata": {
                "audnex": {
                    "base_url": "https://api.audnex.us",
                    "regions": ["us"],
                    "try_all_regions_on_error": False,
                    "max_regions_to_try": 1,
                    "seed_authors": False,
                    "force_update": False,
                }
            }
        }
        mock_load_config.return_value = config
        mock_http_client.fetch_first_success.return_value = ([SAMPLE_AUTHOR_RESPONSE], "uk")

        audnex = AudnexMetadata(client=mock_http_client)
        await audnex.search_author_by_name("Andy Weir", region="uk")

        # Should only try single region (uk)
        call_args = mock_http_client.fetch_first_success.call_args
        regions = call_args.kwargs["regions"]
        assert regions == ["uk"]

        # Also test that url_factory works correctly
        url_factory = call_args.kwargs["url_factory"]
        url = url_factory("us")
        assert "name=Andy+Weir" in url or "name=Andy%20Weir" in url
        assert "region=us" in url
        assert "/authors?" in url


class TestSingleRegionModeAuthorByAsin:
    """Test single region mode for author by ASIN."""

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_single_region_author_by_asin(self, mock_load_config, mock_http_client):
        """Test author by ASIN with single region mode."""
        config = {
            "metadata": {
                "audnex": {
                    "base_url": "https://api.audnex.us",
                    "regions": ["us"],
                    "try_all_regions_on_error": False,
                    "max_regions_to_try": 1,
                    "seed_authors": False,
                    "force_update": False,
                }
            }
        }
        mock_load_config.return_value = config
        mock_http_client.fetch_first_success.return_value = (SAMPLE_AUTHOR_RESPONSE, "uk")

        audnex = AudnexMetadata(client=mock_http_client)
        await audnex.get_author_by_asin("B00G0WYW92", region="uk")

        # Should only try single region (uk)
        call_args = mock_http_client.fetch_first_success.call_args
        regions = call_args.kwargs["regions"]
        assert regions == ["uk"]

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.load_config")
    async def test_single_region_author_by_asin_with_update(self, mock_load_config, mock_http_client):
        """Test author by ASIN with update parameter."""
        config = {
            "metadata": {
                "audnex": {
                    "base_url": "https://api.audnex.us",
                    "regions": ["us"],
                    "try_all_regions_on_error": False,
                    "max_regions_to_try": 1,
                    "seed_authors": False,
                    "force_update": False,
                }
            }
        }
        mock_load_config.return_value = config
        mock_http_client.fetch_first_success.return_value = (SAMPLE_AUTHOR_RESPONSE, "us")

        audnex = AudnexMetadata(client=mock_http_client)
        await audnex.get_author_by_asin("B00G0WYW92", update=True)

        # Verify url_factory includes update=1
        call_args = mock_http_client.fetch_first_success.call_args
        url_factory = call_args.kwargs["url_factory"]
        url = url_factory("us")
        assert "update=1" in url


class TestCleanBookMetadataEdgeCases:
    """Test edge cases in _clean_book_metadata."""

    @patch("src.audnex_metadata.load_config")
    def test_clean_book_metadata_invalid_runtime(self, mock_load_config, mock_config):
        """Test _clean_book_metadata handles invalid runtime gracefully."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        data = {
            "title": "Test Book",
            "runtimeLengthMin": "not a number",  # Invalid
        }
        result = audnex._clean_book_metadata(data)

        assert result["duration"] == 0

    @patch("src.audnex_metadata.load_config")
    def test_clean_book_metadata_none_runtime(self, mock_load_config, mock_config):
        """Test _clean_book_metadata handles None runtime."""
        mock_load_config.return_value = mock_config
        audnex = AudnexMetadata()

        data = {
            "title": "Test Book",
            "runtimeLengthMin": None,
        }
        result = audnex._clean_book_metadata(data)

        assert result["duration"] == 0


class TestCLIFullCoverage:
    """Additional CLI tests for full coverage."""

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.AudnexMetadata")
    async def test_cli_book_with_extra_fields(self, MockAudnex):
        """Test CLI displays literatureType, copyright, isAdult."""
        mock_instance = AsyncMock()
        book_result = SAMPLE_BOOK_RESPONSE.copy()
        book_result["audnex_region"] = "us"
        book_result["literatureType"] = "fiction"
        book_result["copyright"] = "2021 Andy Weir"
        book_result["isAdult"] = True
        book_result["series"] = [{"series": "Test", "sequence": "1"}]
        mock_instance.get_book_by_asin.return_value = book_result
        MockAudnex.return_value.__aenter__.return_value = mock_instance
        MockAudnex.return_value.__aexit__.return_value = None

        printed = []
        with patch("sys.argv", ["audnex", "B08G9PRS1K"]):
            with patch("builtins.print", side_effect=lambda x: printed.append(str(x))):
                await async_main()

        # Verify extra fields are printed
        output = " ".join(printed)
        assert "fiction" in output
        assert "2021 Andy Weir" in output
        assert "Adult content: Yes" in output

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.AudnexMetadata")
    async def test_cli_book_without_extra_fields(self, MockAudnex):
        """Test CLI when literatureType, copyright, isAdult are not present."""
        mock_instance = AsyncMock()
        book_result = SAMPLE_BOOK_RESPONSE.copy()
        book_result["audnex_region"] = "us"
        book_result["literatureType"] = None
        book_result["copyright"] = None
        book_result["isAdult"] = False
        book_result["series"] = None
        mock_instance.get_book_by_asin.return_value = book_result
        MockAudnex.return_value.__aenter__.return_value = mock_instance
        MockAudnex.return_value.__aexit__.return_value = None

        printed = []
        with patch("sys.argv", ["audnex", "B08G9PRS1K"]):
            with patch("builtins.print", side_effect=lambda x: printed.append(str(x))):
                await async_main()

        # Verify extra fields are NOT printed
        output = " ".join(printed)
        assert "Adult content" not in output
        assert "Type:" not in output
        assert "Copyright:" not in output

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.AudnexMetadata")
    async def test_cli_author_with_full_details(self, MockAudnex):
        """Test CLI author with description, genres, and similar authors."""
        mock_instance = AsyncMock()
        author_result = SAMPLE_AUTHOR_RESPONSE.copy()
        author_result["audnex_region"] = "us"
        author_result["description"] = "A long description about the author that goes on and on..." + "x" * 300
        author_result["genres"] = ["Science Fiction", "Fantasy"]
        author_result["similar"] = [{"name": "Author 1"}, {"name": "Author 2"}]
        mock_instance.get_author_by_asin.return_value = author_result
        MockAudnex.return_value.__aenter__.return_value = mock_instance
        MockAudnex.return_value.__aexit__.return_value = None

        printed = []
        with patch("sys.argv", ["audnex", "--author", "B00G0WYW92"]):
            with patch("builtins.print", side_effect=lambda x: printed.append(str(x))):
                await async_main()

        # Verify author details are printed
        output = " ".join(printed)
        assert "Description:" in output
        assert "Genres:" in output
        assert "Similar authors:" in output

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.AudnexMetadata")
    async def test_cli_book_with_many_chapters_truncation(self, MockAudnex):
        """Test CLI truncates chapter list after 5 chapters."""
        mock_instance = AsyncMock()
        book_result = SAMPLE_BOOK_RESPONSE.copy()
        book_result["audnex_region"] = "us"
        book_result["series"] = None
        mock_instance.get_book_by_asin.return_value = book_result

        # Create more than 5 chapters
        chapters = {
            "chapter_count": 10,
            "runtimeLengthMin": 600,
            "isAccurate": True,
            "chapters": [{"title": f"Chapter {i}", "lengthSec": 100} for i in range(10)],
        }
        mock_instance.get_chapters_by_asin.return_value = chapters
        MockAudnex.return_value.__aenter__.return_value = mock_instance
        MockAudnex.return_value.__aexit__.return_value = None

        printed = []
        with patch("sys.argv", ["audnex", "B08G9PRS1K", "--chapters"]):
            with patch("builtins.print", side_effect=lambda x: printed.append(str(x))):
                await async_main()

        # Verify truncation message is printed
        output = " ".join(printed)
        assert "more chapters" in output

    @pytest.mark.asyncio
    @patch("src.audnex_metadata.AudnexMetadata")
    async def test_cli_author_no_description(self, MockAudnex):
        """Test CLI author with no description."""
        mock_instance = AsyncMock()
        author_result = SAMPLE_AUTHOR_RESPONSE.copy()
        author_result["audnex_region"] = "us"
        author_result["description"] = None
        author_result["genres"] = None
        author_result["similar"] = None
        mock_instance.get_author_by_asin.return_value = author_result
        MockAudnex.return_value.__aenter__.return_value = mock_instance
        MockAudnex.return_value.__aexit__.return_value = None

        printed = []
        with patch("sys.argv", ["audnex", "--author", "B00G0WYW92"]):
            with patch("builtins.print", side_effect=lambda x: printed.append(str(x))):
                await async_main()

        # Verify nothing crashes and basic info is printed
        output = " ".join(printed)
        assert "Andy Weir" in output
        # These should NOT be present
        assert "Description:" not in output
        assert "Genres:" not in output
        assert "Similar authors:" not in output
