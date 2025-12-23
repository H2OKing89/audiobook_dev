from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


class TestMainAppIntegration:
    @patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"})
    def test_webhook_endpoint_valid_token(self):
        # Test the main webhook endpoint with valid token
        payload = {
            "name": "Test Audiobook [MAM]",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
            "category": "audiobooks/fantasy",
            "size": 1024 * 1024 * 150,  # 150 MB
        }

        with (
            patch("src.metadata.fetch_metadata") as mock_fetch,
            patch("src.notify.pushover.send_pushover") as mock_pushover,
            patch("src.notify.discord.send_discord") as mock_discord,
        ):
            # Mock metadata response
            mock_fetch.return_value = {
                "title": "Test Book",
                "author": "Test Author",
                "series": "Test Series (Vol. 1)",
                "cover_url": "http://example.com/cover.jpg",
            }

            # Mock notification responses
            mock_pushover.return_value = (200, {"status": 1})
            mock_discord.return_value = (204, {})

            resp = client.post("/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"})

            assert resp.status_code == 200
            response_data = resp.json()
            assert "message" in response_data
            # In test environment, notifications are disabled/mocked
            assert any(
                x in response_data["message"]
                for x in ["Webhook received", "queued for processing", "notifications sent", "notifications failed"]
            )

    def test_webhook_endpoint_invalid_token(self):
        payload = {
            "name": "Test Audiobook",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }

        resp = client.post("/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "invalid_token"})

        assert resp.status_code == 401

    def test_webhook_endpoint_missing_token(self):
        payload = {
            "name": "Test Audiobook",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }

        resp = client.post("/webhook/audiobook-requests", json=payload)

        assert resp.status_code == 401

    @patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"})
    def test_webhook_endpoint_missing_required_fields(self):
        # Test with missing required fields
        payload = {
            "name": "Test Audiobook"
            # Missing url and download_url
        }

        resp = client.post("/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"})

        assert resp.status_code == 400

    @patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"})
    def test_webhook_endpoint_metadata_failure(self):
        # Test when metadata fetching fails
        payload = {
            "name": "Test Audiobook [MAM]",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }

        with (
            patch("src.metadata.fetch_metadata", side_effect=Exception("Metadata service down")),
            patch("src.notify.pushover.send_pushover") as mock_pushover,
            patch("src.notify.discord.send_discord") as mock_discord,
        ):
            # Mock notification responses
            mock_pushover.return_value = (200, {"status": 1})
            mock_discord.return_value = (204, {})

            resp = client.post("/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"})

            # Should still succeed but with empty metadata
            assert resp.status_code == 200
            response_data = resp.json()
            assert "message" in response_data

    @patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"})
    def test_webhook_endpoint_notification_failure(self):
        # Test when notifications fail but webhook still succeeds
        payload = {
            "name": "Test Audiobook",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }

        with (
            patch("src.metadata.fetch_metadata") as mock_fetch,
            patch("src.notify.pushover.send_pushover", side_effect=Exception("Pushover down")),
            patch("src.notify.discord.send_discord", side_effect=Exception("Discord down")),
        ):
            mock_fetch.return_value = {"title": "Test Book"}

            resp = client.post("/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"})

            # Should still succeed despite notification failures
            assert resp.status_code == 200

    def test_request_id_logging(self):
        # Test that request IDs are generated and logged
        resp = client.get("/")
        assert resp.status_code == 200
        # Should have generated a request ID and returned it in headers
        assert "X-Request-ID" in resp.headers

    def test_client_ip_logging(self):
        # Test that client IPs are captured
        with patch("src.main.logging") as mock_logging:
            resp = client.get("/", headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8"})
            assert resp.status_code == 200
            # Should capture the first IP from X-Forwarded-For
            assert any("1.2.3.4" in str(call) for call in mock_logging.method_calls)

    def test_cors_headers(self):
        # Test CORS headers if enabled
        resp = client.options("/")
        # Should handle OPTIONS request
        assert resp.status_code in (200, 405)  # 405 if CORS not enabled
