"""
Enhanced qBittorrent integration module.

Key improvements over previous implementation:
- Singleton client with proper session management (prevents memory leaks)
- Context manager support for automatic resource cleanup
- Manual torrent download for cookie-authenticated URLs (qBittorrent's cookie param doesn't work for file downloads)
- Granular exception handling using qbittorrent-api's exception hierarchy
- Dataclass-based configuration with validation
- Full type hints throughout
- Backward compatible with existing function signatures
"""

import hashlib
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
from qbittorrentapi import Client
from qbittorrentapi.exceptions import (
    APIConnectionError,
    Conflict409Error,
    LoginFailed,
    NotFound404Error,
    UnsupportedMediaType415Error,
)

from src.logging_setup import get_logger


log = get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass(frozen=True)
class QBittorrentConfig:
    """
    Configuration for qBittorrent connection.

    Attributes:
        host: qBittorrent WebUI URL (e.g., 'http://localhost:8080')
        username: WebUI username
        password: WebUI password
        verify_certificate: Whether to verify SSL certificates (set False for self-signed)
        timeout: Tuple of (connect_timeout, read_timeout) in seconds
    """

    host: str
    username: str
    password: str
    verify_certificate: bool = True
    timeout: tuple[float, float] = (3.1, 30.0)  # connect, read

    @classmethod
    def from_env(cls) -> "QBittorrentConfig":
        """
        Load configuration from environment variables.

        Environment variables:
            QBITTORRENT_URL: WebUI URL
            QBITTORRENT_USERNAME: WebUI username
            QBITTORRENT_PASSWORD: WebUI password
            QBITTORRENT_VERIFY_SSL: 'true' or 'false' (default: 'true')

        Raises:
            ValueError: If required environment variables are not set
        """
        host = os.getenv("QBITTORRENT_URL")
        username = os.getenv("QBITTORRENT_USERNAME")
        password = os.getenv("QBITTORRENT_PASSWORD")
        verify = os.getenv("QBITTORRENT_VERIFY_SSL", "true").lower() == "true"

        if not all([host, username, password]):
            raise ValueError("QBITTORRENT_URL, QBITTORRENT_USERNAME, and QBITTORRENT_PASSWORD must be set")

        # Type narrowing: all() check above ensures these are not None
        assert isinstance(host, str), f"host must be a str, got {type(host)}"
        assert isinstance(username, str), f"username must be a str, got {type(username)}"
        assert isinstance(password, str), f"password must be a str, got {type(password)}"

        return cls(
            host=host,
            username=username,
            password=password,
            verify_certificate=verify,
        )


@dataclass
class TorrentAddOptions:
    """
    Options for adding a torrent to qBittorrent.

    All fields are optional and will use qBittorrent defaults if not specified.
    """

    category: str | None = None
    tags: list[str] | None = None
    save_path: str | None = None
    download_path: str | None = None
    is_paused: bool = False
    use_auto_torrent_management: bool = True
    content_layout: Literal["Original", "Subfolder", "NoSubfolder"] = "Subfolder"
    ratio_limit: float | None = None
    seeding_time_limit: int | None = None  # minutes
    upload_limit: int | None = None  # bytes/sec
    download_limit: int | None = None  # bytes/sec
    is_sequential_download: bool = False
    is_first_last_piece_priority: bool = False
    rename: str | None = None
    is_skip_checking: bool = False


# =============================================================================
# Custom Exceptions
# =============================================================================


class QBittorrentError(Exception):
    """Base exception for all qBittorrent operations."""


class QBittorrentConnectionError(QBittorrentError):
    """Failed to connect to qBittorrent WebUI."""


class QBittorrentAuthError(QBittorrentError):
    """Authentication to qBittorrent failed."""


class TorrentAddError(QBittorrentError):
    """Failed to add a torrent."""


class TorrentExistsError(TorrentAddError):
    """Torrent already exists in qBittorrent (not necessarily an error)."""


# =============================================================================
# Helper Functions
# =============================================================================


def extract_info_hash(torrent_data: bytes) -> str | None:
    """
    Extract the info hash from raw torrent data.

    Uses simple bencode parsing to find and hash the info dictionary.
    Returns None if parsing fails.

    Args:
        torrent_data: Raw .torrent file bytes

    Returns:
        Lowercase hex string of the SHA1 info hash, or None on failure
    """
    try:
        # Simple bencode parser for extracting info dict
        def decode_int(data: bytes, start: int) -> tuple[int, int]:
            """Decode bencode integer: i<number>e"""
            end = data.index(b"e", start)
            return int(data[start + 1 : end]), end + 1

        def decode_string(data: bytes, start: int) -> tuple[bytes, int]:
            """Decode bencode string: <length>:<content>"""
            colon = data.index(b":", start)
            length = int(data[start:colon])
            content_start = colon + 1
            return data[content_start : content_start + length], content_start + length

        def find_info_bounds(data: bytes) -> tuple[int, int] | None:
            """Find start and end positions of 'info' dict in torrent."""
            # Look for '4:info' key in the root dict
            info_key = b"4:info"
            idx = data.find(info_key)
            if idx == -1:
                return None

            # Start of info dict value (after the key)
            info_start = idx + len(info_key)

            # Now we need to find where the info dict ends
            # The info dict starts with 'd' and we need to find matching 'e'
            if data[info_start : info_start + 1] != b"d":
                return None

            depth = 0
            pos = info_start
            while pos < len(data):
                char = data[pos : pos + 1]
                if char in {b"d", b"l"}:
                    depth += 1
                    pos += 1
                elif char == b"e":
                    depth -= 1
                    pos += 1
                    if depth == 0:
                        return info_start, pos
                elif char == b"i":
                    # Integer: skip to 'e'
                    end = data.index(b"e", pos)
                    pos = end + 1
                elif char.isdigit():
                    # String: find colon, then skip content
                    colon = data.index(b":", pos)
                    length = int(data[pos:colon])
                    pos = colon + 1 + length
                else:
                    pos += 1

            return None

        bounds = find_info_bounds(torrent_data)
        if bounds is None:
            return None

        info_start, info_end = bounds
        info_bytes = torrent_data[info_start:info_end]

        # SHA1 hash of the info dict is the torrent's info hash
        return hashlib.sha1(info_bytes).hexdigest().lower()

    except (ValueError, IndexError):
        return None


# =============================================================================
# QBittorrent Manager (Singleton Pattern)
# =============================================================================


class QBittorrentManager:
    """
    Manages qBittorrent client connections with proper lifecycle management.

    This class implements the singleton pattern to ensure only one client
    connection is maintained, preventing memory leaks in qBittorrent caused
    by creating multiple sessions.

    Features:
        - Singleton pattern with lazy initialization
        - Context manager support for automatic cleanup
        - Automatic session management (library handles re-authentication)
        - Configurable connection pooling via REQUESTS_ARGS

    Usage:
        # As singleton
        manager = QBittorrentManager()
        manager.add_torrent_by_url("magnet:?...")

        # With context manager for explicit cleanup
        with qbittorrent_session() as manager:
            manager.add_torrent_by_url("magnet:?...")
    """

    _instance: "QBittorrentManager | None" = None

    def __new__(cls) -> "QBittorrentManager":
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the manager (only runs once due to singleton)."""
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._config: QBittorrentConfig | None = None
            self._client: Client | None = None

    @classmethod
    def create_scoped(cls) -> "QBittorrentManager":
        """
        Create a non-singleton instance for scoped usage (e.g., context managers).

        This bypasses the singleton pattern and creates a fresh instance that
        can be independently managed and cleaned up.

        Returns:
            New QBittorrentManager instance (not the singleton)
        """
        instance = object.__new__(cls)
        instance._initialized = True
        instance._config = None
        instance._client = None
        return instance

    def configure(self, config: QBittorrentConfig | None = None) -> None:
        """
        Configure the manager with connection settings.

        Args:
            config: Configuration object. If None, loads from environment variables.
        """
        self._config = config or QBittorrentConfig.from_env()
        # Reset client if reconfigured
        if self._client is not None:
            self.disconnect()

    @property
    def client(self) -> Client:
        """
        Get or create the qBittorrent client (lazy initialization).

        The client is created on first access and reused for subsequent calls.
        The qbittorrent-api library automatically handles session management,
        including re-authentication if the session expires.

        Returns:
            Configured and connected qBittorrent Client

        Raises:
            QBittorrentAuthError: If authentication fails
            QBittorrentConnectionError: If connection cannot be established
        """
        if self._client is None:
            if self._config is None:
                self.configure()

            assert self._config is not None

            log.debug(
                "qbittorrent.client.init",
                host=self._config.host,
                username=self._config.username,
            )

            try:
                self._client = Client(
                    host=self._config.host,
                    username=self._config.username,
                    password=self._config.password,
                    VERIFY_WEBUI_CERTIFICATE=self._config.verify_certificate,
                    REQUESTS_ARGS={"timeout": self._config.timeout},
                    DISABLE_LOGGING_DEBUG_OUTPUT=True,
                )
                # Verify connection works by fetching version
                version = self._client.app_version()
                log.info("qbittorrent.connected", version=version)

            except LoginFailed as e:
                log.exception("qbittorrent.auth.failed")
                self._client = None
                raise QBittorrentAuthError(f"Authentication failed: {e}") from e

            except APIConnectionError as e:
                log.exception("qbittorrent.connection.failed")
                self._client = None
                raise QBittorrentConnectionError(f"Connection failed: {e}") from e

            except Exception as e:
                log.exception("qbittorrent.connection.unexpected_error")
                self._client = None
                raise QBittorrentConnectionError(f"Unexpected error: {e}") from e

        return self._client

    def disconnect(self) -> None:
        """
        Properly close the client connection.

        This logs out from qBittorrent, freeing the session resources.
        Should be called when the application is shutting down or when
        you want to force a new connection.
        """
        if self._client is not None:
            try:
                self._client.auth_log_out()
                log.debug("qbittorrent.logout.success")
            except Exception as e:
                log.debug("qbittorrent.logout.failed", error=str(e), exc_info=True)
            finally:
                self._client = None

    def __enter__(self) -> "QBittorrentManager":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None:
        """Context manager exit - ensures cleanup."""
        self.disconnect()
        return None

    def add_torrent_by_url(
        self,
        url: str,
        options: TorrentAddOptions | None = None,
        cookie: str | None = None,
    ) -> bool:
        """
        Add a torrent by URL (magnet, http, https).

        The qbittorrent-api library handles cookie-authenticated downloads
        natively through its `cookie` parameter - no need to manually download
        .torrent files!

        Args:
            url: Torrent URL (magnet:, http://, https://, bc:)
            options: Torrent configuration options
            cookie: Cookie string for authenticated downloads (e.g., "session=abc123")

        Returns:
            True if torrent was added successfully or already exists

        Raises:
            TorrentAddError: If torrent couldn't be added (invalid URL/file)
            QBittorrentConnectionError: If connection to qBittorrent fails
        """
        # Validate URL format
        if not url:
            log.error("qbittorrent.torrent.add.empty_url")
            raise TorrentAddError("URL cannot be empty")

        parsed = urlparse(url)
        valid_schemes = ("http", "https", "magnet", "bc")
        is_valid = parsed.scheme in valid_schemes and (parsed.scheme == "magnet" or parsed.netloc)
        if not is_valid:
            log.error("qbittorrent.torrent.add.invalid_url", url=url[:100])
            raise TorrentAddError(f"Invalid URL scheme. Expected one of: {valid_schemes}")

        opts = options or TorrentAddOptions()
        safe_cookie = "set" if cookie else "not set"
        log.info("qbittorrent.torrent.add_by_url", url=url[:100], cookie=safe_cookie)

        try:
            result = self.client.torrents_add(
                urls=url,
                cookie=cookie,  # Native cookie support!
                category=opts.category,
                tags=opts.tags,
                save_path=opts.save_path,
                download_path=opts.download_path,
                is_paused=opts.is_paused,
                use_auto_torrent_management=opts.use_auto_torrent_management,
                content_layout=opts.content_layout,
                ratio_limit=opts.ratio_limit,
                seeding_time_limit=opts.seeding_time_limit,
                upload_limit=opts.upload_limit,
                download_limit=opts.download_limit,
                is_sequential_download=opts.is_sequential_download,
                is_first_last_piece_priority=opts.is_first_last_piece_priority,
                rename=opts.rename,
                is_skip_checking=opts.is_skip_checking,
            )

            # Handle both old (string) and new (TorrentsAddedMetadata) responses
            if isinstance(result, str):
                if result == "Ok.":
                    log.info("qbittorrent.torrent.add.success")
                    return True
                elif result == "Fails.":
                    log.warning("qbittorrent.torrent.add.rejected", url=url[:100])
                    return False
                else:
                    # Unknown string response, log it
                    log.debug("qbittorrent.torrent.add.response", response=result)
                    return True
            else:
                # TorrentsAddedMetadata response (newer API versions)
                torrent_hash = getattr(result, "hash", None)
                if torrent_hash:
                    log.info("qbittorrent.torrent.add.success", hash=torrent_hash)
                return True

        except Conflict409Error:
            log.info("qbittorrent.torrent.already_exists")
            return True  # Not an error - torrent already exists

        except UnsupportedMediaType415Error as e:
            log.exception("qbittorrent.torrent.add.invalid_file")
            raise TorrentAddError(f"Invalid torrent URL or file: {e}") from e

        except LoginFailed as e:
            log.exception("qbittorrent.auth.failed")
            self._client = None  # Reset client to force reconnection
            raise QBittorrentAuthError(f"Authentication failed: {e}") from e

        except APIConnectionError as e:
            log.exception("qbittorrent.connection.error")
            raise QBittorrentConnectionError(f"Connection error: {e}") from e

    def add_torrent_file(
        self,
        file_path: str | Path,
        options: TorrentAddOptions | None = None,
    ) -> bool:
        """
        Add a torrent from a local .torrent file.

        Args:
            file_path: Path to the .torrent file
            options: Torrent configuration options

        Returns:
            True if torrent was added successfully or already exists

        Raises:
            TorrentAddError: If file doesn't exist or is invalid
            QBittorrentConnectionError: If connection to qBittorrent fails
        """
        path = Path(file_path)
        opts = options or TorrentAddOptions()

        if not path.exists():
            log.error("qbittorrent.torrent.file.not_found", path=str(path))
            raise TorrentAddError(f"Torrent file not found: {path}")

        if not path.is_file():
            log.error("qbittorrent.torrent.file.not_a_file", path=str(path))
            raise TorrentAddError(f"Path is not a file: {path}")

        log.info("qbittorrent.torrent.add_by_file", filename=path.name)

        try:
            # The library can accept a file path string directly
            result = self.client.torrents_add(
                torrent_files=str(path),
                category=opts.category,
                tags=opts.tags,
                save_path=opts.save_path,
                download_path=opts.download_path,
                is_paused=opts.is_paused,
                use_auto_torrent_management=opts.use_auto_torrent_management,
                content_layout=opts.content_layout,
                ratio_limit=opts.ratio_limit,
                seeding_time_limit=opts.seeding_time_limit,
                upload_limit=opts.upload_limit,
                download_limit=opts.download_limit,
                is_sequential_download=opts.is_sequential_download,
                is_first_last_piece_priority=opts.is_first_last_piece_priority,
                rename=opts.rename,
                is_skip_checking=opts.is_skip_checking,
            )

            success = False  # Initialize before conditional assignment
            if isinstance(result, str):
                success = result == "Ok."
            else:
                # TorrentsAddedMetadata response
                success = bool(getattr(result, "hash", None))

            if success:
                log.info("qbittorrent.torrent.file.add.success", filename=path.name)
            else:
                log.warning(
                    "qbittorrent.torrent.file.add.failed",
                    filename=path.name,
                    response=str(result),
                )

        except Conflict409Error:
            log.info("qbittorrent.torrent.already_exists", filename=path.name)
            return True

        except UnsupportedMediaType415Error as e:
            log.exception("qbittorrent.torrent.file.invalid", filename=path.name)
            raise TorrentAddError(f"Invalid torrent file: {e}") from e

        except LoginFailed as e:
            log.exception("qbittorrent.auth.failed")
            self._client = None
            raise QBittorrentAuthError(f"Authentication failed: {e}") from e

        except APIConnectionError as e:
            log.exception("qbittorrent.connection.error")
            raise QBittorrentConnectionError(f"Connection error: {e}") from e

        else:
            return success

    def add_torrent_data(
        self,
        torrent_data: bytes,
        options: TorrentAddOptions | None = None,
    ) -> bool:
        """
        Add a torrent from raw torrent data (bytes).

        This method is used when the torrent file has been downloaded
        with authentication and we have the raw bytes.

        Args:
            torrent_data: Raw .torrent file content as bytes
            options: Torrent configuration options

        Returns:
            True if torrent was added successfully or already exists

        Raises:
            TorrentAddError: If torrent data is invalid
            QBittorrentConnectionError: If connection to qBittorrent fails
        """
        if not torrent_data:
            log.error("qbittorrent.torrent.data.empty")
            raise TorrentAddError("Torrent data cannot be empty")

        opts = options or TorrentAddOptions()
        log.info("qbittorrent.torrent.add_data", size=len(torrent_data))

        try:
            result = self.client.torrents_add(
                torrent_files=torrent_data,
                category=opts.category,
                tags=opts.tags,
                save_path=opts.save_path,
                download_path=opts.download_path,
                is_paused=opts.is_paused,
                use_auto_torrent_management=opts.use_auto_torrent_management,
                content_layout=opts.content_layout,
                ratio_limit=opts.ratio_limit,
                seeding_time_limit=opts.seeding_time_limit,
                upload_limit=opts.upload_limit,
                download_limit=opts.download_limit,
                is_sequential_download=opts.is_sequential_download,
                is_first_last_piece_priority=opts.is_first_last_piece_priority,
                rename=opts.rename,
                is_skip_checking=opts.is_skip_checking,
            )

            # Handle both old (string) and new (TorrentsAddedMetadata) responses
            success = False
            if isinstance(result, str):
                success = result == "Ok."
            else:
                # TorrentsAddedMetadata response
                success = bool(getattr(result, "hash", None))

            if success:
                log.info("qbittorrent.torrent.data.add.success")
            else:
                # "Fails." can mean the torrent already exists - check for that
                info_hash = extract_info_hash(torrent_data)
                if info_hash:
                    existing = self.get_torrent_info(info_hash)
                    if existing:
                        log.info(
                            "qbittorrent.torrent.already_exists",
                            hash=info_hash,
                            name=existing.get("name", "unknown"),
                        )
                        return True
                log.warning("qbittorrent.torrent.data.add.failed", response=str(result))

        except Conflict409Error:
            log.info("qbittorrent.torrent.already_exists")
            return True

        except UnsupportedMediaType415Error as e:
            log.exception("qbittorrent.torrent.data.invalid")
            raise TorrentAddError(f"Invalid torrent data: {e}") from e

        except LoginFailed as e:
            log.exception("qbittorrent.auth.failed")
            self._client = None
            raise QBittorrentAuthError(f"Authentication failed: {e}") from e

        except APIConnectionError as e:
            log.exception("qbittorrent.connection.error")
            raise QBittorrentConnectionError(f"Connection error: {e}") from e

        else:
            return success

    def get_torrent_info(self, torrent_hash: str) -> dict[str, Any] | None:
        """
        Get information about a specific torrent.

        Args:
            torrent_hash: The hash of the torrent to look up

        Returns:
            Dictionary with torrent information, or None if not found
        """
        try:
            torrents = self.client.torrents_info(torrent_hashes=torrent_hash)
            if torrents:
                return dict(torrents[0])
            return None
        except NotFound404Error:
            return None
        except Exception as e:
            log.warning("qbittorrent.torrent.info.error", hash=torrent_hash, error=str(e))
            return None

    def is_connected(self) -> bool:
        """Check if we have an active connection to qBittorrent."""
        if self._client is None:
            return False
        try:
            self._client.app_version()
            return True
        except Exception:
            return False


# =============================================================================
# Module-level singleton access
# =============================================================================


def get_manager() -> QBittorrentManager:
    """
    Get the singleton QBittorrentManager instance.

    Returns:
        The shared QBittorrentManager instance
    """
    # QBittorrentManager implements singleton pattern via __new__
    return QBittorrentManager()


@contextmanager
def qbittorrent_session() -> Iterator[QBittorrentManager]:
    """
    Context manager for qBittorrent operations with automatic cleanup.

    This creates a fresh manager instance (not the singleton) and ensures
    proper logout when the context exits.

    Usage:
        with qbittorrent_session() as qbt:
            qbt.add_torrent_by_url("magnet:?...")

    Yields:
        QBittorrentManager instance
    """
    # Create a non-singleton instance for scoped usage
    manager = QBittorrentManager.create_scoped()

    try:
        yield manager
    finally:
        manager.disconnect()


# =============================================================================
# Backward Compatible Functions
# =============================================================================


def get_client() -> Client:
    """
    Initialize and return a qBittorrent Client using environment variables.

    This function is provided for backward compatibility. For new code,
    prefer using `get_manager()` or `qbittorrent_session()`.

    Returns:
        Configured qBittorrent Client instance

    Raises:
        ValueError: If required environment variables are not set
        ConnectionError: If connection or authentication fails
    """
    try:
        return get_manager().client
    except QBittorrentAuthError as e:
        raise ConnectionError(str(e)) from e
    except QBittorrentConnectionError as e:
        raise ConnectionError(str(e)) from e


def add_torrent(torrent_data: dict[str, Any]) -> bool:
    """
    Add torrent via qBittorrent API (by URL).

    Backward compatible function - for new code, prefer using
    `get_manager().add_torrent_by_url()`.

    Args:
        torrent_data: Dictionary containing 'url' key with the torrent URL

    Returns:
        True if successful, False otherwise
    """
    url = torrent_data.get("url")
    if not url:
        log.error("qbittorrent.torrent.add.no_url")
        return False

    try:
        return get_manager().add_torrent_by_url(url)
    except QBittorrentError:
        log.exception("qbittorrent.torrent.add.error")
        return False
    except Exception:
        log.exception("qbittorrent.torrent.add.unexpected_error")
        return False


def add_torrent_file_with_cookie(
    download_url: str,
    name: str,
    category: str | None = None,
    tags: str | list[str] | None = None,
    cookie: str | None = None,
    paused: bool = False,
    autoTMM: bool = True,
    contentLayout: str = "Subfolder",
) -> bool:
    """
    Add a torrent with cookie authentication.

    This function downloads the .torrent file using the provided cookie,
    then adds it to qBittorrent as raw torrent data. This is necessary because
    qBittorrent's `cookie` parameter in torrents_add() is for tracker
    authentication, NOT for downloading the .torrent file itself.

    Args:
        download_url: URL to the torrent (http/https/magnet)
        name: Name for the torrent (used for logging)
        category: Category to assign to the torrent
        tags: Tag(s) to assign to the torrent
        cookie: Cookie string for authenticated downloads (e.g., "mam_id=xxx")
        paused: Whether to add the torrent in paused state
        autoTMM: Whether to use automatic torrent management
        contentLayout: Content layout ('Original', 'Subfolder', 'NoSubfolder')

    Returns:
        True if successful, False otherwise
    """
    # Convert tags to list if needed
    tags_list: list[str] | None = None
    if tags is not None:
        if isinstance(tags, list):
            tags_list = tags
        else:
            # tags is a string at this point
            tags_list = [tags] if tags else None

    # Map contentLayout string to proper type
    valid_layouts: set[str] = {"Original", "Subfolder", "NoSubfolder"}
    if contentLayout not in valid_layouts:
        log.warning(
            "qbittorrent.torrent.invalid_content_layout",
            value=contentLayout,
            default="Subfolder",
        )
        layout: Literal["Original", "Subfolder", "NoSubfolder"] = "Subfolder"
    else:
        # Type narrowing: contentLayout is now known to be a valid literal
        layout = contentLayout  # type: ignore[assignment]

    options = TorrentAddOptions(
        category=category,
        tags=tags_list,
        is_paused=paused,
        use_auto_torrent_management=autoTMM,
        content_layout=layout,
        rename=name if name else None,
    )

    log.info("qbittorrent.torrent.add_with_cookie", name=name)

    # For magnet links, no cookie download needed
    parsed = urlparse(download_url)
    if parsed.scheme == "magnet":
        log.debug("qbittorrent.torrent.magnet_link", name=name)
        try:
            return get_manager().add_torrent_by_url(
                url=download_url,
                options=options,
                cookie=None,  # Magnets don't need cookies
            )
        except QBittorrentError:
            log.exception("qbittorrent.torrent.add.failed", name=name)
            return False

    # For HTTP(S) URLs with cookies, we need to download the .torrent file ourselves
    # because qBittorrent's cookie parameter is for tracker auth, not file download
    if cookie and parsed.scheme in ("http", "https"):
        log.info("qbittorrent.torrent.download_with_cookie", url=download_url[:100])
        try:
            # Download the .torrent file with cookie authentication
            headers = {"Cookie": cookie}
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(download_url, headers=headers)
                response.raise_for_status()

                # Verify we got a torrent file (should start with 'd' for bencoded dict)
                torrent_data = response.content
                if not torrent_data or not torrent_data.startswith(b"d"):
                    log.error(
                        "qbittorrent.torrent.invalid_response",
                        content_type=response.headers.get("content-type"),
                        size=len(torrent_data),
                    )
                    return False

                log.info("qbittorrent.torrent.downloaded", size=len(torrent_data))

            # Add the torrent data to qBittorrent
            return get_manager().add_torrent_data(
                torrent_data=torrent_data,
                options=options,
            )

        except httpx.HTTPStatusError as e:
            log.error(
                "qbittorrent.torrent.download_failed",
                status_code=e.response.status_code,
                url=download_url[:100],
            )
            return False
        except httpx.RequestError as e:
            log.error("qbittorrent.torrent.download_error", error=str(e))
            return False
        except QBittorrentError:
            log.exception("qbittorrent.torrent.add.failed", name=name)
            return False
        except Exception:
            log.exception("qbittorrent.torrent.add.unexpected_error", name=name)
            return False

    # For URLs without cookies, use the standard method
    try:
        return get_manager().add_torrent_by_url(
            url=download_url,
            options=options,
            cookie=cookie,
        )
    except QBittorrentError:
        log.exception("qbittorrent.torrent.add.failed", name=name)
        return False
    except Exception:
        log.exception("qbittorrent.torrent.add.unexpected_error", name=name)
        return False
