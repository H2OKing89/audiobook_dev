import re
import requests
import logging
from typing import Optional
from src.config import load_config
from src.utils import validate_payload


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
                return asin
    except Exception as e:
        logging.error(f"Error scraping Audible for ASIN: {e}")
    return None


def fetch_metadata(payload: dict) -> dict:
    """
    Extract ASIN from payload, fetch metadata from Audnex API, fallback to Audible scrape if needed.
    """
    config = load_config()
    req_keys = config.get('payload', {}).get('required_keys', [])
    if not validate_payload(payload, req_keys):
        raise ValueError(f"Payload missing required keys: {req_keys}")

    name = payload.get('name', '')
    asin_regex = config.get('payload', {}).get('asin_regex')
    match = re.search(asin_regex, name) if asin_regex else None
    if match:
        asin = match.group(0)
    else:
        logging.warning(f"ASIN not found via regex in name: {name}, trying Audible search")
        title = payload.get('title') or name
        author = payload.get('author', '')
        asin = get_audible_asin(title, author)
        if not asin:
            raise ValueError(f"ASIN could not be determined for name: {name}")

    api_url = config.get('audnex', {}).get('api_url', '').rstrip('/')
    resp = requests.get(f"{api_url}/{asin}")
    resp.raise_for_status()
    data = resp.json()

    metadata = {
        'asin': asin,
        'title': data.get('title'),
        'author': None,
        'description': data.get('description'),
        'cover_url': data.get('image'),
        'narrators': [n.get('name') for n in data.get('narrators', [])],
        'publisher': data.get('publisherName'),
        'release_date': data.get('releaseDate'),
        'runtime_minutes': data.get('runtimeLengthMin'),
        'series_primary': data.get('seriesPrimary', {})
    }
    # Try to extract author from Audnex API response
    if 'authors' in data and isinstance(data['authors'], list) and data['authors']:
        # Use the first author with a name
        for author in data['authors']:
            if 'name' in author:
                metadata['author'] = author['name']
                break
    if not metadata['author']:
        # fallback to payload
        metadata['author'] = payload.get('author', '')
    return metadata