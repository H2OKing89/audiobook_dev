"""MAM API adapter for torrent metadata lookups."""

import asyncio
import os
import re
import time
from typing import Any
from urllib.parse import parse_qs, urlparse, urlunparse

import httpx
from pydantic import ValidationError

from src.logging_setup import get_logger

from .client import MAM_AUTH_ERROR_MESSAGE, MamApiError, MamAsyncClient
from .models import MamTorrentRaw


log = get_logger(__name__)


def _sanitize_url_for_log(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _is_mam_auth_error(exc: MamApiError) -> bool:
    message = str(exc)
    return MAM_AUTH_ERROR_MESSAGE in message or "MAM_ID not configured" in message


class MAMApiAdapter:
    """
    Adapter that retrieves MAM metadata through the JSON API.

    Auth uses the MAM_ID environment variable, which should contain the
    mam_id session cookie value.
    """

    def __init__(self, mam_id: str | None = None, rate_limit_seconds: float = 2.0) -> None:
        """
        Initialize the adapter.

        Args:
            mam_id: MAM session cookie value. If not provided, reads from MAM_ID env var.
            rate_limit_seconds: Minimum seconds between API calls (default: 2.0)
        """
        self.mam_id = mam_id or os.getenv("MAM_ID")
        if not self.mam_id:
            log.warning("mam.adapter.no_mam_id")

        # Instance-level rate limiting to avoid shared state across instances
        self._last_api_call_time: float = 0
        self._rate_limit_seconds: float = rate_limit_seconds
        self._client: MamAsyncClient | None = None

    async def _get_client(self) -> MamAsyncClient:
        """Get or create the async client."""
        if self._client is None:
            if not self.mam_id:
                raise MamApiError("MAM_ID not configured - cannot create client")
            self._client = MamAsyncClient(mam_id=self.mam_id)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "MAMApiAdapter":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _check_rate_limit(self) -> None:
        """Enforce rate limiting between API calls."""
        current_time = time.time()
        time_since_last = current_time - self._last_api_call_time

        if time_since_last < self._rate_limit_seconds:
            wait_time = self._rate_limit_seconds - time_since_last
            log.debug("mam.adapter.rate_limit", wait_time=wait_time)
            await asyncio.sleep(wait_time)

        self._last_api_call_time = time.time()

    @staticmethod
    def extract_tid_from_url(url: str | None) -> int | None:
        """
        Extract torrent ID (tid) from MAM URL.

        Supported URL formats:
            - https://www.myanonamouse.net/t/12345
            - https://www.myanonamouse.net/tor/viewRequest.php/12345.xxx
            - https://www.myanonamouse.net/torrents.php?id=12345

        Args:
            url: MAM URL

        Returns:
            Torrent ID as integer, or None if not found
        """
        if not url:
            return None

        # Pattern 1: /t/12345
        match = re.search(r"/t/(\d+)", url)
        if match:
            return int(match.group(1))

        # Pattern 2: /tor/viewRequest.php/12345.xxx
        match = re.search(r"/tor/viewRequest\.php/(\d+)", url)
        if match:
            return int(match.group(1))

        # Pattern 3: /torrents.php?id=12345
        parsed = urlparse(url)
        if "torrents.php" in parsed.path:
            qs = parse_qs(parsed.query)
            if "id" in qs:
                try:
                    return int(qs["id"][0])
                except (ValueError, IndexError):
                    pass

        safe_url = _sanitize_url_for_log(url)
        log.warning("mam.adapter.tid_extract_failed", url=safe_url)
        return None

    async def get_torrent_data(self, url: str) -> MamTorrentRaw | None:
        """
        Get full torrent data from MAM API.

        Args:
            url: MAM torrent URL

        Returns:
            MamTorrentRaw object with all torrent metadata, or None if not found
        """
        tid = self.extract_tid_from_url(url)
        if not tid:
            log.error("mam.adapter.no_tid", url=url)
            return None

        log.info("mam.adapter.fetch_torrent", tid=tid)

        try:
            await self._check_rate_limit()
            client = await self._get_client()
            torrent = await client.get_torrent(tid)

            if torrent:
                log.info("mam.adapter.torrent_found", title=torrent.title)
                return torrent
            else:
                log.warning("mam.adapter.torrent_not_found", tid=tid)
                return None

        except MamApiError as exc:
            if _is_mam_auth_error(exc):
                log.exception("mam.adapter.auth_error", tid=tid)
                raise

            log.exception("mam.adapter.api_error", tid=tid)
            return None
        except httpx.HTTPError:
            log.exception("mam.adapter.http_error", tid=tid)
            return None
        except ValidationError:
            log.exception("mam.adapter.validation_error", tid=tid)
            return None

    async def get_asin_from_url(self, url: str) -> str | None:
        """
        Get ASIN from MAM URL using the JSON API.

        Args:
            url: MAM torrent URL

        Returns:
            ASIN string if found, None otherwise
        """
        torrent = await self.get_torrent_data(url)
        if not torrent:
            return None

        # Extract ASIN from torrent data
        asin = torrent.asin

        if asin:
            log.info("mam.adapter.asin_found", asin=asin)
            return asin
        else:
            log.warning("mam.adapter.no_asin", reason="torrent_missing_asin_field")
            return None

    async def get_full_metadata(self, url: str) -> dict[str, Any] | None:
        """
        Get full metadata from MAM URL.

        This is an enhanced method that returns more data than get_asin_from_url().

        Args:
            url: MAM torrent URL

        Returns:
            Dict with metadata including:
                - asin: ASIN if available
                - title: Torrent title
                - authors: List of author names
                - narrators: List of narrator names
                - series: Series name if available
                - series_position: Position in series
                - description: Book description
                - duration: Audio duration in seconds
                - language: Language code
                - mam_id: MAM torrent ID
        """
        torrent = await self.get_torrent_data(url)
        if not torrent:
            return None

        # Use raw torrent for author/narrator lists, normalized for other fields
        normalized = torrent.to_normalized()

        # Extract series position from raw series_info if available
        series_position = None
        if torrent.series_info:
            for _, entry in torrent.series_info.items():
                if len(entry) >= 2:
                    series_position = str(entry[1])
                    break

        return {
            "asin": normalized.asin,
            "title": normalized.title,
            "authors": torrent.author_names,  # List from raw
            "narrators": torrent.narrator_names,  # List from raw
            "series": normalized.series,
            "series_position": series_position,
            "description": torrent.description,
            "duration": normalized.duration,
            "language": torrent.lang_code,
            "mam_id": normalized.tid,
            "source": "mam_api",
        }
