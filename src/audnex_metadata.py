"""
Audnex API metadata fetcher
Gets audiobook metadata from api.audnex.us using ASIN

This module provides async methods for fetching audiobook metadata from the Audnex API,
with parallel region fetching for improved performance.
"""

import argparse
import asyncio
import logging
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from src.config import load_config
from src.http_client import (
    DEFAULT_REGIONS,
    AsyncHttpClient,
    get_default_client,
    get_regions_priority,
)


logger = logging.getLogger(__name__)

# Ensure logs directory exists before configuring logging
_log_dir = Path(__file__).parent.parent / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)

# Configure logging (only if not already configured)
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(_log_dir / "audnex_metadata.log")],
    )


class AudnexMetadata:
    """
    Async Audnex API metadata client with parallel region fetching.

    Example usage:
        async with AudnexMetadata() as audnex:
            metadata = await audnex.get_book_by_asin("B08G9PRS1K")
            chapters = await audnex.get_chapters_by_asin("B08G9PRS1K")
    """

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
        pass

    async def get_book_by_asin(self, asin: str, region: str = "us") -> dict[str, Any] | None:
        """
        Get book metadata by ASIN with parallel region fetching.

        Args:
            asin: Amazon Standard Identification Number (10 characters)
            region: Preferred region to try first (default: "us")

        Returns:
            Cleaned metadata dict or None if not found
        """
        if not asin or len(asin) != 10:
            logger.error("Invalid ASIN format: %s", asin)
            return None

        asin = asin.upper()
        client = await self._get_client()

        # Build region list with preferred region first
        if self.try_all_regions:
            regions = get_regions_priority(region, max_regions=self.max_regions)
        else:
            regions = [region]

        logger.info("Fetching book metadata for ASIN: %s (trying %d regions)", asin, len(regions))

        # Parallel fetch with ASIN validation
        result, found_region = await client.fetch_first_success(
            regions=regions,
            url_factory=lambda r: f"{self.base_url}/books/{asin}?region={r}",
            validator=lambda d: bool(d.get("asin")),
        )

        if result:
            logger.info("Book found for ASIN %s in region %s", asin, found_region)
            metadata = self._clean_book_metadata(result)
            metadata["audnex_region"] = found_region
            return metadata

        logger.error("No metadata found for ASIN %s in any region", asin)
        return None

    async def get_chapters_by_asin(self, asin: str, region: str = "us") -> dict[str, Any] | None:
        """
        Get chapter information by ASIN with parallel region fetching.

        Args:
            asin: Amazon Standard Identification Number (10 characters)
            region: Preferred region to try first (default: "us")

        Returns:
            Chapters dict or None if not found
        """
        if not asin or len(asin) != 10:
            logger.error("Invalid ASIN format: %s", asin)
            return None

        asin = asin.upper()
        client = await self._get_client()

        # Build region list with preferred region first
        if self.try_all_regions:
            regions = get_regions_priority(region, max_regions=self.max_regions)
        else:
            regions = [region]

        logger.info("Fetching chapters for ASIN: %s (trying %d regions)", asin, len(regions))

        # Parallel fetch - chapters just need to be non-empty
        result, found_region = await client.fetch_first_success(
            regions=regions,
            url_factory=lambda r: f"{self.base_url}/books/{asin}/chapters?region={r}",
            validator=lambda d: bool(d),
        )

        if result:
            logger.info("Chapters found for ASIN %s in region %s", asin, found_region)
            if isinstance(result, dict):
                result["audnex_region"] = found_region
            return result

        logger.error("No chapters found for ASIN %s in any region", asin)
        return None

    async def search_author_by_name(self, name: str, region: str = "us") -> list[dict[str, Any]]:
        """
        Search for authors by name.

        Args:
            name: Author name to search for
            region: Audible region (default: "us")

        Returns:
            List of author results
        """
        client = await self._get_client()

        params = {"name": name}
        if region:
            params["region"] = region

        url = f"{self.base_url}/authors?{urlencode(params)}"
        logger.info("Searching for author: %s (region: %s)", name, region)

        result = await client.get_json(url)

        if result:
            if isinstance(result, list):
                logger.info("Found %d author results for: %s", len(result), name)
                return result
            else:
                logger.info("Found 1 author result for: %s", name)
                return [result]

        logger.warning("No authors found for: %s", name)
        return []

    async def get_author_by_asin(self, asin: str, region: str = "us") -> dict[str, Any] | None:
        """
        Get author information by ASIN.

        Args:
            asin: Author ASIN (10 characters)
            region: Audible region (default: "us")

        Returns:
            Author info dict or None if not found
        """
        if not asin or len(asin) != 10:
            logger.error("Invalid ASIN format: %s", asin)
            return None

        asin = asin.upper()
        client = await self._get_client()

        params = {"region": region} if region else {}
        url = f"{self.base_url}/authors/{asin}"
        if params:
            url += f"?{urlencode(params)}"

        logger.info("Fetching author for ASIN: %s (region: %s)", asin, region)

        result = await client.get_json(url)

        if result and result.get("asin"):
            logger.info("Author found for ASIN: %s", asin)
            return result

        logger.warning("No author found for ASIN: %s", asin)
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

        # Process series information
        series = []
        if series_primary:
            series.append(
                {
                    "series": series_primary.get("name"),
                    "sequence": self._clean_series_sequence(
                        series_primary.get("name", ""), series_primary.get("position", "")
                    ),
                }
            )
        if series_secondary:
            series.append(
                {
                    "series": series_secondary.get("name"),
                    "sequence": self._clean_series_sequence(
                        series_secondary.get("name", ""), series_secondary.get("position", "")
                    ),
                }
            )

        # Filter genres and tags
        genres_filtered = [g.get("name") for g in genres if g.get("type") == "genre"]
        tags_filtered = [g.get("name") for g in genres if g.get("type") == "tag"]

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
            "duration": int(runtime_length_min) if runtime_length_min and str(runtime_length_min).isdigit() else 0,
            "region": item.get("region") or "us",
            "rating": item.get("rating") or None,
            "abridged": format_type == "abridged",
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
            "book_duration": int(runtime_length_min) if runtime_length_min and str(runtime_length_min).isdigit() else 0,
            "book_rating": item.get("rating") or 0,
            "book_genres": ", ".join(genres_filtered) if genres_filtered else "",
            "book_tags": ", ".join(tags_filtered) if tags_filtered else "",
            # Series information for templates
            "book_series": series[0]["series"] if series else "",
            "book_series_sequence": series[0]["sequence"] if series else "",
            "book_series_info": f"{series[0]['series']} #{series[0]['sequence']}" if series else "",
            # Publishing information
            "book_published_year": release_date.split("-")[0] if release_date else "",
            "book_release_date": release_date or "",
            "book_format": format_type or "",
            "book_abridged": format_type == "abridged",
            # Technical fields
            "runtime_length_min": runtime_length_min,
            "runtime_length_hours": round(runtime_length_min / 60, 1) if runtime_length_min else 0,
            "file_size_mb": item.get("file_size_mb", 0),  # May not be available from Audnex
            "quality": item.get("quality", "Unknown"),  # May not be available from Audnex
        }

        return cleaned

    def _clean_series_sequence(self, series_name: str, sequence: str) -> str:
        """Clean series sequence to extract just the number portion."""
        if not sequence:
            return ""

        # Match any number with optional decimal (e.g, 1 or 1.5 or .5)
        match = re.search(r"\.\d+|\d+(?:\.\d+)?", sequence)
        updated_sequence = match.group(0) if match else sequence

        if sequence != updated_sequence:
            logger.debug('Series "%s" sequence cleaned from "%s" to "%s"', series_name, sequence, updated_sequence)

        return updated_sequence


async def async_main():
    """Async main function for command line usage."""
    parser = argparse.ArgumentParser(description="Audnex Metadata Fetcher")
    parser.add_argument("asin", help="ASIN to fetch metadata for")
    parser.add_argument("--region", default="us", help="Audible region (default: us)")
    parser.add_argument("--chapters", action="store_true", help="Also fetch chapter information")
    args = parser.parse_args()

    async with AudnexMetadata() as fetcher:
        # Get book metadata
        metadata = await fetcher.get_book_by_asin(args.asin, region=args.region)

        if metadata:
            print("Book metadata found:")
            print(f"  Title: {metadata.get('title')}")
            print(f"  Author: {metadata.get('author')}")
            print(f"  ASIN: {metadata.get('asin')}")
            print(f"  Publisher: {metadata.get('publisher')}")
            print(f"  Duration: {metadata.get('duration')} minutes")
            if metadata.get("series"):
                for series in metadata["series"]:
                    print(f"  Series: {series['series']} #{series['sequence']}")

            # Get chapters if requested
            if args.chapters:
                chapters = await fetcher.get_chapters_by_asin(args.asin, region=args.region)
                if chapters:
                    print(f"\nFound {len(chapters.get('chapters', []))} chapters")
        else:
            print(f"No metadata found for ASIN: {args.asin}")


def main():
    """Main entry point for command line usage."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
