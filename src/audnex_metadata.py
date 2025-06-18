#!/usr/bin/env python3
"""
Audnex API metadata fetcher
Gets audiobook metadata from api.audnex.us using ASIN
"""

import requests
import logging
import time
import sys
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/audnex_metadata.log')
    ]
)

class AudnexMetadata:
    def __init__(self):
        self.config = load_config()
        self.audnex_config = self.config.get('metadata', {}).get('audnex', {})
        self.base_url = self.audnex_config.get('base_url', 'https://api.audnex.us')
        self.rate_limit = self.audnex_config.get('rate_limit_seconds', 0.15)
        self.global_rate_limit = self.config.get('metadata', {}).get('rate_limit_seconds', 120)
        self.last_request_time = 0
        self.last_global_request_time = 0
        
    def _throttle_request(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        
        # Local rate limiting (150ms between requests)
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit:
            time.sleep(self.rate_limit - time_since_last)
        
        self.last_request_time = time.time()
    
    def _check_global_rate_limit(self):
        """Check if we need to wait for global rate limit (2 minutes)."""
        current_time = time.time()
        time_since_last_global = current_time - self.last_global_request_time
        
        if time_since_last_global < self.global_rate_limit:
            wait_time = self.global_rate_limit - time_since_last_global
            logging.info(f"Global rate limit: waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)
        
        self.last_global_request_time = time.time()
    
    def _make_request(self, url: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Make a request to the Audnex API with rate limiting and retry logic."""
        self._throttle_request()
        self._check_global_rate_limit()
        
        for attempt in range(max_retries):
            try:
                logging.debug(f"Making request to: {url}")
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                logging.debug(f"Response received, status: {response.status_code}")
                return data
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    retry_after = int(e.response.headers.get('retry-after', 5))
                    logging.warning(f'Rate limit exceeded. Retrying in {retry_after} seconds.')
                    time.sleep(retry_after)
                    continue
                else:
                    logging.error(f'HTTP error: {e}')
                    if attempt == max_retries - 1:
                        return None
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
            except requests.exceptions.RequestException as e:
                logging.error(f'Request error: {e}')
                if attempt == max_retries - 1:
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff
                
        return None
    
    def get_book_by_asin(self, asin: str, region: str = 'us') -> Optional[Dict[str, Any]]:
        """Get book metadata by ASIN."""
        if not asin or len(asin) != 10:
            logging.error(f"Invalid ASIN format: {asin}")
            return None
        
        asin = asin.upper()
        params = {'region': region} if region else {}
        url = f"{self.base_url}/books/{asin}"
        
        if params:
            url += f"?{urlencode(params)}"
        
        logging.info(f"Fetching book metadata for ASIN: {asin} (region: {region})")
        
        result = self._make_request(url)
        
        if result and result.get('asin'):
            logging.info(f"✅ Book metadata found for ASIN: {asin}")
            return self._clean_book_metadata(result)
        else:
            logging.warning(f"❌ No metadata found for ASIN: {asin}")
            return None
    
    def get_chapters_by_asin(self, asin: str, region: str = 'us') -> Optional[Dict[str, Any]]:
        """Get chapter information by ASIN."""
        if not asin or len(asin) != 10:
            logging.error(f"Invalid ASIN format: {asin}")
            return None
        
        asin = asin.upper()
        params = {'region': region} if region else {}
        url = f"{self.base_url}/books/{asin}/chapters"
        
        if params:
            url += f"?{urlencode(params)}"
        
        logging.info(f"Fetching chapters for ASIN: {asin} (region: {region})")
        
        result = self._make_request(url)
        
        if result:
            logging.info(f"✅ Chapters found for ASIN: {asin}")
            return result
        else:
            logging.warning(f"❌ No chapters found for ASIN: {asin}")
            return None
    
    def search_author_by_name(self, name: str, region: str = 'us') -> List[Dict[str, Any]]:
        """Search for authors by name."""
        params = {'name': name}
        if region:
            params['region'] = region
        
        url = f"{self.base_url}/authors?{urlencode(params)}"
        
        logging.info(f"Searching for author: {name} (region: {region})")
        
        result = self._make_request(url)
        
        if result:
            if isinstance(result, list):
                logging.info(f"✅ Found {len(result)} author results for: {name}")
                return result
            else:
                logging.info(f"✅ Found 1 author result for: {name}")
                return [result]
        else:
            logging.warning(f"❌ No authors found for: {name}")
            return []
    
    def get_author_by_asin(self, asin: str, region: str = 'us') -> Optional[Dict[str, Any]]:
        """Get author information by ASIN."""
        if not asin or len(asin) != 10:
            logging.error(f"Invalid ASIN format: {asin}")
            return None
        
        asin = asin.upper()
        params = {'region': region} if region else {}
        url = f"{self.base_url}/authors/{asin}"
        
        if params:
            url += f"?{urlencode(params)}"
        
        logging.info(f"Fetching author for ASIN: {asin} (region: {region})")
        
        result = self._make_request(url)
        
        if result and result.get('asin'):
            logging.info(f"✅ Author found for ASIN: {asin}")
            return result
        else:
            logging.warning(f"❌ No author found for ASIN: {asin}")
            return None
    
    def _clean_book_metadata(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and format book metadata from Audnex response."""
        # Extract basic information
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
        
        # Process series information
        series = []
        if series_primary:
            series.append({
                'series': series_primary.get('name'),
                'sequence': self._clean_series_sequence(
                    series_primary.get('name', ''), 
                    series_primary.get('position', '')
                )
            })
        if series_secondary:
            series.append({
                'series': series_secondary.get('name'),
                'sequence': self._clean_series_sequence(
                    series_secondary.get('name', ''), 
                    series_secondary.get('position', '')
                )
            })
        
        # Filter genres and tags
        genres_filtered = [g.get('name') for g in genres if g.get('type') == 'genre']
        tags_filtered = [g.get('name') for g in genres if g.get('type') == 'tag']
        
        # Build clean metadata object
        cleaned = {
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
            'abridged': format_type == 'abridged',
            
            # Additional fields for compatibility
            'authors_raw': authors,
            'narrators_raw': narrators,
            'series_raw': series,
            'runtime_minutes': runtime_length_min,
            'release_date': release_date,
            'cover_url': image
        }
        
        return cleaned
    
    def _clean_series_sequence(self, series_name: str, sequence: str) -> str:
        """Clean series sequence to extract just the number portion."""
        if not sequence:
            return ''
        
        import re
        # Match any number with optional decimal (e.g, 1 or 1.5 or .5)
        match = re.search(r'\.\d+|\d+(?:\.\d+)?', sequence)
        updated_sequence = match.group(0) if match else sequence
        
        if sequence != updated_sequence:
            logging.debug(f'Series "{series_name}" sequence cleaned from "{sequence}" to "{updated_sequence}"')
        
        return updated_sequence


def main():
    """Main function for command line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Audnex Metadata Fetcher")
    parser.add_argument("asin", help="ASIN to fetch metadata for")
    parser.add_argument("--region", default="us", help="Audible region (default: us)")
    parser.add_argument("--chapters", action="store_true", help="Also fetch chapter information")
    args = parser.parse_args()
    
    fetcher = AudnexMetadata()
    
    # Get book metadata
    metadata = fetcher.get_book_by_asin(args.asin, region=args.region)
    
    if metadata:
        print("✅ Book metadata found:")
        print(f"  Title: {metadata.get('title')}")
        print(f"  Author: {metadata.get('author')}")
        print(f"  ASIN: {metadata.get('asin')}")
        print(f"  Publisher: {metadata.get('publisher')}")
        print(f"  Duration: {metadata.get('duration')} minutes")
        if metadata.get('series'):
            for series in metadata['series']:
                print(f"  Series: {series['series']} #{series['sequence']}")
        
        # Get chapters if requested
        if args.chapters:
            chapters = fetcher.get_chapters_by_asin(args.asin, region=args.region)
            if chapters:
                print(f"\n✅ Found {len(chapters.get('chapters', []))} chapters")
    else:
        print(f"❌ No metadata found for ASIN: {args.asin}")


if __name__ == "__main__":
    main()