import os
import logging
import tempfile
import requests
from qbittorrentapi import Client, LoginFailed, exceptions as qbexc


def get_client():
    """Initialize and return a qBittorrent Client using environment variables."""
    host = os.getenv('QBITTORRENT_URL')
    username = os.getenv('QBITTORRENT_USERNAME')
    password = os.getenv('QBITTORRENT_PASSWORD')
    logging.debug(f"Initializing qBittorrent client with host={host}, username={username}")
    if not host or not username or not password:
        raise ValueError('QBITTORRENT_URL, QBITTORRENT_USERNAME, and QBITTORRENT_PASSWORD must be set')
    return Client(host=host, username=username, password=password)


def add_torrent(torrent_data):
    """Add torrent via qBittorrent API (by URL)."""
    try:
        client = get_client()
        url = torrent_data.get('url')
        logging.info(f"Adding torrent by URL: {url}")
        resp = client.torrents_add(urls=url)
        logging.info(f"Added torrent: {url}, qBittorrent API response: {resp}")
        return True
    except Exception as e:
        logging.error(f"Error adding torrent: {e}")
        return False


def add_torrent_file_with_cookie(download_url, name, category=None, tags=None, cookie=None, paused=False, autoTMM=True, contentLayout="Subfolder"):
    """
    Download a .torrent file (with optional cookie) and upload to qBittorrent with options.
    """
    tmp = None
    try:
        # Download .torrent file
        headers = {"Cookie": cookie} if cookie else {}
        safe_cookie = 'set' if cookie else 'not set'
        logging.info(f"Downloading .torrent file from {download_url} with cookie: {safe_cookie}")
        base_name = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in name)
        tmp = tempfile.NamedTemporaryFile(delete=False, prefix=f"{base_name}.", suffix=".torrent")
        with requests.get(download_url, headers=headers, stream=True, timeout=30) as r:
            logging.debug(f"HTTP GET {download_url} status={r.status_code}")
            r.raise_for_status()
            for chunk in r.iter_content(1024 * 128):
                tmp.write(chunk)
        tmp.close()
        logging.info(f"Downloaded torrent to {tmp.name}")
        # Upload to qBittorrent
        client = get_client()
        try:
            logging.debug("Logging in to qBittorrent...")
            client.auth_log_in()
            logging.info("Logged in to qBittorrent successfully.")
        except LoginFailed as e:
            logging.error(f"qBittorrent login failed: {e}")
            raise Exception(f"qBittorrent login failed: {e}")
        logging.info(f"Uploading torrent file to qBittorrent with options: category={category}, tags={tags}, paused={paused}, autoTMM={autoTMM}, contentLayout={contentLayout}")
        with open(tmp.name, "rb") as f:
            resp = client.torrents_add(
                torrent_files=f,
                category=category,
                paused=paused,
                autoTMM=autoTMM,
                contentLayout=contentLayout,
                tags=tags or [],
            )
            logging.info(f"qBittorrent API response: {resp}")
        logging.info("Successfully uploaded torrent to qBittorrent")
        return True
    except Exception as e:
        logging.error(f"Failed to add torrent file: {e}")
        logging.exception("Full exception traceback for failed torrent upload:")
        return False
    finally:
        if tmp:
            try:
                os.remove(tmp.name)
                logging.debug(f"Removed temp file: {tmp.name}")
            except Exception:
                logging.warning(f"Could not remove temp file: {tmp.name}")