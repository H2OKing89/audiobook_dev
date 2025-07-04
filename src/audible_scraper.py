#!/usr/bin/env python3
"""
Audible.com metadata fallback scraper
Searches for audiobook metadata using Audible's search API
"""

import requests
import logging
import time
import sys
import re
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import load_config
from src.audnex_metadata import AudnexMetadata

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/audible_scraper.log')
    ]
)

class AudibleScraper:
    def __init__(self):
        self.config = load_config()
        self.audible_config = self.config.get('metadata', {}).get('audible', {})
        self.base_url = self.audible_config.get('base_url', 'https://api.audible.com')
        self.search_endpoint = self.audible_config.get('search_endpoint', '/1.0/catalog/products')
        self.global_rate_limit = self.config.get('metadata', {}).get('rate_limit_seconds', 120)
        self.last_global_request_time = 0
        self.audnex = AudnexMetadata()
        
        # Region mapping for different Audible domains
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
    
    def _check_global_rate_limit(self):
        """Check if we need to wait for global rate limit (2 minutes)."""
        current_time = time.time()
        time_since_last_global = current_time - self.last_global_request_time
        
        if time_since_last_global < self.global_rate_limit:
            wait_time = self.global_rate_limit - time_since_last_global
            logging.info(f"Global rate limit: waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)
        
        self.last_global_request_time = time.time()
    
    def _is_valid_asin(self, asin: str) -> bool:
        """Validate ASIN format (10 characters, alphanumeric)."""
        if not asin or not isinstance(asin, str):
            return False
        return len(asin) == 10 and asin.isalnum()
    
    def _product_to_book(self, product: dict) -> dict:
        """Convert Audible API product to a structured book dictionary."""
        return {
            "asin": product.get("asin"),
            "title": product.get("title"),
            "subtitle": product.get("subtitle"),
            "description": product.get("publisher_summary"),
            "length": product.get("runtime_length_min"),
            "authors": [a.get("name") for a in product.get("authors", [])],
            "narrators": [n.get("name") for n in product.get("narrators", [])],
            "publisher": product.get("publisher_name"),
            "publishYear": product.get("publication_datetime"),
            "releaseDate": product.get("issue_date"),
            "series": [
                {"title": s.get("title"), "sequence": s.get("sequence")}
                for s in product.get("series", [])
            ],
            "language": product.get("language"),
            "genres": [
                item["name"]
                for cl in product.get("category_ladders", [])
                for i, item in enumerate(cl.get("ladder", [])) if i == 0
            ],
            "tags": [
                item["name"]
                for cl in product.get("category_ladders", [])
                for i, item in enumerate(cl.get("ladder", [])) if i > 0
            ],
        }

    def search_by_title_author(self, title: str, author: str = '', region: str = 'us') -> List[Dict[str, Any]]:
        """Search for audiobooks by title and author using Audible's catalog API, only English results."""
        if region not in self.region_map:
            logging.error(f"Invalid region: {region}")
            region = 'us'
        self._check_global_rate_limit()
        params = {
            'num_results': '10',
            'products_sort_by': 'Relevance',
            'title': title
        }
        if author:
            params['author'] = author
        tld = self.region_map[region]
        url = f"https://api.audible{tld}{self.search_endpoint}?{urlencode(params)}"
        logging.info(f"Searching Audible catalog: title='{title}', author='{author}', region={region}")
        logging.debug(f"Search URL: {url}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            products = data.get('products', [])
            logging.info(f"Found {len(products)} products from Audible search")
            if not products:
                return []
            detailed_results = []
            for product in products:
                # Only include English books
                if product.get("language", "").lower() != "english":
                    continue
                asin = product.get('asin')
                if not asin:
                    continue
                # Get detailed metadata from Audnex
                metadata = self.audnex.get_book_by_asin(asin, region=region)
                if metadata and metadata.get("language", "").lower() == "english":
                    detailed_results.append(self._product_to_book(metadata))
                    logging.debug(f"Got detailed metadata for ASIN: {asin}")
                elif not metadata:
                    # Fallback to product if Audnex fails
                    detailed_results.append(self._product_to_book(product))
                    logging.debug(f"No detailed metadata for ASIN: {asin}, using fallback product data")
            return detailed_results
        except requests.exceptions.RequestException as e:
            logging.error(f"Audible search error: {e}")
            return []
    
    def search_by_asin(self, asin: str, region: str = 'us') -> Optional[Dict[str, Any]]:
        """Search for audiobook by ASIN (delegates to Audnex)."""
        if not self._is_valid_asin(asin):
            logging.error(f"Invalid ASIN format: {asin}")
            return None
        
        logging.info(f"Searching by ASIN: {asin} (region: {region})")
        
        # Use Audnex for ASIN lookups as it's more reliable
        return self.audnex.get_book_by_asin(asin, region=region)
    
    def search(self, title: str = '', author: str = '', asin: str = '', region: str = 'us') -> List[Dict[str, Any]]:
        """
        Comprehensive search using multiple strategies.
        Priority: ASIN -> Title as ASIN -> Title/Author search
        """
        results = []
        
        # Strategy 1: Direct ASIN search
        if asin and self._is_valid_asin(asin.upper()):
            logging.info(f"Strategy 1: Searching by provided ASIN: {asin}")
            result = self.search_by_asin(asin.upper(), region=region)
            if result:
                results.append(result)
                return results
        
        # Strategy 2: Check if title looks like an ASIN
        if title and self._is_valid_asin(title.upper()):
            logging.info(f"Strategy 2: Title looks like ASIN: {title}")
            result = self.search_by_asin(title.upper(), region=region)
            if result:
                results.append(result)
                return results
        
        # Strategy 3: Title/Author search via Audible catalog
        if title:
            logging.info(f"Strategy 3: Searching by title/author: '{title}' by '{author}'")
            results = self.search_by_title_author(title, author, region=region)
        
        return results
    
    def extract_title_author_from_name(self, name: str) -> tuple[str, str]:
        """Extract title and author from torrent-style names."""
        # Common patterns in torrent names
        patterns = [
            r'^(.+?)\s+by\s+(.+?)\s*\[',  # "Title by Author [extras]"
            r'^(.+?)\s+by\s+(.+?)$',      # "Title by Author"
            r'^(.+?)\s+-\s+(.+?)\s*\[',   # "Title - Author [extras]"  
            r'^(.+?)\s+-\s+(.+?)$',       # "Title - Author"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                author = match.group(2).strip()
                logging.debug(f"Extracted from '{name}': title='{title}', author='{author}'")
                return title, author
        
        # Fallback: assume entire name is title
        logging.debug(f"Could not extract author from '{name}', using as title")
        return name.strip(), ""
    
    def search_from_webhook_name(self, name: str, region: str = 'us') -> List[Dict[str, Any]]:
        """Search for metadata using a webhook-style name."""
        logging.info(f"Searching from webhook name: '{name}'")
        
        # Extract title and author
        title, author = self.extract_title_author_from_name(name)
        
        # Search using extracted information
        return self.search(title=title, author=author, region=region)


def main():
    """Main function for command line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Audible Metadata Scraper")
    parser.add_argument("--title", help="Book title to search for")
    parser.add_argument("--author", default="", help="Book author to search for")
    parser.add_argument("--asin", help="ASIN to search for")
    parser.add_argument("--name", help="Webhook-style name to parse and search")
    parser.add_argument("--region", default="us", help="Audible region (default: us)")
    args = parser.parse_args()
    
    scraper = AudibleScraper()
    
    # Determine search method
    if args.name:
        results = scraper.search_from_webhook_name(args.name, region=args.region)
    elif args.asin:
        result = scraper.search_by_asin(args.asin, region=args.region)
        results = [result] if result else []
    elif args.title:
        results = scraper.search(title=args.title, author=args.author, region=args.region)
    else:
        print("Error: Must provide --title, --asin, or --name")
        return
    
    # Display results
    if results:
        print(f"✅ Found {len(results)} result(s):")
        for i, result in enumerate(results, 1):
            print(f"\nResult {i}:")
            print(f"  Title: {result.get('title')}")
            print(f"  Author: {result.get('author')}")
            print(f"  ASIN: {result.get('asin')}")
            print(f"  Publisher: {result.get('publisher')}")
            print(f"  Duration: {result.get('length')} minutes")
            if result.get('series'):
                for series in result['series']:
                    print(f"  Series: {series['title']} #{series['sequence']}")
    else:
        print("❌ No results found")


if __name__ == "__main__":
    main()