"""Additional tests to achieve 100% coverage for qbittorrent module."""

from unittest.mock import MagicMock, patch

import pytest
from qbittorrentapi.exceptions import (
    APIConnectionError,
    Conflict409Error,
    LoginFailed,
    NotFound404Error,
    UnsupportedMediaType415Error,
)

from src.qbittorrent import (
    QBittorrentAuthError,
    QBittorrentConfig,
    QBittorrentConnectionError,
    QBittorrentManager,
    TorrentAddError,
    add_torrent,
    add_torrent_file_with_cookie,
    get_client,
)


class TestReconfigureManager:
    """Test reconfiguration scenarios."""

    def test_reconfigure_with_existing_client(self, monkeypatch):
        """Test reconfiguring manager when client already exists."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()
            # Access client to initialize it
            _ = manager.client
            assert manager._client is not None

            # Now reconfigure - should call disconnect
            new_config = QBittorrentConfig(
                host="http://newhost:8080",
                username="newuser",
                password="newpass",
            )
            manager.configure(new_config)

            # Client should be reset
            assert manager._client is None


class TestClientExceptionHandling:
    """Test exception handling during client initialization."""

    def test_client_login_failed(self, monkeypatch):
        """Test handling of LoginFailed exception."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "wrongpass")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client_class.side_effect = LoginFailed("Login failed")

            manager = QBittorrentManager()

            with pytest.raises(QBittorrentAuthError, match="Authentication failed"):
                _ = manager.client

    def test_client_connection_error(self, monkeypatch):
        """Test handling of APIConnectionError exception."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client_class.side_effect = APIConnectionError("Connection failed")

            manager = QBittorrentManager()

            with pytest.raises(QBittorrentConnectionError, match="Connection failed"):
                _ = manager.client

    def test_client_unexpected_error(self, monkeypatch):
        """Test handling of unexpected exceptions during client creation."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client_class.side_effect = RuntimeError("Unexpected error")

            manager = QBittorrentManager()

            with pytest.raises(QBittorrentConnectionError, match="Unexpected error"):
                _ = manager.client


class TestDisconnectEdgeCases:
    """Test disconnect method edge cases."""

    def test_disconnect_with_exception(self, monkeypatch):
        """Test disconnect when auth_log_out raises an exception."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.auth_log_out.side_effect = RuntimeError("Logout failed")
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()
            _ = manager.client

            # Should not raise, but log the error
            manager.disconnect()

            # Client should still be None after disconnect
            assert manager._client is None


class TestAddTorrentByUrlEdgeCases:
    """Test add_torrent_by_url edge cases."""

    def test_torrent_already_exists(self, monkeypatch):
        """Test handling of Conflict409Error (torrent already exists)."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_add.side_effect = Conflict409Error("Torrent already exists")
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            # Should return True when torrent already exists
            result = manager.add_torrent_by_url("magnet:?xt=urn:btih:abc123")
            assert result is True

    def test_unsupported_media_type(self, monkeypatch):
        """Test handling of UnsupportedMediaType415Error."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_add.side_effect = UnsupportedMediaType415Error("Invalid file")
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            with pytest.raises(TorrentAddError, match="Invalid torrent URL or file"):
                manager.add_torrent_by_url("http://example.com/bad.torrent")

    def test_login_failed_during_add(self, monkeypatch):
        """Test handling of LoginFailed during torrent add."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_add.side_effect = LoginFailed("Session expired")
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            with pytest.raises(QBittorrentAuthError, match="Authentication failed"):
                manager.add_torrent_by_url("magnet:?xt=urn:btih:abc123")

            # Client should be reset
            assert manager._client is None

    def test_api_connection_error_during_add(self, monkeypatch):
        """Test handling of APIConnectionError during torrent add."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_add.side_effect = APIConnectionError("Connection lost")
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            with pytest.raises(QBittorrentConnectionError, match="Connection error"):
                manager.add_torrent_by_url("magnet:?xt=urn:btih:abc123")

    def test_unknown_string_response(self, monkeypatch):
        """Test handling of unknown string response."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            # Return an unknown string response
            mock_client.torrents_add.return_value = "Unknown response"
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            # Should return True for unknown responses (assume success)
            result = manager.add_torrent_by_url("magnet:?xt=urn:btih:abc123")
            assert result is True

    def test_metadata_response_with_hash(self, monkeypatch):
        """Test handling of TorrentsAddedMetadata response with hash."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            # Return a metadata object with hash
            metadata = MagicMock()
            metadata.hash = "abc123"
            mock_client.torrents_add.return_value = metadata
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            result = manager.add_torrent_by_url("magnet:?xt=urn:btih:abc123")
            assert result is True

    def test_metadata_response_without_hash(self, monkeypatch):
        """Test handling of TorrentsAddedMetadata response without hash."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            # Return a metadata object without hash
            metadata = MagicMock(spec=[])  # No hash attribute
            mock_client.torrents_add.return_value = metadata
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            # Should still return True (benefit of doubt)
            result = manager.add_torrent_by_url("magnet:?xt=urn:btih:abc123")
            assert result is True


class TestAddTorrentFile:
    """Test add_torrent_file method."""

    def test_file_not_found(self, monkeypatch):
        """Test adding a torrent file that doesn't exist."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        manager = QBittorrentManager()

        with pytest.raises(TorrentAddError, match="Torrent file not found"):
            manager.add_torrent_file("/nonexistent/file.torrent")

    def test_path_not_a_file(self, monkeypatch, tmp_path):
        """Test adding a torrent file that is actually a directory."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        # Create a directory instead of a file
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        manager = QBittorrentManager()

        with pytest.raises(TorrentAddError, match="Path is not a file"):
            manager.add_torrent_file(test_dir)

    def test_add_torrent_file_success(self, monkeypatch, tmp_path):
        """Test successfully adding a torrent file."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        # Create a temporary torrent file
        torrent_file = tmp_path / "test.torrent"
        torrent_file.write_text("fake torrent data")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_add.return_value = "Ok."
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            result = manager.add_torrent_file(torrent_file)
            assert result is True

    def test_add_torrent_file_failed_response(self, monkeypatch, tmp_path):
        """Test adding a torrent file with failed response."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        torrent_file = tmp_path / "test.torrent"
        torrent_file.write_text("fake torrent data")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            # Return a failed response
            mock_client.torrents_add.return_value = "Failed"
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            result = manager.add_torrent_file(torrent_file)
            assert result is False

    def test_add_torrent_file_conflict(self, monkeypatch, tmp_path):
        """Test adding a torrent file that already exists."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        torrent_file = tmp_path / "test.torrent"
        torrent_file.write_text("fake torrent data")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_add.side_effect = Conflict409Error("Already exists")
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            result = manager.add_torrent_file(torrent_file)
            assert result is True

    def test_add_torrent_file_unsupported_media_type(self, monkeypatch, tmp_path):
        """Test adding an invalid torrent file."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        torrent_file = tmp_path / "invalid.torrent"
        torrent_file.write_text("invalid data")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_add.side_effect = UnsupportedMediaType415Error("Invalid")
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            with pytest.raises(TorrentAddError, match="Invalid torrent file"):
                manager.add_torrent_file(torrent_file)

    def test_add_torrent_file_login_failed(self, monkeypatch, tmp_path):
        """Test adding a torrent file when login fails."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        torrent_file = tmp_path / "test.torrent"
        torrent_file.write_text("fake torrent data")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_add.side_effect = LoginFailed("Session expired")
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            with pytest.raises(QBittorrentAuthError):
                manager.add_torrent_file(torrent_file)

    def test_add_torrent_file_connection_error(self, monkeypatch, tmp_path):
        """Test adding a torrent file when connection fails."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        torrent_file = tmp_path / "test.torrent"
        torrent_file.write_text("fake torrent data")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_add.side_effect = APIConnectionError("Connection lost")
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            with pytest.raises(QBittorrentConnectionError):
                manager.add_torrent_file(torrent_file)

    def test_add_torrent_file_metadata_response(self, monkeypatch, tmp_path):
        """Test adding a torrent file with metadata response."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        torrent_file = tmp_path / "test.torrent"
        torrent_file.write_text("fake torrent data")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            # Return a metadata object with hash
            metadata = MagicMock()
            metadata.hash = "abc123def456"
            mock_client.torrents_add.return_value = metadata
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            result = manager.add_torrent_file(torrent_file)
            assert result is True


class TestGetTorrentInfo:
    """Test get_torrent_info method."""

    def test_get_torrent_info_found(self, monkeypatch):
        """Test getting info for an existing torrent."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_torrent = {"hash": "abc123", "name": "Test Torrent"}
            mock_client.torrents_info.return_value = [mock_torrent]
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            result = manager.get_torrent_info("abc123")
            assert result == mock_torrent

    def test_get_torrent_info_not_found(self, monkeypatch):
        """Test getting info for a non-existent torrent."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_info.return_value = []
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            result = manager.get_torrent_info("nonexistent")
            assert result is None

    def test_get_torrent_info_404_error(self, monkeypatch):
        """Test getting info when NotFound404Error is raised."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_info.side_effect = NotFound404Error("Not found")
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            result = manager.get_torrent_info("abc123")
            assert result is None

    def test_get_torrent_info_general_error(self, monkeypatch):
        """Test getting info when a general error occurs."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_info.side_effect = RuntimeError("Unexpected error")
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()

            result = manager.get_torrent_info("abc123")
            assert result is None


class TestIsConnected:
    """Test is_connected method."""

    def test_is_connected_with_client(self, monkeypatch):
        """Test is_connected when client is active."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()
            _ = manager.client  # Initialize client

            assert manager.is_connected() is True

    def test_is_connected_without_client(self):
        """Test is_connected when client is not initialized."""
        manager = QBittorrentManager()

        assert manager.is_connected() is False

    def test_is_connected_with_error(self, monkeypatch):
        """Test is_connected when app_version raises an error."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client_class.return_value = mock_client

            manager = QBittorrentManager()
            _ = manager.client  # Initialize client

            # Now make app_version fail
            mock_client.app_version.side_effect = RuntimeError("Connection lost")

            assert manager.is_connected() is False


class TestBackwardCompatibleFunctions:
    """Test backward compatible module-level functions."""

    def test_get_client_auth_error(self, monkeypatch):
        """Test get_client when authentication fails."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "wrong")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client_class.side_effect = LoginFailed("Login failed")

            with pytest.raises(ConnectionError, match="Authentication failed"):
                get_client()

    def test_get_client_connection_error(self, monkeypatch):
        """Test get_client when connection fails."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client_class.side_effect = APIConnectionError("Connection failed")

            with pytest.raises(ConnectionError, match="Connection failed"):
                get_client()

    def test_add_torrent_qbittorrent_error(self, monkeypatch):
        """Test add_torrent when qBittorrent error occurs."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_add.side_effect = UnsupportedMediaType415Error("Invalid")
            mock_client_class.return_value = mock_client

            result = add_torrent({"url": "http://example.com/bad.torrent"})
            assert result is False

    def test_add_torrent_unexpected_error(self, monkeypatch):
        """Test add_torrent when unexpected error occurs."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_add.side_effect = RuntimeError("Unexpected")
            mock_client_class.return_value = mock_client

            result = add_torrent({"url": "magnet:?xt=urn:btih:abc123"})
            assert result is False


class TestAddTorrentFileWithCookieEdgeCases:
    """Test add_torrent_file_with_cookie edge cases."""

    def test_empty_tags_string(self, monkeypatch):
        """Test handling of empty tags string."""
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
                name="Test",
                tags="",  # Empty string
            )
            assert result is True

    def test_tags_as_list(self, monkeypatch):
        """Test handling of tags as a list."""
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
                name="Test",
                tags=["tag1", "tag2"],  # List of tags
            )
            assert result is True

    def test_unrecognized_content_layout(self, monkeypatch):
        """Test handling of unrecognized contentLayout value."""
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
                name="Test",
                contentLayout="InvalidLayout",  # Unrecognized value
            )
            assert result is True

    def test_qbittorrent_error_in_add_file_with_cookie(self, monkeypatch):
        """Test QBittorrentError handling in add_torrent_file_with_cookie."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_add.side_effect = UnsupportedMediaType415Error("Invalid")
            mock_client_class.return_value = mock_client

            result = add_torrent_file_with_cookie(
                download_url="http://example.com/bad.torrent",
                name="Test",
            )
            assert result is False

    def test_unexpected_error_in_add_file_with_cookie(self, monkeypatch):
        """Test unexpected error handling in add_torrent_file_with_cookie."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client.torrents_add.side_effect = RuntimeError("Unexpected")
            mock_client_class.return_value = mock_client

            result = add_torrent_file_with_cookie(
                download_url="http://example.com/test.torrent",
                name="Test",
            )
            assert result is False


class TestContextManagerWithExceptions:
    """Test context manager with exceptions during execution."""

    def test_context_manager_with_exception_in_block(self, monkeypatch):
        """Test that context manager still cleans up when exception occurs in with block."""
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        from src.qbittorrent import qbittorrent_session

        with patch("src.qbittorrent.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.app_version.return_value = "4.5.0"
            mock_client_class.return_value = mock_client

            try:
                with qbittorrent_session() as manager:
                    _ = manager.client
                    raise RuntimeError("Test exception")
            except RuntimeError:
                pass

            # Should still call disconnect
            mock_client.auth_log_out.assert_called_once()
