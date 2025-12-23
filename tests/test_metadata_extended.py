from unittest.mock import MagicMock, patch

import pytest

from src.metadata import clean_metadata, fetch_metadata, get_audible_asin, levenshtein_distance


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

    @patch("src.metadata.httpx.get")
    @patch("builtins.__import__")
    def test_get_audible_asin_success(self, mock_import, mock_get):
        # Mock BeautifulSoup import
        mock_response = MagicMock()
        mock_response.text = '<div class="adbl-impression-container" data-asin="B123456789"></div>'
        mock_get.return_value = mock_response

        # Mock the bs4 import
        mock_bs4 = MagicMock()
        mock_soup = MagicMock()
        mock_bs4.BeautifulSoup.return_value = mock_soup
        mock_soup.find.return_value = {"data-asin": "B123456789"}

        # Store original import
        original_import = __builtins__["__import__"]

        def import_side_effect(name, *args, **kwargs):
            if name == "bs4":
                return mock_bs4
            elif name == "bs4.element":
                mock_element = MagicMock()
                return mock_element
            return original_import(name, *args, **kwargs)

        mock_import.side_effect = import_side_effect

        asin = get_audible_asin("Test Title", "Test Author")
        assert asin == "B123456789"

    @patch("src.metadata.httpx.get")
    @patch("builtins.__import__")
    def test_get_audible_asin_not_found(self, mock_import, mock_get):
        mock_response = MagicMock()
        mock_response.text = "<div>No ASIN here</div>"
        mock_get.return_value = mock_response

        # Mock the bs4 import
        mock_bs4 = MagicMock()
        mock_soup = MagicMock()
        mock_bs4.BeautifulSoup.return_value = mock_soup
        mock_soup.find.return_value = None

        # Store original import
        original_import = __builtins__["__import__"]

        def import_side_effect(name, *args, **kwargs):
            if name == "bs4":
                return mock_bs4
            elif name == "bs4.element":
                mock_element = MagicMock()
                return mock_element
            return original_import(name, *args, **kwargs)

        mock_import.side_effect = import_side_effect

        asin = get_audible_asin("Unknown Title", "Unknown Author")
        assert asin is None

    def test_get_audible_asin_no_beautifulsoup(self):
        # Test when BeautifulSoup is not available
        with patch("builtins.__import__", side_effect=ImportError("No module named 'bs4'")):
            asin = get_audible_asin("Test Title", "Test Author")
            assert asin is None

    @patch("src.metadata_coordinator.MetadataCoordinator.get_metadata_from_webhook")
    @patch("src.metadata.get_cached_metadata")
    def test_fetch_metadata_success(self, mock_cached, mock_coord):
        # Mock successful metadata fetch
        expected_metadata = {"title": "Test Book", "authors": [{"name": "Test Author"}], "asin": "B123456789"}
        mock_cached.return_value = expected_metadata
        mock_coord.return_value = expected_metadata

        payload = {
            "name": "Test Book by Test Author [B123456789]",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }
        result = fetch_metadata(payload)

        assert result["title"] == "Test Book"
        assert "asin" in result

    @patch("src.metadata_coordinator.MetadataCoordinator.get_metadata_from_webhook")
    @patch("src.metadata.get_cached_metadata")
    @patch("src.metadata.get_audible_asin")
    def test_fetch_metadata_fallback_to_scraping(self, mock_scrape, mock_cached, mock_coord):
        # Test fallback when API fails but scraping succeeds
        mock_cached.return_value = None
        mock_scrape.return_value = "B987654321"

        # Mock successful API call with scraped ASIN
        def cached_side_effect(asin, region, api_url):
            if asin == "B987654321":
                return {"title": "Scraped Book", "asin": asin}
            return None

        mock_cached.side_effect = cached_side_effect
        mock_coord.return_value = {"title": "Scraped Book", "asin": "B987654321"}

        payload = {
            "name": "Unknown Book by Unknown Author",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }
        result = fetch_metadata(payload)

        assert "title" in result
        assert result.get("asin") == "B987654321"

    @patch("src.metadata_coordinator.MetadataCoordinator.get_metadata_from_webhook")
    def test_fetch_metadata_no_asin_found(self, mock_coord):
        # Test when no ASIN can be extracted or found
        payload = {
            "name": "Very Obscure Book",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }

        # Override autouse mock to raise ValueError
        mock_coord.return_value = None

        with (
            patch("src.metadata.get_cached_metadata", return_value=None),
            patch("src.metadata.get_audible_asin", return_value=None),
        ):
            # Should raise ValueError when no ASIN can be found
            with pytest.raises(ValueError, match="ASIN could not be determined"):
                fetch_metadata(payload)

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
