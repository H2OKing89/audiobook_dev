"""
Comprehensive tests for MetadataCoordinator.

Tests cover:
- Initialization and configuration
- get_metadata_from_webhook workflow (MAM → Audnex → Audible fallback)
- get_metadata_by_asin direct lookup
- search_metadata title/author search
- get_enhanced_metadata chapter enrichment
- Error handling branches
- CLI main function
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.metadata_coordinator import MetadataCoordinator, main


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_config():
    """Mock config with test values."""
    return {
        "mam": {
            "cookie": "test_cookie",
            "api_key": "test_api_key",
        },
        "metadata": {
            "audnex": {
                "base_url": "https://api.audnex.us",
                "seed_authors": True,
                "force_update": False,
            },
            "audible": {
                "base_url": "https://api.audible.com",
            },
        },
    }


@pytest.fixture
def coordinator(mock_config):
    """Create a MetadataCoordinator with mocked dependencies."""
    with patch("src.metadata_coordinator.load_config", return_value=mock_config):
        with patch("src.metadata_coordinator.MAMApiAdapter") as mock_mam:
            with patch("src.metadata_coordinator.AudnexMetadata") as mock_audnex:
                with patch("src.metadata_coordinator.AudibleScraper") as mock_audible:
                    # Set up mock instances
                    mock_mam_instance = MagicMock()
                    mock_audnex_instance = MagicMock()
                    mock_audible_instance = MagicMock()

                    mock_mam.return_value = mock_mam_instance
                    mock_audnex.return_value = mock_audnex_instance
                    mock_audible.return_value = mock_audible_instance

                    coord = MetadataCoordinator()
                    # Ensure our mock instances are assigned
                    coord.mam_scraper = mock_mam_instance
                    coord.audnex = mock_audnex_instance
                    coord.audible = mock_audible_instance

                    # Yield keeps the context alive for the test
                    yield coord


@pytest.fixture
def sample_webhook_payload():
    """Sample webhook payload from Prowlarr/Sonarr."""
    return {
        "name": "The Hobbit by J.R.R. Tolkien [Audiobook]",
        "url": "https://www.myanonamouse.net/t/12345",
        "download_url": "https://www.myanonamouse.net/download.php?id=12345&token=abc",
        "indexer": "MyAnonamouse",
        "category": "Audiobooks",
        "size": 524288000,
        "seeders": 15,
        "leechers": 2,
        "quality": "MP3",
        "format": "128kbps",
        "language": "English",
        "uploader": "test_user",
        "upload_date": "2025-01-01",
        "freeleech": True,
    }


@pytest.fixture
def sample_audnex_metadata():
    """Sample metadata from Audnex API."""
    return {
        "asin": "B0TEST1234",
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "narrator": "Martin Freeman",
        "publisher": "HarperAudio",
        "publishedYear": 2012,
        "duration": 680,
        "description": "Bilbo Baggins is a hobbit...",
        "series": [{"title": "Middle-earth", "sequence": "1"}],
        "audnex_region": "us",
    }


@pytest.fixture
def sample_audible_metadata():
    """Sample metadata from Audible API."""
    return {
        "asin": "B0TEST1234",
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "narrator": "Martin Freeman",
        "publisher": "HarperAudio",
        "audible_region": "us",
    }


@pytest.fixture
def sample_chapters():
    """Sample chapter data."""
    return {
        "asin": "B0TEST1234",
        "chapters": [
            {"title": "Chapter 1", "startMs": 0, "endMs": 120000},
            {"title": "Chapter 2", "startMs": 120000, "endMs": 240000},
        ],
    }


# =============================================================================
# Initialization Tests
# =============================================================================


@pytest.mark.no_mock_external_apis
class TestMetadataCoordinatorInit:
    """Test MetadataCoordinator initialization."""

    def test_init_with_defaults(self, mock_config):
        """Test initialization loads config defaults."""
        with patch("src.metadata_coordinator.load_config", return_value=mock_config):
            with patch("src.metadata_coordinator.MAMApiAdapter"):
                with patch("src.metadata_coordinator.AudnexMetadata"):
                    with patch("src.metadata_coordinator.AudibleScraper"):
                        coord = MetadataCoordinator()

                        assert coord.seed_authors is True
                        assert coord.force_update is False

    def test_init_missing_config_uses_defaults(self):
        """Test initialization with missing config sections."""
        minimal_config = {}

        with patch("src.metadata_coordinator.load_config", return_value=minimal_config):
            with patch("src.metadata_coordinator.MAMApiAdapter"):
                with patch("src.metadata_coordinator.AudnexMetadata"):
                    with patch("src.metadata_coordinator.AudibleScraper"):
                        coord = MetadataCoordinator()

                        # Should use hardcoded defaults
                        assert coord.seed_authors is False
                        assert coord.force_update is False


# =============================================================================
# get_metadata_from_webhook Tests
# =============================================================================


@pytest.mark.no_mock_external_apis
class TestGetMetadataFromWebhook:
    """Test webhook-based metadata retrieval."""

    @pytest.mark.asyncio
    async def test_webhook_mam_url_success(self, coordinator, sample_webhook_payload, sample_audnex_metadata):
        """Test successful ASIN extraction from MAM URL."""
        # MAM returns ASIN
        coordinator.mam_scraper.scrape_asin_from_url = AsyncMock(return_value="B0TEST1234")
        # Audnex returns metadata
        coordinator.audnex.get_book_by_asin = AsyncMock(return_value=sample_audnex_metadata.copy())

        result = await coordinator.get_metadata_from_webhook(sample_webhook_payload)

        assert result is not None
        assert result["asin"] == "B0TEST1234"
        assert result["source"] == "audnex"
        assert result["asin_source"] == "mam"
        coordinator.mam_scraper.scrape_asin_from_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_mam_no_asin_falls_back_to_audible(
        self, coordinator, sample_webhook_payload, sample_audible_metadata
    ):
        """Test fallback to Audible search when MAM returns no ASIN."""
        # MAM returns no ASIN
        coordinator.mam_scraper.scrape_asin_from_url = AsyncMock(return_value=None)
        # Audible search returns results
        coordinator.audible.search_from_webhook_name = AsyncMock(return_value=[sample_audible_metadata.copy()])

        result = await coordinator.get_metadata_from_webhook(sample_webhook_payload)

        assert result is not None
        assert result["source"] == "audible"
        assert result["asin_source"] == "search"

    @pytest.mark.asyncio
    async def test_webhook_no_mam_url_goes_to_audible(self, coordinator, sample_audible_metadata):
        """Test non-MAM webhook goes directly to Audible search."""
        payload = {
            "name": "The Hobbit by J.R.R. Tolkien",
            "url": "https://some-other-indexer.com/t/123",
        }

        coordinator.audible.search_from_webhook_name = AsyncMock(return_value=[sample_audible_metadata.copy()])

        result = await coordinator.get_metadata_from_webhook(payload)

        assert result is not None
        assert result["source"] == "audible"
        # MAM should not be called for non-MAM URLs
        coordinator.mam_scraper.scrape_asin_from_url.assert_not_called()

    @pytest.mark.asyncio
    async def test_webhook_audnex_failure_falls_back_to_audible(
        self, coordinator, sample_webhook_payload, sample_audible_metadata
    ):
        """Test Audnex failure falls back to Audible."""
        # MAM returns ASIN
        coordinator.mam_scraper.scrape_asin_from_url = AsyncMock(return_value="B0TEST1234")
        # Audnex fails
        coordinator.audnex.get_book_by_asin = AsyncMock(return_value=None)
        # Audible search succeeds
        coordinator.audible.search_from_webhook_name = AsyncMock(return_value=[sample_audible_metadata.copy()])

        result = await coordinator.get_metadata_from_webhook(sample_webhook_payload)

        assert result is not None
        assert result["source"] == "audible"

    @pytest.mark.asyncio
    async def test_webhook_all_sources_fail(self, coordinator, sample_webhook_payload):
        """Test when all metadata sources fail."""
        coordinator.mam_scraper.scrape_asin_from_url = AsyncMock(return_value=None)
        coordinator.audible.search_from_webhook_name = AsyncMock(return_value=None)

        result = await coordinator.get_metadata_from_webhook(sample_webhook_payload)

        assert result is None

    @pytest.mark.asyncio
    async def test_webhook_mam_network_error(self, coordinator, sample_webhook_payload, sample_audible_metadata):
        """Test MAM network error is handled gracefully."""
        coordinator.mam_scraper.scrape_asin_from_url = AsyncMock(side_effect=httpx.RequestError("Network error"))
        coordinator.audible.search_from_webhook_name = AsyncMock(return_value=[sample_audible_metadata.copy()])

        result = await coordinator.get_metadata_from_webhook(sample_webhook_payload)

        # Should fall back to Audible
        assert result is not None
        assert result["source"] == "audible"

    @pytest.mark.asyncio
    async def test_webhook_audnex_network_error(self, coordinator, sample_webhook_payload, sample_audible_metadata):
        """Test Audnex network error falls back to Audible."""
        coordinator.mam_scraper.scrape_asin_from_url = AsyncMock(return_value="B0TEST1234")
        coordinator.audnex.get_book_by_asin = AsyncMock(side_effect=httpx.RequestError("Network error"))
        coordinator.audible.search_from_webhook_name = AsyncMock(return_value=[sample_audible_metadata.copy()])

        result = await coordinator.get_metadata_from_webhook(sample_webhook_payload)

        assert result is not None
        assert result["source"] == "audible"

    @pytest.mark.asyncio
    async def test_webhook_audnex_value_error(self, coordinator, sample_webhook_payload, sample_audible_metadata):
        """Test Audnex ValueError (malformed response) falls back."""
        coordinator.mam_scraper.scrape_asin_from_url = AsyncMock(return_value="B0TEST1234")
        coordinator.audnex.get_book_by_asin = AsyncMock(side_effect=ValueError("Malformed response"))
        coordinator.audible.search_from_webhook_name = AsyncMock(return_value=[sample_audible_metadata.copy()])

        result = await coordinator.get_metadata_from_webhook(sample_webhook_payload)

        assert result is not None
        assert result["source"] == "audible"

    @pytest.mark.asyncio
    async def test_webhook_audnex_unexpected_error(self, coordinator, sample_webhook_payload, sample_audible_metadata):
        """Test Audnex unexpected error is handled."""
        coordinator.mam_scraper.scrape_asin_from_url = AsyncMock(return_value="B0TEST1234")
        coordinator.audnex.get_book_by_asin = AsyncMock(side_effect=RuntimeError("Unexpected"))
        coordinator.audible.search_from_webhook_name = AsyncMock(return_value=[sample_audible_metadata.copy()])

        result = await coordinator.get_metadata_from_webhook(sample_webhook_payload)

        assert result is not None
        assert result["source"] == "audible"

    @pytest.mark.asyncio
    async def test_webhook_audible_network_error_raises(self, coordinator, sample_webhook_payload):
        """Test Audible network error raises ValueError."""
        coordinator.mam_scraper.scrape_asin_from_url = AsyncMock(return_value=None)
        coordinator.audible.search_from_webhook_name = AsyncMock(side_effect=httpx.RequestError("Network error"))

        with pytest.raises(ValueError, match="Could not fetch metadata"):
            await coordinator.get_metadata_from_webhook(sample_webhook_payload)

    @pytest.mark.asyncio
    async def test_webhook_audible_value_error_raises(self, coordinator, sample_webhook_payload):
        """Test Audible ValueError raises."""
        coordinator.mam_scraper.scrape_asin_from_url = AsyncMock(return_value=None)
        coordinator.audible.search_from_webhook_name = AsyncMock(side_effect=ValueError("Malformed response"))

        with pytest.raises(ValueError, match="Could not fetch metadata"):
            await coordinator.get_metadata_from_webhook(sample_webhook_payload)

    @pytest.mark.asyncio
    async def test_webhook_audible_unexpected_error_returns_none(self, coordinator, sample_webhook_payload):
        """Test Audible unexpected error returns None."""
        coordinator.mam_scraper.scrape_asin_from_url = AsyncMock(return_value=None)
        coordinator.audible.search_from_webhook_name = AsyncMock(side_effect=RuntimeError("Unexpected"))

        result = await coordinator.get_metadata_from_webhook(sample_webhook_payload)

        assert result is None

    @pytest.mark.asyncio
    async def test_webhook_passes_seed_authors_and_update(
        self, coordinator, sample_webhook_payload, sample_audnex_metadata
    ):
        """Test that seed_authors and update params are passed to Audnex."""
        coordinator.seed_authors = True
        coordinator.force_update = True
        coordinator.mam_scraper.scrape_asin_from_url = AsyncMock(return_value="B0TEST1234")
        coordinator.audnex.get_book_by_asin = AsyncMock(return_value=sample_audnex_metadata.copy())

        await coordinator.get_metadata_from_webhook(sample_webhook_payload)

        coordinator.audnex.get_book_by_asin.assert_called_once_with(
            "B0TEST1234",
            seed_authors=True,
            update=True,
        )

    @pytest.mark.asyncio
    async def test_webhook_empty_name_still_works(self, coordinator, sample_audible_metadata):
        """Test webhook with empty name field."""
        payload = {
            "name": "",
            "url": "https://www.myanonamouse.net/t/12345",
        }
        coordinator.mam_scraper.scrape_asin_from_url = AsyncMock(return_value=None)
        coordinator.audible.search_from_webhook_name = AsyncMock(return_value=[sample_audible_metadata.copy()])

        result = await coordinator.get_metadata_from_webhook(payload)

        # Even with empty name, should attempt search
        assert result is not None

    @pytest.mark.asyncio
    async def test_webhook_mam_value_error(self, coordinator, sample_webhook_payload, sample_audible_metadata):
        """Test MAM ValueError (malformed response) continues to Audible."""
        coordinator.mam_scraper.scrape_asin_from_url = AsyncMock(side_effect=ValueError("Malformed response"))
        coordinator.audible.search_from_webhook_name = AsyncMock(return_value=[sample_audible_metadata.copy()])

        result = await coordinator.get_metadata_from_webhook(sample_webhook_payload)

        assert result is not None
        assert result["source"] == "audible"

    @pytest.mark.asyncio
    async def test_webhook_mam_unexpected_error(self, coordinator, sample_webhook_payload, sample_audible_metadata):
        """Test MAM unexpected error continues to Audible."""
        coordinator.mam_scraper.scrape_asin_from_url = AsyncMock(side_effect=RuntimeError("Unexpected"))
        coordinator.audible.search_from_webhook_name = AsyncMock(return_value=[sample_audible_metadata.copy()])

        result = await coordinator.get_metadata_from_webhook(sample_webhook_payload)

        assert result is not None
        assert result["source"] == "audible"


# =============================================================================
# get_metadata_by_asin Tests
# =============================================================================


@pytest.mark.no_mock_external_apis
class TestGetMetadataByAsin:
    """Test direct ASIN lookup."""

    @pytest.mark.asyncio
    async def test_asin_lookup_success(self, coordinator, sample_audnex_metadata):
        """Test successful ASIN lookup."""
        coordinator.audnex.get_book_by_asin = AsyncMock(return_value=sample_audnex_metadata.copy())

        result = await coordinator.get_metadata_by_asin("B0TEST1234")

        assert result is not None
        assert result["asin"] == "B0TEST1234"
        assert result["source"] == "audnex"
        assert result["asin_source"] == "direct"

    @pytest.mark.asyncio
    async def test_asin_lookup_with_region(self, coordinator, sample_audnex_metadata):
        """Test ASIN lookup with custom region."""
        coordinator.audnex.get_book_by_asin = AsyncMock(return_value=sample_audnex_metadata.copy())

        await coordinator.get_metadata_by_asin("B0TEST1234", region="uk")

        coordinator.audnex.get_book_by_asin.assert_called_once()
        call_args = coordinator.audnex.get_book_by_asin.call_args
        assert call_args.kwargs["region"] == "uk"

    @pytest.mark.asyncio
    async def test_asin_lookup_override_seed_authors(self, coordinator, sample_audnex_metadata):
        """Test seed_authors parameter override."""
        coordinator.seed_authors = False  # Config default
        coordinator.audnex.get_book_by_asin = AsyncMock(return_value=sample_audnex_metadata.copy())

        await coordinator.get_metadata_by_asin("B0TEST1234", seed_authors=True)

        call_args = coordinator.audnex.get_book_by_asin.call_args
        assert call_args.kwargs["seed_authors"] is True

    @pytest.mark.asyncio
    async def test_asin_lookup_override_update(self, coordinator, sample_audnex_metadata):
        """Test update parameter override."""
        coordinator.force_update = False  # Config default
        coordinator.audnex.get_book_by_asin = AsyncMock(return_value=sample_audnex_metadata.copy())

        await coordinator.get_metadata_by_asin("B0TEST1234", update=True)

        call_args = coordinator.audnex.get_book_by_asin.call_args
        assert call_args.kwargs["update"] is True

    @pytest.mark.asyncio
    async def test_asin_lookup_uses_config_defaults(self, coordinator, sample_audnex_metadata):
        """Test that config defaults are used when params not provided."""
        coordinator.seed_authors = True
        coordinator.force_update = True
        coordinator.audnex.get_book_by_asin = AsyncMock(return_value=sample_audnex_metadata.copy())

        await coordinator.get_metadata_by_asin("B0TEST1234")

        call_args = coordinator.audnex.get_book_by_asin.call_args
        assert call_args.kwargs["seed_authors"] is True
        assert call_args.kwargs["update"] is True

    @pytest.mark.asyncio
    async def test_asin_lookup_not_found(self, coordinator):
        """Test ASIN lookup when not found."""
        coordinator.audnex.get_book_by_asin = AsyncMock(return_value=None)

        result = await coordinator.get_metadata_by_asin("B0NOTFOUND")

        assert result is None

    @pytest.mark.asyncio
    async def test_asin_lookup_network_error(self, coordinator):
        """Test ASIN lookup network error handling."""
        coordinator.audnex.get_book_by_asin = AsyncMock(side_effect=httpx.RequestError("Network error"))

        result = await coordinator.get_metadata_by_asin("B0TEST1234")

        assert result is None

    @pytest.mark.asyncio
    async def test_asin_lookup_value_error(self, coordinator):
        """Test ASIN lookup with malformed response."""
        coordinator.audnex.get_book_by_asin = AsyncMock(side_effect=ValueError("Malformed"))

        result = await coordinator.get_metadata_by_asin("B0TEST1234")

        assert result is None

    @pytest.mark.asyncio
    async def test_asin_lookup_unexpected_error(self, coordinator):
        """Test ASIN lookup with unexpected error."""
        coordinator.audnex.get_book_by_asin = AsyncMock(side_effect=RuntimeError("Unexpected"))

        result = await coordinator.get_metadata_by_asin("B0TEST1234")

        assert result is None


# =============================================================================
# search_metadata Tests
# =============================================================================


@pytest.mark.no_mock_external_apis
class TestSearchMetadata:
    """Test title/author search."""

    @pytest.mark.asyncio
    async def test_search_success(self, coordinator, sample_audible_metadata):
        """Test successful search."""
        coordinator.audible.search = AsyncMock(return_value=[sample_audible_metadata.copy()])

        result = await coordinator.search_metadata("The Hobbit", author="Tolkien")

        assert result is not None
        assert result["title"] == "The Hobbit"
        assert result["source"] == "audible"
        assert result["asin_source"] == "search"

    @pytest.mark.asyncio
    async def test_search_with_custom_region(self, coordinator, sample_audible_metadata):
        """Test search with custom region."""
        coordinator.audible.search = AsyncMock(return_value=[sample_audible_metadata.copy()])

        await coordinator.search_metadata("The Hobbit", region="uk")

        coordinator.audible.search.assert_called_once_with(title="The Hobbit", author="", region="uk")

    @pytest.mark.asyncio
    async def test_search_no_results(self, coordinator):
        """Test search with no results."""
        coordinator.audible.search = AsyncMock(return_value=[])

        result = await coordinator.search_metadata("Unknown Book")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_returns_none(self, coordinator):
        """Test search returning None."""
        coordinator.audible.search = AsyncMock(return_value=None)

        result = await coordinator.search_metadata("Unknown Book")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_network_error(self, coordinator):
        """Test search network error."""
        coordinator.audible.search = AsyncMock(side_effect=httpx.RequestError("Network error"))

        result = await coordinator.search_metadata("The Hobbit")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_value_error(self, coordinator):
        """Test search with malformed response."""
        coordinator.audible.search = AsyncMock(side_effect=ValueError("Malformed"))

        result = await coordinator.search_metadata("The Hobbit")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_unexpected_error(self, coordinator):
        """Test search with unexpected error."""
        coordinator.audible.search = AsyncMock(side_effect=RuntimeError("Unexpected"))

        result = await coordinator.search_metadata("The Hobbit")

        assert result is None


# =============================================================================
# get_enhanced_metadata Tests
# =============================================================================


@pytest.mark.no_mock_external_apis
class TestGetEnhancedMetadata:
    """Test metadata enhancement with chapters."""

    @pytest.mark.asyncio
    async def test_enhanced_metadata_with_chapters(self, coordinator, sample_audnex_metadata, sample_chapters):
        """Test adding chapters to metadata."""
        coordinator.audnex.get_chapters_by_asin = AsyncMock(return_value=sample_chapters)

        result = await coordinator.get_enhanced_metadata(sample_audnex_metadata)

        assert "chapters" in result
        assert result["chapter_count"] == 2
        assert "metadata_workflow" in result
        assert result["metadata_workflow"]["coordinator_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_enhanced_metadata_no_asin(self, coordinator):
        """Test enhancement when no ASIN present."""
        metadata = {"title": "Test Book"}

        result = await coordinator.get_enhanced_metadata(metadata)

        assert "chapters" not in result
        assert "metadata_workflow" in result

    @pytest.mark.asyncio
    async def test_enhanced_metadata_chapters_not_found(self, coordinator, sample_audnex_metadata):
        """Test enhancement when chapters not available."""
        coordinator.audnex.get_chapters_by_asin = AsyncMock(return_value=None)

        result = await coordinator.get_enhanced_metadata(sample_audnex_metadata)

        assert "chapters" not in result
        assert "metadata_workflow" in result

    @pytest.mark.asyncio
    async def test_enhanced_metadata_uses_audnex_region(self, coordinator, sample_audnex_metadata, sample_chapters):
        """Test that enhancement uses the region from book metadata."""
        sample_audnex_metadata["audnex_region"] = "uk"
        coordinator.audnex.get_chapters_by_asin = AsyncMock(return_value=sample_chapters)

        await coordinator.get_enhanced_metadata(sample_audnex_metadata)

        call_args = coordinator.audnex.get_chapters_by_asin.call_args
        assert call_args.kwargs["region"] == "uk"

    @pytest.mark.asyncio
    async def test_enhanced_metadata_passes_force_update(self, coordinator, sample_audnex_metadata, sample_chapters):
        """Test that force_update is passed to chapters lookup."""
        coordinator.force_update = True
        coordinator.audnex.get_chapters_by_asin = AsyncMock(return_value=sample_chapters)

        await coordinator.get_enhanced_metadata(sample_audnex_metadata)

        call_args = coordinator.audnex.get_chapters_by_asin.call_args
        assert call_args.kwargs["update"] is True

    @pytest.mark.asyncio
    async def test_enhanced_metadata_network_error(self, coordinator, sample_audnex_metadata):
        """Test network error during chapter fetch."""
        coordinator.audnex.get_chapters_by_asin = AsyncMock(side_effect=httpx.RequestError("Network error"))

        result = await coordinator.get_enhanced_metadata(sample_audnex_metadata)

        # Should still return enhanced metadata without chapters
        assert "chapters" not in result
        assert "metadata_workflow" in result

    @pytest.mark.asyncio
    async def test_enhanced_metadata_value_error(self, coordinator, sample_audnex_metadata):
        """Test malformed chapter response."""
        coordinator.audnex.get_chapters_by_asin = AsyncMock(side_effect=ValueError("Malformed"))

        result = await coordinator.get_enhanced_metadata(sample_audnex_metadata)

        assert "chapters" not in result
        assert "metadata_workflow" in result

    @pytest.mark.asyncio
    async def test_enhanced_metadata_unexpected_error(self, coordinator, sample_audnex_metadata):
        """Test unexpected error during chapter fetch."""
        coordinator.audnex.get_chapters_by_asin = AsyncMock(side_effect=RuntimeError("Unexpected"))

        result = await coordinator.get_enhanced_metadata(sample_audnex_metadata)

        assert "chapters" not in result
        assert "metadata_workflow" in result

    @pytest.mark.asyncio
    async def test_enhanced_metadata_cancelled_error_propagates(self, coordinator, sample_audnex_metadata):
        """Test that CancelledError is re-raised."""
        coordinator.audnex.get_chapters_by_asin = AsyncMock(side_effect=asyncio.CancelledError())

        with pytest.raises(asyncio.CancelledError):
            await coordinator.get_enhanced_metadata(sample_audnex_metadata)

    @pytest.mark.asyncio
    async def test_enhanced_metadata_preserves_original(self, coordinator, sample_audnex_metadata):
        """Test that original metadata is not modified."""
        original_copy = sample_audnex_metadata.copy()
        coordinator.audnex.get_chapters_by_asin = AsyncMock(return_value=None)

        await coordinator.get_enhanced_metadata(sample_audnex_metadata)

        # Original should be unchanged
        assert sample_audnex_metadata == original_copy


# =============================================================================
# _add_webhook_info Tests
# =============================================================================


@pytest.mark.no_mock_external_apis
class TestAddWebhookInfo:
    """Test webhook info extraction."""

    def test_add_webhook_info_full_payload(self, coordinator, sample_webhook_payload):
        """Test extracting all webhook info fields."""
        result = coordinator._add_webhook_info(sample_webhook_payload)

        assert result["webhook_name"] == "The Hobbit by J.R.R. Tolkien [Audiobook]"
        assert result["webhook_url"] == "https://www.myanonamouse.net/t/12345"
        assert result["webhook_indexer"] == "MyAnonamouse"
        assert result["webhook_category"] == "Audiobooks"
        assert result["webhook_size"] == 524288000
        assert result["webhook_size_mb"] == pytest.approx(500.0, rel=0.01)
        assert result["webhook_seeders"] == 15
        assert result["webhook_leechers"] == 2
        assert result["torrent_name"] == "The Hobbit by J.R.R. Tolkien [Audiobook]"
        assert result["quality"] == "MP3"
        assert result["format"] == "128kbps"
        assert result["language"] == "English"
        assert result["uploader"] == "test_user"
        assert result["freeleech"] is True
        assert "processing_time" in result
        assert "processing_date" in result

    def test_add_webhook_info_empty_payload(self, coordinator):
        """Test with empty payload uses defaults."""
        result = coordinator._add_webhook_info({})

        assert result["webhook_name"] == ""
        assert result["webhook_url"] == ""
        assert result["webhook_size"] == 0
        assert result["webhook_size_mb"] == 0
        assert result["freeleech"] is False

    def test_add_webhook_info_size_calculation(self, coordinator):
        """Test size MB calculation."""
        payload = {"size": 1048576}  # 1 MB

        result = coordinator._add_webhook_info(payload)

        assert result["webhook_size_mb"] == 1.0

    def test_add_webhook_info_no_size(self, coordinator):
        """Test when size is not provided."""
        payload = {"name": "Test"}

        result = coordinator._add_webhook_info(payload)

        assert result["webhook_size_mb"] == 0


# =============================================================================
# CLI main() Tests
# =============================================================================


@pytest.mark.no_mock_external_apis
class TestCLIMain:
    """Test command line interface."""

    def test_main_no_args_shows_error(self, capsys):
        """Test that running with no args shows error."""
        with patch("sys.argv", ["metadata_coordinator"]), patch("src.metadata_coordinator.MetadataCoordinator"):
            main()

        captured = capsys.readouterr()
        assert "Error: Must provide --url/--name, --asin, or --title" in captured.out

    def test_main_with_asin_lookup(self, capsys, sample_audnex_metadata):
        """Test CLI with --asin flag."""
        with patch("sys.argv", ["metadata_coordinator", "--asin", "B0TEST1234"]):
            with patch("src.metadata_coordinator.MetadataCoordinator") as MockCoord:
                mock_instance = MagicMock()
                mock_instance.get_metadata_by_asin = AsyncMock(return_value=sample_audnex_metadata.copy())
                MockCoord.return_value = mock_instance

                main()

        captured = capsys.readouterr()
        assert "✅ Metadata found:" in captured.out
        assert "The Hobbit" in captured.out

    def test_main_with_url(self, capsys, sample_audnex_metadata):
        """Test CLI with --url flag."""
        with patch("sys.argv", ["metadata_coordinator", "--url", "https://mam.net/t/123"]):
            with patch("src.metadata_coordinator.MetadataCoordinator") as MockCoord:
                mock_instance = MagicMock()
                mock_instance.get_metadata_from_webhook = AsyncMock(return_value=sample_audnex_metadata.copy())
                MockCoord.return_value = mock_instance

                main()

        captured = capsys.readouterr()
        assert "✅ Metadata found:" in captured.out

    def test_main_with_name(self, capsys, sample_audnex_metadata):
        """Test CLI with --name flag."""
        with patch("sys.argv", ["metadata_coordinator", "--name", "The Hobbit"]):
            with patch("src.metadata_coordinator.MetadataCoordinator") as MockCoord:
                mock_instance = MagicMock()
                mock_instance.get_metadata_from_webhook = AsyncMock(return_value=sample_audnex_metadata.copy())
                MockCoord.return_value = mock_instance

                main()

        captured = capsys.readouterr()
        assert "✅ Metadata found:" in captured.out

    def test_main_with_title_search(self, capsys, sample_audible_metadata):
        """Test CLI with --title flag."""
        with patch("sys.argv", ["metadata_coordinator", "--title", "The Hobbit", "--author", "Tolkien"]):
            with patch("src.metadata_coordinator.MetadataCoordinator") as MockCoord:
                mock_instance = MagicMock()
                mock_instance.search_metadata = AsyncMock(return_value=sample_audible_metadata.copy())
                MockCoord.return_value = mock_instance

                main()

        captured = capsys.readouterr()
        assert "✅ Metadata found:" in captured.out

    def test_main_with_enhanced_flag(self, capsys, sample_audnex_metadata, sample_chapters):
        """Test CLI with --enhanced flag."""
        enhanced_meta = sample_audnex_metadata.copy()
        enhanced_meta["chapters"] = sample_chapters
        enhanced_meta["chapter_count"] = 2

        with patch("sys.argv", ["metadata_coordinator", "--asin", "B0TEST", "--enhanced"]):
            with patch("src.metadata_coordinator.MetadataCoordinator") as MockCoord:
                mock_instance = MagicMock()
                mock_instance.get_metadata_by_asin = AsyncMock(return_value=sample_audnex_metadata.copy())
                mock_instance.get_enhanced_metadata = AsyncMock(return_value=enhanced_meta)
                MockCoord.return_value = mock_instance

                main()

        captured = capsys.readouterr()
        assert "Chapters: 2" in captured.out

    def test_main_not_found(self, capsys):
        """Test CLI when metadata not found."""
        with patch("sys.argv", ["metadata_coordinator", "--asin", "B0NOTFOUND"]):
            with patch("src.metadata_coordinator.MetadataCoordinator") as MockCoord:
                mock_instance = MagicMock()
                mock_instance.get_metadata_by_asin = AsyncMock(return_value=None)
                MockCoord.return_value = mock_instance

                main()

        captured = capsys.readouterr()
        assert "❌ No metadata found" in captured.out

    def test_main_displays_series_info_dict(self, capsys, sample_audnex_metadata):
        """Test CLI displays series info as dict."""
        sample_audnex_metadata["series"] = [{"title": "Middle-earth", "sequence": "1"}]

        with patch("sys.argv", ["metadata_coordinator", "--asin", "B0TEST"]):
            with patch("src.metadata_coordinator.MetadataCoordinator") as MockCoord:
                mock_instance = MagicMock()
                mock_instance.get_metadata_by_asin = AsyncMock(return_value=sample_audnex_metadata.copy())
                MockCoord.return_value = mock_instance

                main()

        captured = capsys.readouterr()
        assert "Series: Middle-earth #1" in captured.out

    def test_main_displays_series_info_string(self, capsys, sample_audnex_metadata):
        """Test CLI displays series info as string."""
        sample_audnex_metadata["series"] = ["Middle-earth #1"]

        with patch("sys.argv", ["metadata_coordinator", "--asin", "B0TEST"]):
            with patch("src.metadata_coordinator.MetadataCoordinator") as MockCoord:
                mock_instance = MagicMock()
                mock_instance.get_metadata_by_asin = AsyncMock(return_value=sample_audnex_metadata.copy())
                MockCoord.return_value = mock_instance

                main()

        captured = capsys.readouterr()
        assert "Series: Middle-earth #1" in captured.out

    def test_main_displays_description(self, capsys, sample_audnex_metadata):
        """Test CLI displays truncated description."""
        sample_audnex_metadata["description"] = "A" * 300  # Long description

        with patch("sys.argv", ["metadata_coordinator", "--asin", "B0TEST"]):
            with patch("src.metadata_coordinator.MetadataCoordinator") as MockCoord:
                mock_instance = MagicMock()
                mock_instance.get_metadata_by_asin = AsyncMock(return_value=sample_audnex_metadata.copy())
                MockCoord.return_value = mock_instance

                main()

        captured = capsys.readouterr()
        assert "Description:" in captured.out
        assert "..." in captured.out  # Truncated

    def test_main_with_custom_region(self, capsys, sample_audnex_metadata):
        """Test CLI with --region flag."""
        with patch("sys.argv", ["metadata_coordinator", "--asin", "B0TEST", "--region", "uk"]):
            with patch("src.metadata_coordinator.MetadataCoordinator") as MockCoord:
                mock_instance = MagicMock()
                mock_instance.get_metadata_by_asin = AsyncMock(return_value=sample_audnex_metadata.copy())
                MockCoord.return_value = mock_instance

                main()

        # Verify region was passed
        mock_instance.get_metadata_by_asin.assert_called_once()
        call_args = mock_instance.get_metadata_by_asin.call_args
        assert call_args.kwargs["region"] == "uk"


# =============================================================================
# Integration-style Tests
# =============================================================================


@pytest.mark.no_mock_external_apis
class TestIntegrationScenarios:
    """Test complete workflow scenarios."""

    @pytest.mark.asyncio
    async def test_full_workflow_mam_to_audnex_to_chapters(
        self, coordinator, sample_webhook_payload, sample_audnex_metadata, sample_chapters
    ):
        """Test complete workflow: webhook → MAM → Audnex → chapters."""
        # Setup mocks
        coordinator.mam_scraper.scrape_asin_from_url = AsyncMock(return_value="B0TEST1234")
        coordinator.audnex.get_book_by_asin = AsyncMock(return_value=sample_audnex_metadata.copy())
        coordinator.audnex.get_chapters_by_asin = AsyncMock(return_value=sample_chapters)

        # Get metadata from webhook
        metadata = await coordinator.get_metadata_from_webhook(sample_webhook_payload)
        assert metadata is not None
        assert metadata["source"] == "audnex"

        # Enhance with chapters
        enhanced = await coordinator.get_enhanced_metadata(metadata)
        assert enhanced["chapter_count"] == 2
        assert "metadata_workflow" in enhanced

    @pytest.mark.asyncio
    async def test_full_workflow_fallback_to_audible(
        self, coordinator, sample_webhook_payload, sample_audible_metadata
    ):
        """Test workflow with fallback: MAM fails → Audnex fails → Audible succeeds."""
        # MAM fails
        coordinator.mam_scraper.scrape_asin_from_url = AsyncMock(side_effect=httpx.RequestError("MAM down"))
        # Audible succeeds
        coordinator.audible.search_from_webhook_name = AsyncMock(return_value=[sample_audible_metadata.copy()])

        metadata = await coordinator.get_metadata_from_webhook(sample_webhook_payload)

        assert metadata is not None
        assert metadata["source"] == "audible"
        assert metadata["asin_source"] == "search"
