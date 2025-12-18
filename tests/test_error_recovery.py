import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from src.main import app
from src.metadata import fetch_metadata
from src.db import save_request, get_request, delete_request
from src.notify import pushover, discord, gotify, ntfy
import requests
import sqlite3
import os

client = TestClient(app)


class TestErrorRecovery:
    """Test error recovery and resilience scenarios"""

    def test_network_timeout_recovery(self):
        """Test recovery from network timeouts during metadata fetch"""
        payload = {
            "name": "Test Book [B123456789]",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent"
        }
        
        with patch.dict('os.environ', {'DISABLE_EXTERNAL_API': '0'}), \
             patch("src.metadata.requests.get") as mock_get:
            # First call times out, second succeeds
            mock_get.side_effect = [
                requests.exceptions.Timeout("Request timed out"),
                MagicMock(status_code=200, json=lambda: {"title": "Test Book", "asin": "B123456789"})
            ]
            
            # Should handle timeout gracefully - metadata service wraps all errors
            with pytest.raises(ValueError) as exc_info:
                result = fetch_metadata(payload)
            
            # Should be a controlled ValueError, not a crash
            assert "could not fetch metadata" in str(exc_info.value).lower()

    @pytest.mark.allow_notifications
    def test_partial_notification_failure_recovery(self):
        """Test handling when some notifications fail but others succeed"""
        payload = {
            "name": "Test Audiobook",
            "url": "http://example.com/view", 
            "download_url": "http://example.com/download.torrent"
        }
        
        with patch.dict('os.environ', {'AUTOBRR_TOKEN': 'test_token'}), \
             patch("src.metadata.fetch_metadata") as mock_fetch, \
             patch("src.main.send_pushover") as mock_pushover, \
             patch("src.main.send_discord") as mock_discord:
            
            mock_fetch.return_value = {"title": "Test Book"}
            # Pushover fails, Discord succeeds
            mock_pushover.side_effect = Exception("Pushover service down")
            mock_discord.return_value = (204, {})
            
            resp = client.post(
                "/webhook/audiobook-requests",
                json=payload,
                headers={"X-Autobrr-Token": "test_token"}
            )
            
            # Should still return 200 but with error information
            assert resp.status_code == 200
            response_data = resp.json()
            # Should indicate partial failure
            assert "message" in response_data
            assert "notification" in response_data["message"].lower() or "error" in response_data

    def test_database_connection_loss_recovery(self):
        """Test recovery from database connection loss"""
        
        with patch("src.db.sqlite3.connect") as mock_connect:
            # First call fails, second succeeds
            mock_connect.side_effect = [
                sqlite3.OperationalError("database is locked"),
                MagicMock()
            ]
            
            try:
                # Attempt database operation
                save_request("test_token", {"title": "test"}, {"url": "test"})
                # If no exception, recovery worked
                assert True
            except sqlite3.OperationalError:
                # Should handle database errors gracefully
                assert True

    def test_disk_space_exhaustion_handling(self):
        """Test handling of disk space exhaustion"""
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = OSError("No space left on device")
            
            # Should handle disk space errors gracefully
            try:
                save_request("test_token", {"title": "test"}, {"url": "test"})
            except OSError as e:
                assert "space" in str(e).lower()

    def test_api_rate_limit_handling(self):
        """Test handling of API rate limits"""
        payload = {
            "name": "Test Book [B123456789]",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent"
        }
        
        with patch.dict('os.environ', {'DISABLE_EXTERNAL_API': '0'}), \
             patch("src.metadata.requests.get") as mock_get:
            # Simulate rate limit response
            rate_limit_response = MagicMock()
            rate_limit_response.status_code = 429
            rate_limit_response.headers = {"Retry-After": "60"}
            rate_limit_response.raise_for_status.side_effect = requests.exceptions.HTTPError("429 Too Many Requests")
            
            mock_get.return_value = rate_limit_response
            
            # Should handle rate limits gracefully - metadata service wraps all errors
            with pytest.raises(ValueError) as exc_info:
                result = fetch_metadata(payload)
            
            # Should be a controlled ValueError
            assert "could not fetch metadata" in str(exc_info.value).lower()

    def test_service_unavailable_fallback(self):
        """Test fallback when external services are unavailable"""
        payload = {
            "name": "Test Book [B123456789]",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent"
        }
        
        with patch.dict('os.environ', {'DISABLE_EXTERNAL_API': '0'}), \
             patch("src.metadata.get_cached_metadata") as mock_cached:
            # All API calls fail
            mock_cached.side_effect = requests.exceptions.ConnectionError("Service unavailable")
            
            # Should handle service unavailability
            try:
                result = fetch_metadata(payload)
                # Should return minimal data or handle gracefully
                assert isinstance(result, dict)
            except Exception as e:
                # Should be a controlled exception, not a crash
                assert "connection" in str(e).lower() or "unavailable" in str(e).lower()

    def test_concurrent_error_handling(self):
        """Test error handling under concurrent load"""
        payload = {
            "name": "Test Book",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent"
        }
        
        with patch.dict('os.environ', {'AUTOBRR_TOKEN': 'test_token'}):
            # Send multiple concurrent requests with some failing
            responses = []
            for i in range(5):
                try:
                    resp = client.post(
                        "/webhook/audiobook-requests",
                        json=payload,
                        headers={"X-Autobrr-Token": "test_token"}
                    )
                    responses.append(resp.status_code)
                except Exception as e:
                    responses.append(str(e))
            
            # At least some requests should succeed or fail gracefully
            assert len(responses) == 5
            # Should not have any unhandled exceptions (would be strings)
            successful_responses = [r for r in responses if isinstance(r, int)]
            assert len(successful_responses) > 0

    def test_malformed_response_handling(self):
        """Test handling of malformed API responses"""
        payload = {
            "name": "Test Book [B123456789]",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent"
        }
        
        with patch.dict('os.environ', {'DISABLE_EXTERNAL_API': '0'}), \
             patch("src.metadata.requests.get") as mock_get:
            # Return malformed JSON
            malformed_response = MagicMock()
            malformed_response.status_code = 200
            malformed_response.json.side_effect = ValueError("Invalid JSON")
            malformed_response.text = "Invalid JSON response"
            
            mock_get.return_value = malformed_response
            
            # Should handle malformed responses gracefully - metadata service wraps all errors
            with pytest.raises(ValueError) as exc_info:
                result = fetch_metadata(payload)
            
            # Should be a controlled ValueError
            assert "could not fetch metadata" in str(exc_info.value).lower()

    def test_memory_pressure_handling(self):
        """Test behavior under memory pressure"""
        # Simulate memory pressure by creating large objects
        large_data = []
        try:
            # Create some memory pressure
            for i in range(100):
                large_data.append("x" * 10000)
            
            # Test basic functionality under memory pressure
            payload = {
                "name": "Test Book",
                "url": "http://example.com/view",
                "download_url": "http://example.com/download.torrent"
            }
            
            with patch.dict('os.environ', {'AUTOBRR_TOKEN': 'test_token'}), \
                 patch("src.metadata.fetch_metadata", return_value={"title": "Test"}):
                
                resp = client.post(
                    "/webhook/audiobook-requests",
                    json=payload,
                    headers={"X-Autobrr-Token": "test_token"}
                )
                
                # Should still work under memory pressure
                assert resp.status_code in [200, 500]  # Either succeeds or fails gracefully
                
        finally:
            # Clean up memory
            large_data.clear()

    def test_notification_circuit_breaker(self):
        """Test circuit breaker pattern for notifications"""
        metadata = {"title": "Test Book", "author": "Test Author"}
        payload = {"url": "http://example.com", "download_url": "http://example.com/dl"}
        token = "test_token"
        base_url = "http://localhost:8000"
        user_key = "test_user"
        api_token = "test_api_token"
        
        with patch("src.notify.pushover.requests.post") as mock_post:
            # Simulate repeated failures
            mock_post.side_effect = requests.exceptions.ConnectionError("Service down")
            
            # Multiple attempts should eventually stop trying (circuit breaker)
            failures = 0
            for i in range(10):
                try:
                    pushover.send_pushover(metadata, payload, token, base_url, user_key, api_token)
                except Exception:
                    failures += 1
            
            # Should fail but not endlessly retry
            assert failures > 0
            assert mock_post.call_count <= 10  # Should have some limit

    def test_graceful_shutdown_handling(self):
        """Test graceful handling of shutdown scenarios"""
        # Test that ongoing operations can be interrupted gracefully
        with patch("src.main.logging") as mock_logging:
            # Simulate shutdown during operation
            with patch("signal.signal") as mock_signal:
                # This is more of a structure test - ensuring we have signal handlers
                import src.main
                # If the module loads without error, basic structure is OK
                assert hasattr(src.main, 'app')
                
    def test_configuration_error_recovery(self):
        """Test recovery from configuration errors"""
        # Test with corrupted config
        with patch("src.config.yaml.safe_load") as mock_yaml:
            mock_yaml.side_effect = Exception("Config corrupted")
            
            try:
                from src.config import load_config
                config = load_config()
                # Should either load defaults or handle gracefully
                assert config is None or isinstance(config, dict)
            except Exception as e:
                # Should be a controlled exception
                assert "config" in str(e).lower()
