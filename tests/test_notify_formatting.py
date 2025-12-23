import pytest
from unittest.mock import patch, MagicMock
from src.notify.pushover import send_pushover
from src.notify.gotify import send_gotify
from src.notify.discord import send_discord
from src.notify.ntfy import send_ntfy

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

def test_pushover_message_formatting():
    with patch("src.notify.pushover.httpx.post") as mock_post, \
         patch("src.notify.pushover.httpx.get") as mock_get:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"status": 1}
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"fakeimg"
        status, resp = send_pushover(
            sample_metadata, sample_payload, "tok", "http://base", "user", "api", sound="magic", html=1, priority=0
        )
        assert status == 200
        assert resp["status"] == 1

def test_gotify_message_formatting():
    with patch("src.notify.gotify.httpx.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"id": 123}
        status, resp = send_gotify(
            sample_metadata, sample_payload, "tok", "http://base", "http://gotify", "token"
        )
        assert status == 200
        assert "id" in resp

def test_discord_message_formatting():
    with patch("src.notify.discord.httpx.post") as mock_post:
        mock_post.return_value.status_code = 204
        mock_post.return_value.json.return_value = {}
        status, resp = send_discord(
            sample_metadata, sample_payload, "tok", "http://base", "http://discord/webhook"
        )
        assert status == 204

def test_ntfy_message_formatting():
    with patch("src.notify.ntfy.httpx.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"result": "ok"}
        status, resp = send_ntfy(
            sample_metadata, sample_payload, "tok", "http://base", "topic", "http://ntfy"
        )
        assert status == 200
        assert resp["result"] == "ok"

@pytest.mark.parametrize("field", ["url", "download_url"])
def test_notify_missing_urls(field):
    meta = dict(sample_metadata)
    payload = dict(sample_payload)
    payload.pop(field, None)
    with patch("src.notify.ntfy.httpx.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"result": "ok"}
        status, resp = send_ntfy(meta, payload, "tok", "http://base", "topic", "http://ntfy")
        assert status == 200

# Test that HTML is stripped from notification fields
def test_html_sanitization_in_notifications():
    meta = dict(sample_metadata)
    meta["description"] = "<b>Bold</b> <script>alert(1)</script>"
    with patch("src.notify.gotify.httpx.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"id": 1}
        status, resp = send_gotify(meta, sample_payload, "tok", "http://base", "http://gotify", "token")
        assert status == 200
        # The message sent should not contain <b> or <script>
        args, kwargs = mock_post.call_args
        assert "<b>" not in kwargs["json"]["message"]
        assert "<script>" not in kwargs["json"]["message"]

# Test error handling: simulate network error
def test_notify_network_error_handling():
    with patch("src.notify.pushover.httpx.post", side_effect=Exception("fail")):
        try:
            send_pushover(sample_metadata, sample_payload, "tok", "http://base", "user", "api")
        except Exception as e:
            assert "fail" in str(e)
