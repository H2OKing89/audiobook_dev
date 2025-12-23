import contextlib
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.db import delete_request, save_request
from src.main import app
from src.security import reset_rate_limit_buckets
from src.token_gen import generate_token


# Configure pytest-asyncio mode
pytest_plugins = ("pytest_asyncio",)


# =============================================================================
# Global httpx mock to prevent ANY real HTTP calls during tests
# =============================================================================


@pytest.fixture(autouse=True, scope="function")
def mock_httpx_globally(request):
    """Mock all httpx calls globally to prevent any real HTTP requests.

    This is a safety net to ensure no notification or API calls escape during tests.
    Tests can opt-out using @pytest.mark.allow_httpx marker.
    """
    if request.node.get_closest_marker("allow_httpx"):
        yield
        return

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 123, "status": 1, "result": "ok"}
    mock_response.content = b"mock content"
    mock_response.text = "mock text"

    with (
        patch("httpx.post", return_value=mock_response) as mock_post,
        patch("httpx.get", return_value=mock_response) as mock_get,
    ):
        yield {"post": mock_post, "get": mock_get}


# =============================================================================
# Session-scoped fixtures for performance optimization
# =============================================================================


@pytest.fixture(scope="session")
def test_client():
    """Session-scoped FastAPI TestClient for testing.

    Uses manual lifecycle management to handle event loop cleanup issues
    that occur when pytest-asyncio closes the loop before session teardown.
    """
    client = TestClient(app)
    client.__enter__()
    yield client
    # Suppress only the expected "Event loop is closed" during session teardown
    # This is expected with session-scoped fixtures and pytest-asyncio
    try:
        client.__exit__(None, None, None)
    except RuntimeError as exc:
        if "Event loop is closed" not in str(exc):
            raise


@pytest.fixture
def valid_token(test_client):
    """Create a valid token and clean up after the test.

    Use this fixture when you need a pre-created token for testing endpoints.
    The token is automatically deleted after the test completes.

    Args:
        test_client: Dependency to ensure FastAPI app is initialized before token creation
    """

    token = generate_token()
    metadata = {"title": "Test Book", "author": "Test Author"}
    payload = {"url": "http://test.com", "download_url": "http://test.com/download"}
    save_request(token, metadata, payload)
    yield token
    # Cleanup - delete_request is safe to call even if token was already consumed
    delete_request(token)


@pytest.fixture(autouse=True)
def mock_notifications(request):
    """Mock all notification services by default to prevent real API calls.

    This is autouse=True to ensure no test accidentally sends real notifications.
    Tests can disable this by using the marker: @pytest.mark.no_mock_notifications

    Returns a dict of mocks that can be used to verify notification calls:
        mocks = mock_notifications
        mocks['pushover'].assert_called_once()
    """
    # Allow tests to opt-out of auto-mocking with a marker
    if request.node.get_closest_marker("no_mock_notifications"):
        yield None
        return

    with (
        patch("src.notify.pushover.send_pushover") as pushover,
        patch("src.notify.discord.send_discord") as discord,
        patch("src.notify.gotify.send_gotify") as gotify,
        patch("src.notify.ntfy.send_ntfy") as ntfy,
    ):
        pushover.return_value = (200, {"status": 1})
        discord.return_value = (204, {})
        gotify.return_value = (200, {})
        ntfy.return_value = (200, {})
        yield {"pushover": pushover, "discord": discord, "gotify": gotify, "ntfy": ntfy}


@pytest.fixture
def mock_metadata():
    """Mock metadata fetching with a standard response.

    Returns the mock object so callers can customize the return value:
        mock_metadata.return_value = {"title": "Custom Title"}
    """
    with patch("src.metadata.fetch_metadata", new_callable=AsyncMock) as mock:
        mock.return_value = {
            "title": "Test Book",
            "author": "Test Author",
            "series": "Test Series",
            "cover_url": "http://example.com/cover.jpg",
            "asin": "B123456789",
        }
        yield mock


@pytest.fixture
def mock_qbittorrent():
    """Mock qBittorrent client and torrent addition.

    Returns a dict with both mocks:
        mocks = mock_qbittorrent
        mocks['add_torrent'].assert_called_once()
    """
    with (
        patch("src.qbittorrent.get_client") as get_client,
        patch("src.webui.add_torrent_file_with_cookie") as add_torrent,
    ):
        mock_client = MagicMock()
        get_client.return_value = mock_client
        add_torrent.return_value = True
        yield {"get_client": get_client, "client": mock_client, "add_torrent": add_torrent}


@pytest.fixture
def auth_headers():
    """Standard authenticated headers for webhook tests."""
    return {"X-Autobrr-Token": "test_token"}


@pytest.fixture
def auth_env():
    """Context manager to set AUTOBRR_TOKEN environment variable."""
    with patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}):
        yield


# =============================================================================
# Autouse fixtures for test isolation
# =============================================================================


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Reset rate limiting buckets before each test"""
    reset_rate_limit_buckets()
    yield
    reset_rate_limit_buckets()


@pytest.fixture(autouse=True)
def mock_external_apis():
    """Automatically mock all external API calls to prevent real network requests.

    This ensures tests are fast and don't depend on external services.
    Tests that need real network calls should use @pytest.mark.allow_network.
    """
    # Patch the metadata coordinator's method which orchestrates all external calls
    # Also patch chapter fetching to prevent network calls
    # Use AsyncMock since these methods are now async
    with (
        patch(
            "src.metadata_coordinator.MetadataCoordinator.get_metadata_from_webhook", new_callable=AsyncMock
        ) as mock_coord,
        patch("src.audnex_metadata.AudnexMetadata.get_chapters_by_asin", new_callable=AsyncMock) as mock_chapters,
    ):
        mock_coord.return_value = {
            "title": "Mocked Book Title",
            "author": "Mocked Author",
            "asin": "B000000000",
            "cover_url": "http://example.com/cover.jpg",
        }
        mock_chapters.return_value = None  # No chapters found
        yield {"metadata": mock_coord, "chapters": mock_chapters}


# =============================================================================
# Pytest configuration
# =============================================================================


def pytest_configure(config):
    # Register markers for test organization
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "allow_network: allow real network calls (disables mock_external_apis)")


@pytest.fixture(scope="session", autouse=True)
def disable_notifications_session():
    """Disable webhook notifications globally for the test session to avoid spamming external services."""
    prev = os.environ.get("DISABLE_WEBHOOK_NOTIFICATIONS")
    os.environ["DISABLE_WEBHOOK_NOTIFICATIONS"] = "1"
    try:
        yield
    finally:
        # Restore previous value after tests
        if prev is None:
            os.environ.pop("DISABLE_WEBHOOK_NOTIFICATIONS", None)
        else:
            os.environ["DISABLE_WEBHOOK_NOTIFICATIONS"] = prev


@pytest.fixture(scope="session", autouse=True)
def speed_up_rate_limits():
    """Reduce metadata rate limits during test sessions to avoid long sleeps/blocking."""
    # Use environment variables to configure faster rate limits for testing
    # This avoids fragile direct mutation of private _config variable
    prev_audible = os.environ.get("AUDIBLE_RATE_LIMIT_SECONDS")
    prev_audnex = os.environ.get("AUDNEX_RATE_LIMIT_SECONDS")

    os.environ["AUDIBLE_RATE_LIMIT_SECONDS"] = "0.01"
    os.environ["AUDNEX_RATE_LIMIT_SECONDS"] = "0.01"

    try:
        yield
    finally:
        # Restore previous values
        if prev_audible is None:
            os.environ.pop("AUDIBLE_RATE_LIMIT_SECONDS", None)
        else:
            os.environ["AUDIBLE_RATE_LIMIT_SECONDS"] = prev_audible

        if prev_audnex is None:
            os.environ.pop("AUDNEX_RATE_LIMIT_SECONDS", None)
        else:
            os.environ["AUDNEX_RATE_LIMIT_SECONDS"] = prev_audnex


@pytest.fixture
def sample_html():
    return "<p>First paragraph.</p><p>Second<br>Line</p>"


@pytest.fixture
def sample_authors():
    return [{"name": "John Doe"}, {"name": "Jane Translator"}, {"name": "Alice Illustrator"}]


@pytest.fixture
def sample_item():
    return {
        "title": "Test Title",
        "subtitle": "SubTitle",
        "authors": [{"name": "Author One"}, {"name": "Translator Two"}],
        "narrators": [{"name": "Narrator A"}],
        "publisherName": "Pub House",
        "releaseDate": "2020-01-01T00:00:00Z",
        "summary": "<p>Summary paragraph.</p>",
        "description": "<p>Description paragraph.</p>",
        "image": "http://example.com/cover.jpg",
        "asin": "B000123456",
        "isbn": "1234567890",
        "genres": [{"type": "genre", "name": "Fantasy"}, {"type": "tag", "name": "Epic"}],
        "seriesPrimary": {"name": "Series Name", "position": "1"},
        "seriesSecondary": {"name": "Other Series", "position": ""},
        "language": "en",
        "runtimeLengthMin": 600,
        "region": "us",
        "rating": 4.5,
        "formatType": "abridged",
    }


@pytest.fixture
def sample_payload():
    return {"name": "Test Name", "url": "http://example.com", "download_url": "http://example.com/file"}
