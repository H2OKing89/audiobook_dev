"""
Audnex API metadata fetcher
Gets audiobook metadata from api.audnex.us using ASIN
"""

import argparse
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import load_config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("logs/audnex_metadata.log")],
)


class AudnexMetadata:
    def __init__(self) -> None:
        self.config: dict = load_config()
        self.audnex_config: dict = self.config.get("metadata", {}).get("audnex", {})
        self.base_url: str = self.audnex_config.get("base_url", "https://api.audnex.us")
        self.rate_limit: float = self.audnex_config.get("rate_limit_seconds", 0.15)
        self.global_rate_limit: float = self.config.get("metadata", {}).get("rate_limit_seconds", 120)
        self.last_request_time: float = 0.0
        self.last_global_request_time: float = 0.0
        # Multi-region support
        self.regions: list[str] = self.audnex_config.get(
            "regions", ["us", "uk", "ca", "au", "de", "fr", "es", "it", "jp", "in"]
        )
        self.try_all_regions: bool = self.audnex_config.get("try_all_regions_on_error", True)
        self.max_regions: int = self.audnex_config.get("max_regions_to_try", 5)

    def _throttle_request(self) -> None:
        """Apply rate limiting between requests."""
        current_time = time.time()

        # Local rate limiting (150ms between requests)
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit:
            time.sleep(self.rate_limit - time_since_last)

        self.last_request_time = time.time()

    def _check_global_rate_limit(self):
        """Check if we need to wait for global rate limit (2 minutes)."""
        current_time = time.time()
        time_since_last_global = current_time - self.last_global_request_time

        if time_since_last_global < self.global_rate_limit:
            wait_time = self.global_rate_limit - time_since_last_global
            logging.info(f"Global rate limit: waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)

        self.last_global_request_time = time.time()

    def _make_request(self, url: str, max_retries: int = 3) -> dict[str, Any] | None:
        """Make a request to the Audnex API with rate limiting and retry logic."""
        self._throttle_request()
        self._check_global_rate_limit()

        for attempt in range(max_retries):
            try:
                logging.debug(f"Making request to: {url}")
                response = httpx.get(url, timeout=30)
                response.raise_for_status()

                data: dict[str, Any] = response.json()
                logging.debug(f"Response received, status: {response.status_code}")
                return data

            except httpx.HTTPStatusError as e:
                if e.response is not None and e.response.status_code == 429:  # Rate limited
                    retry_after_header = e.response.headers.get("retry-after", "5")
                    try:
                        retry_after = int(retry_after_header)
                    except ValueError:
                        logging.warning(f"Invalid retry-after header: {retry_after_header}, using default 5s")
                        retry_after = 5
                    logging.warning(f"Rate limit exceeded. Retrying in {retry_after} seconds.")
                    time.sleep(retry_after)
                    continue
                elif e.response is not None and e.response.status_code == 500:
                    # For 500 errors, don't retry - likely the data doesn't exist in this region
                    logging.error(f"HTTP error: {e}")
                    return None
                else:
                    logging.error(f"HTTP error: {e}")
                    if attempt == max_retries - 1:
                        return None
                    time.sleep(2**attempt)  # Exponential backoff

            except httpx.RequestError as e:
                logging.error(f"Request error: {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(2**attempt)  # Exponential backoff

        return None

    def get_book_by_asin(self, asin: str, region: str = "us") -> dict[str, Any] | None:
        """Get book metadata by ASIN with multi-region fallback."""
        if not asin or len(asin) != 10:
            logging.error(f"Invalid ASIN format: {asin}")
            return None

        asin = asin.upper()

        # If try_all_regions is enabled and we get an error, try other regions
        regions_to_try = [region]  # Start with requested region
        if self.try_all_regions:
            # Add additional regions based on max_regions config
            other_regions = [r for r in self.regions if r != region]
            regions_to_try.extend(other_regions[: self.max_regions - 1])

        for try_region in regions_to_try:
            params = {"region": try_region} if try_region else {}
            url = f"{self.base_url}/books/{asin}"

            if params:
                url += f"?{urlencode(params)}"

            logging.info(f"Fetching book metadata for ASIN: {asin} (region: {try_region})")

            # Use single retry when trying multiple regions to avoid excessive delays
            max_retries = 1 if len(regions_to_try) > 1 else 3
            result = self._make_request(url, max_retries=max_retries)

            if result and result.get("asin"):
                logging.info(f"✅ Book metadata found for ASIN: {asin} in region: {try_region}")
                metadata = self._clean_book_metadata(result)
                metadata["audnex_region"] = try_region  # Track which region worked
                return metadata
            elif result is None and try_region != regions_to_try[-1]:
                # Only log as warning if we're trying another region
                logging.warning(f"⚠️  No metadata for ASIN {asin} in region {try_region}, trying next region...")
            else:
                logging.warning(f"❌ No metadata found for ASIN: {asin} in region: {try_region}")

        logging.error(f"❌ No metadata found for ASIN {asin} in any region")
        return None

    def get_chapters_by_asin(self, asin: str, region: str = "us") -> dict[str, Any] | None:
        """Get chapter information by ASIN with multi-region fallback."""
        if not asin or len(asin) != 10:
            logging.error(f"Invalid ASIN format: {asin}")
            return None

        asin = asin.upper()

        # If try_all_regions is enabled and we get an error, try other regions
        regions_to_try = [region]  # Start with requested region
        if self.try_all_regions:
            # Add additional regions based on max_regions config
            other_regions = [r for r in self.regions if r != region]
            regions_to_try.extend(other_regions[: self.max_regions - 1])

        for try_region in regions_to_try:
            params = {"region": try_region} if try_region else {}
            url = f"{self.base_url}/books/{asin}/chapters"

            if params:
                url += f"?{urlencode(params)}"

            logging.info(f"Fetching chapters for ASIN: {asin} (region: {try_region})")

            # Use single retry when trying multiple regions to avoid excessive delays
            max_retries = 1 if len(regions_to_try) > 1 else 3
            result = self._make_request(url, max_retries=max_retries)

            if result:
                logging.info(f"✅ Chapters found for ASIN: {asin} in region: {try_region}")
                if isinstance(result, dict):
                    result["audnex_region"] = try_region  # Track which region worked
                return result
            elif result is None and try_region != regions_to_try[-1]:
                logging.warning(f"⚠️  No chapters for ASIN {asin} in region {try_region}, trying next region...")
            else:
                logging.warning(f"❌ No chapters found for ASIN: {asin} in region: {try_region}")

        logging.error(f"❌ No chapters found for ASIN {asin} in any region")
        return None

    def search_author_by_name(self, name: str, region: str = "us") -> list[dict[str, Any]]:
        """Search for authors by name."""
        params = {"name": name}
        if region:
            params["region"] = region

        url = f"{self.base_url}/authors?{urlencode(params)}"

        logging.info(f"Searching for author: {name} (region: {region})")

        result = self._make_request(url)

        if result:
            if isinstance(result, list):
                logging.info(f"✅ Found {len(result)} author results for: {name}")
                return result
            else:
                logging.info(f"✅ Found 1 author result for: {name}")
                return [result]
        else:
            logging.warning(f"❌ No authors found for: {name}")
            return []

    def get_author_by_asin(self, asin: str, region: str = "us") -> dict[str, Any] | None:
        """Get author information by ASIN."""
        if not asin or len(asin) != 10:
            logging.error(f"Invalid ASIN format: {asin}")
            return None

        asin = asin.upper()
        params = {"region": region} if region else {}
        url = f"{self.base_url}/authors/{asin}"

        if params:
            url += f"?{urlencode(params)}"

        logging.info(f"Fetching author for ASIN: {asin} (region: {region})")

        result = self._make_request(url)

        if result and result.get("asin"):
            logging.info(f"✅ Author found for ASIN: {asin}")
            return result
        else:
            logging.warning(f"❌ No author found for ASIN: {asin}")
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
            logging.debug(f'Series "{series_name}" sequence cleaned from "{sequence}" to "{updated_sequence}"')

        return updated_sequence


def main():
    """Main function for command line usage."""
    parser = argparse.ArgumentParser(description="Audnex Metadata Fetcher")
    parser.add_argument("asin", help="ASIN to fetch metadata for")
    parser.add_argument("--region", default="us", help="Audible region (default: us)")
    parser.add_argument("--chapters", action="store_true", help="Also fetch chapter information")
    args = parser.parse_args()

    fetcher = AudnexMetadata()

    # Get book metadata
    metadata = fetcher.get_book_by_asin(args.asin, region=args.region)

    if metadata:
        print("✅ Book metadata found:")
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
            chapters = fetcher.get_chapters_by_asin(args.asin, region=args.region)
            if chapters:
                print(f"\n✅ Found {len(chapters.get('chapters', []))} chapters")
    else:
        print(f"❌ No metadata found for ASIN: {args.asin}")


if __name__ == "__main__":
    main()
