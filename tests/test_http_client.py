"""Tests for the shared async HTTP client."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.http_client import (
    DEFAULT_REGIONS,
    REGION_MAP,
    AllRegionsFailedError,
    AsyncHttpClient,
    HttpClientConfig,
    HttpClientError,
    RateLimitError,
    close_default_client,
    get_default_client,
    get_region_tld,
    get_regions_priority,
)


class TestHttpClientConfig:
    """Test HttpClientConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = HttpClientConfig()

        assert config.timeout == 30.0
        assert config.http2 is True
        assert config.max_retries == 3
        assert config.retry_backoff_base == 2.0
        assert config.rate_limit_seconds == 0.15
        assert config.default_region == "us"
        assert len(config.regions) == 10

    def test_custom_values(self):
        """Test custom configuration values."""
        config = HttpClientConfig(
            timeout=60.0,
            http2=False,
            max_retries=5,
            rate_limit_seconds=0.5,
            default_region="uk",
        )

        assert config.timeout == 60.0
        assert config.http2 is False
        assert config.max_retries == 5
        assert config.rate_limit_seconds == 0.5
        assert config.default_region == "uk"

    def test_from_config_with_defaults(self):
        """Test loading config from config.yaml with defaults."""
        with patch("src.http_client.load_config") as mock_load:
            mock_load.return_value = {}
            config = HttpClientConfig.from_config()

            assert config.timeout == 30.0
            assert config.http2 is True

    def test_from_config_with_values(self):
        """Test loading config from config.yaml with custom values."""
        with patch("src.http_client.load_config") as mock_load:
            mock_load.return_value = {
                "metadata": {
                    "http_client": {
                        "timeout": 45.0,
                        "http2": False,
                        "max_retries": 2,
                    },
                    "audnex": {
                        "regions": ["us", "uk"],
                        "max_regions_to_try": 3,
                    },
                }
            }
            config = HttpClientConfig.from_config()

            assert config.timeout == 45.0
            assert config.http2 is False
            assert config.max_retries == 2
            assert config.regions == ["us", "uk"]
            assert config.max_regions_to_try == 3


class TestRegionHelpers:
    """Test region helper functions."""

    def test_region_map_has_all_regions(self):
        """Test that REGION_MAP has all expected regions."""
        expected = {"us", "ca", "uk", "au", "fr", "de", "jp", "it", "in", "es"}
        assert set(REGION_MAP.keys()) == expected

    def test_default_regions_order(self):
        """Test that DEFAULT_REGIONS starts with US."""
        assert DEFAULT_REGIONS[0] == "us"
        assert len(DEFAULT_REGIONS) == 10

    def test_get_region_tld(self):
        """Test getting TLD for regions."""
        assert get_region_tld("us") == ".com"
        assert get_region_tld("uk") == ".co.uk"
        assert get_region_tld("de") == ".de"
        assert get_region_tld("unknown") == ".com"  # Default fallback

    def test_get_regions_priority_preferred_first(self):
        """Test that preferred region is first."""
        regions = get_regions_priority("uk")
        assert regions[0] == "uk"
        assert "us" in regions
        assert len(regions) == 10

    def test_get_regions_priority_with_max(self):
        """Test limiting number of regions."""
        regions = get_regions_priority("de", max_regions=3)
        assert regions[0] == "de"
        assert len(regions) == 3

    def test_get_regions_priority_no_duplicates(self):
        """Test that no region appears twice."""
        regions = get_regions_priority("us")
        assert len(regions) == len(set(regions))


class TestExceptions:
    """Test custom exception classes."""

    def test_http_client_error(self):
        """Test base exception."""
        err = HttpClientError("test error")
        assert str(err) == "test error"

    def test_rate_limit_error_with_retry(self):
        """Test rate limit error with retry-after."""
        err = RateLimitError(retry_after=30)
        assert err.retry_after == 30
        assert "30s" in str(err)

    def test_rate_limit_error_no_retry(self):
        """Test rate limit error without retry-after."""
        err = RateLimitError()
        assert err.retry_after is None
        assert "Rate limited" in str(err)

    def test_all_regions_failed_error(self):
        """Test all regions failed error."""
        err = AllRegionsFailedError(
            regions_tried=["us", "uk", "de"],
            errors={"us": ValueError("test")},
        )
        assert err.regions_tried == ["us", "uk", "de"]
        assert "us" in err.errors
        assert "3 regions failed" in str(err)


@pytest.mark.asyncio
class TestAsyncHttpClientBasic:
    """Test basic AsyncHttpClient functionality."""

    async def test_context_manager(self):
        """Test async context manager opens and closes client."""
        async with AsyncHttpClient() as client:
            assert client._client is not None

        # After exiting, client should be closed
        assert client._client is None

    async def test_aclose(self):
        """Test explicit close."""
        client = AsyncHttpClient()
        await client._ensure_client()
        assert client._client is not None

        await client.aclose()
        assert client._client is None

    async def test_lazy_client_creation(self):
        """Test client is created lazily."""
        client = AsyncHttpClient()
        assert client._client is None

        await client._ensure_client()
        assert client._client is not None

        await client.aclose()


@pytest.mark.asyncio
class TestAsyncHttpClientRequests:
    """Test HTTP request functionality."""

    async def test_get_json_success(self):
        """Test successful JSON GET request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"asin": "B123456789", "title": "Test"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with AsyncHttpClient() as client:
                result = await client.get_json("https://api.example.com/books/test")

            assert result == {"asin": "B123456789", "title": "Test"}

    async def test_get_json_http_error_returns_none(self):
        """Test that HTTP errors return None from get_json."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response,
            )

            async with AsyncHttpClient() as client:
                result = await client.get_json("https://api.example.com/notfound")

            assert result is None

    async def test_get_json_request_error_returns_none(self):
        """Test that request errors return None from get_json."""
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.RequestError("Connection failed")

            async with AsyncHttpClient() as client:
                result = await client.get_json("https://api.example.com/test")

            assert result is None

    async def test_retry_on_http_error(self):
        """Test retry logic on HTTP errors."""
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 503
        mock_response_fail.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Service Unavailable",
            request=MagicMock(),
            response=mock_response_fail,
        )

        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"success": True}
        mock_response_success.raise_for_status = MagicMock()

        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.HTTPStatusError(
                    "Service Unavailable",
                    request=MagicMock(),
                    response=mock_response_fail,
                )
            return mock_response_success

        config = HttpClientConfig(max_retries=3, retry_backoff_base=0.01)

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = mock_request

            async with AsyncHttpClient(config=config) as client:
                result = await client.get_json("https://api.example.com/test")

            assert result == {"success": True}
            assert call_count == 2

    async def test_429_rate_limit_retry(self):
        """Test retry on 429 rate limit."""
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"retry-after": "1"}

        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"success": True}
        mock_response_success.raise_for_status = MagicMock()

        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.HTTPStatusError(
                    "Too Many Requests",
                    request=MagicMock(),
                    response=mock_response_429,
                )
            return mock_response_success

        config = HttpClientConfig(max_retries=3, rate_limit_seconds=0.01)

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = mock_request
            with patch("asyncio.sleep", new_callable=AsyncMock):  # Speed up test
                async with AsyncHttpClient(config=config) as client:
                    result = await client.get_json("https://api.example.com/test")

            assert result == {"success": True}
            assert call_count == 2

    async def test_500_error_no_retry(self):
        """Test that 500 errors don't retry (data likely doesn't exist)."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.HTTPStatusError(
                "Internal Server Error",
                request=MagicMock(),
                response=mock_response,
            )

            async with AsyncHttpClient() as client:
                result = await client.get_json("https://api.example.com/test")

            assert result is None
            # Should only be called once (no retry)
            assert mock_request.call_count == 1


@pytest.mark.asyncio
class TestParallelRegionFetch:
    """Test parallel region fetching."""

    async def test_first_success_wins(self):
        """Test that first successful region wins."""
        results = {
            "us": None,  # Will fail
            "uk": {"asin": "B123", "title": "UK Book"},
            "de": {"asin": "B456", "title": "DE Book"},
        }

        async def mock_get_json(url):
            # Simulate varying response times
            region = url.split("region=")[-1]
            if region == "uk":
                await asyncio.sleep(0.01)  # UK responds first
            elif region == "de":
                await asyncio.sleep(0.1)  # DE is slower
            return results.get(region)

        async with AsyncHttpClient() as client:
            # Mock the get_json method
            client.get_json = mock_get_json

            result, region = await client.fetch_first_success(
                regions=["us", "uk", "de"],
                url_factory=lambda r: f"https://api.example.com/books/B123?region={r}",
            )

        assert result == {"asin": "B123", "title": "UK Book"}
        assert region == "uk"

    async def test_all_regions_fail_returns_none(self):
        """Test that when all regions fail, returns (None, None)."""

        async def mock_get_json(url):
            return None  # All fail

        async with AsyncHttpClient() as client:
            client.get_json = mock_get_json

            result, region = await client.fetch_first_success(
                regions=["us", "uk", "de"],
                url_factory=lambda r: f"https://api.example.com/books/B123?region={r}",
            )

        assert result is None
        assert region is None

    async def test_respects_max_regions(self):
        """Test that max_regions limits the number of regions tried."""
        regions_tried = []

        async def mock_get_json(url):
            region = url.split("region=")[-1]
            regions_tried.append(region)

        async with AsyncHttpClient() as client:
            client.get_json = mock_get_json

            await client.fetch_first_success(
                regions=["us", "uk", "de", "fr", "es"],
                url_factory=lambda r: f"https://api.example.com/books/B123?region={r}",
                max_regions=2,
            )

        assert len(regions_tried) == 2

    async def test_custom_validator(self):
        """Test custom validator function."""
        results = {
            "us": {"asin": "B123", "language": "german"},  # Wrong language
            "uk": {"asin": "B456", "language": "english"},  # Correct
        }

        async def mock_get_json(url):
            region = url.split("region=")[-1]
            return results.get(region)

        def english_only(data):
            return data.get("language") == "english"

        async with AsyncHttpClient() as client:
            client.get_json = mock_get_json

            result, region = await client.fetch_first_success(
                regions=["us", "uk"],
                url_factory=lambda r: f"https://api.example.com/books/B123?region={r}",
                validator=english_only,
            )

        assert result == {"asin": "B456", "language": "english"}
        assert region == "uk"

    async def test_empty_regions_returns_none(self):
        """Test that empty regions list returns (None, None)."""
        async with AsyncHttpClient() as client:
            result, region = await client.fetch_first_success(
                regions=[],
                url_factory=lambda r: f"https://api.example.com/books/B123?region={r}",
            )

        assert result is None
        assert region is None


@pytest.mark.asyncio
class TestRateLimiting:
    """Test rate limiting functionality."""

    async def test_rate_limiting_delays_requests(self):
        """Test that rate limiting adds delays between requests."""
        request_times = []
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()

        async def track_request(*args, **kwargs):
            request_times.append(asyncio.get_event_loop().time())
            return mock_response

        config = HttpClientConfig(rate_limit_seconds=0.1)

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = track_request

            async with AsyncHttpClient(config=config) as client:
                await client.get_json("https://api.example.com/test1")
                await client.get_json("https://api.example.com/test2")

        assert len(request_times) == 2
        # Second request should be delayed by at least rate_limit_seconds
        assert request_times[1] - request_times[0] >= 0.09  # Allow small tolerance


@pytest.mark.asyncio
class TestDefaultClient:
    """Test default client management."""

    async def test_get_default_client_creates_singleton(self):
        """Test that get_default_client returns a singleton."""
        try:
            client1 = await get_default_client()
            client2 = await get_default_client()

            assert client1 is client2
        finally:
            await close_default_client()

    async def test_close_default_client(self):
        """Test closing the default client."""
        from src import http_client

        try:
            await get_default_client()
            assert http_client._ClientHolder.client is not None

            await close_default_client()
            assert http_client._ClientHolder.client is None
        finally:
            # Ensure cleanup even if test fails
            await close_default_client()
