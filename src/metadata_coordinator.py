"""
Metadata Coordinator
Orchestrates the metadata fetching workflow:
1. Try to extract ASIN from MAM URL
2. Use ASIN to get metadata from Audnex
3. Fallback to Audible search if no ASIN found
"""

import argparse
import asyncio
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
from src.logging_setup import get_logger
from src.mam_api import MAMApiAdapter  # New API-based adapter (was MAMScraper)


log = get_logger(__name__)


class MetadataCoordinator:
    def __init__(self):
        self.config = load_config()
        self.mam_scraper = MAMApiAdapter()  # New API-based adapter
        self.audnex = AudnexMetadata()
        self.audible = AudibleScraper()

        # Store audnex config options for method calls
        audnex_config = self.config.get("metadata", {}).get("audnex", {})
        self.seed_authors = audnex_config.get("seed_authors", False)
        self.force_update = audnex_config.get("force_update", False)

        log.info("coordinator.init", seed_authors=self.seed_authors, force_update=self.force_update)

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

        log.info("coordinator.workflow.start", name=name, url=url)

        # Step 1: Try to extract ASIN from MAM URL if it's a MAM URL
        asin = None
        if url and "myanonamouse.net" in url:
            log.info("coordinator.step1.mam_extract")
            try:
                asin = await self.mam_scraper.scrape_asin_from_url(url)
                if asin:
                    log.info("coordinator.step1.asin_found", asin=asin)
                else:
                    log.warning("coordinator.step1.no_asin", reason="mam_torrent_has_no_asin")
            except httpx.RequestError:
                log.exception("coordinator.step1.network_error")
            except ValueError:
                log.exception("coordinator.step1.malformed_response")
            except Exception:
                log.exception("coordinator.step1.unexpected_error")
        else:
            log.info("coordinator.step1.skipped")

        # Step 2: If we have an ASIN, get metadata from Audnex
        if asin:
            log.info("coordinator.step2.audnex_fetch", asin=asin, seed_authors=self.seed_authors)
            try:
                metadata = await self.audnex.get_book_by_asin(
                    asin,
                    seed_authors=self.seed_authors,
                    update=self.force_update,
                )
                if metadata:
                    log.info("coordinator.step2.metadata_found")
                    # Add source and workflow information
                    metadata["source"] = "audnex"
                    metadata["asin_source"] = "mam"
                    metadata["workflow_path"] = "mam_asin_audnex"

                    # Add webhook payload information
                    metadata.update(self._add_webhook_info(webhook_payload))

                    return metadata
                else:
                    log.warning("coordinator.step2.no_metadata")
            except httpx.RequestError:
                log.exception("coordinator.step2.network_error")
            except ValueError:
                log.exception("coordinator.step2.malformed_response")
            except Exception:
                log.exception("coordinator.step2.unexpected_error")

        # Step 3: Fallback to Audible search using title/author from name
        log.info("coordinator.step3.audible_search")
        try:
            results = await self.audible.search_from_webhook_name(name)
            if results:
                metadata = results[0]  # Take the first (best) result
                log.info("coordinator.step3.metadata_found")
                # Add source and workflow information
                metadata["source"] = "audible"
                metadata["asin_source"] = "search"
                metadata["workflow_path"] = "audible_search"

                # Add webhook payload information
                metadata.update(self._add_webhook_info(webhook_payload))

                return metadata
            else:
                log.warning("coordinator.step3.no_metadata")
        except httpx.RequestError as e:
            log.exception("coordinator.step3.network_error")
            # Surface network errors to callers/tests as a controlled ValueError
            raise ValueError("Could not fetch metadata") from e
        except ValueError as e:
            # Malformed JSON or other parsing errors from upstream APIs should be treated
            # as controlled metadata fetch failures so callers/tests see a deterministic
            # ValueError("Could not fetch metadata").
            log.exception("coordinator.step3.malformed_response")
            raise ValueError("Could not fetch metadata") from e
        except Exception:
            log.exception("coordinator.step3.unexpected_error")

        log.error("coordinator.workflow.exhausted")
        return None

    async def get_metadata_by_asin(
        self,
        asin: str,
        region: str = "us",
        *,
        seed_authors: bool | None = None,
        update: bool | None = None,
    ) -> dict[str, Any] | None:
        """Get metadata directly by ASIN.

        Args:
            asin: Amazon Standard Identification Number
            region: Audible region (default: "us")
            seed_authors: Whether to seed author information (default: from config)
            update: Force server to check for updated data (default: from config)

        Returns:
            Metadata dict or None if not found
        """
        # Use config defaults if not explicitly provided
        use_seed_authors = seed_authors if seed_authors is not None else self.seed_authors
        use_update = update if update is not None else self.force_update

        log.info("coordinator.asin_lookup", asin=asin, region=region, seed_authors=use_seed_authors, update=use_update)

        try:
            metadata = await self.audnex.get_book_by_asin(
                asin,
                region=region,
                seed_authors=use_seed_authors,
                update=use_update,
            )
            if metadata:
                log.info("coordinator.asin_lookup.found")
                metadata["source"] = "audnex"
                metadata["asin_source"] = "direct"
                return metadata
        except httpx.RequestError:
            log.exception("coordinator.asin_lookup.network_error")
        except ValueError:
            log.exception("coordinator.asin_lookup.malformed_response")
        except Exception:
            log.exception("coordinator.asin_lookup.unexpected_error")

        log.error("coordinator.asin_lookup.not_found")
        return None

    async def search_metadata(self, title: str, author: str = "", region: str = "us") -> dict[str, Any] | None:
        """Search for metadata by title and author."""
        log.info("coordinator.search", title=title, author=author, region=region)

        try:
            results = await self.audible.search(title=title, author=author, region=region)
            if results:
                metadata = results[0]  # Take the first (best) result
                log.info("coordinator.search.found")
                metadata["source"] = "audible"
                metadata["asin_source"] = "search"
                return metadata
        except httpx.RequestError:
            log.exception("coordinator.search.network_error")
        except ValueError:
            log.exception("coordinator.search.malformed_response")
        except Exception:
            log.exception("coordinator.search.unexpected_error")

        log.error("coordinator.search.not_found")
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
                chapters = await self.audnex.get_chapters_by_asin(
                    asin,
                    region=region,
                    update=self.force_update,
                )
                if chapters:
                    enhanced["chapters"] = chapters
                    enhanced["chapter_count"] = len(chapters.get("chapters", []))
                    log.info("coordinator.enhanced.chapters_added", count=enhanced.get("chapter_count", 0))
            except asyncio.CancelledError:
                # Re-raise cancellation to properly propagate task cancellation
                raise
            except httpx.RequestError:
                log.exception("coordinator.enhanced.network_error")
            except ValueError:
                log.exception("coordinator.enhanced.malformed_response")
            except Exception:
                log.exception("coordinator.enhanced.unexpected_error")

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
