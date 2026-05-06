"""Tests for the Audible scraper transport selection."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
        "language": "english",
    }

    mock_auth = MagicMock()
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value={"products": [product]})
    mock_client.close = AsyncMock()

    with patch.dict(os.environ, {"AUDIBLE_AUTH_FILE_PASSWORD": "test-password"}, clear=False):
        with patch("src.audible_scraper.load_config", return_value=mock_config):
            with patch("src.audible_client.audible.Authenticator.from_file", return_value=mock_auth) as mock_from_file:
                with patch("src.audible_client.audible.AsyncClient", return_value=mock_client) as mock_async_client:
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
