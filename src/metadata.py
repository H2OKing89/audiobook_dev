import asyncio
import logging
import os
import re
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from src.config import load_config
from src.utils import clean_author_list, validate_payload


# ASIN validation
def is_valid_asin(asin: str) -> bool:
    """Validate ASIN format (10 characters, alphanumeric)"""
    if not asin or not isinstance(asin, str):
        return False
    return len(asin) == 10 and asin.isalnum()


# Levenshtein distance implementation for best-match logic
def levenshtein_distance(s1: str, s2: str) -> int:
    if s1 == s2:
        return 0
    len1, len2 = len(s1), len(s2)
    dp = list(range(len2 + 1))
    for i in range(1, len1 + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, len2 + 1):
            cur = dp[j]
            if s1[i - 1] == s2[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j - 1], dp[j])
            prev = cur
    return dp[len2]


class Audible:
    def __init__(self, response_timeout: int = 30000) -> None:
        self.response_timeout = response_timeout
        self.region_map = {
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

    def clean_series_sequence(self, series_name: str, sequence: str) -> str:
        """
        Audible will sometimes send sequences with "Book 1" or "2, Dramatized Adaptation"
        Clean to extract just the number portion
        """
        if not sequence:
            return ""
        # match any number with optional decimal (e.g, 1 or 1.5 or .5)
        match = re.search(r"\.\d+|\d+(?:\.\d+)?", sequence)
        updated_sequence = match.group(0) if match else sequence
        if sequence != updated_sequence:
            logging.debug(
                f'[Audible] Series "{series_name}" sequence was cleaned from "{sequence}" to "{updated_sequence}"'
            )
        return updated_sequence

    def clean_result(self, item: dict[str, Any]) -> dict[str, Any]:
        """Clean and format the result from Audnex API"""
        title = item.get("title")
        subtitle = item.get("subtitle")
        asin = item.get("asin")
        authors = item.get("authors", [])
        narrators = item.get("narrators", [])
        publisher_name = item.get("publisherName")
        summary = item.get("summary")
        release_date = item.get("releaseDate")
        image = item.get("image")
        genres = item.get("genres", [])
        series_primary = item.get("seriesPrimary")
        series_secondary = item.get("seriesSecondary")
        language = item.get("language")
        runtime_length_min = item.get("runtimeLengthMin")
        format_type = item.get("formatType")
        isbn = item.get("isbn")

        series = []
        if series_primary:
            series.append(
                {
                    "series": series_primary.get("name"),
                    "sequence": self.clean_series_sequence(
                        series_primary.get("name", ""), series_primary.get("position", "")
                    ),
                }
            )
        if series_secondary:
            series.append(
                {
                    "series": series_secondary.get("name"),
                    "sequence": self.clean_series_sequence(
                        series_secondary.get("name", ""), series_secondary.get("position", "")
                    ),
                }
            )

        genres_filtered = [g.get("name") for g in genres if g.get("type") == "genre"]
        tags_filtered = [g.get("name") for g in genres if g.get("type") == "tag"]

        return {
            "title": title,
            "subtitle": subtitle or None,
            "author": ", ".join([a.get("name", "") for a in authors]) if authors else None,
            "narrator": ", ".join([n.get("name", "") for n in narrators]) if narrators else None,
            "publisher": publisher_name,
            "publishedYear": release_date.split("-")[0] if release_date else None,
            "description": summary or None,
            "cover": image,
            "asin": asin,
            "isbn": isbn,
            "genres": genres_filtered if genres_filtered else None,
            "tags": ", ".join(tags_filtered) if tags_filtered else None,
            "series": series if series else None,
            "language": language.capitalize() if language else None,
            "duration": int(runtime_length_min) if runtime_length_min and str(runtime_length_min).isdigit() else 0,
            "region": item.get("region") or None,
            "rating": item.get("rating") or None,
            "abridged": format_type == "abridged",
        }

    def asin_search(self, asin: str, region: str = "us", timeout: int | None = None) -> dict[str, Any] | None:
        """Search for a book by ASIN"""
        if not asin:
            return None
        if not timeout:
            timeout = self.response_timeout

        asin = asin.upper()
        region_query = f"?region={region}" if region else ""
        url = f"https://api.audnex.us/books/{asin}{region_query}"
        logging.debug(f"[Audible] ASIN url: {url}")

        try:
            response = httpx.get(url, timeout=timeout / 1000)  # Convert ms to seconds
            response.raise_for_status()
            data = response.json()
            if not data.get("asin"):
                return None
            return data
        except httpx.RequestError as error:
            # Propagate network-related errors so callers can handle them uniformly
            logging.error(f"[Audible] ASIN search network error: {error}")
            raise
        except Exception as error:
            logging.error(f"[Audible] ASIN search error: {error}")
            return None

    def search(
        self, title: str, author: str = "", asin: str = "", region: str = "us", timeout: int | None = None
    ) -> list[dict[str, Any]]:
        """Search for books using title, author, and/or ASIN"""
        if region and region not in self.region_map:
            logging.error(f"[Audible] search: Invalid region {region}")
            region = "us"

        if not timeout:
            timeout = self.response_timeout

        items = []

        # Try ASIN search first if valid
        if asin and is_valid_asin(asin.upper()):
            item = self.asin_search(asin, region, timeout)
            if item:
                items.append(item)

        # Try title as ASIN if no results and title looks like ASIN
        if not items and is_valid_asin(title.upper()):
            item = self.asin_search(title, region, timeout)
            if item:
                items.append(item)

        # Fallback to catalog search
        if not items:
            query_obj = {"num_results": "10", "products_sort_by": "Relevance", "title": title}
            if author:
                query_obj["author"] = author

            query_string = urlencode(query_obj)
            tld = self.region_map.get(region, ".com")
            url = f"https://api.audible{tld}/1.0/catalog/products?{query_string}"
            logging.debug(f"[Audible] Search url: {url}")

            try:
                response = httpx.get(url, timeout=timeout / 1000)
                response.raise_for_status()
                data = response.json()

                if data.get("products"):
                    # Get detailed info for each product
                    detailed_items = []
                    for result in data["products"]:
                        if result.get("asin"):
                            detailed_item = self.asin_search(result["asin"], region, timeout)
                            if detailed_item:
                                detailed_items.append(detailed_item)
                    items = detailed_items
                else:
                    items = []
            except httpx.RequestError as error:
                logging.error(f"[Audible] query search error: {error}")
                # Propagate network-related errors up so callers can wrap them appropriately
                raise
            except Exception as error:
                logging.error(f"[Audible] query search error: {error}")
                items = []

        # Clean and return results
        return [self.clean_result(item) for item in items if item]


class Audnexus:
    _instance = None

    def __new__(cls) -> "Audnexus":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "initialized"):
            return

        self.base_url = "https://api.audnex.us"
        self.request_interval = 0.15  # 150ms between requests
        self.last_request_time = 0
        self.initialized = True

    def _throttle_request(self):
        """Simple throttling to avoid rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_interval:
            time.sleep(self.request_interval - time_since_last)
        self.last_request_time = time.time()

    def _process_request(self, url: str, max_retries: int = 1) -> dict[str, Any] | None:
        """Process request with rate limiting and retry logic"""
        for _attempt in range(max_retries + 1):
            try:
                self._throttle_request()
                response = httpx.get(url)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response is not None and e.response.status_code == 429:  # Rate limited
                    retry_after_header = e.response.headers.get("retry-after", "5")
                    try:
                        retry_after = int(retry_after_header)
                    except ValueError:
                        # Try parsing as HTTP-date (not implemented for simplicity, use default)
                        logging.warning(f"[Audnexus] Non-integer retry-after header: {retry_after_header}, using default 5s")
                        retry_after = 5
                    logging.warning(f"[Audnexus] Rate limit exceeded. Retrying in {retry_after} seconds.")
                    time.sleep(retry_after)
                    continue
                else:
                    logging.error(f"[Audnexus] HTTP error: {e}")
                    return None
            except httpx.RequestError as e:
                logging.error(f"[Audnexus] Request error: {e}")
                return None
        return None

    def author_asins_request(self, name: str, region: str = "") -> list[dict[str, Any]]:
        """Get author ASINs by name"""
        params = {"name": name}
        if region:
            params["region"] = region

        url = f"{self.base_url}/authors?{urlencode(params)}"
        logging.info(f'[Audnexus] Searching for author "{url}"')

        result = self._process_request(url)
        if result is None:
            return []
        return result if isinstance(result, list) else [result]

    def author_request(self, asin: str, region: str = "") -> dict[str, Any] | None:
        """Get author details by ASIN"""
        if not is_valid_asin(asin.upper()):
            logging.error(f"[Audnexus] Invalid ASIN {asin}")
            return None

        asin = asin.upper()
        params = {"region": region} if region else {}
        url = f"{self.base_url}/authors/{asin}"
        if params:
            url += f"?{urlencode(params)}"

        logging.info(f'[Audnexus] Searching for author "{url}"')

        result = self._process_request(url)
        return result

    def find_author_by_asin(self, asin: str, region: str = "") -> dict[str, Any] | None:
        """Find author by ASIN"""
        author = self.author_request(asin, region)

        if author:
            return {
                "asin": author.get("asin"),
                "description": author.get("description"),
                "image": author.get("image") or None,
                "name": author.get("name"),
            }
        return None

    def find_author_by_name(self, name: str, region: str = "", max_levenshtein: int = 3) -> dict[str, Any] | None:
        """Find author by name with fuzzy matching"""
        logging.debug(f"[Audnexus] Looking up author by name {name}")
        author_asin_objs = self.author_asins_request(name, region)

        closest_match = None
        for author_asin_obj in author_asin_objs:
            author_name = author_asin_obj.get("name", "")
            distance = levenshtein_distance(author_name, name)
            author_asin_obj["levenshtein_distance"] = distance

            if not closest_match or closest_match["levenshtein_distance"] > distance:
                closest_match = author_asin_obj

        if not closest_match or closest_match["levenshtein_distance"] > max_levenshtein:
            return None

        author = self.author_request(closest_match.get("asin", ""), region)
        if not author:
            return None

        return {
            "asin": author.get("asin"),
            "description": author.get("description"),
            "image": author.get("image") or None,
            "name": author.get("name"),
        }

    def get_chapters_by_asin(self, asin: str, region: str = "") -> dict[str, Any] | None:
        """Get chapters for a book by ASIN"""
        logging.debug(f"[Audnexus] Get chapters for ASIN {asin}/{region}")

        asin = asin.upper()
        params = {"region": region} if region else {}
        url = f"{self.base_url}/books/{asin}/chapters"
        if params:
            url += f"?{urlencode(params)}"

        result = self._process_request(url)
        return result


# Main fetch metadata function compatible with existing code
def get_cached_metadata(_asin: str, _region: str = "us", _api_url: str | None = None) -> dict | None:
    """Intentional stub kept for signature compatibility - tests are expected to patch/override this.

    This function is a placeholder whose parameters are currently unused in the default implementation.
    The function signature is maintained for backwards compatibility with existing code and tests.

    Args:
        _asin: The Amazon Standard Identification Number (10 alphanumeric characters) to look up
        _region: The Audible region/marketplace (e.g., 'us', 'uk', 'ca') for regional content
        _api_url: Optional custom API endpoint URL for metadata lookup (typically None)

    Returns:
        None by default. Tests should patch this function to return mock metadata dict when needed.
        A real implementation might query a local cache or external API.

    Note:
        This is an intentional no-op stub. The default behavior returns None to indicate no cached
        metadata is available. Tests that require cached metadata should mock/patch this function
        to return appropriate test data.
    """
    # Default behavior: no cache. Tests may patch this to return values.
    return None


def get_audible_asin(title: str, author: str = "") -> str | None:
    """Try to extract an ASIN by scraping Audible search results.

    This function attempts to import BeautifulSoup and parse the page returned by
    a simple Audible search. If bs4 is not available or parsing fails, return None.
    """
    try:
        import bs4  # noqa: PLC0415
        BeautifulSoup = bs4.BeautifulSoup
    except ImportError:
        return None

    try:
        query = f"{title} {author}".strip()
        # Simple Audible search URL; tests mock httpx.get and only care about response text
        search_url = f"https://www.audible.com/search?keywords={query.replace(' ', '+')}"
        resp = httpx.get(search_url)
        resp.raise_for_status()
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        # Audible sometimes puts ASINs in adbl-impression-container data-asin
        el = soup.find("div", class_="adbl-impression-container")
        if el and el.get("data-asin"):
            return el.get("data-asin")

        # Fallback: look for data-asin attributes elsewhere
        el2 = soup.find(attrs={"data-asin": True})
        if el2:
            return el2.get("data-asin")

        return None
    except httpx.RequestError:
        raise
    except (AttributeError, ValueError, TypeError) as e:
        # Expected parsing-related errors - log and return None
        logging.debug(f"get_audible_asin failed: {e}")
        return None
    except Exception as e:
        # bs4.FeatureNotFound and other BeautifulSoup parsing exceptions
        if "bs4" in type(e).__module__:
            logging.debug(f"get_audible_asin BeautifulSoup parsing failed: {e}")
            return None
        # Unexpected exceptions should propagate
        raise


def fetch_metadata(payload: dict, regions: list[str] | None = None) -> dict:
    """
    Compatibility wrapper: Enhanced fetch using the new modular coordinator
    """
    from src.metadata_coordinator import MetadataCoordinator  # noqa: PLC0415

    # Validate payload early to fail fast for invalid input
    config = load_config()
    req_keys = config.get("payload", {}).get("required_keys") or ["name", "url", "download_url"]
    if not validate_payload(payload, req_keys):
        raise ValueError(f"Payload missing required keys: {req_keys}")

    # Optional test-mode guard to prevent real external API calls during CI/test runs
    if os.getenv("DISABLE_EXTERNAL_API") == "1":
        logging.info("DISABLE_EXTERNAL_API set; avoiding external API calls in fetch_metadata()")
        raise ValueError("External API calls are disabled in this environment")

    coordinator = MetadataCoordinator()

    metadata = asyncio.run(coordinator.get_metadata_from_webhook(payload))

    if metadata:
        # Get enhanced metadata with chapters
        return coordinator.get_enhanced_metadata(metadata)
    else:
        # Fallback to original logic for compatibility
        name = payload.get("name", "")
        title = payload.get("title") or name
        author = payload.get("author", "")

        # Extract ASIN from name if present
        asin_regex = config.get("payload", {}).get("asin_regex")
        match = re.search(asin_regex, name) if asin_regex else None
        asin = match.group(0) if match else None

        # Use provided regions or default sequence
        if not regions:
            regions = ["us", "ca", "uk", "au", "fr", "de", "jp", "it", "in", "es"]

        # If we have an ASIN, try to get cached metadata first
        if asin:
            try:
                cached = get_cached_metadata(asin, region="us", api_url=None)
            except httpx.RequestError as e:
                logging.error(f"Network error fetching cached metadata: {e}")
                raise ValueError(f"Could not fetch metadata: {e}") from e
            if cached:
                return cached

        # Attempt scraping to find an ASIN if none was extracted
        if not asin:
            try:
                scraped = get_audible_asin(title, author)
            except httpx.RequestError as e:
                logging.error(f"Network error while attempting to scrape Audible: {e}")
                # Wrap network errors into a controlled ValueError
                raise ValueError("Could not fetch metadata") from e

            if scraped:
                asin = scraped
                cached = get_cached_metadata(asin, region="us", api_url=None)
                if cached:
                    return cached

        # If we still don't have an ASIN, try regions searching
        audible = Audible()

        # If we have an ASIN but no cached record, try using the audible search (ASIN search first)
        network_issue = False
        for region in regions:
            try:
                if asin:
                    results = audible.search(title=title, author=author, asin=asin, region=region)
                else:
                    results = audible.search(title=title, author=author, asin="", region=region)

                if results:
                    # Return the first (best) result
                    return results[0]
            except httpx.HTTPStatusError as e:
                # Rate limits or HTTP errors should be treated as controlled fetch failures
                if e.response is not None and e.response.status_code == 429:
                    logging.error(f"Rate limited searching region {region}: {e}")
                    raise ValueError("Could not fetch metadata") from e
                logging.error(f"HTTP error searching region {region}: {e}")
                network_issue = True
                continue
            except httpx.RequestError as e:
                # Network error for a single region shouldn't abort the entire ASIN discovery;
                # mark that a network issue occurred and continue searching other regions.
                logging.error(f"Network error searching region {region}: {e}")
                network_issue = True
                continue
            except ValueError as e:
                # Malformed JSON or parsing errors should be treated as controlled fetch failures
                logging.error(f"Malformed response searching region {region}: {e}")
                raise ValueError("Could not fetch metadata") from e
            except Exception as e:
                logging.error(f"Error searching region {region}: {e}")
                continue

        # If we encountered network or HTTP issues across regions, propagate a controlled error
        if network_issue:
            raise ValueError("Could not fetch metadata")

        # Final error if we couldn't determine any metadata
        if not asin:
            raise ValueError("ASIN could not be determined")
        raise ValueError(f"Could not fetch metadata for '{name}' [{asin}]")


# Additional compatibility functions for existing tests and code
def clean_metadata(item: dict[str, Any]) -> dict[str, Any]:
    """Compatibility wrapper that returns legacy-shaped metadata for templates/tests.

    - Normalizes series into a readable string like "Series Name (Vol. 1.5)"
    - Ensures `narrators` is a list and `series` is an empty string when missing
    - Exposes `runtime_minutes` and both `cover` and `cover_url`
    """
    audible = Audible()
    base = audible.clean_result(item)

    result: dict[str, Any] = {}
    result["title"] = base.get("title")
    # Prefer cleaned authors (exclude translators/illustrators)
    authors_raw = item.get("authors") or []
    filtered_authors = clean_author_list(authors_raw)
    result["authors_raw"] = authors_raw
    result["author"] = filtered_authors[0] if filtered_authors else None

    # Narrators as list and narrator string
    narrator_raw = base.get("narrator")
    if narrator_raw:
        narrators = [n.strip() for n in narrator_raw.split(",") if n.strip()]
        narrator_str = narrator_raw
    else:
        # Fallback to raw item structure
        narrators_obj = item.get("narrators") or []
        narrators = [n.get("name") for n in narrators_obj if n.get("name")]
        narrator_str = ", ".join(narrators) if narrators else ""

    result["narrators"] = narrators
    result["narrator"] = narrator_str

    # Series formatting - prefer primary series only
    series_list = base.get("series")
    if series_list and isinstance(series_list, list) and len(series_list) > 0:
        entry = series_list[0]
        name = entry.get("series") or ""
        seq = entry.get("sequence") or ""
        if seq:
            result["series"] = f"{name} (Vol. {seq})"
        else:
            result["series"] = name
    else:
        result["series"] = ""
    # Also expose raw primary series from original item
    result["series_primary"] = item.get("seriesPrimary")

    # Genres and tags
    result["genres"] = base.get("genres") or []
    result["tags"] = base.get("tags") or ""

    # Summary / description (preserve raw description fields)
    result["summary"] = item.get("summary") or base.get("description") or ""
    result["description"] = item.get("description") or base.get("description") or ""

    # Runtime and cover
    result["runtime_minutes"] = base.get("duration", 0)
    result["cover"] = base.get("cover")
    result["cover_url"] = base.get("cover")

    # Preserve other useful fields for compatibility
    result["asin"] = base.get("asin")
    # Release date - prefer raw YYYY-MM-DD if available
    result["release_date"] = item.get("releaseDate") or base.get("publishedYear") or ""

    return result
