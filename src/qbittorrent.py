import logging
import os
import tempfile
from typing import IO, Any

import httpx
from qbittorrentapi import Client, LoginFailed


logger = logging.getLogger(__name__)


def get_client() -> Client:
    """Initialize and return a qBittorrent Client using environment variables."""
    host = os.getenv("QBITTORRENT_URL")
    username = os.getenv("QBITTORRENT_USERNAME")
    password = os.getenv("QBITTORRENT_PASSWORD")
    logger.debug("Initializing qBittorrent client with host=%s, username=%s", host, username)
    if not host or not username or not password:
        raise ValueError("QBITTORRENT_URL, QBITTORRENT_USERNAME, and QBITTORRENT_PASSWORD must be set")
    return Client(host=host, username=username, password=password)


def add_torrent(torrent_data: dict[str, Any]) -> bool:
    """Add torrent via qBittorrent API (by URL)."""
    try:
        client = get_client()
        url = torrent_data.get("url")
        logger.info("Adding torrent by URL: %s", url)
        resp = client.torrents_add(urls=url)
        logger.info("Added torrent: %s, qBittorrent API response: %s", url, resp)
        return True
    except Exception:
        logger.exception("Error adding torrent")
        return False


def add_torrent_file_with_cookie(
    download_url: str,
    name: str,
    category: str | None = None,
    tags: Any | None = None,
    cookie: str | None = None,
    paused: bool = False,
    autoTMM: bool = True,
    contentLayout: str = "Subfolder",
) -> bool:
    """
    Download a .torrent file (with optional cookie) and upload to qBittorrent with options.
    """
    tmp: IO[bytes] | None = None
    try:
        # Validate download URL before attempting network call
        from urllib.parse import urlparse

        parsed = urlparse(download_url or "")
        if not (parsed.scheme in ("http", "https") and parsed.netloc):
            logger.error("Invalid download URL provided: %s", download_url)
            return False

        # Download .torrent file
        headers = {"Cookie": cookie} if cookie else {}
        safe_cookie = "set" if cookie else "not set"
        logger.info("Downloading .torrent file from %s with cookie: %s", download_url, safe_cookie)
        base_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
        tmp = tempfile.NamedTemporaryFile(delete=False, prefix=f"{base_name}.", suffix=".torrent")
        try:
            with httpx.stream("GET", download_url, headers=headers, timeout=30.0, follow_redirects=True) as r:
                logger.debug("HTTP GET %s status=%s", download_url, getattr(r, "status_code", "unknown"))
                r.raise_for_status()
                for chunk in r.iter_bytes(1024 * 128):
                    tmp.write(chunk)
        finally:
            tmp.close()
        logger.info("Downloaded torrent to %s", tmp.name)
        # Upload to qBittorrent
        client = get_client()
        try:
            logger.debug("Logging in to qBittorrent...")
            client.auth_log_in()
            logger.info("Logged in to qBittorrent successfully.")
        except LoginFailed as e:
            logger.exception("qBittorrent login failed")
            raise Exception(f"qBittorrent login failed: {e}") from e
        logger.info(
            "Uploading torrent file to qBittorrent with options: category=%s, tags=%s, paused=%s, autoTMM=%s, contentLayout=%s",
            category,
            tags,
            paused,
            autoTMM,
            contentLayout,
        )
        with open(tmp.name, "rb") as f:
            resp = client.torrents_add(
                torrent_files=f,
                category=category,
                paused=paused,
                autoTMM=autoTMM,
                contentLayout=contentLayout,
                tags=tags or [],
            )
            logger.info("qBittorrent API response: %s", resp)
        logger.info("Successfully uploaded torrent to qBittorrent")
        return True
    except Exception:
        logger.exception("Failed to add torrent file")
        return False
    finally:
        if tmp:
            try:
                os.remove(tmp.name)
                logger.debug("Removed temp file: %s", tmp.name)
            except Exception:
                logger.warning("Could not remove temp file: %s", tmp.name)
