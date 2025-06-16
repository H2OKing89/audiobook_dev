import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.main import app
from src.db import save_request, delete_request

client = TestClient(app)


class TestWebUIEndpoints:
    def test_homepage_content(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Audiobook" in resp.text
        assert "Welcome" in resp.text
        # Check for meta tags
        assert "og:title" in resp.text
        assert "twitter:card" in resp.text

    def test_approve_page_valid_token(self):
        # Create a test token with metadata
        token = "test_token_123"
        metadata = {"title": "Test Book", "author": "Test Author"}
        payload = {"url": "http://test.com", "download_url": "http://test.com/download"}
        save_request(token, metadata, payload)
        
        try:
            resp = client.get(f"/approve/{token}")
            assert resp.status_code == 200
            assert "Test Book" in resp.text
            assert "Test Author" in resp.text
        finally:
            delete_request(token)

    def test_approve_page_invalid_token(self):
        resp = client.get("/approve/nonexistent_token")
        assert resp.status_code in (401, 410, 404)
        assert "expired" in resp.text.lower() or "unauthorized" in resp.text.lower() or "not found" in resp.text.lower()

    def test_approve_action_valid_token(self):
        # Create a test token
        token = "test_action_token"
        metadata = {"title": "Action Test"}
        payload = {"url": "http://test.com", "download_url": "http://test.com/download"}
        save_request(token, metadata, payload)
        
        try:
            with patch("src.qbittorrent.add_torrent_file_with_cookie") as mock_add, \
                 patch("src.notify.pushover.send_pushover") as mock_pushover, \
                 patch("src.notify.discord.send_discord") as mock_discord:
                mock_add.return_value = True
                mock_pushover.return_value = (200, {"status": 1})
                mock_discord.return_value = (204, {})
                
                resp = client.get(f"/approve/{token}/action")
                assert resp.status_code == 200
                assert "successful" in resp.text.lower() or "approved" in resp.text.lower()
        finally:
            delete_request(token)

    def test_reject_valid_token(self):
        # Create a test token
        token = "test_reject_token"
        metadata = {"title": "Reject Test"}
        payload = {"url": "http://test.com", "download_url": "http://test.com/download"}
        save_request(token, metadata, payload)
        
        try:
            resp = client.get(f"/reject/{token}")
            assert resp.status_code == 200
            assert "reject" in resp.text.lower()
        finally:
            delete_request(token)

    def test_reject_invalid_token(self):
        resp = client.get("/reject/nonexistent_token")
        assert resp.status_code in (401, 410, 404)

    def test_approve_action_qbittorrent_failure(self):
        # Test when qBittorrent fails
        token = "test_fail_token"
        metadata = {"title": "Fail Test"}
        payload = {"url": "http://test.com", "download_url": "http://test.com/download"}
        save_request(token, metadata, payload)
        
        try:
            with patch("src.qbittorrent.add_torrent_file_with_cookie", return_value=False):
                resp = client.get(f"/approve/{token}/action")
                # Should still return success page but log the error
                assert resp.status_code == 200
        finally:
            delete_request(token)

    def test_metadata_formatting_in_approval_page(self):
        # Test that metadata is properly formatted and escaped
        token = "test_format_token"
        metadata = {
            "title": "Test <b>Title</b>",
            "author": "Author & Co.",
            "series": "Series (Vol. 1)",
            "release_date": "2020-01-01T00:00:00Z",
            "size": 1024 * 1024 * 100  # 100 MB
        }
        payload = {"url": "http://test.com", "download_url": "http://test.com/download"}
        save_request(token, metadata, payload)
        
        try:
            resp = client.get(f"/approve/{token}")
            assert resp.status_code == 200
            # HTML should be escaped
            assert "&lt;b&gt;" in resp.text or "Test Title" in resp.text  # HTML escaped or stripped
            assert "Author &amp; Co." in resp.text or "Author & Co." in resp.text
            # Date should be formatted to YYYY-MM-DD
            assert "2020-01-01" in resp.text
        finally:
            delete_request(token)

    def test_token_expiry_handling(self, monkeypatch):
        # Test expired token handling
        import time
        import src.db as dbmod
        
        token = "test_expire_token"
        metadata = {"title": "Expire Test"}
        payload = {"url": "http://test.com", "download_url": "http://test.com/download"}
        save_request(token, metadata, payload)
        
        # Mock time to simulate expiry
        old_time = time.time
        dbmod.TTL = 1
        monkeypatch.setattr(time, "time", lambda: old_time() + 3600)
        
        try:
            resp = client.get(f"/approve/{token}")
            assert resp.status_code in (401, 410, 404)
            assert "expired" in resp.text.lower() or "not found" in resp.text.lower()
        finally:
            monkeypatch.setattr(time, "time", old_time)
            delete_request(token)
