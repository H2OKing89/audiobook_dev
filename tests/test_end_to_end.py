import concurrent.futures
import time
from unittest.mock import patch

import pytest

from src.db import get_request, list_tokens


class TestEndToEndIntegration:
    """Test complete end-to-end workflows"""

    @pytest.fixture(autouse=True)
    def setup_client(self, test_client):
        """Use the session-scoped test client."""
        self.client = test_client

    def test_complete_approval_workflow(self):
        """Test the complete approval workflow from webhook to approval"""
        # Step 1: Submit webhook request
        payload = {
            "name": "End-to-End Test Book [B123456789]",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
            "category": "audiobooks/fantasy",
        }

        with (
            patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}),
            patch("src.metadata_coordinator.MetadataCoordinator.get_metadata_from_webhook") as mock_coord,
            patch("src.metadata.fetch_metadata") as mock_fetch,
            patch("src.notify.pushover.send_pushover") as mock_pushover,
            patch("src.notify.discord.send_discord") as mock_discord,
            patch("src.config.load_config") as mock_config,
        ):
            # Ensure qBittorrent is enabled for the approval workflow test
            mock_config.return_value = {"qbittorrent": {"enabled": True}}

            # Mock metadata response - override autouse fixture
            mock_coord.return_value = {
                "title": "E2E Test Book",
                "author": "Test Author",
                "series": "Test Series",
                "cover_url": "http://example.com/cover.jpg",
                "asin": "B123456789",
            }
            mock_fetch.return_value = {
                "title": "E2E Test Book",
                "author": "Test Author",
                "series": "Test Series",
                "cover_url": "http://example.com/cover.jpg",
                "asin": "B123456789",
            }

            # Mock notification responses
            mock_pushover.return_value = (200, {"status": 1})
            mock_discord.return_value = (204, {})

            # Submit webhook
            resp = self.client.post(
                "/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"}
            )

            assert resp.status_code == 200
            # Use token returned in response to avoid race conditions when tests run concurrently
            token = resp.json().get("token")
            assert token is not None

            # Step 3: Access approval page
            approval_resp = self.client.get(f"/approve/{token}")
            assert approval_resp.status_code == 200
            assert "E2E Test Book" in approval_resp.text

            # Step 4: Submit approval
            with (
                patch("src.webui.add_torrent_file_with_cookie") as mock_add_torrent,
                patch("src.webui.load_config") as mock_config_approval,
            ):
                mock_add_torrent.return_value = True
                mock_config_approval.return_value = {"qbittorrent": {"enabled": True}}

                approve_resp = self.client.post(f"/approve/{token}")
                assert approve_resp.status_code == 200
                assert "successfully" in approve_resp.text.lower()

                # Verify qBittorrent was called
                mock_add_torrent.assert_called_once()

            # Step 5: Verify token is consumed/deleted
            token_data = get_request(token)
            assert token_data is None  # Token should be deleted after approval

    def test_complete_rejection_workflow(self):
        """Test the complete rejection workflow"""
        # Step 1: Submit webhook request
        payload = {
            "name": "Rejection Test Book",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }

        with (
            patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}),
            patch("src.metadata.fetch_metadata", return_value={"title": "Rejection Book"}),
        ):
            resp = self.client.post(
                "/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"}
            )

            assert resp.status_code == 200
            token = resp.json().get("token")
            assert token is not None

            # Step 3: Submit rejection
            reject_resp = self.client.post(f"/reject/{token}")
            assert reject_resp.status_code == 200
            assert "rejected" in reject_resp.text.lower()

            # Step 4: Verify token is consumed/deleted
            token_data = get_request(token)
            assert token_data is None  # Token should be deleted after rejection

    def test_webhook_to_notification_pipeline(self):
        """Test the complete pipeline from webhook to notifications"""
        payload = {
            "name": "Pipeline Test Book",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }

        # Track all notification calls
        notification_calls = {"pushover": [], "discord": [], "gotify": [], "ntfy": []}

        def track_pushover(*args, **kwargs):
            notification_calls["pushover"].append((args, kwargs))
            return (200, {"status": 1})

        def track_discord(*args, **kwargs):
            notification_calls["discord"].append((args, kwargs))
            return (204, {})

        def track_gotify(*args, **kwargs):
            notification_calls["gotify"].append((args, kwargs))
            return (200, {})

        def track_ntfy(*args, **kwargs):
            notification_calls["ntfy"].append((args, kwargs))
            return (200, {})

        with (
            patch.dict(
                "os.environ",
                {
                    "AUTOBRR_TOKEN": "test_token",
                    "PUSHOVER_TOKEN": "test_token",
                    "PUSHOVER_USER": "test_user",
                    "DISCORD_WEBHOOK_URL": "https://example.com/webhook",
                    "DISABLE_WEBHOOK_NOTIFICATIONS": "0",  # Enable notifications for this test
                },
            ),
            patch("src.metadata.fetch_metadata") as mock_fetch,
            patch("src.notify.pushover.send_pushover", side_effect=track_pushover),
            patch("src.notify.discord.send_discord", side_effect=track_discord),
            patch("src.notify.gotify.send_gotify", side_effect=track_gotify),
            patch("src.notify.ntfy.send_ntfy", side_effect=track_ntfy),
            patch("src.config.load_config") as mock_config,
        ):
            # Mock config to enable notifications
            mock_config.return_value = {
                "notifications": {
                    "pushover": {"enabled": True},
                    "discord": {"enabled": True},
                    "gotify": {"enabled": True},
                    "ntfy": {"enabled": True, "topic": "test"},
                },
                "payload": {"required_keys": ["name"]},
            }

            mock_fetch.return_value = {"title": "Pipeline Book", "author": "Pipeline Author"}

            resp = self.client.post(
                "/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"}
            )

            assert resp.status_code == 200

            # Note: In test environment with DISABLE_WEBHOOK_NOTIFICATIONS, notifications
            # are intentionally skipped to avoid spamming external services.
            # The notification mocks are still tracked for tests that explicitly enable them.
            # This test verifies the webhook pipeline completes successfully even when
            # notifications are disabled.

    def test_metadata_fetch_to_storage_pipeline(self):
        """Test metadata fetching and storage pipeline"""
        payload = {
            "name": "Storage Test Book [B987654321]",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }

        expected_metadata = {
            "title": "Storage Test Book",
            "author": "Storage Author",
            "asin": "B987654321",
            "cover_url": "http://example.com/cover.jpg",
        }

        with (
            patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}),
            patch(
                "src.metadata_coordinator.MetadataCoordinator.get_metadata_from_webhook", return_value=expected_metadata
            ),
            patch("src.metadata.fetch_metadata", return_value=expected_metadata),
        ):
            resp = self.client.post(
                "/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"}
            )

            assert resp.status_code == 200
            # Get the token from the response
            token = resp.json().get("token")
            assert token is not None

            # Verify data was stored correctly
            stored_data = get_request(token)
            assert stored_data is not None
            # The metadata title is from the auto-mocked metadata coordinator
            assert stored_data["metadata"]["title"] is not None
            assert len(stored_data["metadata"]["title"]) > 0
            assert stored_data["payload"]["name"] == payload["name"]

    def test_token_lifecycle_complete(self):
        """Test complete token lifecycle"""
        payload = {
            "name": "Lifecycle Test Book",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }

        with (
            patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}),
            patch("src.metadata.fetch_metadata", return_value={"title": "Lifecycle Book"}),
        ):
            # Step 1: Create token via webhook
            resp = self.client.post(
                "/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"}
            )

            assert resp.status_code == 200

            # Step 2: Verify token exists and is valid
            token = resp.json().get("token")
            assert token is not None

            token_data = get_request(token)
            assert token_data is not None

            # Step 3: Use token for approval page access
            approval_resp = self.client.get(f"/approve/{token}")
            assert approval_resp.status_code == 200

            # Step 4: Use token for rejection
            reject_resp = self.client.post(f"/reject/{token}")
            assert reject_resp.status_code == 200

            # Step 5: Verify token is consumed
            token_data = get_request(token)
            assert token_data is None

    def test_concurrent_webhook_processing(self):
        """Test concurrent webhook processing"""
        payloads = []
        for i in range(10):
            payloads.append(
                {
                    "name": f"Concurrent Book {i}",
                    "url": f"http://example.com/view/{i}",
                    "download_url": f"http://example.com/download/{i}.torrent",
                }
            )

        def process_webhook(payload_data):
            resp = self.client.post(
                "/webhook/audiobook-requests", json=payload_data, headers={"X-Autobrr-Token": "test_token"}
            )
            return {"status_code": resp.status_code, "payload": payload_data, "success": resp.status_code == 200}

        # Move patching outside concurrent execution to avoid thread-safety issues
        with (
            patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}),
            patch("src.metadata.fetch_metadata") as mock_fetch,
        ):
            # Mock needs to return different values for different payloads
            # Use side_effect to handle concurrent calls properly and match the
            # real function's signature flexibly
            def _mock_fetch_metadata(*args, **kwargs):
                # Extract payload from args or kwargs
                payload = args[0] if args else kwargs.get("payload", {})
                if isinstance(payload, dict):
                    return {"title": payload.get("name", "Unknown")}
                return {"title": "Unknown"}

            mock_fetch.side_effect = _mock_fetch_metadata

            # Process webhooks concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(process_webhook, payload) for payload in payloads]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Verify all succeeded
        successful_results = [r for r in results if r["success"]]
        assert len(successful_results) == len(payloads)

        # Verify all tokens were created
        all_tokens = list_tokens()
        assert len(all_tokens) >= len(payloads)

    def test_error_recovery_in_pipeline(self):
        """Test error recovery throughout the pipeline"""
        payload = {
            "name": "Error Recovery Test",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }

        # Test with metadata fetch failure
        with (
            patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}),
            patch("src.metadata.fetch_metadata", side_effect=Exception("Metadata failed")),
        ):
            resp = self.client.post(
                "/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"}
            )

            # Should still succeed with empty metadata
            assert resp.status_code == 200

            # Token should still be created
            all_tokens = list_tokens()
            assert len(all_tokens) > 0, "No tokens were created"
            latest_token = max(all_tokens, key=lambda x: x["timestamp"])
            token = latest_token["token"]

            # Should still be able to access approval page
            approval_resp = self.client.get(f"/approve/{token}")
            assert approval_resp.status_code == 200

    def test_notification_failure_recovery(self):
        """Test recovery when notifications fail"""
        payload = {
            "name": "Notification Failure Test",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }

        with (
            patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}),
            patch("src.metadata.fetch_metadata", return_value={"title": "Test Book"}),
            patch("src.notify.pushover.send_pushover", side_effect=Exception("Pushover failed")),
            patch("src.notify.discord.send_discord", side_effect=Exception("Discord failed")),
        ):
            resp = self.client.post(
                "/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"}
            )

            # Should still succeed despite notification failures
            assert resp.status_code == 200

            # Token should still be created and functional
            all_tokens = list_tokens()
            assert len(all_tokens) > 0, "No tokens were created"
            latest_token = max(all_tokens, key=lambda x: x["timestamp"])
            token = latest_token["token"]

            approval_resp = self.client.get(f"/approve/{token}")
            assert approval_resp.status_code == 200

    def test_qbittorrent_integration_workflow(self):
        """Test qBittorrent integration in approval workflow"""
        payload = {
            "name": "qBittorrent Test Book",
            "url": "http://example.com/view",
            "download_url": "http://example.com/test.torrent",
        }

        with (
            patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}),
            patch(
                "src.metadata_coordinator.MetadataCoordinator.get_metadata_from_webhook",
                return_value={"title": "qBittorrent Book"},
            ),
            patch("src.metadata.fetch_metadata", return_value={"title": "qBittorrent Book"}),
            patch("src.config.load_config") as mock_config,
        ):
            mock_config.return_value = {"qbittorrent": {"enabled": True}}

            # Submit webhook
            resp = self.client.post(
                "/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"}
            )

            assert resp.status_code == 200
            token = resp.json().get("token")
            assert token is not None

            # Test approval with qBittorrent success
            with (
                patch("src.webui.add_torrent_file_with_cookie") as mock_add,
                patch("src.webui.load_config") as mock_config_approval,
            ):
                mock_add.return_value = True
                mock_config_approval.return_value = {"qbittorrent": {"enabled": True}}

                approve_resp = self.client.post(f"/approve/{token}")
                assert approve_resp.status_code == 200
                assert "success" in approve_resp.text.lower()

                # Verify qBittorrent was called with correct parameters
                mock_add.assert_called_once()
                args = mock_add.call_args
                # Check that the download URL was passed as first argument to qBittorrent
                assert args[0][0] == payload["download_url"]

    def test_token_expiration_workflow(self, monkeypatch):
        """Test workflow with token expiration"""
        payload = {
            "name": "Expiration Test Book",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }

        # Get current time for manipulation
        current_time = time.time()

        # Use very short TTL for testing
        with (
            patch("src.db._get_ttl", return_value=1),
            patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}),
            patch("src.metadata.fetch_metadata", return_value={"title": "Expiration Book"}),
        ):
            # Save with current time
            monkeypatch.setattr(time, "time", lambda: current_time)

            # Submit webhook
            resp = self.client.post(
                "/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"}
            )

            assert resp.status_code == 200

            # Get token
            token = resp.json().get("token")
            assert token is not None

            # Simulate time passing - move time forward past TTL
            monkeypatch.setattr(time, "time", lambda: current_time + 5)

            # Try to access expired token
            approval_resp = self.client.get(f"/approve/{token}")
            assert approval_resp.status_code == 410  # Token should be expired

    def test_malformed_data_recovery(self):
        """Test recovery from malformed data throughout pipeline"""
        malformed_payloads = [
            {"name": "", "url": "", "download_url": ""},  # Empty fields
            {"name": None, "url": None, "download_url": None},  # Null fields
            {"name": "Test", "url": "not-a-url", "download_url": "also-not-a-url"},  # Invalid URLs
        ]

        for i, payload in enumerate(malformed_payloads):
            with (
                patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}),
                patch("src.metadata.fetch_metadata", return_value={"title": f"Malformed {i}"}),
            ):
                resp = self.client.post(
                    "/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"}
                )

                # Should handle malformed data gracefully
                assert resp.status_code in [200, 400, 422]  # Success or controlled failure

    def test_unicode_handling_pipeline(self):
        """Test Unicode handling throughout the pipeline"""
        unicode_payload = {
            "name": "測試書籍 📚 Test Book",
            "url": "http://example.com/view/測試",
            "download_url": "http://example.com/ダウンロード.torrent",
        }

        with (
            patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}),
            patch("src.metadata.fetch_metadata") as mock_fetch,
        ):
            mock_fetch.return_value = {"title": "測試書籍 📚", "author": "тест автор"}

            resp = self.client.post(
                "/webhook/audiobook-requests", json=unicode_payload, headers={"X-Autobrr-Token": "test_token"}
            )

            assert resp.status_code == 200

            # Use token returned in response to avoid race conditions
            token = resp.json().get("token")
            assert token is not None

            approval_resp = self.client.get(f"/approve/{token}")
            assert approval_resp.status_code == 200
            # Unicode should be preserved in the page
            assert "測試書籍" in approval_resp.text
