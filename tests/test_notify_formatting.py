"""Tests for notification formatting - uses global httpx mock from conftest."""
import pytest

# Import modules to call notification functions
from src.notify import discord, gotify, ntfy, pushover

# Disable the autouse mock_notifications fixture since we need
# to test the actual notification formatting logic (httpx is mocked globally)
pytestmark = pytest.mark.no_mock_notifications


# Sample minimal metadata and payload for notification tests
sample_metadata = {
    "title": "Test <b>Title</b>",
    "author": "Author <i>One</i>",
    "description": "<p>Desc with <a href='#'>link</a></p>",
    "cover_url": "http://example.com/cover.jpg",
    "series_primary": {"name": "Series Name", "position": "1"},
    "release_date": "2020-01-01T00:00:00Z",
    "narrators": ["Narrator A"],
}
sample_payload = {
    "name": "TorrentName",
    "url": "http://example.com/view",
    "download_url": "http://example.com/download",
    "category": "fantasy",
    "size": 1234567890,
}


def test_pushover_message_formatting(mock_httpx_globally):
    """Test Pushover notification formatting with mocked HTTP calls."""
    # Configure mock response for this test
    mock_httpx_globally["post"].return_value.status_code = 200
    mock_httpx_globally["post"].return_value.json.return_value = {"status": 1}
    mock_httpx_globally["get"].return_value.status_code = 200
    mock_httpx_globally["get"].return_value.content = b"fakeimg"
    
    # Use test credentials - httpx is mocked globally so no real calls happen
    status, resp = pushover.send_pushover(
        sample_metadata, 
        sample_payload, 
        "test_token", 
        "http://localhost:8000", 
        "test_user", 
        "test_api_key", 
        sound="magic", 
        html=1, 
        priority=0
    )
    
    assert status == 200
    assert resp["status"] == 1
    assert mock_httpx_globally["post"].called


def test_gotify_message_formatting(mock_httpx_globally):
    """Test Gotify notification formatting with mocked HTTP calls."""
    # Configure mock response
    mock_httpx_globally["post"].return_value.status_code = 200
    mock_httpx_globally["post"].return_value.json.return_value = {"id": 123}
    
    # Use dummy URLs - httpx is mocked globally
    status, resp = gotify.send_gotify(
        sample_metadata, 
        sample_payload, 
        "test_token", 
        "http://localhost:8000", 
        "http://test-gotify.localhost", 
        "test_gotify_token"
    )
    
    assert status == 200
    assert "id" in resp
    assert mock_httpx_globally["post"].called


def test_discord_message_formatting(mock_httpx_globally):
    """Test Discord notification formatting with mocked HTTP calls."""
    mock_httpx_globally["post"].return_value.status_code = 204
    mock_httpx_globally["post"].return_value.json.return_value = {}
    
    status, resp = discord.send_discord(
        sample_metadata, 
        sample_payload, 
        "test_token", 
        "http://localhost:8000", 
        "http://test-discord.localhost/webhook"
    )
    
    assert status == 204
    assert mock_httpx_globally["post"].called


def test_ntfy_message_formatting(mock_httpx_globally):
    """Test ntfy notification formatting with mocked HTTP calls."""
    mock_httpx_globally["post"].return_value.status_code = 200
    mock_httpx_globally["post"].return_value.json.return_value = {"result": "ok"}
    
    status, resp = ntfy.send_ntfy(
        sample_metadata, 
        sample_payload, 
        "test_token", 
        "http://localhost:8000", 
        "test-topic", 
        "http://test-ntfy.localhost"
    )
    
    assert status == 200
    assert resp["result"] == "ok"
    assert mock_httpx_globally["post"].called


@pytest.mark.parametrize("field", ["url", "download_url"])
def test_notify_missing_urls(field, mock_httpx_globally):
    """Test notification handling when URLs are missing."""
    meta = dict(sample_metadata)
    payload = dict(sample_payload)
    payload.pop(field, None)
    
    mock_httpx_globally["post"].return_value.status_code = 200
    mock_httpx_globally["post"].return_value.json.return_value = {"result": "ok"}
    
    status, resp = ntfy.send_ntfy(
        meta, payload, "test_token", "http://localhost:8000", 
        "test-topic", "http://test-ntfy.localhost"
    )
    assert status == 200
    assert mock_httpx_globally["post"].called


def test_html_sanitization_in_notifications(mock_httpx_globally):
    """Test that HTML tags are properly escaped/stripped in notifications."""
    meta = dict(sample_metadata)
    meta["description"] = "<b>Bold</b> <script>alert(1)</script>"
    
    mock_httpx_globally["post"].return_value.status_code = 200
    mock_httpx_globally["post"].return_value.json.return_value = {"id": 1}
    
    status, resp = gotify.send_gotify(
        meta, sample_payload, "test_token", "http://localhost:8000", 
        "http://test-gotify.localhost", "test_gotify_token"
    )
    assert status == 200
    
    # The message sent should not contain <b> or <script>
    args, kwargs = mock_httpx_globally["post"].call_args
    assert "<b>" not in kwargs["json"]["message"]
    assert "<script>" not in kwargs["json"]["message"]


def test_notify_network_error_handling(mock_httpx_globally):
    """Test that network errors (httpx.RequestError) are propagated correctly."""
    import httpx as httpx_module
    
    # Simulate a real network error (RequestError) instead of generic Exception
    mock_httpx_globally["post"].side_effect = httpx_module.RequestError("Connection refused")
    
    # The pushover function re-raises httpx.RequestError for network errors
    with pytest.raises(httpx_module.RequestError) as exc_info:
        pushover.send_pushover(
            sample_metadata, sample_payload, "test_token", 
            "http://localhost:8000", "test_user", "test_api_key"
        )
    
    assert "Connection refused" in str(exc_info.value)
