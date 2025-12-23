import logging
import os
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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
    try:
        return Client(host=host, username=username, password=password)
    except LoginFailed as e:
        logger.error("qBittorrent login failed for host=%s, username=%s: %s", host, username, e)
        raise ConnectionError(f"Failed to authenticate with qBittorrent at {host}") from e
    except Exception as e:
        logger.error("Failed to connect to qBittorrent at host=%s: %s", host, e)
        raise ConnectionError(f"Failed to connect to qBittorrent at {host}: {e}") from e


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
    tmp_name: str | None = None
    try:
        # Validate download URL before attempting network call
        parsed = urlparse(download_url or "")
        if not (parsed.scheme in ("http", "https") and parsed.netloc):
            logger.error("Invalid download URL provided: %s", download_url)
            return False

        # Download .torrent file
        headers = {"Cookie": cookie} if cookie else {}
        safe_cookie = "set" if cookie else "not set"
        logger.info("Downloading .torrent file from %s with cookie: %s", download_url, safe_cookie)
        base_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
        with tempfile.NamedTemporaryFile(delete=False, prefix=f"{base_name}.", suffix=".torrent") as tmp:
            with httpx.stream("GET", download_url, headers=headers, timeout=30.0, follow_redirects=True) as r:
                logger.debug("HTTP GET %s status=%s", download_url, getattr(r, "status_code", "unknown"))
                r.raise_for_status()
                for chunk in r.iter_bytes(1024 * 128):
                    tmp.write(chunk)
            tmp_name = tmp.name
        logger.info("Downloaded torrent to %s", tmp_name)
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
        with Path(tmp_name).open("rb") as f:
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
        if tmp_name:
            try:
                Path(tmp_name).unlink()
                logger.debug("Removed temp file: %s", tmp_name)
            except Exception:
                logger.warning("Could not remove temp file: %s", tmp_name)
