import re
import requests
import logging
import time
from typing import Optional, List, Dict, Any
from functools import lru_cache
from urllib.parse import urlencode
from src.config import load_config
from src.utils import validate_payload, clean_author_list

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
    def __init__(self, response_timeout: int = 30000):
        self.response_timeout = response_timeout
        self.region_map = {
            'us': '.com',
            'ca': '.ca',
            'uk': '.co.uk',
            'au': '.com.au',
            'fr': '.fr',
            'de': '.de',
            'jp': '.co.jp',
            'it': '.it',
            'in': '.in',
            'es': '.es'
        }

    def clean_series_sequence(self, series_name: str, sequence: str) -> str:
        """
        Audible will sometimes send sequences with "Book 1" or "2, Dramatized Adaptation"
        Clean to extract just the number portion
        """
        if not sequence:
            return ''
        # match any number with optional decimal (e.g, 1 or 1.5 or .5)
        match = re.search(r'\.\d+|\d+(?:\.\d+)?', sequence)
        updated_sequence = match.group(0) if match else sequence
        if sequence != updated_sequence:
            logging.debug(f'[Audible] Series "{series_name}" sequence was cleaned from "{sequence}" to "{updated_sequence}"')
        return updated_sequence

    def clean_result(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and format the result from Audnex API"""
        title = item.get('title')
        subtitle = item.get('subtitle')
        asin = item.get('asin')
        authors = item.get('authors', [])
        narrators = item.get('narrators', [])
        publisher_name = item.get('publisherName')
        summary = item.get('summary')
        release_date = item.get('releaseDate')
        image = item.get('image')
        genres = item.get('genres', [])
        series_primary = item.get('seriesPrimary')
        series_secondary = item.get('seriesSecondary')
        language = item.get('language')
        runtime_length_min = item.get('runtimeLengthMin')
        format_type = item.get('formatType')
        isbn = item.get('isbn')

        series = []
        if series_primary:
            series.append({
                'series': series_primary.get('name'),
                'sequence': self.clean_series_sequence(
                    series_primary.get('name', ''), 
                    series_primary.get('position', '')
                )
            })
        if series_secondary:
            series.append({
                'series': series_secondary.get('name'),
                'sequence': self.clean_series_sequence(
                    series_secondary.get('name', ''), 
                    series_secondary.get('position', '')
                )
            })

        genres_filtered = [g.get('name') for g in genres if g.get('type') == 'genre']
        tags_filtered = [g.get('name') for g in genres if g.get('type') == 'tag']

        return {
            'title': title,
            'subtitle': subtitle or None,
            'author': ', '.join([a.get('name', '') for a in authors]) if authors else None,
            'narrator': ', '.join([n.get('name', '') for n in narrators]) if narrators else None,
            'publisher': publisher_name,
            'publishedYear': release_date.split('-')[0] if release_date else None,
            'description': summary or None,
            'cover': image,
            'asin': asin,
            'isbn': isbn,
            'genres': genres_filtered if genres_filtered else None,
            'tags': ', '.join(tags_filtered) if tags_filtered else None,
            'series': series if series else None,
            'language': language.capitalize() if language else None,
            'duration': int(runtime_length_min) if runtime_length_min and str(runtime_length_min).isdigit() else 0,
            'region': item.get('region') or None,
            'rating': item.get('rating') or None,
            'abridged': format_type == 'abridged'
        }

    def asin_search(self, asin: str, region: str = 'us', timeout: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Search for a book by ASIN"""
        if not asin:
            return None
        if not timeout:
            timeout = self.response_timeout

        asin = asin.upper()
        region_query = f'?region={region}' if region else ''
        url = f'https://api.audnex.us/books/{asin}{region_query}'
        logging.debug(f'[Audible] ASIN url: {url}')
        
        try:
            response = requests.get(url, timeout=timeout/1000)  # Convert ms to seconds
            response.raise_for_status()
            data = response.json()
            if not data.get('asin'):
                return None
            return data
        except Exception as error:
            logging.error(f'[Audible] ASIN search error: {error}')
            return None

    def search(self, title: str, author: str = '', asin: str = '', region: str = 'us', timeout: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for books using title, author, and/or ASIN"""
        if region and region not in self.region_map:
            logging.error(f'[Audible] search: Invalid region {region}')
            region = 'us'
        
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
            query_obj = {
                'num_results': '10',
                'products_sort_by': 'Relevance',
                'title': title
            }
            if author:
                query_obj['author'] = author
            
            query_string = urlencode(query_obj)
            tld = self.region_map.get(region, '.com')
            url = f'https://api.audible{tld}/1.0/catalog/products?{query_string}'
            logging.debug(f'[Audible] Search url: {url}')
            
            try:
                response = requests.get(url, timeout=timeout/1000)
                response.raise_for_status()
                data = response.json()
                
                if data.get('products'):
                    # Get detailed info for each product
                    detailed_items = []
                    for result in data['products']:
                        if result.get('asin'):
                            detailed_item = self.asin_search(result['asin'], region, timeout)
                            if detailed_item:
                                detailed_items.append(detailed_item)
                    items = detailed_items
                else:
                    items = []
            except Exception as error:
                logging.error(f'[Audible] query search error: {error}')
                items = []
        
        # Clean and return results
        return [self.clean_result(item) for item in items if item]


class Audnexus:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, 'initialized'):
            return
        
        self.base_url = 'https://api.audnex.us'
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
    
    def _process_request(self, url: str, max_retries: int = 1) -> Optional[Dict[str, Any]]:
        """Process request with rate limiting and retry logic"""
        for attempt in range(max_retries + 1):
            try:
                self._throttle_request()
                response = requests.get(url)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    retry_after = int(e.response.headers.get('retry-after', 5))
                    logging.warning(f'[Audnexus] Rate limit exceeded. Retrying in {retry_after} seconds.')
                    time.sleep(retry_after)
                    continue
                else:
                    logging.error(f'[Audnexus] HTTP error: {e}')
                    return None
            except Exception as e:
                logging.error(f'[Audnexus] Request error: {e}')
                return None
        return None
    
    def author_asins_request(self, name: str, region: str = '') -> List[Dict[str, Any]]:
        """Get author ASINs by name"""
        params = {'name': name}
        if region:
            params['region'] = region
        
        url = f"{self.base_url}/authors?{urlencode(params)}"
        logging.info(f'[Audnexus] Searching for author "{url}"')
        
        result = self._process_request(url)
        if result is None:
            return []
        return result if isinstance(result, list) else [result]
    
    def author_request(self, asin: str, region: str = '') -> Optional[Dict[str, Any]]:
        """Get author details by ASIN"""
        if not is_valid_asin(asin.upper()):
            logging.error(f'[Audnexus] Invalid ASIN {asin}')
            return None
        
        asin = asin.upper()
        params = {'region': region} if region else {}
        url = f"{self.base_url}/authors/{asin}"
        if params:
            url += f"?{urlencode(params)}"
        
        logging.info(f'[Audnexus] Searching for author "{url}"')
        
        result = self._process_request(url)
        return result
    
    def find_author_by_asin(self, asin: str, region: str = '') -> Optional[Dict[str, Any]]:
        """Find author by ASIN"""
        author = self.author_request(asin, region)
        
        if author:
            return {
                'asin': author.get('asin'),
                'description': author.get('description'),
                'image': author.get('image') or None,
                'name': author.get('name')
            }
        return None
    
    def find_author_by_name(self, name: str, region: str = '', max_levenshtein: int = 3) -> Optional[Dict[str, Any]]:
        """Find author by name with fuzzy matching"""
        logging.debug(f'[Audnexus] Looking up author by name {name}')
        author_asin_objs = self.author_asins_request(name, region)
        
        closest_match = None
        for author_asin_obj in author_asin_objs:
            author_name = author_asin_obj.get('name', '')
            distance = levenshtein_distance(author_name, name)
            author_asin_obj['levenshtein_distance'] = distance
            
            if not closest_match or closest_match['levenshtein_distance'] > distance:
                closest_match = author_asin_obj
        
        if not closest_match or closest_match['levenshtein_distance'] > max_levenshtein:
            return None
        
        author = self.author_request(closest_match.get('asin', ''), region)
        if not author:
            return None
        
        return {
            'asin': author.get('asin'),
            'description': author.get('description'),
            'image': author.get('image') or None,
            'name': author.get('name')
        }
    
    def get_chapters_by_asin(self, asin: str, region: str = '') -> Optional[Dict[str, Any]]:
        """Get chapters for a book by ASIN"""
        logging.debug(f'[Audnexus] Get chapters for ASIN {asin}/{region}')
        
        asin = asin.upper()
        params = {'region': region} if region else {}
        url = f"{self.base_url}/books/{asin}/chapters"
        if params:
            url += f"?{urlencode(params)}"
        
        result = self._process_request(url)
        return result

# Main fetch metadata function compatible with existing code
def fetch_metadata(payload: dict, regions: Optional[List[str]] = None) -> dict:
    """
    Enhanced fetch using AudioBookShelf-style logic
    """
    config = load_config()
    req_keys = config.get('payload', {}).get('required_keys', [])
    if not validate_payload(payload, req_keys):
        raise ValueError(f"Payload missing required keys: {req_keys}")

    name = payload.get('name', '')
    title = payload.get('title') or name
    author = payload.get('author', '')
    
    # Extract ASIN from name if present
    asin_regex = config.get('payload', {}).get('asin_regex')
    match = re.search(asin_regex, name) if asin_regex else None
    asin = match.group(0) if match else None
    
    # Use provided regions or default sequence
    if not regions:
        regions = ['us', 'ca', 'uk', 'au', 'fr', 'de', 'jp', 'it', 'in', 'es']
    
    audible = Audible()
    
    # Try each region until we get results
    for region in regions:
        try:
            results = audible.search(title=title, author=author, asin=asin or '', region=region)
            if results:
                # Return the first (best) result
                return results[0]
        except Exception as e:
            logging.error(f"Error searching region {region}: {e}")
            continue
    
    raise ValueError(f"Could not fetch metadata for '{name}' [{asin}]")


def fetch_metadata_audiobookshelf(payload: dict, region: str = 'us') -> Optional[dict]:
    """
    Direct AudioBookShelf-style metadata fetch
    """
    asin = payload.get('asin')
    title = payload.get('title')
    author = payload.get('author')
    
    audible = Audible()
    results = audible.search(title=title or '', author=author or '', asin=asin or '', region=region)
    
    return results[0] if results else None


# Compatibility functions for existing code
def get_audible_asin(title: str, author: str) -> Optional[str]:
    """
    Get ASIN by searching Audible - simplified version
    """
    try:
        audible = Audible()
        results = audible.search(title=title, author=author, region='us')
        if results:
            return results[0].get('asin')
    except Exception as e:
        logging.error(f"Error getting ASIN for '{title}' by '{author}': {e}")
    return None


def clean_series_sequence(series_name: str, sequence: str) -> str:
    """Compatibility function - use Audible class method"""
    audible = Audible()
    return audible.clean_series_sequence(series_name, sequence)


def clean_metadata(item: Dict[str, Any]) -> Dict[str, Any]:
    """Compatibility function - use Audible class method"""
    audible = Audible()
    return audible.clean_result(item)