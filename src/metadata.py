import re
import requests
import logging
from typing import Optional, List, Dict, Any
from functools import lru_cache
from src.config import load_config
from src.utils import validate_payload, clean_author_list

# LRU cache for metadata lookups to avoid unbounded growth
@lru_cache(maxsize=512)
def get_cached_metadata(asin: str, region: str, api_url: str) -> Optional[Dict[str, Any]]:
    try:
        resp = requests.get(f"{api_url}/{asin}", params={'region': region})
        resp.raise_for_status()
        data = resp.json()
        if data.get('asin'):
            return clean_metadata(data)
    except Exception as e:
        logging.error(f"Error fetching ASIN {asin}/{region}: {e}")
    return None

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


def get_audible_asin(title: str, author: str) -> Optional[str]:
    """
    Scrape Audible search results to find the first ASIN for the given title and author.
    """
    # Requires beautifulsoup4: pip install beautifulsoup4
    try:
        from bs4 import BeautifulSoup  # type: ignore
        from bs4.element import Tag    # type: ignore
    except ImportError:
        logging.error("beautifulsoup4 is not installed, cannot scrape Audible.")
        return None

    query = f"{title} {author}".strip().replace(" ", "+")
    url = f"https://www.audible.com/search?keywords={query}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        for link in soup.find_all('a', href=True):
            if not isinstance(link, Tag):
                continue
            href = link.attrs.get('href')
            if not isinstance(href, str):
                continue
            m = re.search(r'/pd/[^/]+/([A-Z0-9]{10})', href)
            if m:
                asin = m.group(1)
                logging.info(f"Scraped ASIN from Audible: {asin}")
                return asin
    except Exception as e:
        logging.error(f"Error scraping Audible for ASIN: {e}")
    return None


def clean_series_sequence(series_name: str, sequence: str) -> str:
    import re
    if not sequence:
        return ''
    m = re.search(r'\.\d+|\d+(?:\.\d+)?', sequence)
    updated_sequence = m.group(0) if m else sequence
    if sequence != updated_sequence:
        logging.debug(f'Series "{series_name}" sequence cleaned from "{sequence}" to "{updated_sequence}"')
    return updated_sequence


def clean_metadata(item: Dict[str, Any]) -> Dict[str, Any]:
    # Series raw
    series = []
    if item.get('seriesPrimary'):
        name = item['seriesPrimary'].get('name')
        seq = clean_series_sequence(name, item['seriesPrimary'].get('position', ''))
        series.append({'series': name, 'sequence': seq})
    if item.get('seriesSecondary'):
        name = item['seriesSecondary'].get('name')
        seq = clean_series_sequence(name, item['seriesSecondary'].get('position', ''))
        series.append({'series': name, 'sequence': seq})

    # Genres and tags
    genres = [g['name'] for g in item.get('genres', []) if g.get('type') == 'genre']
    tags = [g['name'] for g in item.get('genres', []) if g.get('type') == 'tag']

    # Authors
    authors_raw = item.get('authors', [])
    authors_clean = clean_author_list(authors_raw)
    author_str = ', '.join(authors_clean) if authors_clean else None

    # Narrators
    narrators_list = [n.get('name') for n in item.get('narrators', [])] if item.get('narrators') else []
    narrator_str = ', '.join(narrators_list) if narrators_list else None

    # Build display string for the series (first one only)
    series_display = ""
    if series:
        s = series[0]
        if s['series'] and s['sequence']:
            series_display = f"{s['series']} (Vol. {s['sequence']})"
        elif s['series']:
            series_display = s['series']

    return {
        'title': item.get('title'),
        'subtitle': item.get('subtitle'),
        'author': author_str,
        'authors_raw': authors_raw,
        'narrator': narrator_str,
        'narrators': narrators_list,
        'publisher': item.get('publisherName'),
        'publishedYear': item.get('releaseDate', '').split('-')[0] if item.get('releaseDate') else None,
        'release_date': item.get('releaseDate'),
        'description': item.get('summary') or item.get('description'),
        'cover': item.get('image'),
        'cover_url': item.get('image'),  # always present
        'asin': item.get('asin'),
        'isbn': item.get('isbn'),
        'genres': genres or None,
        'tags': ', '.join(tags) if tags else None,
        'series': series_display,
        'series_primary': item.get('seriesPrimary', {}),
        'series_raw': series or None,
        'language': item.get('language', '').capitalize() if item.get('language') else None,
        'duration': int(item.get('runtimeLengthMin', 0)) if item.get('runtimeLengthMin') else 0,
        'runtime_minutes': item.get('runtimeLengthMin', 0),
        'region': item.get('region'),
        'rating': item.get('rating'),
        'abridged': item.get('formatType') == 'abridged'
    }


def fetch_metadata(payload: dict, regions: Optional[List[str]] = None) -> dict:
    """
    Enhanced fetch: try ASIN search with region failover, caching, short-circuit on first good match,
    and best-match via Levenshtein distance for title.
    """
    config = load_config()
    req_keys = config.get('payload', {}).get('required_keys', [])
    if not validate_payload(payload, req_keys):
        raise ValueError(f"Payload missing required keys: {req_keys}")

    name = payload.get('name', '')
    title = payload.get('title') or name
    author = payload.get('author', '')
    asin_regex = config.get('payload', {}).get('asin_regex')
    match = re.search(asin_regex, name) if asin_regex else None
    asin = match.group(0) if match else None
    if not asin:
        logging.warning(f"ASIN not in name '{name}', scraping Audible")
        asin = get_audible_asin(title, author)
        if not asin:
            raise ValueError(f"ASIN could not be determined for '{name}'")
    asin = asin.upper()

    # Build region list: user-specified or default sequence
    default_regions = ['us','ca','uk','au','fr','de','jp','it','in','es']
    if regions:
        seq = [r for r in regions if r]
        seq += [r for r in default_regions if r not in seq]
    else:
        seq = default_regions

    api_url = config.get('audnex', {}).get('api_url', '').rstrip('/')

    for region in seq:
        meta = get_cached_metadata(asin, region, api_url)
        if meta:
            logging.debug(f"Cache hit or fresh fetch for {asin}/{region}")
            return meta

        # 2) Fallback: search via Audible catalog
        try:
            url = 'https://api.audible.com/1.0/catalog/products'
            params = {'num_results':'10','products_sort_by':'Relevance','title':title}
            if author:
                params['author'] = author
            resp = requests.get(url, params=params)
            resp.raise_for_status()
            products = resp.json().get('products', []) or []
        except Exception as e:
            logging.error(f"Search error for title '{title}' author '{author}': {e}")
            products = []

        best_item = None
        best_dist = float('inf')
        for prod in products:
            asin2 = prod.get('asin')
            if not asin2:
                continue
            cand = get_cached_metadata(asin2, region, api_url)
            if not cand:
                continue
            title_cand_val = cand.get('title', '')
            if not isinstance(title_cand_val, str):
                continue
            title_cand = title_cand_val.lower()
            dist = levenshtein_distance(title_cand, title.lower())
            if dist < best_dist:
                best_item = cand
                best_dist = dist
                if dist == 0:
                    break
        if best_item:
            return best_item

    raise ValueError(f"Could not fetch metadata for '{name}' [{asin}]")

def fetch_metadata_audiobookshelf(payload: dict, region: str = 'us') -> Optional[dict]:
    asin = payload.get('asin')
    title = payload.get('title')
    author = payload.get('author')
    base_url = 'https://api.audnex.us/books/'

    # Try ASIN first
    if asin:
        url = f"{base_url}{asin}"
        params = {'region': region}
        resp = requests.get(url, params=params)
        if resp.ok and resp.json().get('asin'):
            return clean_metadata(resp.json())

    # Fallback: search by title/author
    search_url = f"https://api.audible.com/1.0/catalog/products"
    params = {
        'num_results': 10,
        'products_sort_by': 'Relevance',
        'title': title
    }
    if author:
        params['author'] = author
    resp = requests.get(search_url, params=params)
    if resp.ok and resp.json().get('products'):
        for product in resp.json()['products']:
            asin = product.get('asin')
            if asin:
                # Fetch full metadata for each ASIN
                meta_resp = requests.get(f"{base_url}{asin}", params={'region': region})
                if meta_resp.ok and meta_resp.json().get('asin'):
                    return clean_metadata(meta_resp.json())
    return None