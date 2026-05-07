"""Tests for the Audible scraper transport selection."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.audible_client import AudibleClientProvider
from src.audible_scraper import AudibleScraper


@pytest.mark.asyncio
async def test_search_by_title_author_uses_audible_library_backend(tmp_path: Path) -> None:
    """Use mkb79/Audible when an auth file and password are configured."""
    auth_file = tmp_path / "audible-auth.json"
    auth_file.write_text("{}")

    mock_config = {
        "metadata": {
            "audible": {
                "auth_file": str(auth_file),
                "search_endpoint": "/1.0/catalog/products",
            }
        }
    }
    product = {
        "asin": "B0TEST1234",
        "title": "The Hobbit",
        "authors": [{"name": "J.R.R. Tolkien"}],
        "narrators": [{"name": "Andy Serkis"}],
        "language": "en",
    }

    mock_auth = MagicMock()
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value={"products": [product]})
    mock_client.close = AsyncMock()

    with patch.dict(os.environ, {"AUDIBLE_AUTH_FILE_PASSWORD": "test-password"}, clear=False):
        with patch("src.audible_scraper.load_config", return_value=mock_config):
            with patch(
                "src.audible_client._audible_mod.Authenticator.from_file", return_value=mock_auth
            ) as mock_from_file:
                with patch(
                    "src.audible_client._audible_mod.AsyncClient", return_value=mock_client
                ) as mock_async_client:
                    scraper = AudibleScraper()
                    results = await scraper.search_by_title_author("The Hobbit", "J.R.R. Tolkien")

    assert len(results) == 1
    assert results[0]["asin"] == "B0TEST1234"
    assert results[0]["source"] == "audible_api"
    mock_from_file.assert_called_once_with(
        auth_file,
        password="test-password",
    )
    mock_async_client.assert_called_once_with(auth=mock_auth, country_code="us")
    mock_client.get.assert_awaited_once_with(
        "/1.0/catalog/products",
        params={
            "num_results": 10,
            "products_sort_by": "Relevance",
            "keywords": "The Hobbit",
            "response_groups": "product_desc,product_attrs,product_extended_attrs,media,contributors,series,rating",
            "author": "J.R.R. Tolkien",
        },
    )


@pytest.mark.asyncio
async def test_search_by_title_author_returns_empty_without_auth_config() -> None:
    """The package-backed Audible backend requires an auth file and decrypt password."""
    mock_config = {
        "metadata": {
            "audible": {
                "search_endpoint": "/1.0/catalog/products",
            }
        }
    }

    with patch.dict(os.environ, {"AUDIBLE_AUTH_FILE_PASSWORD": "", "AUDIBLE_AUTH_FILE": ""}):
        with patch("src.audible_scraper.load_config", return_value=mock_config):
            scraper = AudibleScraper()
            results = await scraper.search_by_title_author("The Hobbit", "J.R.R. Tolkien")

    assert results == []


@pytest.mark.asyncio
async def test_search_by_asin_uses_catalog_params(tmp_path: Path) -> None:
    """ASIN lookup should use the catalog search endpoint with params."""
    auth_file = tmp_path / "audible-auth.json"
    auth_file.write_text("{}")

    mock_config = {
        "metadata": {
            "audible": {
                "auth_file": str(auth_file),
                "search_endpoint": "/1.0/catalog/products",
            }
        }
    }
    product = {"asin": "B0TEST1234", "title": "The Hobbit", "language": "en"}

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value={"products": [product]})
    mock_client.close = AsyncMock()

    with patch.dict(os.environ, {"AUDIBLE_AUTH_FILE_PASSWORD": "test-password"}, clear=False):
        with patch("src.audible_scraper.load_config", return_value=mock_config):
            with patch("src.audible_client._audible_mod.Authenticator.from_file", return_value=MagicMock()):
                with patch("src.audible_client._audible_mod.AsyncClient", return_value=mock_client):
                    scraper = AudibleScraper()
                    result = await scraper.search_by_asin("B0TEST1234")

    assert result is not None
    assert result["asin"] == "B0TEST1234"
    mock_client.get.assert_awaited_once_with(
        "/1.0/catalog/products",
        params={
            "asin": "B0TEST1234",
            "response_groups": "contributors,media,product_attrs,product_desc,product_details,product_extended_attrs,series,rating,category_ladders",
        },
    )


@pytest.mark.asyncio
async def test_shared_injected_provider_is_not_closed_on_scraper_exit() -> None:
    """Injected Audible providers should remain usable after one scraper exits."""
    mock_config = {"metadata": {"audible": {"search_endpoint": "/1.0/catalog/products"}}}
    product = {"asin": "B0TEST1234", "title": "Shared Provider Book", "language": "english"}

    shared_provider = MagicMock(spec=AudibleClientProvider)
    shared_provider.get_client = AsyncMock()
    shared_provider.aclose = AsyncMock()

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value={"products": [product]})
    shared_provider.get_client.return_value = mock_client

    with patch("src.audible_scraper.load_config", return_value=mock_config):
        async with AudibleScraper(audible_client_provider=shared_provider) as first_scraper:
            first_results = await first_scraper.search_by_title_author("Shared Provider Book")

        shared_provider.aclose.assert_not_awaited()

        async with AudibleScraper(audible_client_provider=shared_provider) as second_scraper:
            second_results = await second_scraper.search_by_title_author("Shared Provider Book")

    assert first_results[0]["asin"] == "B0TEST1234"
    assert second_results[0]["asin"] == "B0TEST1234"


def test_is_english_language_accepts_common_locale_variants() -> None:
    assert AudibleScraper._is_english_language("english")
    assert AudibleScraper._is_english_language("en-au")
    assert AudibleScraper._is_english_language("en-ca")
    assert not AudibleScraper._is_english_language("fr")
