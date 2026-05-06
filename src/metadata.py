"""Metadata compatibility helpers and legacy Audnexus client."""

import re
from typing import Any
from urllib.parse import urlencode

from src.audible_scraper import AudibleScraper
from src.http_client import (
    AsyncHttpClient,
    get_default_client,
)
from src.logging_setup import get_logger
from src.utils import clean_author_list


log = get_logger(__name__)


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


def clean_series_sequence(series_name: str, sequence: str) -> str:
    """Normalize series numbering like "Book 1" to a plain numeric value."""
    if not sequence:
        return ""

    match = re.search(r"\.\d+|\d+(?:\.\d+)?", sequence)
    updated_sequence = match.group(0) if match else sequence
    if sequence != updated_sequence:
        log.debug(
            "metadata.series_sequence.cleaned",
            series=series_name,
            original=sequence,
            cleaned=updated_sequence,
        )
    return updated_sequence


def _extract_names(values: list[Any]) -> list[str]:
    names: list[str] = []
    for value in values:
        if isinstance(value, dict):
            name = value.get("name", "")
        elif isinstance(value, str):
            name = value
        else:
            name = ""

        if name:
            names.append(name)

    return names


def normalize_book_result(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize raw Audnex or Audible payloads into the app's common shape."""
    title = item.get("title")
    subtitle = item.get("subtitle")
    asin = item.get("asin")
    authors = _extract_names(item.get("authors", []))
    narrators = _extract_names(item.get("narrators", []))
    publisher_name = item.get("publisherName") or item.get("publisher_name") or item.get("publisher")
    summary = item.get("summary") or item.get("description")
    release_date = item.get("releaseDate") or item.get("release_date")
    image = item.get("image") or item.get("cover") or item.get("cover_url")
    genres = item.get("genres", [])
    language = item.get("language")
    runtime_length_min = (
        item.get("runtimeLengthMin")
        or item.get("runtime_length_min")
        or item.get("runtime_minutes")
        or item.get("duration")
        or item.get("length")
    )
    format_type = item.get("formatType") or item.get("format_type")
    isbn = item.get("isbn")

    series: list[dict[str, str]] = []
    for existing_series in item.get("series", []):
        if not isinstance(existing_series, dict):
            continue
        series_name = existing_series.get("series") or existing_series.get("title") or existing_series.get("name") or ""
        sequence = existing_series.get("sequence") or existing_series.get("position") or ""
        if series_name:
            series.append(
                {
                    "series": series_name,
                    "sequence": clean_series_sequence(series_name, str(sequence)),
                }
            )

    for series_key in ("seriesPrimary", "seriesSecondary"):
        series_entry = item.get(series_key)
        if not isinstance(series_entry, dict):
            continue
        series_name = series_entry.get("name", "")
        if not series_name:
            continue
        series.append(
            {
                "series": series_name,
                "sequence": clean_series_sequence(series_name, series_entry.get("position", "")),
            }
        )

    genres_filtered: list[str] = []
    tags_filtered: list[str] = []
    for genre in genres:
        if isinstance(genre, dict):
            name = genre.get("name")
            genre_type = genre.get("type")
            if not name:
                continue
            if genre_type == "tag":
                tags_filtered.append(name)
            else:
                genres_filtered.append(name)
        elif isinstance(genre, str):
            genres_filtered.append(genre)

    existing_tags = item.get("tags")
    tags_value: str | None
    if isinstance(existing_tags, str):
        tags_value = existing_tags
    else:
        tags_value = ", ".join(tags_filtered) if tags_filtered else None

    duration = 0
    if runtime_length_min is not None and str(runtime_length_min).isdigit():
        duration = int(runtime_length_min)

    return {
        "title": title,
        "subtitle": subtitle or None,
        "author": ", ".join(authors) if authors else item.get("author") or None,
        "narrator": ", ".join(narrators) if narrators else item.get("narrator") or None,
        "publisher": publisher_name,
        "publishedYear": release_date.split("-")[0] if release_date else item.get("publishedYear") or None,
        "description": summary or None,
        "cover": image,
        "asin": asin,
        "isbn": isbn,
        "genres": genres_filtered if genres_filtered else None,
        "tags": tags_value,
        "series": series if series else None,
        "language": language.capitalize() if isinstance(language, str) else None,
        "duration": duration,
        "region": item.get("region") or None,
        "rating": item.get("rating") or None,
        "abridged": format_type == "abridged",
    }


class Audnexus:
    """
    Async Audnexus API client using shared HTTP client.

    .. deprecated::
        This class is deprecated. Use :class:`src.audnex_metadata.AudnexMetadata` instead,
        which provides enhanced functionality including:
        - Parallel region fetching
        - seed_authors and update parameters
        - Input validation and cleaning
        - Config-based defaults

    Example usage:
        # Preferred: Use AudnexMetadata instead
        from src.audnex_metadata import AudnexMetadata
        async with AudnexMetadata() as audnex:
            author = await audnex.search_author_by_name("Brandon Sanderson")
            chapters = await audnex.get_chapters_by_asin("B08G9PRS1K")

        # Legacy (deprecated):
        async with Audnexus() as audnexus:
            author = await audnexus.find_author_by_name("Brandon Sanderson")
            chapters = await audnexus.get_chapters_by_asin("B08G9PRS1K")
    """

    def __init__(self, client: AsyncHttpClient | None = None) -> None:
        import warnings

        warnings.warn(
            "Audnexus is deprecated, use AudnexMetadata from src.audnex_metadata instead",
            DeprecationWarning,
            stacklevel=2,
        )
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
        log.info("metadata.audnex.author_asins_search", url=url)

        result = await client.get_json(url)
        if result is None:
            return []
        return result if isinstance(result, list) else [result]

    async def author_request(self, asin: str, region: str = "") -> dict[str, Any] | None:
        """Get author details by ASIN"""
        if not is_valid_asin(asin.upper()):
            log.error("metadata.audnex.invalid_asin", asin=asin)
            return None

        client = await self._get_client()

        asin = asin.upper()
        params = {"region": region} if region else {}
        url = f"{self.base_url}/authors/{asin}"
        if params:
            url += f"?{urlencode(params)}"

        log.info("metadata.audnex.author_request", url=url)

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
        log.debug("metadata.audnex.find_author_by_name", name=name)
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
        log.debug("metadata.audnex.get_chapters", asin=asin, region=region)

        client = await self._get_client()

        asin = asin.upper()
        params = {"region": region} if region else {}
        url = f"{self.base_url}/books/{asin}/chapters"
        if params:
            url += f"?{urlencode(params)}"

        result = await client.get_json(url)
        return result


async def get_audible_asin(title: str, author: str = "") -> str | None:
    """Try to extract an ASIN using the package-backed Audible search backend."""

    try:
        async with AudibleScraper() as scraper:
            results = await scraper.search(title=title, author=author)
            for result in results:
                asin = result.get("asin")
                if isinstance(asin, str) and is_valid_asin(asin.upper()):
                    return asin.upper()
        return None
    except Exception as e:
        log.debug("metadata.get_audible_asin.failed", error=str(e))
        return None


# Additional compatibility functions for existing tests and code
def clean_metadata(item: dict[str, Any]) -> dict[str, Any]:
    """Compatibility wrapper that returns legacy-shaped metadata for templates/tests.

    - Normalizes series into a readable string like "Series Name (Vol. 1.5)"
    - Ensures `narrators` is a list and `series` is an empty string when missing
    - Exposes `runtime_minutes` and both `cover` and `cover_url`
    """
    base = normalize_book_result(item)

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
