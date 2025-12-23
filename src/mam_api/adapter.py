#!/usr/bin/env python3
"""
MAM API Adapter

Provides backward-compatible interface for existing code that used MAMScraper.
This adapter uses the new MAM JSON API instead of Playwright HTML scraping.

Usage:
    # Drop-in replacement for MAMScraper
    from src.mam_api.adapter import MAMApiAdapter
    
    adapter = MAMApiAdapter()
    asin = await adapter.scrape_asin_from_url(url)
"""

import asyncio
import logging
import os
import re
import time
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs

import httpx
from pydantic import ValidationError

from .client import MamAsyncClient, MamApiError
from .models import MamTorrentRaw

logger = logging.getLogger(__name__)


class MAMApiAdapter:
    """
    Backward-compatible adapter that provides the same interface as MAMScraper
    but uses the MAM JSON API instead of Playwright.
    
    Key differences from MAMScraper:
    - No browser automation (faster, lighter)
    - Uses mam_id from environment instead of mam_config.json
    - Gets more data than just ASIN (author, narrator, series, etc.)
    """
    
    # Rate limiting
    _last_api_call_time = 0
    _rate_limit_seconds = 2.0  # Default 2 seconds between calls
    
    def __init__(self, mam_id: Optional[str] = None, rate_limit_seconds: float = 2.0) -> None:
        """
        Initialize the adapter.
        
        Args:
            mam_id: MAM session cookie value. If not provided, reads from MAM_ID env var.
            rate_limit_seconds: Minimum seconds between API calls (default: 2.0)
        """
        self.mam_id = mam_id or os.getenv("MAM_ID")
        if not self.mam_id:
            logger.warning(
                "MAM_ID not provided. Set MAM_ID environment variable or pass mam_id to constructor."
            )
        
        MAMApiAdapter._rate_limit_seconds = rate_limit_seconds
        self._client: Optional[MamAsyncClient] = None
        
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
            await self._client.close()
            self._client = None
            
    async def _check_rate_limit(self) -> None:
        """Enforce rate limiting between API calls."""
        current_time = time.time()
        time_since_last = current_time - MAMApiAdapter._last_api_call_time
        
        if time_since_last < MAMApiAdapter._rate_limit_seconds:
            wait_time = MAMApiAdapter._rate_limit_seconds - time_since_last
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            
        MAMApiAdapter._last_api_call_time = time.time()
        
    @staticmethod
    def extract_tid_from_url(url: str) -> Optional[int]:
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
        match = re.search(r'/t/(\d+)', url)
        if match:
            return int(match.group(1))
            
        # Pattern 2: /tor/viewRequest.php/12345.xxx
        match = re.search(r'/tor/viewRequest\.php/(\d+)', url)
        if match:
            return int(match.group(1))
            
        # Pattern 3: /torrents.php?id=12345
        parsed = urlparse(url)
        if 'torrents.php' in parsed.path:
            qs = parse_qs(parsed.query)
            if 'id' in qs:
                try:
                    return int(qs['id'][0])
                except (ValueError, IndexError):
                    pass
                    
        logger.warning(f"Could not extract torrent ID from URL: {url}")
        return None
        
    async def get_torrent_data(self, url: str) -> Optional[MamTorrentRaw]:
        """
        Get full torrent data from MAM API.
        
        Args:
            url: MAM torrent URL
            
        Returns:
            MamTorrentRaw object with all torrent metadata, or None if not found
        """
        tid = self.extract_tid_from_url(url)
        if not tid:
            logger.error(f"Could not extract torrent ID from URL: {url}")
            return None
            
        logger.info(f"Fetching torrent data for tid={tid}")
        
        try:
            await self._check_rate_limit()
            client = await self._get_client()
            torrent = await client.get_torrent(tid)
            
            if torrent:
                logger.info(f"✅ Torrent data retrieved: {torrent.title}")
                return torrent
            else:
                logger.warning(f"No torrent found for tid={tid}")
                return None
                
        except MamApiError:
            logger.exception("MAM API error for tid=%s", tid)
            return None
        except httpx.HTTPError:
            logger.exception("HTTP error fetching torrent tid=%s", tid)
            return None
        except ValidationError:
            logger.exception("Validation error parsing torrent tid=%s", tid)
            return None
            
    async def scrape_asin_from_url(self, url: str, force_login: bool = False) -> Optional[str]:
        """
        Get ASIN from MAM URL using the JSON API.
        
        This method provides backward compatibility with MAMScraper.scrape_asin_from_url().
        The force_login parameter is ignored since we use cookie-based auth.
        
        Args:
            url: MAM torrent URL
            force_login: Ignored (kept for backward compatibility)
            
        Returns:
            ASIN string if found, None otherwise
        """
        if force_login:
            logger.debug("force_login parameter ignored - using cookie-based auth")
            
        torrent = await self.get_torrent_data(url)
        if not torrent:
            return None
            
        # Extract ASIN from torrent data
        asin = torrent.asin
        
        if asin:
            logger.info(f"✅ ASIN found via API: {asin}")
            return asin
        else:
            logger.warning("No ASIN found in torrent metadata")
            return None
            
    async def get_full_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get full metadata from MAM URL.
        
        This is an enhanced method that returns more data than scrape_asin_from_url().
        
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
            # series_info is {id: [name, "position", position_float]}
            for _, entry in torrent.series_info.items():
                if len(entry) >= 2:
                    series_position = str(entry[1])
                    break
        
        return {
            'asin': normalized.asin,
            'title': normalized.title,
            'authors': torrent.author_names,  # List from raw
            'narrators': torrent.narrator_names,  # List from raw
            'series': normalized.series,
            'series_position': series_position,
            'description': torrent.description,
            'duration': normalized.duration,
            'language': torrent.lang_code,
            'mam_id': normalized.tid,
            'source': 'mam_api',
        }


# For backward compatibility, also expose as MAMScraper alias
# This allows gradual migration without changing all imports at once
MAMScraper = MAMApiAdapter
