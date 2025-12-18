import sys, os
# allow tests to import from the 'src' package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from src.security import reset_rate_limit_buckets

@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Reset rate limiting buckets before each test"""
    reset_rate_limit_buckets()
    yield
    reset_rate_limit_buckets()


def pytest_configure(config):
    # Register markers so tests can opt-in to enable notifications when needed
    config.addinivalue_line("markers", "allow_notifications: enable external notifications for this test")


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
    # Import inside fixture to avoid import-time side-effects
    import src.config as _config_mod
    prev = _config_mod._config
    # Ensure config is loaded
    cfg = _config_mod.load_config()
    # Create a shallow copy and set small rate limits for testing
    fast_cfg = dict(cfg)
    meta = dict(fast_cfg.get('metadata', {}))
    meta['rate_limit_seconds'] = 0.01
    audnex_cfg = dict(meta.get('audnex', {}))
    audnex_cfg['rate_limit_seconds'] = 0.01
    meta['audnex'] = audnex_cfg
    fast_cfg['metadata'] = meta
    _config_mod._config = fast_cfg

    try:
        yield
    finally:
        _config_mod._config = prev


@pytest.fixture(autouse=True)
def maybe_enable_notifications(request):
    """If a test is marked with @pytest.mark.allow_notifications, temporarily enable notifications."""
    marker = request.node.get_closest_marker("allow_notifications")
    if marker:
        prev = os.environ.pop("DISABLE_WEBHOOK_NOTIFICATIONS", None)
        try:
            yield
        finally:
            if prev is not None:
                os.environ["DISABLE_WEBHOOK_NOTIFICATIONS"] = prev
    else:
        yield

@pytest.fixture
def sample_html():
    return "<p>First paragraph.</p><p>Second<br>Line</p>"

@pytest.fixture
def sample_authors():
    return [
        {"name": "John Doe"},
        {"name": "Jane Translator"},
        {"name": "Alice Illustrator"}
    ]

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
        "genres": [
            {"type": "genre", "name": "Fantasy"},
            {"type": "tag", "name": "Epic"}
        ],
        "seriesPrimary": {"name": "Series Name", "position": "1"},
        "seriesSecondary": {"name": "Other Series", "position": ""},
        "language": "en",
        "runtimeLengthMin": 600,
        "region": "us",
        "rating": 4.5,
        "formatType": "abridged"
    }

@pytest.fixture
def sample_payload():
    return {"name": "Test Name", "url": "http://example.com", "download_url": "http://example.com/file"}
