"""
Metadata fetching and processing for audiobooks.

This module provides async classes and functions for fetching audiobook metadata
from Audible and Audnex APIs, with support for multiple regions and fallback logic.
"""

import logging
import os
import re
from typing import Any
from urllib.parse import urlencode

import httpx

from src.config import load_config
from src.http_client import (
    REGION_MAP,
    AsyncHttpClient,
    get_default_client,
    get_region_tld,
    get_regions_priority,
)
from src.utils import clean_author_list, validate_payload


logger = logging.getLogger(__name__)


# ASIN validation
def is_valid_asin(asin: str) -> bool:
    """Validate ASIN format (10 characters, alphanumeric)"""
    if not asin or not isinstance(asin, str):
        return False
    return len(asin) == 10 and asin.isalnum()


# Levenshtein distance implementation for best-match logic
def levenshtein_distance(s1: str, s2: str) -> int:
    if s1 == s2:
        return 0
    len1, len2 = len(s1), len(s2)
    dp = list(range(len2 + 1))
    for i in range(1, len1 + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, len2 + 1):
            cur = dp[j]
            if s1[i - 1] == s2[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j - 1], dp[j])
            prev = cur
    return dp[len2]


class Audible:
    """
    Async Audible metadata client using shared HTTP client.

    Example usage:
        async with Audible() as audible:
            results = await audible.search(title="The Hobbit", author="Tolkien")
            metadata = await audible.asin_search("B08G9PRS1K")
    """

    def __init__(self, client: AsyncHttpClient | None = None, response_timeout: int = 30000) -> None:
        self._client = client
        self.response_timeout = response_timeout
        # Use shared region map from http_client
        self.region_map = REGION_MAP

    async def _get_client(self) -> AsyncHttpClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = await get_default_client()
        return self._client

    async def __aenter__(self) -> "Audible":
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

    def clean_series_sequence(self, series_name: str, sequence: str) -> str:
        """
        Audible will sometimes send sequences with "Book 1" or "2, Dramatized Adaptation"
        Clean to extract just the number portion
        """
        if not sequence:
            return ""
        # match any number with optional decimal (e.g, 1 or 1.5 or .5)
        match = re.search(r"\.\d+|\d+(?:\.\d+)?", sequence)
        updated_sequence = match.group(0) if match else sequence
        if sequence != updated_sequence:
            logger.debug(
                '[Audible] Series "%s" sequence was cleaned from "%s" to "%s"',
                series_name,
                sequence,
                updated_sequence,
            )
        return updated_sequence

    def clean_result(self, item: dict[str, Any]) -> dict[str, Any]:
        """Clean and format the result from Audnex API"""
        title = item.get("title")
        subtitle = item.get("subtitle")
        asin = item.get("asin")
        authors = item.get("authors", [])
        narrators = item.get("narrators", [])
        publisher_name = item.get("publisherName")
        summary = item.get("summary")
        release_date = item.get("releaseDate")
        image = item.get("image")
        genres = item.get("genres", [])
        series_primary = item.get("seriesPrimary")
        series_secondary = item.get("seriesSecondary")
        language = item.get("language")
        runtime_length_min = item.get("runtimeLengthMin")
        format_type = item.get("formatType")
        isbn = item.get("isbn")

        series = []
        if series_primary:
            series.append(
                {
                    "series": series_primary.get("name"),
                    "sequence": self.clean_series_sequence(
                        series_primary.get("name", ""), series_primary.get("position", "")
                    ),
                }
            )
        if series_secondary:
            series.append(
                {
                    "series": series_secondary.get("name"),
                    "sequence": self.clean_series_sequence(
                        series_secondary.get("name", ""), series_secondary.get("position", "")
                    ),
                }
            )

        genres_filtered = [g.get("name") for g in genres if g.get("type") == "genre"]
        tags_filtered = [g.get("name") for g in genres if g.get("type") == "tag"]

        return {
            "title": title,
            "subtitle": subtitle or None,
            "author": ", ".join([a.get("name", "") for a in authors]) if authors else None,
            "narrator": ", ".join([n.get("name", "") for n in narrators]) if narrators else None,
            "publisher": publisher_name,
            "publishedYear": release_date.split("-")[0] if release_date else None,
            "description": summary or None,
            "cover": image,
            "asin": asin,
            "isbn": isbn,
            "genres": genres_filtered if genres_filtered else None,
            "tags": ", ".join(tags_filtered) if tags_filtered else None,
            "series": series if series else None,
            "language": language.capitalize() if language else None,
            "duration": int(runtime_length_min) if runtime_length_min and str(runtime_length_min).isdigit() else 0,
            "region": item.get("region") or None,
            "rating": item.get("rating") or None,
            "abridged": format_type == "abridged",
        }

    async def asin_search(self, asin: str, region: str = "us", timeout: int | None = None) -> dict[str, Any] | None:
        """Search for a book by ASIN

        Args:
            asin: The ASIN to search for
            region: The region code (default: us)
            timeout: Request timeout in seconds (uses client default if None)
        """
        if not asin:
            return None

        client = await self._get_client()
        asin = asin.upper()
        region_query = f"?region={region}" if region else ""
        url = f"https://api.audnex.us/books/{asin}{region_query}"
        logger.debug("[Audible] ASIN url: %s", url)

        data = await client.get_json(url, timeout=timeout)
        if data and data.get("asin"):
            return data
        return None

    async def search(
        self, title: str, author: str = "", asin: str = "", region: str = "us", timeout: int | None = None
    ) -> list[dict[str, Any]]:
        """Search for books using title, author, and/or ASIN

        Args:
            title: Book title to search for
            author: Author name (optional)
            asin: ASIN code (optional)
            region: Region code (default: us)
            timeout: Request timeout in seconds (uses client default if None)
        """
        if region and region not in self.region_map:
            logger.error("[Audible] search: Invalid region %s", region)
            region = "us"

        client = await self._get_client()
        items = []

        # Try ASIN search first if valid
        if asin and is_valid_asin(asin.upper()):
            item = await self.asin_search(asin, region, timeout)
            if item:
                items.append(item)

        # Try title as ASIN if no results and title looks like ASIN
        if not items and is_valid_asin(title.upper()):
            item = await self.asin_search(title, region, timeout)
            if item:
                items.append(item)

        # Fallback to catalog search
        if not items:
            query_obj = {"num_results": "10", "products_sort_by": "Relevance", "title": title}
            if author:
                query_obj["author"] = author

            query_string = urlencode(query_obj)
            tld = get_region_tld(region)
            url = f"https://api.audible{tld}/1.0/catalog/products?{query_string}"
            logger.debug("[Audible] Search url: %s", url)

            data = await client.get_json(url)

            if data and data.get("products"):
                # Get detailed info for each product
                detailed_items = []
                for result in data["products"]:
                    if result.get("asin"):
                        detailed_item = await self.asin_search(result["asin"], region, timeout)
                        if detailed_item:
                            detailed_items.append(detailed_item)
                items = detailed_items

        # Clean and return results
        return [self.clean_result(item) for item in items if item]


class Audnexus:
    """
    Async Audnexus API client using shared HTTP client.

    Example usage:
        async with Audnexus() as audnexus:
            author = await audnexus.find_author_by_name("Brandon Sanderson")
            chapters = await audnexus.get_chapters_by_asin("B08G9PRS1K")
    """

    def __init__(self, client: AsyncHttpClient | None = None) -> None:
        self._client = client
        self.base_url = "https://api.audnex.us"

    async def _get_client(self) -> AsyncHttpClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = await get_default_client()
        return self._client

    async def __aenter__(self) -> "Audnexus":
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

    async def author_asins_request(self, name: str, region: str = "") -> list[dict[str, Any]]:
        """Get author ASINs by name"""
        client = await self._get_client()

        params = {"name": name}
        if region:
            params["region"] = region

        url = f"{self.base_url}/authors?{urlencode(params)}"
        logger.info('[Audnexus] Searching for author "%s"', url)

        result = await client.get_json(url)
        if result is None:
            return []
        return result if isinstance(result, list) else [result]

    async def author_request(self, asin: str, region: str = "") -> dict[str, Any] | None:
        """Get author details by ASIN"""
        if not is_valid_asin(asin.upper()):
            logger.error("[Audnexus] Invalid ASIN %s", asin)
            return None

        client = await self._get_client()

        asin = asin.upper()
        params = {"region": region} if region else {}
        url = f"{self.base_url}/authors/{asin}"
        if params:
            url += f"?{urlencode(params)}"

        logger.info('[Audnexus] Searching for author "%s"', url)

        result = await client.get_json(url)
        return result

    async def find_author_by_asin(self, asin: str, region: str = "") -> dict[str, Any] | None:
        """Find author by ASIN"""
        author = await self.author_request(asin, region)

        if author:
            return {
                "asin": author.get("asin"),
                "description": author.get("description"),
                "image": author.get("image") or None,
                "name": author.get("name"),
            }
        return None

    async def find_author_by_name(self, name: str, region: str = "", max_levenshtein: int = 3) -> dict[str, Any] | None:
        """Find author by name with fuzzy matching"""
        logger.debug("[Audnexus] Looking up author by name %s", name)
        author_asin_objs = await self.author_asins_request(name, region)

        closest_match = None
        for author_asin_obj in author_asin_objs:
            author_name = author_asin_obj.get("name", "")
            distance = levenshtein_distance(author_name, name)
            author_asin_obj["levenshtein_distance"] = distance

            if not closest_match or closest_match["levenshtein_distance"] > distance:
                closest_match = author_asin_obj

        if not closest_match or closest_match["levenshtein_distance"] > max_levenshtein:
            return None

        author = await self.author_request(closest_match.get("asin", ""), region)
        if not author:
            return None

        return {
            "asin": author.get("asin"),
            "description": author.get("description"),
            "image": author.get("image") or None,
            "name": author.get("name"),
        }

    async def get_chapters_by_asin(self, asin: str, region: str = "") -> dict[str, Any] | None:
        """Get chapters for a book by ASIN"""
        logger.debug("[Audnexus] Get chapters for ASIN %s/%s", asin, region)

        client = await self._get_client()

        asin = asin.upper()
        params = {"region": region} if region else {}
        url = f"{self.base_url}/books/{asin}/chapters"
        if params:
            url += f"?{urlencode(params)}"

        result = await client.get_json(url)
        return result


# Main fetch metadata function compatible with existing code
def get_cached_metadata(asin: str, region: str = "us", api_url: str | None = None) -> dict | None:  # noqa: ARG001
    """Intentional stub kept for signature compatibility - tests are expected to patch/override this.

    This function is a placeholder whose parameters are currently unused in the default implementation.
    The function signature is maintained for backwards compatibility with existing code and tests.

    Args:
        asin: The Amazon Standard Identification Number (10 alphanumeric characters) to look up
        region: The Audible region/marketplace (e.g., 'us', 'uk', 'ca') for regional content
        api_url: Optional custom API endpoint URL for metadata lookup (typically None)

    Returns:
        None by default. Tests should patch this function to return mock metadata dict when needed.
        A real implementation might query a local cache or external API.

    Note:
        This is an intentional no-op stub. The default behavior returns None to indicate no cached
        metadata is available. Tests that require cached metadata should mock/patch this function
        to return appropriate test data.
    """
    # Default behavior: no cache. Tests may patch this to return values.
    return None


async def get_audible_asin(title: str, author: str = "") -> str | None:
    """Try to extract an ASIN by scraping Audible search results.

    This function attempts to import BeautifulSoup and parse the page returned by
    a simple Audible search. If bs4 is not available or parsing fails, return None.
    """
    try:
        import bs4

        BeautifulSoup = bs4.BeautifulSoup
    except ImportError:
        return None

    try:
        client = await get_default_client()

        query = f"{title} {author}".strip()
        # Simple Audible search URL
        search_url = f"https://www.audible.com/search?keywords={query.replace(' ', '+')}"

        response = await client.get(search_url)
        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        # Audible sometimes puts ASINs in adbl-impression-container data-asin
        el = soup.find("div", class_="adbl-impression-container")
        if el and hasattr(el, "get") and el.get("data-asin"):
            asin = el.get("data-asin")
            return str(asin) if asin and not isinstance(asin, list) else None

        # Fallback: look for data-asin attributes elsewhere
        el2 = soup.find(attrs={"data-asin": True})
        if el2 and hasattr(el2, "get"):
            asin2 = el2.get("data-asin")
            return str(asin2) if asin2 and not isinstance(asin2, list) else None

        return None
    except (AttributeError, ValueError, TypeError) as e:
        # Expected parsing-related errors - log and return None
        logger.debug("get_audible_asin failed: %s", e)
        return None
    except Exception as e:
        # bs4.FeatureNotFound and other BeautifulSoup parsing exceptions
        if "bs4" in type(e).__module__:
            logger.debug("get_audible_asin BeautifulSoup parsing failed: %s", e)
            return None
        # Unexpected exceptions should propagate
        raise


async def fetch_metadata(payload: dict, regions: list[str] | None = None) -> dict:
    """
    Enhanced metadata fetch using the new modular coordinator.

    Args:
        payload: Dict containing 'name', 'url', 'download_url'
        regions: Optional list of regions to try

    Returns:
        Metadata dict

    Raises:
        ValueError: If metadata cannot be fetched
    """
    from src.metadata_coordinator import MetadataCoordinator

    # Validate payload early to fail fast for invalid input
    config = load_config()
    req_keys = config.get("payload", {}).get("required_keys") or ["name", "url", "download_url"]
    if not validate_payload(payload, req_keys):
        raise ValueError(f"Payload missing required keys: {req_keys}")

    # Optional test-mode guard to prevent real external API calls during CI/test runs
    if os.getenv("DISABLE_EXTERNAL_API") == "1":
        logger.info("DISABLE_EXTERNAL_API set; avoiding external API calls in fetch_metadata()")
        raise ValueError("External API calls are disabled in this environment")

    coordinator = MetadataCoordinator()

    metadata = await coordinator.get_metadata_from_webhook(payload)

    if metadata:
        # Get enhanced metadata with chapters
        return await coordinator.get_enhanced_metadata(metadata)
    else:
        # Fallback to original logic for compatibility
        name = payload.get("name", "")
        title = payload.get("title") or name
        author = payload.get("author", "")

        # Extract ASIN from name if present
        asin_regex = config.get("payload", {}).get("asin_regex")
        match = re.search(asin_regex, name) if asin_regex else None
        asin = match.group(0) if match else None

        # Use provided regions or default sequence
        if not regions:
            regions = ["us", "ca", "uk", "au", "fr", "de", "jp", "it", "in", "es"]

        # If we have an ASIN, try to get cached metadata first
        if asin:
            cached = get_cached_metadata(asin, region="us", api_url=None)
            if cached:
                return cached

        # Attempt scraping to find an ASIN if none was extracted
        if not asin:
            scraped = await get_audible_asin(title, author)
            if scraped:
                asin = scraped
                cached = get_cached_metadata(asin, region="us", api_url=None)
                if cached:
                    return cached

        # If we still don't have an ASIN, try regions searching
        async with Audible() as audible:
            # Try searching with parallel regions (only if we have an ASIN)
            if asin:
                client = await get_default_client()
                regions_to_try = get_regions_priority(regions[0] if regions else "us", max_regions=len(regions))

                result, _found_region = await client.fetch_first_success(
                    regions=regions_to_try,
                    url_factory=lambda r: f"https://api.audnex.us/books/{asin}?region={r}",
                    validator=lambda d: bool(d.get("asin")),
                )

                if result:
                    return audible.clean_result(result)

            # Fallback to catalog search
            for region in regions:
                try:
                    if asin:
                        results = await audible.search(title=title, author=author, asin=asin, region=region)
                    else:
                        results = await audible.search(title=title, author=author, asin="", region=region)

                    if results:
                        # Return the first (best) result
                        return results[0]
                except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as e:
                    logger.warning("Error searching region %s: %s", region, e)
                    continue

        # Final error if we couldn't determine any metadata
        if not asin:
            raise ValueError("ASIN could not be determined")
        raise ValueError(f"Could not fetch metadata for '{name}' [{asin}]")


# Additional compatibility functions for existing tests and code
def clean_metadata(item: dict[str, Any]) -> dict[str, Any]:
    """Compatibility wrapper that returns legacy-shaped metadata for templates/tests.

    - Normalizes series into a readable string like "Series Name (Vol. 1.5)"
    - Ensures `narrators` is a list and `series` is an empty string when missing
    - Exposes `runtime_minutes` and both `cover` and `cover_url`
    """
    audible = Audible()
    base = audible.clean_result(item)

    result: dict[str, Any] = {}
    result["title"] = base.get("title")
    # Prefer cleaned authors (exclude translators/illustrators)
    authors_raw = item.get("authors") or []
    filtered_authors = clean_author_list(authors_raw)
    result["authors_raw"] = authors_raw
    result["author"] = filtered_authors[0] if filtered_authors else None

    # Narrators as list and narrator string
    narrator_raw = base.get("narrator")
    if narrator_raw:
        narrators = [n.strip() for n in narrator_raw.split(",") if n.strip()]
        narrator_str = narrator_raw
    else:
        # Fallback to raw item structure
        narrators_obj = item.get("narrators") or []
        narrators = [n.get("name") for n in narrators_obj if n.get("name")]
        narrator_str = ", ".join(narrators) if narrators else ""

    result["narrators"] = narrators
    result["narrator"] = narrator_str

    # Series formatting - prefer primary series only
    series_list = base.get("series")
    if series_list and isinstance(series_list, list) and len(series_list) > 0:
        entry = series_list[0]
        name = entry.get("series") or ""
        seq = entry.get("sequence") or ""
        if seq:
            result["series"] = f"{name} (Vol. {seq})"
        else:
            result["series"] = name
    else:
        result["series"] = ""
    # Also expose raw primary series from original item
    result["series_primary"] = item.get("seriesPrimary")

    # Genres and tags
    result["genres"] = base.get("genres") or []
    result["tags"] = base.get("tags") or ""

    # Summary / description (preserve raw description fields)
    result["summary"] = item.get("summary") or base.get("description") or ""
    result["description"] = item.get("description") or base.get("description") or ""

    # Runtime and cover
    result["runtime_minutes"] = base.get("duration", 0)
    result["cover"] = base.get("cover")
    result["cover_url"] = base.get("cover")

    # Preserve other useful fields for compatibility
    result["asin"] = base.get("asin")
    # Release date - prefer raw YYYY-MM-DD if available
    result["release_date"] = item.get("releaseDate") or base.get("publishedYear") or ""

    return result
