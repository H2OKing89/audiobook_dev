import os
from unittest.mock import MagicMock, patch

import pytest

from src.qbittorrent import (
    QBittorrentConfig,
    QBittorrentManager,
    TorrentAddOptions,
    add_torrent,
    add_torrent_file_with_cookie,
    get_client,
    qbittorrent_session,
)


class TestQBittorrentConfig:
    def test_from_env_success(self, monkeypatch):
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        config = QBittorrentConfig.from_env()

        assert config.host == "http://localhost:8080"
        assert config.username == "admin"
        assert config.password == "password"
        assert config.verify_certificate is True

    def test_from_env_with_ssl_disabled(self, monkeypatch):
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")
        monkeypatch.setenv("QBITTORRENT_VERIFY_SSL", "false")

        config = QBittorrentConfig.from_env()

        assert config.verify_certificate is False

    def test_from_env_missing_vars(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(
                ValueError, match="QBITTORRENT_URL, QBITTORRENT_USERNAME, and QBITTORRENT_PASSWORD must be set"
            ),
        ):
            QBittorrentConfig.from_env()


class TestTorrentAddOptions:
    def test_default_values(self):
        options = TorrentAddOptions()

        assert options.category is None
        assert options.tags is None
        assert options.is_paused is False
        assert options.use_auto_torrent_management is True
        assert options.content_layout == "Subfolder"

    def test_custom_values(self):
        options = TorrentAddOptions(
            category="audiobooks",
            tags=["new", "fiction"],
            is_paused=True,
            content_layout="NoSubfolder",
        )

        assert options.category == "audiobooks"
        assert options.tags == ["new", "fiction"]
        assert options.is_paused is True
        assert options.content_layout == "NoSubfolder"


class TestQBittorrentManager:
    def test_singleton_pattern(self, monkeypatch):
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        manager1 = QBittorrentManager()
        manager2 = QBittorrentManager()

        assert manager1 is manager2

    def test_create_scoped_not_singleton(self, monkeypatch):
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        singleton = QBittorrentManager()
        scoped = QBittorrentManager.create_scoped()

        assert singleton is not scoped

    def test_client_lazy_initialization(self, monkeypatch):
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()
            # Client not created yet
            mock_client_class.assert_not_called()

            # Access client property - now it's created
            _ = manager.client
            mock_client_class.assert_called_once()

    def test_add_torrent_by_url_success(self, monkeypatch):
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_add.return_value = "Ok."
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()
            result = manager.add_torrent_by_url("magnet:?xt=urn:btih:abc123")

            assert result is True
            mock_client.torrents_add.assert_called_once()

    def test_add_torrent_by_url_with_cookie(self, monkeypatch):
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_add.return_value = "Ok."
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()
            result = manager.add_torrent_by_url(
                "https://example.com/torrent.torrent",
                cookie="session=abc123",
            )

            assert result is True
            # Verify cookie was passed
            call_kwargs = mock_client.torrents_add.call_args.kwargs
            assert call_kwargs.get("cookie") == "session=abc123"

    def test_add_torrent_by_url_invalid_url(self, monkeypatch):
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            from src.qbittorrent import TorrentAddError

            with pytest.raises(TorrentAddError):
                manager.add_torrent_by_url("ftp://invalid.com/file.torrent")

    def test_add_torrent_by_url_empty_string(self, monkeypatch):
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            from src.qbittorrent import TorrentAddError

            with pytest.raises(TorrentAddError, match="URL cannot be empty"):
                manager.add_torrent_by_url("")

    def test_add_torrent_by_url_malformed_magnet(self, monkeypatch):
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            # Simulate that qBittorrent returns "Fails." for malformed magnet
            mock_client.torrents_add.return_value = "Fails."
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            # Should return False for failed torrent add
            result = manager.add_torrent_by_url("magnet:?xt=urn:btih:")
            assert result is False


class TestQbittorrentClient:
    def test_get_client_success(self, monkeypatch):
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client_class.return_value = mock_client

            client = get_client()

            assert client is mock_client
            mock_client_class.assert_called_once()

    def test_get_client_missing_env(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(
                ValueError, match="QBITTORRENT_URL, QBITTORRENT_USERNAME, and QBITTORRENT_PASSWORD must be set"
            ),
        ):
            get_client()

    def test_add_torrent_success(self, monkeypatch):
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_add.return_value = "Ok."
            mock_client_class.return_value = mock_client

            result = add_torrent({"url": "http://example.com/test.torrent"})

            assert result is True

    def test_add_torrent_no_url(self, monkeypatch):
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        result = add_torrent({})
        assert result is False

    def test_add_torrent_file_with_cookie_success(self, monkeypatch):
        """Test adding torrent with cookie using the native library support."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_add.return_value = "Ok."
            mock_client_class.return_value = mock_client

            result = add_torrent_file_with_cookie(
                download_url="http://example.com/test.torrent",
                name="Test Torrent",
                cookie="session=abc123",
                category="audiobooks",
            )

            assert result is True
            # Verify the cookie was passed to torrents_add
            call_kwargs = mock_client.torrents_add.call_args.kwargs
            assert call_kwargs.get("cookie") == "session=abc123"
            assert call_kwargs.get("category") == "audiobooks"

    def test_add_torrent_file_invalid_url(self, monkeypatch):
        """Test that invalid URLs are rejected."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        # Empty URL - should return False since the function catches exceptions
        result = add_torrent_file_with_cookie(download_url="", name="No URL")
        assert result is False

        # Unsupported scheme
        result = add_torrent_file_with_cookie(download_url="ftp://example.com/file.torrent", name="FTP")
        assert result is False


class TestQbittorrentSession:
    def test_context_manager_cleanup(self, monkeypatch):
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client_class.return_value = mock_client

            with qbittorrent_session() as manager:
                _ = manager.client
                assert manager._client is not None

            # After context exit, auth_log_out should have been called
            mock_client.auth_log_out.assert_called_once()
