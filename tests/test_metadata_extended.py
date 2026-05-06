from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.metadata import clean_metadata, clean_series_sequence, get_audible_asin, levenshtein_distance


class TestMetadataModule:
    def test_levenshtein_distance_identical(self):
        assert levenshtein_distance("hello", "hello") == 0

    def test_levenshtein_distance_different(self):
        assert levenshtein_distance("kitten", "sitting") == 3
        assert levenshtein_distance("", "abc") == 3
        assert levenshtein_distance("abc", "") == 3

    def test_levenshtein_distance_empty(self):
        assert levenshtein_distance("", "") == 0

    def test_clean_metadata_series_handling(self):
        # Test series cleaning and formatting - note: clean_metadata doesn't strip light novel from title
        item = {
            "title": "Test Book (Light Novel)",
            "seriesPrimary": {"name": "Test Series (light novel)", "position": "1.5"},
            "authors": [{"name": "Author One"}],
            "narrators": [{"name": "Narrator One"}],
        }

        result = clean_metadata(item)
        # Title is not cleaned in clean_metadata, it's cleaned in get_notification_fields
        assert result["title"] == "Test Book (Light Novel)"
        assert result["series"] == "Test Series (light novel) (Vol. 1.5)"

    def test_clean_metadata_missing_fields(self):
        # Test with minimal metadata
        item = {"title": "Minimal Book"}

        result = clean_metadata(item)
        assert result["title"] == "Minimal Book"
        assert result["author"] is None
        assert result["series"] == ""
        assert result["narrators"] == []

    def test_clean_metadata_scalar_author_fallback(self):
        item = {"title": "Minimal Book", "author": "Brandon Sanderson"}

        result = clean_metadata(item)

        assert result["author"] == "Brandon Sanderson"

    def test_clean_series_sequence_numeric_inputs(self):
        assert clean_series_sequence("Test Series", 1) == "1"
        assert clean_series_sequence("Test Series", 1.5) == "1.5"

    def test_clean_metadata_genres_and_tags(self):
        item = {
            "title": "Test Book",
            "genres": [
                {"type": "genre", "name": "Fantasy"},
                {"type": "genre", "name": "Adventure"},
                {"type": "tag", "name": "Epic"},
                {"type": "tag", "name": "Magic"},
            ],
        }

        result = clean_metadata(item)
        assert result["genres"] == ["Fantasy", "Adventure"]
        assert result["tags"] == "Epic, Magic"

    @pytest.mark.asyncio
    @patch("src.metadata.AudibleScraper")
    async def test_get_audible_asin_success(self, mock_scraper_cls):
        mock_scraper = MagicMock()
        mock_scraper.__aenter__ = AsyncMock(return_value=mock_scraper)
        mock_scraper.__aexit__ = AsyncMock(return_value=False)
        mock_scraper.search = AsyncMock(return_value=[{"asin": "B123456789"}])
        mock_scraper_cls.return_value = mock_scraper

        asin = await get_audible_asin("Test Title", "Test Author")
        assert asin == "B123456789"

    @pytest.mark.asyncio
    @patch("src.metadata.AudibleScraper")
    async def test_get_audible_asin_not_found(self, mock_scraper_cls):
        mock_scraper = MagicMock()
        mock_scraper.__aenter__ = AsyncMock(return_value=mock_scraper)
        mock_scraper.__aexit__ = AsyncMock(return_value=False)
        mock_scraper.search = AsyncMock(return_value=[{"title": "Unknown Title"}])
        mock_scraper_cls.return_value = mock_scraper

        asin = await get_audible_asin("Unknown Title", "Unknown Author")
        assert asin is None

    @pytest.mark.asyncio
    @patch("src.metadata.AudibleScraper")
    async def test_get_audible_asin_search_error(self, mock_scraper_cls):
        mock_scraper = MagicMock()
        mock_scraper.__aenter__ = AsyncMock(return_value=mock_scraper)
        mock_scraper.__aexit__ = AsyncMock(return_value=False)
        mock_scraper.search = AsyncMock(side_effect=RuntimeError("search failed"))
        mock_scraper_cls.return_value = mock_scraper

        asin = await get_audible_asin("Test Title", "Test Author")
        assert asin is None

    @pytest.mark.asyncio
    @pytest.mark.no_mock_external_apis
    async def test_coordinator_webhook_success(self, coordinator):
        payload = {
            "name": "Test Book by Test Author [B123456789]",
            "url": "https://www.myanonamouse.net/t/12345",
            "download_url": "http://example.com/download.torrent",
        }

        coordinator.mam_adapter.get_asin_from_url = AsyncMock(return_value="B123456789")
        coordinator.audnex.get_book_by_asin = AsyncMock(
            return_value={"title": "Test Book", "authors": [{"name": "Test Author"}], "asin": "B123456789"}
        )

        result = await coordinator.get_metadata_from_webhook(payload)

        assert result["title"] == "Test Book"
        assert result["asin"] == "B123456789"
        assert result["source"] == "audnex"

    @pytest.mark.asyncio
    @pytest.mark.no_mock_external_apis
    async def test_coordinator_fallback_to_audible_search(self, coordinator):
        payload = {
            "name": "Unknown Book by Unknown Author",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }

        coordinator.mam_adapter.get_asin_from_url = AsyncMock(return_value=None)
        coordinator.audnex.get_book_by_asin = AsyncMock(return_value=None)
        coordinator.audible.search_from_webhook_name = AsyncMock(
            return_value=[{"title": "Resolved Book", "asin": "B987654321"}]
        )

        result = await coordinator.get_metadata_from_webhook(payload)

        assert result is not None
        assert result["title"] == "Resolved Book"
        assert result["asin"] == "B987654321"
        assert result["source"] == "audible"

    @pytest.mark.asyncio
    @pytest.mark.no_mock_external_apis
    async def test_coordinator_returns_none_when_no_metadata_found(self, coordinator):
        payload = {
            "name": "Very Obscure Book",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }

        coordinator.mam_adapter.get_asin_from_url = AsyncMock(return_value=None)
        coordinator.audnex.get_book_by_asin = AsyncMock(return_value=None)
        coordinator.audible.search_from_webhook_name = AsyncMock(return_value=[])

        result = await coordinator.get_metadata_from_webhook(payload)

        assert result is None

    def test_clean_metadata_runtime_conversion(self):
        # Test runtime conversion from minutes to readable format
        item = {
            "title": "Test Book",
            "runtimeLengthMin": 360,  # 6 hours
        }

        result = clean_metadata(item)
        assert result["runtime_minutes"] == 360

    def test_clean_metadata_cover_url_extraction(self):
        # Test cover URL extraction and normalization
        item = {"title": "Test Book", "image": "http://example.com/cover.jpg"}

        result = clean_metadata(item)
        assert result["cover"] == "http://example.com/cover.jpg"
        assert result["cover_url"] == "http://example.com/cover.jpg"
