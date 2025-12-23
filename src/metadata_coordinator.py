"""
Metadata Coordinator
Orchestrates the metadata fetching workflow:
1. Try to extract ASIN from MAM URL
2. Use ASIN to get metadata from Audnex
3. Fallback to Audible search if no ASIN found
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Any

import httpx


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.audible_scraper import AudibleScraper
from src.audnex_metadata import AudnexMetadata
from src.config import load_config
from src.mam_api import MAMApiAdapter  # New API-based adapter (was MAMScraper)


logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("logs/metadata_coordinator.log")],
)


class MetadataCoordinator:
    def __init__(self):
        self.config = load_config()
        self.mam_scraper = MAMApiAdapter()  # New API-based adapter
        self.audnex = AudnexMetadata()
        self.audible = AudibleScraper()

        logging.info("Metadata coordinator initialized")

    async def get_metadata_from_webhook(self, webhook_payload: dict[str, Any]) -> dict[str, Any] | None:
        """
        Main workflow: Get metadata from webhook payload.

        Args:
            webhook_payload: Dict containing 'url', 'name', etc.

        Returns:
            Dict with metadata or None if not found
        """
        url = webhook_payload.get("url")
        name = webhook_payload.get("name", "")

        logging.info(f"Starting metadata workflow for: {name}")
        logging.info(f"Source URL: {url}")

        # Step 1: Try to extract ASIN from MAM URL if it's a MAM URL
        asin = None
        if url and "myanonamouse.net" in url:
            logging.info("Step 1: Attempting to extract ASIN from MAM URL...")
            try:
                asin = await self.mam_scraper.scrape_asin_from_url(url)
                if asin:
                    logging.info(f"✅ ASIN extracted from MAM: {asin}")
                else:
                    logging.warning("❌ No ASIN found on MAM page")
            except Exception as e:
                logging.error(f"Error scraping MAM: {e}")
        else:
            logging.info("Step 1: Skipped (not a MAM URL)")

        # Step 2: If we have an ASIN, get metadata from Audnex
        if asin:
            logging.info(f"Step 2: Getting metadata from Audnex for ASIN: {asin}")
            try:
                metadata = await self.audnex.get_book_by_asin(asin)
                if metadata:
                    logging.info("✅ Metadata found via Audnex")
                    # Add source and workflow information
                    metadata["source"] = "audnex"
                    metadata["asin_source"] = "mam"
                    metadata["workflow_path"] = "mam_asin_audnex"

                    # Add webhook payload information
                    metadata.update(self._add_webhook_info(webhook_payload))

                    return metadata
                else:
                    logging.warning("❌ No metadata found in Audnex for extracted ASIN")
            except Exception as e:
                logging.error(f"Error fetching from Audnex: {e}")

        # Step 3: Fallback to Audible search using title/author from name
        logging.info("Step 3: Falling back to Audible search...")
        try:
            results = await self.audible.search_from_webhook_name(name)
            if results:
                metadata = results[0]  # Take the first (best) result
                logging.info("✅ Metadata found via Audible search")
                # Add source and workflow information
                metadata["source"] = "audible"
                metadata["asin_source"] = "search"
                metadata["workflow_path"] = "audible_search"

                # Add webhook payload information
                metadata.update(self._add_webhook_info(webhook_payload))

                return metadata
            else:
                logging.warning("❌ No metadata found via Audible search")
        except httpx.RequestError as e:
            logger.exception("Network error searching Audible")
            # Surface network errors to callers/tests as a controlled ValueError
            raise ValueError("Could not fetch metadata") from e
        except ValueError as e:
            # Malformed JSON or other parsing errors from upstream APIs should be treated
            # as controlled metadata fetch failures so callers/tests see a deterministic
            # ValueError("Could not fetch metadata").
            logger.exception("Malformed response searching Audible")
            raise ValueError("Could not fetch metadata") from e
        except Exception:
            logger.exception("Error searching Audible")

        logging.error("❌ All metadata sources exhausted - no metadata found")
        return None

    async def get_metadata_by_asin(self, asin: str, region: str = "us") -> dict[str, Any] | None:
        """Get metadata directly by ASIN."""
        logging.info(f"Getting metadata for ASIN: {asin} (region: {region})")

        try:
            metadata = await self.audnex.get_book_by_asin(asin, region=region)
            if metadata:
                logging.info("✅ Metadata found via Audnex")
                metadata["source"] = "audnex"
                metadata["asin_source"] = "direct"
                return metadata
        except Exception as e:
            logging.error(f"Error fetching from Audnex: {e}")

        logging.error("❌ No metadata found for ASIN")
        return None

    async def search_metadata(self, title: str, author: str = "", region: str = "us") -> dict[str, Any] | None:
        """Search for metadata by title and author."""
        logging.info(f"Searching metadata: title='{title}', author='{author}', region={region}")

        try:
            results = await self.audible.search(title=title, author=author, region=region)
            if results:
                metadata = results[0]  # Take the first (best) result
                logging.info("✅ Metadata found via search")
                metadata["source"] = "audible"
                metadata["asin_source"] = "search"
                return metadata
        except Exception as e:
            logging.error(f"Error searching: {e}")

        logging.error("❌ No metadata found via search")
        return None

    async def get_enhanced_metadata(self, basic_metadata: dict[str, Any]) -> dict[str, Any]:
        """Enhance basic metadata with additional information."""
        enhanced = basic_metadata.copy()

        # Try to get chapters if we have an ASIN
        asin = enhanced.get("asin")
        if asin:
            try:
                # Use the same region that worked for book metadata to avoid redundant API calls
                region = enhanced.get("audnex_region", "us")
                chapters = await self.audnex.get_chapters_by_asin(asin, region=region)
                if chapters:
                    enhanced["chapters"] = chapters
                    enhanced["chapter_count"] = len(chapters.get("chapters", []))
                    logging.info(f"Added {enhanced.get('chapter_count', 0)} chapters to metadata")
            except Exception as e:
                logging.error(f"Error fetching chapters: {e}")

        # Add workflow information
        enhanced["metadata_workflow"] = {
            "coordinator_version": "1.0",
            "sources_tried": ["mam", "audnex", "audible"],
            "final_source": enhanced.get("source", "unknown"),
            "asin_source": enhanced.get("asin_source", "unknown"),
        }

        return enhanced

    def _add_webhook_info(self, webhook_payload: dict[str, Any]) -> dict[str, Any]:
        """Add webhook payload information to metadata for notifications and templates."""
        webhook_info = {
            # Webhook source information
            "webhook_name": webhook_payload.get("name", ""),
            "webhook_url": webhook_payload.get("url", ""),
            "webhook_download_url": webhook_payload.get("download_url", ""),
            "webhook_indexer": webhook_payload.get("indexer", ""),
            "webhook_category": webhook_payload.get("category", ""),
            "webhook_size": webhook_payload.get("size", 0),
            "webhook_size_mb": round(int(webhook_payload.get("size", 0)) / (1024 * 1024), 1)
            if webhook_payload.get("size")
            else 0,
            "webhook_seeders": webhook_payload.get("seeders", 0),
            "webhook_leechers": webhook_payload.get("leechers", 0),
            # Torrent information for notifications
            "torrent_name": webhook_payload.get("name", ""),
            "torrent_url": webhook_payload.get("url", ""),
            "torrent_category": webhook_payload.get("category", ""),
            "torrent_size": webhook_payload.get("size", 0),
            "torrent_indexer": webhook_payload.get("indexer", ""),
            # Additional fields that might be in webhook
            "quality": webhook_payload.get("quality", ""),
            "format": webhook_payload.get("format", ""),
            "language": webhook_payload.get("language", ""),
            "uploader": webhook_payload.get("uploader", ""),
            "upload_date": webhook_payload.get("upload_date", ""),
            "freeleech": webhook_payload.get("freeleech", False),
            # Processing metadata
            "processing_time": time.time(),
            "processing_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        return webhook_info


def main():
    """Main function for command line usage."""
    parser = argparse.ArgumentParser(description="Metadata Coordinator")
    parser.add_argument("--url", help="MAM URL to process")
    parser.add_argument("--name", help="Torrent name to parse")
    parser.add_argument("--asin", help="Direct ASIN lookup")
    parser.add_argument("--title", help="Title to search for")

    async def async_main():
        parser.add_argument("--author", default="", help="Author to search for")
        parser.add_argument("--region", default="us", help="Audible region")
        parser.add_argument("--enhanced", action="store_true", help="Get enhanced metadata with chapters")
        args = parser.parse_args()

        coordinator = MetadataCoordinator()
        metadata = None

        # Determine which method to use
        if args.url or args.name:
            # Webhook-style payload
            payload = {}
            if args.url:
                payload["url"] = args.url
            if args.name:
                payload["name"] = args.name

            metadata = await coordinator.get_metadata_from_webhook(payload)

        elif args.asin:
            # Direct ASIN lookup
            metadata = await coordinator.get_metadata_by_asin(args.asin, region=args.region)

        elif args.title:
            # Title/author search
            metadata = await coordinator.search_metadata(args.title, author=args.author, region=args.region)

        else:
            print("Error: Must provide --url/--name, --asin, or --title")
            return

        # Display results
        if metadata:
            if args.enhanced:
                metadata = await coordinator.get_enhanced_metadata(metadata)

            print("✅ Metadata found:")
            print(f"  Title: {metadata.get('title')}")
            print(f"  Author: {metadata.get('author')}")
            print(f"  ASIN: {metadata.get('asin')}")
            print(f"  Publisher: {metadata.get('publisher')}")
            print(f"  Duration: {metadata.get('duration')} minutes ({metadata.get('duration', 0) / 60:.1f} hours)")
            print(f"  Published: {metadata.get('publishedYear')}")

            if metadata.get("series"):
                for series in metadata["series"]:
                    if isinstance(series, dict):
                        title = series.get("title", "")
                        sequence = series.get("sequence", "")
                        print(f"  Series: {title} #{sequence}")
                    else:
                        print(f"  Series: {series}")

            if metadata.get("chapters"):
                print(f"  Chapters: {metadata.get('chapter_count', 0)}")

            print(f"  Source: {metadata.get('source')} (ASIN from: {metadata.get('asin_source')})")

            if metadata.get("description"):
                desc = metadata["description"][:200]
                print(f"  Description: {desc}...")

        else:
            print("❌ No metadata found")

    asyncio.run(async_main())


if __name__ == "__main__":
    main()
