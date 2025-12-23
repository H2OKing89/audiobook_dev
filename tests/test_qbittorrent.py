import os
from unittest.mock import MagicMock, mock_open, patch

import httpx
import pytest

from src.qbittorrent import add_torrent, add_torrent_file_with_cookie, get_client


class TestQbittorrentClient:
    def test_get_client_success(self, monkeypatch):
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.Client") as mock_client:
            get_client()
            mock_client.assert_called_once_with(host="http://localhost:8080", username="admin", password="password")

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

        with patch("src.qbittorrent.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.torrents_add.return_value = "OK"

            result = add_torrent({"url": "http://example.com/test.torrent"})

            assert result is True
            mock_client.torrents_add.assert_called_once_with(urls="http://example.com/test.torrent")

    def test_add_torrent_failure(self, monkeypatch):
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with patch("src.qbittorrent.get_client", side_effect=Exception("Connection failed")):
            result = add_torrent({"url": "http://example.com/test.torrent"})
            assert result is False

    def test_add_torrent_file_with_cookie_success(self, monkeypatch):
        monkeypatch.setenv("QBITTORRENT_URL", "http://localhost:8080")
        monkeypatch.setenv("QBITTORRENT_USERNAME", "admin")
        monkeypatch.setenv("QBITTORRENT_PASSWORD", "password")

        with (
            patch("src.qbittorrent.httpx.stream") as mock_stream,
            patch("src.qbittorrent.get_client") as mock_get_client,
            patch("src.qbittorrent.tempfile.NamedTemporaryFile") as mock_temp,
            patch("builtins.open", mock_open(read_data=b"torrent_data")),
            patch("src.qbittorrent.os.remove"),
        ):
            # Mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.iter_bytes.return_value = [b"torrent_data"]
            mock_stream.return_value.__enter__.return_value = mock_response

            # Mock temp file
            mock_temp_file = MagicMock()
            mock_temp_file.name = "/tmp/test.torrent"
            mock_temp.return_value = mock_temp_file

            # Mock qBittorrent client
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.torrents_add.return_value = "OK"

            result = add_torrent_file_with_cookie(
                download_url="http://example.com/test.torrent", name="Test Torrent", cookie="session=abc123"
            )

            assert result is True
            mock_client.auth_log_in.assert_called_once()
            mock_client.torrents_add.assert_called_once()

    def test_add_torrent_file_network_error(self):
        with patch("src.qbittorrent.httpx.stream", side_effect=httpx.RequestError("Network error")):
            result = add_torrent_file_with_cookie(download_url="http://example.com/test.torrent", name="Test Torrent")
            assert result is False

    def test_add_torrent_file_invalid_url(self):
        # Empty URL
        result = add_torrent_file_with_cookie(download_url="", name="No URL")
        assert result is False

        # Unsupported scheme
        result = add_torrent_file_with_cookie(download_url="ftp://example.com/file.torrent", name="FTP")
        assert result is False

        # Malformed URL
        result = add_torrent_file_with_cookie(download_url="not a url", name="Bad")
        assert result is False
