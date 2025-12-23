"""
Shared async HTTP client with HTTP/2, parallel region fetching, and retry logic.

This module provides a centralized HTTP client used by all metadata-fetching modules,
consolidating connection pooling, retry logic, rate limiting, and multi-region support.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx


if TYPE_CHECKING:
    from collections.abc import Callable

from src.config import load_config


logger = logging.getLogger(__name__)


# Consolidated region mapping (previously duplicated in metadata.py and audible_scraper.py)
REGION_MAP: dict[str, str] = {
    "us": ".com",
    "ca": ".ca",
    "uk": ".co.uk",
    "au": ".com.au",
    "fr": ".fr",
    "de": ".de",
    "jp": ".co.jp",
    "it": ".it",
    "in": ".in",
    "es": ".es",
}

# Default region list ordered by priority
DEFAULT_REGIONS: list[str] = ["us", "uk", "ca", "au", "de", "fr", "es", "it", "jp", "in"]


class HttpClientError(Exception):
    """Base exception for HTTP client errors."""

    pass


class RateLimitError(HttpClientError):
    """Raised when rate limit is exceeded and retries exhausted."""

    def __init__(self, retry_after: int | None = None) -> None:
        self.retry_after = retry_after
        msg = f"Rate limited. Retry after {retry_after}s" if retry_after else "Rate limited"
        super().__init__(msg)


class AllRegionsFailedError(HttpClientError):
    """Raised when all regions fail during parallel fetch."""

    def __init__(self, regions_tried: list[str], errors: dict[str, Exception] | None = None) -> None:
        self.regions_tried = regions_tried
        self.errors = errors or {}
        super().__init__(f"All {len(regions_tried)} regions failed")


@dataclass
class HttpClientConfig:
    """Configuration for the shared HTTP client."""

    timeout: float = 30.0
    http2: bool = True
    max_retries: int = 3
    retry_backoff_base: float = 2.0
    rate_limit_seconds: float = 0.15
    user_agent: str = "AudiobookDev/1.0"

    # Region configuration
    default_region: str = "us"
    regions: list[str] = field(default_factory=lambda: DEFAULT_REGIONS.copy())
    max_regions_to_try: int = 10

    @classmethod
    def from_config(cls) -> HttpClientConfig:
        """Load configuration from config.yaml."""
        config = load_config()
        http_config = config.get("metadata", {}).get("http_client", {})
        audnex_config = config.get("metadata", {}).get("audnex", {})

        return cls(
            timeout=http_config.get("timeout", 30.0),
            http2=http_config.get("http2", True),
            max_retries=http_config.get("max_retries", 3),
            retry_backoff_base=http_config.get("retry_backoff_base", 2.0),
            rate_limit_seconds=http_config.get("rate_limit_seconds", 0.15),
            user_agent=http_config.get("user_agent", "AudiobookDev/1.0"),
            default_region=audnex_config.get("default_region", "us"),
            regions=audnex_config.get("regions", DEFAULT_REGIONS.copy()),
            max_regions_to_try=audnex_config.get("max_regions_to_try", 10),
        )


class AsyncHttpClient:
    """
    Shared async HTTP client with HTTP/2, retries, rate limiting, and parallel region support.

    Example usage:
        async with AsyncHttpClient() as client:
            # Single request
            data = await client.get_json("https://api.audnex.us/books/B123456789")

            # Parallel region fetch - returns first successful result
            result, region = await client.fetch_first_success(
                regions=["us", "uk", "de"],
                url_factory=lambda r: f"https://api.audnex.us/books/B123456789?region={r}",
            )
    """

    def __init__(
        self,
        config: HttpClientConfig | None = None,
        base_url: str = "",
    ) -> None:
        self._config = config or HttpClientConfig.from_config()
        self._base_url = base_url
        self._client: httpx.AsyncClient | None = None
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Lazily create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                http2=self._config.http2,
                timeout=httpx.Timeout(self._config.timeout),
                headers={"User-Agent": self._config.user_agent},
                follow_redirects=True,
            )
        return self._client

    async def aclose(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> AsyncHttpClient:
        await self._ensure_client()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        await self.aclose()

    async def _throttle(self) -> None:
        """Apply rate limiting between requests."""
        async with self._lock:
            current = time.time()
            elapsed = current - self._last_request_time

            if elapsed < self._config.rate_limit_seconds:
                wait = self._config.rate_limit_seconds - elapsed
                await asyncio.sleep(wait)

            self._last_request_time = time.time()

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute request with retry logic and rate limiting.

        Retry behavior:
        - 429 (rate limit): Retry after 'retry-after' header or 5s
        - 5xx (server errors): Retry with exponential backoff (transient failures)
        - 4xx (client errors, except 429): Do NOT retry (permanent failures)
        - Network/timeout errors: Retry with exponential backoff
        """
        await self._throttle()
        client = await self._ensure_client()

        # Status codes that are transient and worth retrying
        retryable_status_codes = {500, 502, 503, 504}
        # Status codes that indicate client errors - don't retry
        non_retryable_status_codes = {400, 401, 403, 404, 405, 406, 410, 422}

        last_error: Exception | None = None

        for attempt in range(self._config.max_retries):
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code

                if status_code == 429:  # Rate limited
                    retry_after_str = e.response.headers.get("retry-after", "5")
                    try:
                        retry_after = int(retry_after_str)
                    except ValueError:
                        retry_after = 5
                    logger.warning("Rate limited. Retrying in %ds", retry_after)
                    await asyncio.sleep(retry_after)
                    continue

                elif status_code in non_retryable_status_codes:
                    # Client errors - don't retry, the request is invalid
                    logger.debug("HTTP %d (non-retryable) for %s", status_code, url)
                    raise

                elif status_code in retryable_status_codes:
                    # Server errors - retry with backoff (transient failures)
                    last_error = e
                    if attempt < self._config.max_retries - 1:
                        backoff = self._config.retry_backoff_base**attempt
                        logger.warning("HTTP %d (transient), retrying in %.1fs: %s", status_code, backoff, url)
                        await asyncio.sleep(backoff)
                    continue

                else:
                    # Unknown status code - don't retry
                    logger.debug("HTTP %d for %s", status_code, url)
                    raise

            except httpx.RequestError as e:
                last_error = e
                if attempt < self._config.max_retries - 1:
                    backoff = self._config.retry_backoff_base**attempt
                    logger.debug("Request error, retrying in %.1fs: %s", backoff, e)
                    await asyncio.sleep(backoff)

        if last_error:
            raise last_error
        raise HttpClientError("Request failed after retries")

    async def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Make a GET request with retry logic."""
        kwargs: dict[str, Any] = {}
        if params:
            kwargs["params"] = params
        if headers:
            kwargs["headers"] = headers
        if timeout:
            kwargs["timeout"] = timeout

        return await self._request_with_retry("GET", url, **kwargs)

    async def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any] | None:
        """Make a GET request and return JSON response, or None on error."""
        try:
            response = await self.get(url, params=params, headers=headers, timeout=timeout)
            return response.json()  # type: ignore[no-any-return]
        except httpx.HTTPStatusError as e:
            logger.debug("HTTP error fetching %s: %s", url, e)
            return None
        except httpx.RequestError as e:
            logger.debug("Request error fetching %s: %s", url, e)
            return None
        except Exception as e:
            logger.debug("Unexpected error fetching %s: %s", url, e)
            return None

    async def post_json(
        self,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any] | None:
        """Make a POST request with JSON body and return JSON response."""
        kwargs: dict[str, Any] = {}
        if json:
            kwargs["json"] = json
        if params:
            kwargs["params"] = params
        if headers:
            kwargs["headers"] = headers
        if timeout:
            kwargs["timeout"] = timeout

        try:
            response = await self._request_with_retry("POST", url, **kwargs)
            return response.json()  # type: ignore[no-any-return]
        except httpx.HTTPStatusError as e:
            logger.debug("HTTP error posting to %s: %s", url, e)
            return None
        except httpx.RequestError as e:
            logger.debug("Request error posting to %s: %s", url, e)
            return None

    async def fetch_first_success(
        self,
        regions: list[str],
        url_factory: Callable[[str], str],
        *,
        validator: Callable[[dict[str, Any]], bool] | None = None,
        max_regions: int | None = None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """
        Fetch from multiple regions in parallel, returning the first successful result.

        Uses asyncio.as_completed to process results as they arrive, stopping early
        once a valid result is found. This avoids the ExceptionGroup complexity of
        TaskGroup while still achieving parallel fetching.

        Args:
            regions: List of region codes to try
            url_factory: Function that takes a region and returns the URL to fetch
            validator: Optional function to validate response (default: check for non-empty dict)
            max_regions: Override max regions to try (default: config.max_regions_to_try)

        Returns:
            Tuple of (result_dict or None, successful_region or None)
        """
        if validator is None:
            validator = lambda d: bool(d)  # noqa: E731

        max_to_try = max_regions or self._config.max_regions_to_try
        regions_to_try = regions[:max_to_try]

        if not regions_to_try:
            return None, None

        errors: dict[str, Exception] = {}

        async def fetch_region(region: str) -> tuple[dict[str, Any] | None, str]:
            """Fetch a single region, returning (data, region) tuple."""
            url = url_factory(region)
            try:
                data = await self.get_json(url)
                return data, region
            except Exception as e:
                errors[region] = e
                logger.debug("Region %s failed: %s", region, e)
                return None, region

        # Create tasks for all regions
        tasks = [asyncio.create_task(fetch_region(region)) for region in regions_to_try]

        result: dict[str, Any] | None = None
        winning_region: str | None = None

        try:
            # Process results as they complete
            for coro in asyncio.as_completed(tasks):
                try:
                    data, region = await coro
                    if data and validator(data):
                        result = data
                        winning_region = region
                        logger.debug("Region %s succeeded first", region)
                        break  # Found a winner, stop waiting
                except Exception as e:
                    logger.debug("Task failed with: %s", e)
                    continue
        finally:
            # Cancel remaining tasks that haven't completed
            for task in tasks:
                if not task.done():
                    task.cancel()
            # Wait for cancellations to complete (suppress CancelledError)
            await asyncio.gather(*tasks, return_exceptions=True)

        if result:
            logger.info("Parallel fetch succeeded via region %s", winning_region)
        else:
            logger.debug(
                "All %d regions failed: %s", len(regions_to_try), {region: str(err) for region, err in errors.items()}
            )

        return result, winning_region


# Module-level default client management using a mutable container to avoid global statement
class _ClientHolder:
    """Container for the default client singleton to avoid global statement."""

    client: AsyncHttpClient | None = None
    lock: asyncio.Lock | None = None
    _init_lock: threading.Lock = threading.Lock()

    @classmethod
    def get_lock(cls) -> asyncio.Lock:
        """Lazily create the lock to avoid issues with event loop."""
        if cls.lock is None:
            with cls._init_lock:
                if cls.lock is None:
                    cls.lock = asyncio.Lock()
        return cls.lock


async def get_default_client() -> AsyncHttpClient:
    """Get or create the default shared client instance."""
    async with _ClientHolder.get_lock():
        if _ClientHolder.client is None:
            _ClientHolder.client = AsyncHttpClient()
        return _ClientHolder.client


async def close_default_client() -> None:
    """Close the default client (call during application shutdown)."""
    async with _ClientHolder.get_lock():
        if _ClientHolder.client is not None:
            await _ClientHolder.client.aclose()
            _ClientHolder.client = None


def get_region_tld(region: str) -> str:
    """Get the TLD suffix for a region code."""
    return REGION_MAP.get(region, ".com")


def get_regions_priority(preferred_region: str, max_regions: int | None = None) -> list[str]:
    """
    Get a list of regions with the preferred region first.

    Args:
        preferred_region: The region to prioritize
        max_regions: Maximum number of regions to return

    Returns:
        List of region codes with preferred_region first
    """
    regions = [preferred_region]
    for r in DEFAULT_REGIONS:
        if r != preferred_region and r not in regions:
            regions.append(r)

    if max_regions:
        return regions[:max_regions]
    return regions
