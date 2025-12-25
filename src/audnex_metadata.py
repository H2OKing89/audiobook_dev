"""
Audnex API metadata fetcher
Gets audiobook metadata from api.audnex.us using ASIN

This module provides async methods for fetching audiobook metadata from the Audnex API,
with parallel region fetching for improved performance.
"""

import argparse
import asyncio
import re
from typing import Any, ClassVar
from urllib.parse import urlencode

from src.config import load_config
from src.http_client import (
    DEFAULT_REGIONS,
    AsyncHttpClient,
    get_default_client,
    get_regions_priority,
)
from src.logging_setup import get_logger


log = get_logger(__name__)


class AudnexMetadata:
    """
    Async Audnex API metadata client with parallel region fetching.

    Supports the Audnex API v1.8.0 endpoints:
    - GET /books/{ASIN} - Get book metadata
    - GET /books/{ASIN}/chapters - Get chapter information
    - GET /authors - Search authors by name
    - GET /authors/{ASIN} - Get author by ASIN

    Example usage:
        async with AudnexMetadata() as audnex:
            metadata = await audnex.get_book_by_asin("B08G9PRS1K")
            chapters = await audnex.get_chapters_by_asin("B08G9PRS1K")
            # With author seeding for enriched author data
            metadata = await audnex.get_book_by_asin("B08G9PRS1K", seed_authors=True)
    """

    # Valid region codes per API spec
    VALID_REGIONS: ClassVar[set[str]] = {"au", "ca", "de", "es", "fr", "in", "it", "jp", "us", "uk"}

    def __init__(self, client: AsyncHttpClient | None = None) -> None:
        """
        Initialize the Audnex metadata client.

        Args:
            client: Optional AsyncHttpClient instance. If not provided, uses the default shared client.
        """
        self._client = client
        self.config: dict = load_config()
        self.audnex_config: dict = self.config.get("metadata", {}).get("audnex", {})
        self.base_url: str = self.audnex_config.get("base_url", "https://api.audnex.us")

        # Region configuration
        self.regions: list[str] = self.audnex_config.get("regions", DEFAULT_REGIONS.copy())
        self.try_all_regions: bool = self.audnex_config.get("try_all_regions_on_error", True)
        self.max_regions: int = self.audnex_config.get("max_regions_to_try", 10)

        # API options (from config)
        self.seed_authors: bool = self.audnex_config.get("seed_authors", False)
        self.force_update: bool = self.audnex_config.get("force_update", False)

    async def _get_client(self) -> AsyncHttpClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = await get_default_client()
        return self._client

    async def __aenter__(self) -> "AudnexMetadata":
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

    def _validate_asin(self, asin: str, context: str = "asin") -> str | None:
        """
        Validate and normalize an ASIN.

        Args:
            asin: The ASIN to validate
            context: Context for logging (e.g., "book", "author", "chapters")

        Returns:
            Normalized uppercase ASIN if valid, None otherwise
        """
        if not asin:
            log.error("audnex.invalid_asin", context=context, asin=asin, reason="empty")
            return None

        # ASINs are typically 10 characters, but allow some flexibility
        # Amazon ASINs are alphanumeric (B followed by 9 alphanumeric chars for books)
        asin = asin.strip().upper()
        if len(asin) != 10:
            log.error("audnex.invalid_asin", context=context, asin=asin, reason="wrong_length")
            return None

        # Basic alphanumeric check
        if not asin.isalnum():
            log.error("audnex.invalid_asin", context=context, asin=asin, reason="non_alphanumeric")
            return None

        return asin

    def _validate_region(self, region: str) -> str:
        """Validate and normalize region code, defaulting to 'us' if invalid."""
        region = region.lower().strip()
        if region not in self.VALID_REGIONS:
            log.warning("audnex.invalid_region", region=region, using="us")
            return "us"
        return region

    async def get_book_by_asin(
        self,
        asin: str,
        region: str = "us",
        *,
        seed_authors: bool | None = None,
        update: bool | None = None,
    ) -> dict[str, Any] | None:
        """
        Get book metadata by ASIN with parallel region fetching.

        Args:
            asin: Amazon Standard Identification Number (10 characters)
            region: Preferred region to try first (default: "us")
            seed_authors: Whether to seed/populate author information (default: from config)
            update: Force server to check for updated data upstream (default: from config)

        Returns:
            Cleaned metadata dict or None if not found
        """
        validated_asin = self._validate_asin(asin, "book")
        if not validated_asin:
            return None

        region = self._validate_region(region)
        client = await self._get_client()

        # Use config defaults if not explicitly provided
        use_seed_authors = seed_authors if seed_authors is not None else self.seed_authors
        use_update = update if update is not None else self.force_update

        # Build region list with preferred region first
        if self.try_all_regions:
            regions = get_regions_priority(region, max_regions=self.max_regions)
        else:
            regions = [region]

        log.info("audnex.book.fetch", asin=validated_asin, region_count=len(regions), seed_authors=use_seed_authors)

        # Build query params
        def url_factory(r: str) -> str:
            params = [f"region={r}"]
            if use_seed_authors:
                params.append("seedAuthors=1")
            if use_update:
                params.append("update=1")
            return f"{self.base_url}/books/{validated_asin}?{'&'.join(params)}"

        # Parallel fetch with ASIN validation
        result, found_region = await client.fetch_first_success(
            regions=regions,
            url_factory=url_factory,
            validator=lambda d: bool(d.get("asin")),
        )

        if result:
            log.info("audnex.book.found", asin=validated_asin, region=found_region)
            metadata = self._clean_book_metadata(result)
            metadata["audnex_region"] = found_region
            return metadata

        log.error("audnex.book.not_found", asin=validated_asin)
        return None

    async def get_chapters_by_asin(
        self,
        asin: str,
        region: str = "us",
        *,
        update: bool | None = None,
    ) -> dict[str, Any] | None:
        """
        Get chapter information by ASIN with parallel region fetching.

        Args:
            asin: Amazon Standard Identification Number (10 characters)
            region: Preferred region to try first (default: "us")
            update: Force server to check for updated data upstream (default: from config)

        Returns:
            Cleaned chapters dict or None if not found
        """
        validated_asin = self._validate_asin(asin, "chapters")
        if not validated_asin:
            return None

        region = self._validate_region(region)
        client = await self._get_client()

        # Use config default if not explicitly provided
        use_update = update if update is not None else self.force_update

        # Build region list with preferred region first
        if self.try_all_regions:
            regions = get_regions_priority(region, max_regions=self.max_regions)
        else:
            regions = [region]

        log.info("audnex.chapters.fetch", asin=validated_asin, region_count=len(regions))

        # Build query params
        def url_factory(r: str) -> str:
            params = [f"region={r}"]
            if use_update:
                params.append("update=1")
            return f"{self.base_url}/books/{validated_asin}/chapters?{'&'.join(params)}"

        # Parallel fetch - chapters just need to be non-empty
        result, found_region = await client.fetch_first_success(
            regions=regions,
            url_factory=url_factory,
            validator=bool,
        )

        if result:
            log.info("audnex.chapters.found", asin=validated_asin, region=found_region)
            cleaned = self._clean_chapters_metadata(result)
            cleaned["audnex_region"] = found_region
            return cleaned

        log.error("audnex.chapters.not_found", asin=validated_asin)
        return None

    async def search_author_by_name(
        self,
        name: str,
        region: str = "us",
    ) -> list[dict[str, Any]]:
        """
        Search for authors by name with parallel region fetching.

        Args:
            name: Author name to search for
            region: Preferred region to try first (default: "us")

        Returns:
            List of author results
        """
        if not name or not name.strip():
            log.error("audnex.author_search.invalid_name", name=name)
            return []

        name = name.strip()
        region = self._validate_region(region)
        client = await self._get_client()

        # Build region list for parallel fetching
        if self.try_all_regions:
            regions = get_regions_priority(region, max_regions=self.max_regions)
        else:
            regions = [region]

        log.info("audnex.author_search.start", name=name, region_count=len(regions))

        # URL factory with proper encoding
        def url_factory(r: str) -> str:
            params = urlencode({"name": name, "region": r})
            return f"{self.base_url}/authors?{params}"

        # Parallel fetch - need at least one result
        result, found_region = await client.fetch_first_success(
            regions=regions,
            url_factory=url_factory,
            validator=lambda d: bool(d) if isinstance(d, list) else bool(d.get("asin")),
        )

        if result:
            log.info("audnex.author_search.found", name=name, region=found_region)
            if isinstance(result, list):
                return result
            else:
                return [result]

        log.warning("audnex.author_search.not_found", name=name)
        return []

    async def get_author_by_asin(
        self,
        asin: str,
        region: str = "us",
        *,
        update: bool | None = None,
    ) -> dict[str, Any] | None:
        """
        Get author information by ASIN with parallel region fetching.

        Args:
            asin: Author ASIN (10 characters)
            region: Preferred region to try first (default: "us")
            update: Force server to check for updated data upstream (default: from config)

        Returns:
            Cleaned author info dict or None if not found
        """
        validated_asin = self._validate_asin(asin, "author")
        if not validated_asin:
            return None

        region = self._validate_region(region)
        client = await self._get_client()

        # Use config default if not explicitly provided
        use_update = update if update is not None else self.force_update

        # Build region list for parallel fetching
        if self.try_all_regions:
            regions = get_regions_priority(region, max_regions=self.max_regions)
        else:
            regions = [region]

        log.info("audnex.author.fetch", asin=validated_asin, region_count=len(regions))

        # Build query params
        def url_factory(r: str) -> str:
            params = [f"region={r}"]
            if use_update:
                params.append("update=1")
            return f"{self.base_url}/authors/{validated_asin}?{'&'.join(params)}"

        # Parallel fetch with ASIN validation
        result, found_region = await client.fetch_first_success(
            regions=regions,
            url_factory=url_factory,
            validator=lambda d: bool(d.get("asin")),
        )

        if result:
            log.info("audnex.author.found", asin=validated_asin, region=found_region)
            cleaned = self._clean_author_metadata(result)
            cleaned["audnex_region"] = found_region
            return cleaned

        log.warning("audnex.author.not_found", asin=validated_asin)
        return None

    def _clean_book_metadata(self, item: dict[str, Any]) -> dict[str, Any]:
        """Clean and format book metadata from Audnex response."""
        # Extract basic information
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

        # New fields from API spec v1.8.0
        copyright_year = item.get("copyright")
        is_adult = item.get("isAdult", False)
        literature_type = item.get("literatureType")  # "fiction" or "nonfiction"
        rating = item.get("rating")

        # Process series information
        series = []
        if series_primary:
            series.append(
                {
                    "series": series_primary.get("name"),
                    "asin": series_primary.get("asin"),
                    "sequence": self._clean_series_sequence(
                        series_primary.get("name", ""), series_primary.get("position", "")
                    ),
                }
            )
        if series_secondary:
            series.append(
                {
                    "series": series_secondary.get("name"),
                    "asin": series_secondary.get("asin"),
                    "sequence": self._clean_series_sequence(
                        series_secondary.get("name", ""), series_secondary.get("position", "")
                    ),
                }
            )

        # Filter genres and tags
        genres_filtered = [g.get("name") for g in genres if g.get("type") == "genre"]
        tags_filtered = [g.get("name") for g in genres if g.get("type") == "tag"]

        # Parse runtime safely
        runtime_min = 0
        if runtime_length_min is not None:
            try:
                runtime_min = int(runtime_length_min)
            except (ValueError, TypeError):
                runtime_min = 0

        # Build comprehensive metadata object matching original script format
        cleaned = {
            # Primary book information
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
            "language": language.capitalize() if language else None,
            "duration": runtime_min,
            "region": item.get("region") or "us",
            "rating": rating,
            "abridged": format_type == "abridged",
            # New fields from API spec v1.8.0
            "copyright": copyright_year,
            "isAdult": is_adult,
            "literatureType": literature_type,
            # Series information
            "series": series if series else None,
            # Genre and categorization
            "genres": genres_filtered if genres_filtered else None,
            "tags": ", ".join(tags_filtered) if tags_filtered else None,
            # Raw data for advanced processing
            "authors_raw": authors,
            "narrators_raw": narrators,
            "series_raw": series,
            "runtime_minutes": runtime_length_min,
            "release_date": release_date,
            "cover_url": image,
            "genres_raw": genres,
            # Additional fields from original script
            "formatType": format_type,
            "runtimeLengthMin": runtime_length_min,
            "publisherName": publisher_name,
            "summary": summary,
            "image": image,
            "seriesPrimary": series_primary,
            "seriesSecondary": series_secondary,
            # Computed fields
            "author_list": [a.get("name", "") for a in authors] if authors else [],
            "narrator_list": [n.get("name", "") for n in narrators] if narrators else [],
            "genre_list": genres_filtered if genres_filtered else [],
            "tag_list": tags_filtered if tags_filtered else [],
            # Compatibility fields for notifications and templates
            "book_title": title,
            "book_author": ", ".join([a.get("name", "") for a in authors]) if authors else "",
            "book_narrator": ", ".join([n.get("name", "") for n in narrators]) if narrators else "",
            "book_publisher": publisher_name or "",
            "book_description": summary or "",
            "book_cover": image or "",
            "book_asin": asin or "",
            "book_isbn": isbn or "",
            "book_language": language.capitalize() if language else "",
            "book_duration": runtime_min,
            "book_rating": rating or 0,
            "book_genres": ", ".join(genres_filtered) if genres_filtered else "",
            "book_tags": ", ".join(tags_filtered) if tags_filtered else "",
            # Series information for templates
            "book_series": series[0]["series"] if series else "",
            "book_series_sequence": series[0]["sequence"] if series else "",
            "book_series_info": f"{series[0]['series']} #{series[0]['sequence']}" if series else "",
            # Publishing information
            "book_copyright": copyright_year or "",
            "book_published_year": release_date.split("-")[0] if release_date else "",
            "book_release_date": release_date or "",
            "book_format": format_type or "",
            "book_abridged": format_type == "abridged",
            "book_is_adult": is_adult,
            "book_literature_type": literature_type or "",
            # Technical fields
            "runtime_length_min": runtime_length_min,
            "runtime_length_hours": round(runtime_min / 60, 1) if runtime_min else 0,
            "file_size_mb": item.get("file_size_mb", 0),  # May not be available from Audnex
            "quality": item.get("quality", "Unknown"),  # May not be available from Audnex
        }

        return cleaned

    def _clean_chapters_metadata(self, item: dict[str, Any]) -> dict[str, Any]:
        """Clean and format chapter metadata from Audnex response."""
        asin = item.get("asin")
        brand_intro_ms = item.get("brandIntroDurationMs", 0)
        brand_outro_ms = item.get("brandOutroDurationMs", 0)
        chapters = item.get("chapters", [])
        is_accurate = item.get("isAccurate", False)
        region = item.get("region", "us")
        runtime_ms = item.get("runtimeLengthMs", 0)
        runtime_sec = item.get("runtimeLengthSec", 0)

        # Clean individual chapters
        cleaned_chapters = []
        for chapter in chapters:
            cleaned_chapters.append(
                {
                    "title": chapter.get("title", ""),
                    "lengthMs": chapter.get("lengthMs", 0),
                    "lengthSec": round(chapter.get("lengthMs", 0) / 1000) if chapter.get("lengthMs") else 0,
                    "startOffsetMs": chapter.get("startOffsetMs", 0),
                    "startOffsetSec": chapter.get("startOffsetSec", 0),
                }
            )

        return {
            "asin": asin,
            "region": region,
            "brandIntroDurationMs": brand_intro_ms,
            "brandOutroDurationMs": brand_outro_ms,
            "brandIntroDurationSec": round(brand_intro_ms / 1000) if brand_intro_ms else 0,
            "brandOutroDurationSec": round(brand_outro_ms / 1000) if brand_outro_ms else 0,
            "chapters": cleaned_chapters,
            "chapter_count": len(cleaned_chapters),
            "isAccurate": is_accurate,
            "runtimeLengthMs": runtime_ms,
            "runtimeLengthSec": runtime_sec,
            "runtimeLengthMin": round(runtime_sec / 60) if runtime_sec else 0,
            "runtimeLengthHours": round(runtime_sec / 3600, 2) if runtime_sec else 0,
            # Raw data
            "chapters_raw": chapters,
        }

    def _clean_author_metadata(self, item: dict[str, Any]) -> dict[str, Any]:
        """Clean and format author metadata from Audnex response."""
        asin = item.get("asin")
        name = item.get("name")
        description = item.get("description")
        image = item.get("image")
        region = item.get("region", "us")
        genres = item.get("genres", [])
        similar = item.get("similar", [])

        # Filter genres
        genres_filtered = [g.get("name") for g in genres if g.get("type") == "genre"]
        tags_filtered = [g.get("name") for g in genres if g.get("type") == "tag"]

        # Process similar authors
        similar_authors = []
        for author in similar:
            similar_authors.append(
                {
                    "asin": author.get("asin"),
                    "name": author.get("name"),
                }
            )

        return {
            "asin": asin,
            "name": name,
            "description": description,
            "image": image,
            "region": region,
            # Genres and tags
            "genres": genres_filtered if genres_filtered else None,
            "tags": tags_filtered if tags_filtered else None,
            "genre_list": genres_filtered if genres_filtered else [],
            "tag_list": tags_filtered if tags_filtered else [],
            "genres_raw": genres,
            # Similar authors
            "similar": similar_authors if similar_authors else None,
            "similar_raw": similar,
            "similar_count": len(similar_authors),
            # Compatibility fields for templates
            "author_name": name or "",
            "author_asin": asin or "",
            "author_description": description or "",
            "author_image": image or "",
            "author_genres": ", ".join(genres_filtered) if genres_filtered else "",
        }

    def _clean_series_sequence(self, series_name: str, sequence: str) -> str:
        """Clean series sequence to extract just the number portion."""
        if not sequence:
            return ""

        # Match any number with optional decimal (e.g, 1 or 1.5 or .5)
        match = re.search(r"\.\d+|\d+(?:\.\d+)?", sequence)
        updated_sequence = match.group(0) if match else sequence

        if sequence != updated_sequence:
            log.debug("audnex.series_sequence.cleaned", series=series_name, original=sequence, cleaned=updated_sequence)

        return updated_sequence


async def async_main():
    """Async main function for command line usage."""
    parser = argparse.ArgumentParser(description="Audnex Metadata Fetcher")
    parser.add_argument("asin", nargs="?", help="ASIN to fetch metadata for")
    parser.add_argument("--region", default="us", help="Audible region (default: us)")
    parser.add_argument("--chapters", action="store_true", help="Also fetch chapter information")
    parser.add_argument("--seed-authors", action="store_true", help="Seed/populate author information")
    parser.add_argument("--update", action="store_true", help="Force server to check for updated data")
    parser.add_argument("--author", help="Fetch author by ASIN")
    parser.add_argument("--search-author", help="Search for authors by name")
    args = parser.parse_args()

    async with AudnexMetadata() as fetcher:
        # Search for authors by name
        if args.search_author:
            authors = await fetcher.search_author_by_name(args.search_author, region=args.region)
            if authors:
                print(f"Found {len(authors)} author(s):")
                for author in authors:
                    print(f"  {author.get('name')} (ASIN: {author.get('asin')})")
            else:
                print(f"No authors found for: {args.search_author}")
            return

        # Fetch author by ASIN
        if args.author:
            author_result = await fetcher.get_author_by_asin(args.author, region=args.region, update=args.update)
            if author_result:
                print("Author found:")
                print(f"  Name: {author_result.get('name')}")
                print(f"  ASIN: {author_result.get('asin')}")
                print(f"  Region: {author_result.get('audnex_region')}")
                description = author_result.get("description")
                if description:
                    print(f"  Description: {str(description)[:200]}...")
                if author_result.get("genres"):
                    print(f"  Genres: {', '.join(author_result.get('genres', []))}")
                if author_result.get("similar"):
                    print(f"  Similar authors: {len(author_result.get('similar', []))}")
            else:
                print(f"No author found for ASIN: {args.author}")
            return

        # Require ASIN for book lookup
        if not args.asin:
            parser.error("ASIN is required for book lookup (or use --author/--search-author)")

        # Get book metadata
        metadata = await fetcher.get_book_by_asin(
            args.asin,
            region=args.region,
            seed_authors=args.seed_authors,
            update=args.update,
        )

        if metadata:
            print("Book metadata found:")
            print(f"  Title: {metadata.get('title')}")
            print(f"  Author: {metadata.get('author')}")
            print(f"  ASIN: {metadata.get('asin')}")
            print(f"  Publisher: {metadata.get('publisher')}")
            print(f"  Duration: {metadata.get('duration')} minutes")
            print(f"  Region: {metadata.get('audnex_region')}")
            if metadata.get("literatureType"):
                print(f"  Type: {metadata.get('literatureType')}")
            if metadata.get("copyright"):
                print(f"  Copyright: {metadata.get('copyright')}")
            if metadata.get("isAdult"):
                print("  Adult content: Yes")
            if metadata.get("series"):
                for series in metadata["series"]:
                    print(f"  Series: {series['series']} #{series['sequence']}")

            # Get chapters if requested
            if args.chapters:
                chapters = await fetcher.get_chapters_by_asin(args.asin, region=args.region, update=args.update)
                if chapters:
                    print(f"\nChapters ({chapters.get('chapter_count', 0)} total):")
                    print(f"  Runtime: {chapters.get('runtimeLengthMin', 0)} minutes")
                    print(f"  Accurate: {chapters.get('isAccurate', False)}")
                    for i, ch in enumerate(chapters.get("chapters", [])[:5]):
                        print(f"    {i + 1}. {ch.get('title')} ({ch.get('lengthSec', 0)}s)")
                    if len(chapters.get("chapters", [])) > 5:
                        print(f"    ... and {len(chapters.get('chapters', [])) - 5} more chapters")
        else:
            print(f"No metadata found for ASIN: {args.asin}")


def main():
    """Main entry point for command line usage."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
