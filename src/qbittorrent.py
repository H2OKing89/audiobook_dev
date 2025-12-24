import os
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from qbittorrentapi import Client, LoginFailed

from src.logging_setup import get_logger


log = get_logger(__name__)


def get_client() -> Client:
    """Initialize and return a qBittorrent Client using environment variables."""
    host = os.getenv("QBITTORRENT_URL")
    username = os.getenv("QBITTORRENT_USERNAME")
    password = os.getenv("QBITTORRENT_PASSWORD")
    log.debug("qbittorrent.client.init", host=host, username=username)
    if not host or not username or not password:
        raise ValueError("QBITTORRENT_URL, QBITTORRENT_USERNAME, and QBITTORRENT_PASSWORD must be set")
    try:
        return Client(host=host, username=username, password=password)
    except LoginFailed as e:
        log.error("qbittorrent.login.failed", host=host, username=username, error=str(e))
        raise ConnectionError(f"Failed to authenticate with qBittorrent at {host}") from e
    except Exception as e:
        log.error("qbittorrent.connect.failed", host=host, error=str(e))
        raise ConnectionError(f"Failed to connect to qBittorrent at {host}: {e}") from e


def add_torrent(torrent_data: dict[str, Any]) -> bool:
    """Add torrent via qBittorrent API (by URL)."""
    try:
        client = get_client()
        url = torrent_data.get("url")
        log.info("qbittorrent.torrent.add_by_url", url=url)
        resp = client.torrents_add(urls=url)

        # Normalize response for comparison
        resp_normalized = str(resp).strip().lower().rstrip(".") if resp else ""

        if resp_normalized == "ok":
            log.info("qbittorrent.torrent.add.success", url=url, result="ok")
            return True
        elif resp_normalized == "fails":
            log.warning(
                "qbittorrent.torrent.add.rejected",
                url=url,
                result="fails",
                reason="duplicate_or_invalid",
            )
            return False
        else:
            log.error(
                "qbittorrent.torrent.add.unknown_response",
                url=url,
                result="unknown",
                api_response=str(resp),
            )
            return False
    except Exception:
        log.exception("qbittorrent.torrent.add.error")
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
            log.error("qbittorrent.download.invalid_url", url=download_url)
            return False

        # Download .torrent file
        headers = {"Cookie": cookie} if cookie else {}
        safe_cookie = "set" if cookie else "not set"
        log.info("qbittorrent.torrent.downloading", url=download_url, cookie_status=safe_cookie)
        base_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
        with tempfile.NamedTemporaryFile(delete=False, prefix=f"{base_name}.", suffix=".torrent") as tmp:
            with httpx.stream("GET", download_url, headers=headers, timeout=30.0, follow_redirects=True) as r:
                log.debug("qbittorrent.http.get", url=download_url, status=getattr(r, "status_code", "unknown"))
                r.raise_for_status()
                for chunk in r.iter_bytes(1024 * 128):
                    tmp.write(chunk)
            tmp_name = tmp.name
        log.info("qbittorrent.torrent.downloaded", path=tmp_name)
        # Upload to qBittorrent
        client = get_client()
        try:
            log.debug("qbittorrent.auth.logging_in")
            client.auth_log_in()
            log.info("qbittorrent.auth.success")
        except LoginFailed as e:
            log.exception("qbittorrent.auth.failed")
            raise Exception(f"qBittorrent login failed: {e}") from e
        log.info(
            "qbittorrent.torrent.uploading",
            category=category,
            tags=tags,
            paused=paused,
            autoTMM=autoTMM,
            contentLayout=contentLayout,
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

        # qBittorrent API returns:
        # - "Ok." on success
        # - "Fails." on failure (duplicate, invalid file, etc.)
        resp_normalized = str(resp).strip().lower().rstrip(".") if resp else ""

        if resp_normalized == "ok":
            log.info(
                "qbittorrent.torrent.upload.success",
                result="ok",
            )
            return True
        elif resp_normalized == "fails":
            # "Fails." typically means duplicate or invalid torrent
            # Log as warning since it might be expected (re-adding same torrent)
            log.warning(
                "qbittorrent.torrent.upload.rejected",
                result="fails",
                reason="duplicate_or_invalid",
                api_response=str(resp),
            )
            return False
        else:
            # Unexpected response - log the full response for debugging
            log.error(
                "qbittorrent.torrent.upload.unknown_response",
                result="unknown",
                api_response=str(resp),
                reason="unexpected_api_response",
            )
            return False
    except Exception:
        log.exception("qbittorrent.torrent.add_file_error")
        return False
    finally:
        if tmp_name:
            try:
                Path(tmp_name).unlink()
                log.debug("qbittorrent.tempfile.removed", path=tmp_name)
            except Exception:
                log.warning("qbittorrent.tempfile.remove_failed", path=tmp_name)
