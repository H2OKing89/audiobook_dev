"""
Audible.com metadata fallback scraper
Searches for audiobook metadata using Audible's search API

This module provides async methods for searching Audible's catalog,
with support for title/author searches and ASIN lookups.
"""

import argparse
import asyncio
import re
from typing import Any
from urllib.parse import urlencode

from src.audnex_metadata import AudnexMetadata
from src.config import load_config
from src.http_client import (
    REGION_MAP,
    AsyncHttpClient,
    get_default_client,
    get_region_tld,
)
from src.logging_setup import get_logger


log = get_logger(__name__)


class AudibleScraper:
    """
    Async Audible metadata scraper with shared HTTP client.

    Example usage:
        async with AudibleScraper() as scraper:
            results = await scraper.search(title="The Hobbit", author="Tolkien")
            metadata = await scraper.search_by_asin("B08G9PRS1K")
    """

    def __init__(self, client: AsyncHttpClient | None = None) -> None:
        """
        Initialize the Audible scraper.

        Args:
            client: Optional AsyncHttpClient instance. If not provided, uses the default shared client.
        """
        self._client = client
        self.config = load_config()
        self.audible_config = self.config.get("metadata", {}).get("audible", {})
        self.base_url = self.audible_config.get("base_url", "https://api.audible.com")
        self.search_endpoint = self.audible_config.get("search_endpoint", "/1.0/catalog/products")

        # Use shared region map from http_client
        self.region_map = REGION_MAP

        # Audnex for detailed metadata lookups
        self._audnex: AudnexMetadata | None = None

    async def _get_client(self) -> AsyncHttpClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = await get_default_client()
        return self._client

    async def _get_audnex(self) -> AudnexMetadata:
        """Get or create the Audnex client."""
        if self._audnex is None:
            self._audnex = AudnexMetadata(self._client)
        return self._audnex

    async def __aenter__(self) -> "AudibleScraper":
        """Async context manager entry."""
        await self._get_client()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        """Async context manager exit.

        Note: Does not close the HTTP client as it's managed by the application lifespan.
        The shared client is closed during app shutdown.
        """

    def _is_valid_asin(self, asin: str) -> bool:
        """Validate ASIN format (10 characters, alphanumeric)."""
        if not asin or not isinstance(asin, str):
            return False
        return len(asin) == 10 and asin.isalnum()

    def _product_to_book(self, product: dict) -> dict:
        """Convert Audible API product to a structured book dictionary."""

        # Handle authors - can be list of dicts or list of strings
        authors = []
        for author in product.get("authors", []):
            if isinstance(author, dict):
                authors.append(author.get("name", ""))
            elif isinstance(author, str):
                authors.append(author)

        # Handle narrators - can be list of dicts or list of strings
        narrators = []
        for narrator in product.get("narrators", []):
            if isinstance(narrator, dict):
                narrators.append(narrator.get("name", ""))
            elif isinstance(narrator, str):
                narrators.append(narrator)

        # Handle series - can be list of dicts
        series = []
        for s in product.get("series", []):
            if isinstance(s, dict):
                series.append({"title": s.get("title", ""), "sequence": s.get("sequence", "")})

        # Extract description from multiple possible fields
        description = (
            product.get("summary")
            or product.get("publisher_summary")
            or product.get("merchandising_summary")
            or product.get("description")
        )

        # Handle publication date - can be in different formats
        publish_year = None
        release_date = product.get("release_date") or product.get("issue_date") or product.get("publication_datetime")
        if release_date:
            try:
                if "T" in str(release_date) or "-" in str(release_date):
                    publish_year = str(release_date).split("-")[0]
                else:
                    publish_year = str(release_date)[:4]
            except Exception as e:
                log.debug("audible.parse_date.failed", release_date=release_date, error=str(e))

        # Handle images
        cover_url = None
        if product.get("product_images"):
            # Get the highest resolution image available
            for size in ["500", "300", "200", "100"]:
                if product["product_images"].get(size):
                    cover_url = product["product_images"][size]
                    break
        elif product.get("image"):
            cover_url = product.get("image")

        # Create standardized book data
        book_data = {
            "asin": product.get("asin"),
            "title": product.get("title"),
            "subtitle": product.get("subtitle"),
            "author": ", ".join(authors) if authors else None,
            "authors": authors,
            "narrator": ", ".join(narrators) if narrators else None,
            "narrators": narrators,
            "publisher": product.get("publisher_name") or product.get("publisherName"),
            "publishedYear": publish_year,
            "publishYear": publish_year,  # Alternative field name
            "releaseDate": release_date,
            "description": description,
            "summary": description,  # Alternative field name
            "cover": cover_url,
            "image": cover_url,  # Alternative field name
            "cover_url": cover_url,  # Alternative field name
            "length": product.get("runtime_length_min") or product.get("runtimeLengthMin"),
            "duration": product.get("runtime_length_min") or product.get("runtimeLengthMin"),
            "runtime_minutes": product.get("runtime_length_min") or product.get("runtimeLengthMin"),
            "series": series,
            "language": product.get("language", "").capitalize() if product.get("language") else None,
            "format_type": product.get("format_type"),
            "abridged": product.get("format_type") == "abridged",
            "isbn": product.get("isbn"),
            "rating": product.get("rating"),
            "region": product.get("region"),
            # Additional metadata for notifications and templates
            "source": "audible_api",
            "has_full_metadata": True,
        }

        # Handle genres and tags if available
        if product.get("genres"):
            genres = []
            tags = []
            for genre in product.get("genres", []):
                if isinstance(genre, dict):
                    name = genre.get("name", "")
                    genre_type = genre.get("type", "")
                    if genre_type == "genre":
                        genres.append(name)
                    elif genre_type == "tag":
                        tags.append(name)
                    else:
                        genres.append(name)  # Default to genre
                elif isinstance(genre, str):
                    genres.append(genre)

            book_data["genres"] = genres if genres else None
            book_data["tags"] = ", ".join(tags) if tags else None

        # Handle category_ladders if available (alternative genre format)
        elif product.get("category_ladders"):
            genres = []
            tags = []
            for cl in product.get("category_ladders", []):
                for i, item in enumerate(cl.get("ladder", [])):
                    name = item.get("name", "")
                    if i == 0:  # First level is usually genre
                        genres.append(name)
                    else:  # Subsequent levels are tags
                        tags.append(name)

            book_data["genres"] = genres if genres else None
            book_data["tags"] = ", ".join(tags) if tags else None

        # Remove None values to clean up the response
        return {k: v for k, v in book_data.items() if v is not None}

    async def search_by_title_author(self, title: str, author: str = "", region: str = "us") -> list[dict[str, Any]]:
        """
        Search for audiobooks by title and author using Audible's catalog API.

        Only returns English results.

        Args:
            title: Book title to search for
            author: Author name (optional)
            region: Audible region (default: "us")

        Returns:
            List of book metadata dicts
        """
        if region not in self.region_map:
            log.error("audible.search.invalid_region", region=region)
            region = "us"

        client = await self._get_client()

        # Add response_groups parameter to get full metadata directly from Audible
        params = {
            "num_results": "10",
            "products_sort_by": "Relevance",
            "title": title,
            "response_groups": "product_desc,media,contributors,series",
        }
        if author:
            params["author"] = author

        tld = get_region_tld(region)
        url = f"https://api.audible{tld}{self.search_endpoint}?{urlencode(params)}"
        log.info("audible.search.start", title=title, author=author, region=region)
        log.debug("audible.search.url", url=url)

        data = await client.get_json(url)

        if not data:
            log.warning("audible.search.no_response")
            return []

        products = data.get("products", [])
        log.info("audible.search.results", count=len(products))

        if not products:
            log.warning("audible.search.no_products")
            return []

        detailed_results = []
        audnex = await self._get_audnex()

        for product in products:
            # Only include English books
            language = product.get("language", "").lower()
            if language and language != "english":
                log.debug("audible.search.skip_non_english", language=language)
                continue

            asin = product.get("asin")
            if not asin:
                log.debug("audible.search.skip_no_asin")
                continue

            # First try to convert the full Audible product data
            try:
                book_data = self._product_to_book(product)
                if book_data and book_data.get("title"):
                    detailed_results.append(book_data)
                    log.info("audible.search.metadata_found", asin=asin, title=book_data.get("title"), source="audible")
                    continue
            except Exception as e:
                log.warning("audible.search.product_error", asin=asin, error=str(e))

            # Fallback: try Audnex for detailed metadata
            try:
                metadata = await audnex.get_book_by_asin(asin, region=region)
                if metadata and metadata.get("language", "").lower() == "english":
                    audnex_book = self._product_to_book(metadata)
                    if audnex_book:
                        detailed_results.append(audnex_book)
                        log.info("audible.search.metadata_found", asin=asin, source="audnex_fallback")
                        continue
            except Exception as e:
                log.warning("audible.search.audnex_fallback_failed", asin=asin, error=str(e))

            log.warning("audible.search.no_metadata", asin=asin)

        if detailed_results:
            log.info("audible.search.complete", result_count=len(detailed_results))
        else:
            log.warning("audible.search.no_results")

        return detailed_results

    async def search_by_asin(self, asin: str, region: str = "us") -> dict[str, Any] | None:
        """
        Search for audiobook by ASIN (delegates to Audnex).

        Args:
            asin: Amazon Standard Identification Number
            region: Audible region (default: "us")

        Returns:
            Book metadata dict or None if not found
        """
        if not self._is_valid_asin(asin):
            log.error("audible.asin_search.invalid_format", asin=asin)
            return None

        log.info("audible.asin_search.start", asin=asin, region=region)

        # Use Audnex for ASIN lookups as it's more reliable
        audnex = await self._get_audnex()
        return await audnex.get_book_by_asin(asin, region=region)

    async def search(
        self, title: str = "", author: str = "", asin: str = "", region: str = "us"
    ) -> list[dict[str, Any]]:
        """
        Comprehensive search using multiple strategies.

        Priority: ASIN -> Title as ASIN -> Title/Author search

        Args:
            title: Book title
            author: Author name
            asin: ASIN if known
            region: Audible region (default: "us")

        Returns:
            List of book metadata dicts
        """
        results = []

        # Strategy 1: Direct ASIN search
        if asin and self._is_valid_asin(asin.upper()):
            log.info("audible.search.strategy1", asin=asin, strategy="direct_asin")
            result = await self.search_by_asin(asin.upper(), region=region)
            if result:
                results.append(result)
                return results

        # Strategy 2: Check if title looks like an ASIN
        if title and self._is_valid_asin(title.upper()):
            log.info("audible.search.strategy2", title=title, strategy="title_as_asin")
            result = await self.search_by_asin(title.upper(), region=region)
            if result:
                results.append(result)
                return results

        # Strategy 3: Title/Author search via Audible catalog
        if title:
            log.info("audible.search.strategy3", title=title, author=author, strategy="title_author")
            results = await self.search_by_title_author(title, author, region=region)

        return results

    def extract_title_author_from_name(self, name: str) -> tuple[str, str]:
        """Extract title and author from torrent-style names."""
        # Common patterns in torrent names
        patterns = [
            r"^(.+?)\s+by\s+(.+?)\s*\[",  # "Title by Author [extras]"
            r"^(.+?)\s+by\s+(.+?)$",  # "Title by Author"
            r"^(.+?)\s+-\s+(.+?)\s*\[",  # "Title - Author [extras]"
            r"^(.+?)\s+-\s+(.+?)$",  # "Title - Author"
        ]

        for pattern in patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                author = match.group(2).strip()
                log.debug("audible.extract.success", name=name, title=title, author=author)
                return title, author

        # Fallback: assume entire name is title
        log.debug("audible.extract.fallback", name=name)
        return name.strip(), ""

    async def search_from_webhook_name(self, name: str, region: str = "us") -> list[dict[str, Any]]:
        """
        Search for metadata using a webhook-style name.

        Args:
            name: Torrent name to parse
            region: Audible region (default: "us")

        Returns:
            List of book metadata dicts
        """
        log.info("audible.webhook_search.start", name=name)

        # Extract title and author
        title, author = self.extract_title_author_from_name(name)

        # Search using extracted information
        return await self.search(title=title, author=author, region=region)


async def async_main():
    """Async main function for command line usage."""
    parser = argparse.ArgumentParser(description="Audible Metadata Scraper")
    parser.add_argument("--title", help="Book title to search for")
    parser.add_argument("--author", default="", help="Book author to search for")
    parser.add_argument("--asin", help="ASIN to search for")
    parser.add_argument("--name", help="Webhook-style name to parse and search")
    parser.add_argument("--region", default="us", help="Audible region (default: us)")
    args = parser.parse_args()

    async with AudibleScraper() as scraper:
        # Determine search method
        if args.name:
            results = await scraper.search_from_webhook_name(args.name, region=args.region)
        elif args.asin:
            result = await scraper.search_by_asin(args.asin, region=args.region)
            results = [result] if result else []
        elif args.title:
            results = await scraper.search(title=args.title, author=args.author, region=args.region)
        else:
            print("Error: Must provide --title, --asin, or --name")
            return

        # Display results
        if results:
            print(f"Found {len(results)} result(s):")
            for i, result in enumerate(results, 1):
                print(f"\nResult {i}:")
                print(f"  Title: {result.get('title')}")
                print(f"  Author: {result.get('author')}")
                print(f"  ASIN: {result.get('asin')}")
                print(f"  Publisher: {result.get('publisher')}")
                print(f"  Duration: {result.get('length') or result.get('duration')} minutes")
                if result.get("series"):
                    for series in result["series"]:
                        if isinstance(series, dict):
                            title = series.get("title", "")
                            sequence = series.get("sequence", "")
                            print(f"  Series: {title} #{sequence}")
                        else:
                            print(f"  Series: {series}")
        else:
            print("No results found")


def main():
    """Main entry point for command line usage."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
