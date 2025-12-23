"""
MAM (MyAnonamouse) API client using httpx with HTTP/2 support.

This module provides:
- MamClient: Synchronous client for MAM JSON API
- MamAsyncClient: Asynchronous client for concurrent operations
- Helper functions for extracting torrent IDs from IRC announcements

SECURITY: Never log the mam_id cookie value - it's a session token!
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

import httpx

from src.mam_api.models import MamSearchResponseRaw, MamTorrentRaw

logger = logging.getLogger(__name__)

MAM_BASE_URL = "https://www.myanonamouse.net"
MAM_SEARCH_PATH = "/tor/js/loadSearchJSONbasic.php"
MAM_DOWNLOAD_PATH = "/tor/download.php"

# Regex to extract tid from MAM URLs like /t/1207719
_TID_RE = re.compile(r"(?:https?://www\.myanonamouse\.net)?/t/(\d+)")


def extract_tid_from_irc(line: str) -> Optional[int]:
    """
    Extract torrent ID from IRC announcement line.
    
    IRC announces include links like:
        Link: ( https://www.myanonamouse.net/t/1207719 )
    
    Returns the numeric tid, or None if not found.
    """
    m = _TID_RE.search(line)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


class MamApiError(RuntimeError):
    """Error from MAM API operations."""


class MamClient:
    """
    Synchronous MAM API client using httpx with HTTP/2.
    
    Auth is via the mam_id session cookie.
    
    Example:
        with MamClient(mam_id="your_cookie_value") as mam:
            torrent = mam.get_torrent(1207719)
            print(torrent.title)
    """

    def __init__(
        self,
        mam_id: str,
        *,
        base_url: str = MAM_BASE_URL,
        timeout: float = 30.0,
        http2: bool = True,
        user_agent: str = "AudiobookDev/1.0 (+https://github.com/H2OKing89/audiobook_dev)",
    ) -> None:
        if not mam_id:
            raise ValueError("mam_id cookie is required for MAM API access")
        
        self._client = httpx.Client(
            base_url=base_url,
            http2=http2,
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": user_agent},
            cookies={"mam_id": mam_id},
            follow_redirects=True,
        )
        # Log initialization without exposing cookie value
        logger.debug("Initialized MAM client with base_url=%s, http2=%s", base_url, http2)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "MamClient":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def search(
        self,
        *,
        tor: Dict[str, Any],
        perpage: int = 100,
        media_info: bool = True,
        isbn: bool = True,
        description: bool = False,
        dl_link: bool = False,
        thumbnail: Optional[bool] = None,
    ) -> MamSearchResponseRaw:
        """
        Search MAM torrents via JSON API.
        
        Args:
            tor: Search parameters dict (id, text, searchIn, searchType, etc.)
            perpage: Results per page (5-1000)
            media_info: Include mediainfo in response
            isbn: Include ISBN/ASIN in response
            description: Include full HTML description (large!)
            dl_link: Include download token in response
            thumbnail: Include thumbnail URL
            
        Returns:
            MamSearchResponseRaw with matched torrents
        """
        if perpage < 5 or perpage > 1000:
            raise ValueError("perpage must be between 5 and 1000")

        payload: Dict[str, Any] = {"tor": tor}

        # MAM treats presence of these keys as "enabled"
        if media_info:
            payload["mediaInfo"] = ""
        if isbn:
            payload["isbn"] = ""
        if description:
            payload["description"] = ""
        if dl_link:
            payload["dlLink"] = ""
        if thumbnail is not None:
            payload["thumbnail"] = "true" if thumbnail else "false"

        payload["perpage"] = perpage

        logger.debug("MAM search request: tor=%s, flags=%s", 
                    {k: v for k, v in tor.items() if k != "id"}, 
                    [k for k in payload if k not in ("tor", "perpage")])

        r = self._client.post(
            MAM_SEARCH_PATH, 
            json=payload, 
            params={"perpage": str(perpage)}
        )
        r.raise_for_status()

        data = r.json()
        response = MamSearchResponseRaw.model_validate(data)
        
        logger.debug("MAM search returned %d results (found=%d)", len(response.data), response.found)
        return response

    def get_torrent(
        self,
        tid: int,
        *,
        media_info: bool = True,
        isbn: bool = True,
        description: bool = False,
        dl_link: bool = False,
    ) -> MamTorrentRaw:
        """
        Fetch a single torrent by ID.
        
        IMPORTANT: tid must be inside tor[id], not as top-level query param.
        
        Args:
            tid: Torrent ID from MAM
            media_info: Include mediainfo
            isbn: Include ISBN/ASIN
            description: Include HTML description
            dl_link: Include download token
            
        Returns:
            MamTorrentRaw for the requested torrent
            
        Raises:
            MamApiError: If torrent not found
        """
        tor = {
            "id": tid,
            "searchIn": "torrents",
            "searchType": "all",
            "sortType": "default",
            "startNumber": "0",
            "cat": ["0"],
            "browse_lang": ["0"],
        }
        
        logger.info("Fetching MAM torrent tid=%d", tid)
        
        resp = self.search(
            tor=tor,
            perpage=5,
            media_info=media_info,
            isbn=isbn,
            description=description,
            dl_link=dl_link,
        )
        
        if not resp.data:
            logger.warning("MAM torrent not found: tid=%d", tid)
            raise MamApiError(f"Torrent not found for tid={tid}")
        
        torrent = resp.data[0]
        logger.info("Retrieved MAM torrent: tid=%d, title=%s", torrent.id, torrent.title)
        return torrent

    def download_torrent_by_tid(self, tid: int) -> bytes:
        """
        Download .torrent file using session cookie.
        
        Args:
            tid: Torrent ID
            
        Returns:
            Raw bytes of the .torrent file
        """
        logger.info("Downloading torrent file: tid=%d", tid)
        r = self._client.get(MAM_DOWNLOAD_PATH, params={"tid": str(tid)})
        r.raise_for_status()
        logger.debug("Downloaded torrent: tid=%d, size=%d bytes", tid, len(r.content))
        return r.content

    def download_torrent_by_dl(self, dl_token: str) -> bytes:
        """
        Download .torrent using dl token (no cookie required).
        
        Args:
            dl_token: Download token from dlLink response
            
        Returns:
            Raw bytes of the .torrent file
        """
        if not dl_token:
            raise ValueError("dl_token is required")
        
        path = f"{MAM_DOWNLOAD_PATH}/{dl_token}"
        logger.info("Downloading torrent via dl token")
        r = self._client.get(path)
        r.raise_for_status()
        logger.debug("Downloaded torrent via dl token: size=%d bytes", len(r.content))
        return r.content


class MamAsyncClient:
    """
    Asynchronous MAM API client for concurrent operations.
    
    Example:
        async with MamAsyncClient(mam_id="your_cookie_value") as mam:
            torrent = await mam.get_torrent(1207719)
            print(torrent.title)
    """

    def __init__(
        self,
        mam_id: str,
        *,
        base_url: str = MAM_BASE_URL,
        timeout: float = 30.0,
        http2: bool = True,
        user_agent: str = "AudiobookDev/1.0 (+https://github.com/H2OKing89/audiobook_dev)",
    ) -> None:
        if not mam_id:
            raise ValueError("mam_id cookie is required for MAM API access")
        
        self._client = httpx.AsyncClient(
            base_url=base_url,
            http2=http2,
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": user_agent},
            cookies={"mam_id": mam_id},
            follow_redirects=True,
        )
        logger.debug("Initialized async MAM client with base_url=%s, http2=%s", base_url, http2)

    async def aclose(self) -> None:
        """Close the async HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "MamAsyncClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.aclose()

    async def search(
        self,
        *,
        tor: Dict[str, Any],
        perpage: int = 100,
        media_info: bool = True,
        isbn: bool = True,
        description: bool = False,
        dl_link: bool = False,
        thumbnail: Optional[bool] = None,
    ) -> MamSearchResponseRaw:
        """
        Search MAM torrents via JSON API (async).
        
        See MamClient.search() for parameter documentation.
        """
        if perpage < 5 or perpage > 1000:
            raise ValueError("perpage must be between 5 and 1000")

        payload: Dict[str, Any] = {"tor": tor}
        if media_info:
            payload["mediaInfo"] = ""
        if isbn:
            payload["isbn"] = ""
        if description:
            payload["description"] = ""
        if dl_link:
            payload["dlLink"] = ""
        if thumbnail is not None:
            payload["thumbnail"] = "true" if thumbnail else "false"

        payload["perpage"] = perpage

        logger.debug("MAM async search request: tor=%s", 
                    {k: v for k, v in tor.items() if k != "id"})

        r = await self._client.post(
            MAM_SEARCH_PATH, 
            json=payload, 
            params={"perpage": str(perpage)}
        )
        r.raise_for_status()
        
        response = MamSearchResponseRaw.model_validate(r.json())
        logger.debug("MAM async search returned %d results", len(response.data))
        return response

    async def get_torrent(
        self,
        tid: int,
        *,
        media_info: bool = True,
        isbn: bool = True,
        description: bool = False,
        dl_link: bool = False,
    ) -> MamTorrentRaw:
        """
        Fetch a single torrent by ID (async).
        
        See MamClient.get_torrent() for parameter documentation.
        """
        tor = {
            "id": tid,
            "searchIn": "torrents",
            "searchType": "all",
            "sortType": "default",
            "startNumber": "0",
            "cat": ["0"],
            "browse_lang": ["0"],
        }
        
        logger.info("Fetching MAM torrent (async): tid=%d", tid)
        
        resp = await self.search(
            tor=tor,
            perpage=5,
            media_info=media_info,
            isbn=isbn,
            description=description,
            dl_link=dl_link,
        )
        
        if not resp.data:
            logger.warning("MAM torrent not found: tid=%d", tid)
            raise MamApiError(f"Torrent not found for tid={tid}")
        
        torrent = resp.data[0]
        logger.info("Retrieved MAM torrent (async): tid=%d, title=%s", torrent.id, torrent.title)
        return torrent

    async def download_torrent_by_tid(self, tid: int) -> bytes:
        """Download .torrent file using session cookie (async)."""
        logger.info("Downloading torrent file (async): tid=%d", tid)
        r = await self._client.get(MAM_DOWNLOAD_PATH, params={"tid": str(tid)})
        r.raise_for_status()
        logger.debug("Downloaded torrent (async): tid=%d, size=%d bytes", tid, len(r.content))
        return r.content

    async def download_torrent_by_dl(self, dl_token: str) -> bytes:
        """Download .torrent using dl token (async)."""
        if not dl_token:
            raise ValueError("dl_token is required")
        
        path = f"{MAM_DOWNLOAD_PATH}/{dl_token}"
        logger.info("Downloading torrent via dl token (async)")
        r = await self._client.get(path)
        r.raise_for_status()
        logger.debug("Downloaded torrent via dl token (async): size=%d bytes", len(r.content))
        return r.content
