#!/usr/bin/env python3
"""
MyAnonamouse.net ASIN scraper
Extracts ASIN from MAM torrent pages using Playwright
"""

from playwright.async_api import async_playwright
from datetime import datetime
import json
import logging
import sys
import re
import time
import argparse
from typing import Optional, Dict, Any
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
        logging.FileHandler('logs/mam_scraper.log')
    ]
)

class MAMScraper:
    def __init__(self):
        self.config = load_config()
        self.mam_config = self.config.get('metadata', {}).get('mam', {})
        self.config_file = self.mam_config.get('config_file', 'mam_config.json')
        self.base_url = self.mam_config.get('base_url', 'https://www.myanonamouse.net')
        self.login_url = self.mam_config.get('login_url', 'https://www.myanonamouse.net/loggedin.php')
        self.global_rate_limit = self.config.get('metadata', {}).get('rate_limit_seconds', 120)
        self.last_global_request_time = 0
        
    def _check_global_rate_limit(self):
        """Check if we need to wait for global rate limit."""
        current_time = time.time()
        time_since_last_global = current_time - self.last_global_request_time
        
        if time_since_last_global < self.global_rate_limit:
            wait_time = self.global_rate_limit - time_since_last_global
            logging.info(f"Global rate limit: waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)
        
        self.last_global_request_time = time.time()
        
    def load_mam_config(self) -> Dict[str, Any]:
        """Load MAM-specific configuration from JSON file."""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            logging.info("MAM configuration loaded successfully")
            return config
        except FileNotFoundError:
            logging.error(f"MAM config file {self.config_file} not found")
            raise
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in MAM config file: {e}")
            raise

    def save_mam_config(self, config: Dict[str, Any]):
        """Save MAM configuration to JSON file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logging.info("MAM configuration saved successfully")
        except Exception as e:
            logging.error(f"Failed to save MAM config: {e}")
            raise

    async def login_and_get_cookies(self, email: str, password: str) -> Dict[str, str]:
        """Login to MAM and retrieve session cookies."""
        logging.info("Starting MAM login process...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            )
            
            try:
                page = await context.new_page()
                
                # Go to login page
                logging.info(f"Navigating to login page: {self.login_url}")
                await page.goto(self.login_url)
                await page.wait_for_load_state("networkidle")
                
                # Check if we're already on the login form
                if await page.locator("input[name='email']").count() == 0:
                    # Try going to the main page
                    logging.info(f"Trying main page: {self.base_url}")
                    await page.goto(self.base_url)
                    await page.wait_for_load_state("networkidle")
                
                # Look for login form
                email_input = page.locator("input[name='email'], input[type='email'], input[name='username']")
                password_input = page.locator("input[name='password'], input[type='password']")
                
                if await email_input.count() == 0:
                    logging.error("Could not find email input field")
                    with open('logs/login_page_debug.html', 'w', encoding='utf-8') as f:
                        f.write(await page.content())
                    raise Exception("Login form not found")
                
                logging.info("Found login form, filling credentials...")
                
                # Fill in credentials
                await email_input.fill(email)
                await password_input.fill(password)
                
                # Look for "Keep me logged in" checkbox
                keep_logged_in_selectors = [
                    "input[type='checkbox']",
                    "input[name='autolog']",
                    "input[name='remember']", 
                    "input[name='stay_logged_in']"
                ]
                
                for selector in keep_logged_in_selectors:
                    checkbox = page.locator(selector)
                    if await checkbox.count() > 0:
                        logging.info(f"Found keep-logged-in checkbox with selector: {selector}")
                        await checkbox.check()
                        break
                
                # Submit the form
                submit_button = page.locator("input[type='submit'], button[type='submit']").first
                
                if await submit_button.count() > 0:
                    logging.info("Submitting login form...")
                    await submit_button.click()
                else:
                    logging.info("No submit button found, trying Enter key")
                    await password_input.press("Enter")
                
                # Wait for navigation after login
                await page.wait_for_load_state("networkidle", timeout=10000)
                
                # Check if login was successful
                current_url = page.url
                logging.info(f"After login, current URL: {current_url}")
                
                # Look for signs of successful login
                if await page.locator("text=logout").count() > 0 or await page.locator("text=Logout").count() > 0:
                    logging.info("✅ Login successful! Found logout link")
                elif "login" in current_url.lower():
                    logging.error("❌ Login failed - still on login page")
                    raise Exception("Login failed - check credentials")
                else:
                    logging.info("Login appears successful (URL changed)")
                
                # Get cookies
                cookies = await context.cookies()
                logging.info(f"Retrieved {len(cookies)} cookies")
                
                # Extract session cookies
                session_cookies = {}
                for cookie in cookies:
                    cookie_name = cookie.get('name', '')
                    cookie_value = cookie.get('value', '')
                    if cookie_name in ['mam_id', 'session', 'PHPSESSID'] or 'session' in cookie_name.lower():
                        session_cookies[cookie_name] = cookie_value
                        logging.info(f"Found session cookie: {cookie_name}")
                
                if not session_cookies:
                    logging.warning("No obvious session cookies found, saving all cookies")
                    session_cookies = {cookie.get('name', ''): cookie.get('value', '') for cookie in cookies}
                
                return session_cookies
                
            except Exception as e:
                logging.error(f"Login process failed: {e}")
                raise
            finally:
                await browser.close()

    def extract_asin_from_page(self, page_source: str) -> Optional[str]:
        """Extract ASIN from page source."""
        logging.info("Starting ASIN extraction...")
        logging.info(f"Page source length: {len(page_source)} characters")
        
        # Primary pattern: ASIN:B0XXXXXXXX
        pattern = r'ASIN:([A-Z0-9]{10})'
        match = re.search(pattern, page_source)
        if match:
            asin = match.group(1)
            logging.info(f"ASIN successfully extracted: {asin}")
            return asin
        
        # Alternative patterns
        alternative_patterns = [
            r'asin[:\s=]+([A-Z0-9]{10})',  # Case insensitive
            r'ASIN[:\s=]+([A-Z0-9]{10})',  # Different separators
            r'B0[A-Z0-9]{8}',              # Direct B0 pattern
        ]
        
        for i, alt_pattern in enumerate(alternative_patterns):
            logging.info(f"Trying alternative pattern {i+1}: {alt_pattern}")
            alt_match = re.search(alt_pattern, page_source, re.IGNORECASE)
            if alt_match:
                asin = alt_match.group(1) if alt_match.groups() else alt_match.group(0)
                logging.info(f"ASIN found with alternative pattern: {asin}")
                return asin
        
        logging.warning("No ASIN found in page source")
        return None

    async def scrape_asin_from_url(self, url: str, force_login: bool = False) -> Optional[str]:
        """Main method to scrape ASIN from MAM URL."""
        logging.info(f"Starting ASIN scraping for URL: {url}")
        
        # Load MAM config
        try:
            mam_config = self.load_mam_config()
        except Exception as e:
            logging.error(f"Failed to load MAM config: {e}")
            return None
        
        # Check if we need to login
        cookies = mam_config.get('cookies', {})
        if not cookies or not cookies.get('mam_id') or force_login:
            logging.info("No valid cookies found or forced login, logging in...")
            
            email = mam_config.get('email')
            password = mam_config.get('password')
            
            if not email or not password:
                logging.error("Email or password not found in MAM config file")
                return None
            
            try:
                cookies = await self.login_and_get_cookies(email, password)
                mam_config['cookies'] = cookies
                mam_config['last_login'] = datetime.now().isoformat()
                self.save_mam_config(mam_config)
                logging.info("Login successful, cookies saved")
            except Exception as e:
                logging.error(f"Login failed: {e}")
                return None
        
        # Now scrape with cookies
        return await self._scrape_with_cookies(url, cookies)

    async def _scrape_with_cookies(self, url: str, cookies: Dict[str, str]) -> Optional[str]:
        """Scrape the torrent page using cookies."""
        async with async_playwright() as p:
            browser = None
            try:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
                )
                
                # Set cookies
                cookie_list = []
                for name, value in cookies.items():
                    cookie_list.append({
                        'name': name,
                        'value': value,
                        'domain': '.myanonamouse.net',
                        'path': '/'
                    })
                
                await context.add_cookies(cookie_list)
                logging.info(f"Set {len(cookie_list)} cookies")
                
                page = await context.new_page()
                logging.info(f"Navigating to {url}")
                
                # Apply global rate limiting
                self._check_global_rate_limit()
                
                response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                if response:
                    status_code = response.status
                    logging.info(f"Page loaded with status: {status_code}")
                    
                    if status_code != 200:
                        logging.warning(f"Unexpected status code: {status_code}")
                else:
                    logging.warning("No response object received")
                
                # Wait for page to fully load
                await page.wait_for_timeout(2000)
                
                # Check if we're logged in
                if await page.locator("text=Login").count() > 0:
                    logging.error("❌ Not logged in - login required")
                    return None
                elif await page.locator("text=logout").count() > 0 or await page.locator("text=Logout").count() > 0:
                    logging.info("✅ Successfully logged in")
                
                # Get page content
                source = await page.content()
                logging.info(f"Page content retrieved, length: {len(source)} characters")
                
                # Extract ASIN
                asin = self.extract_asin_from_page(source)
                return asin
                
            except Exception as e:
                logging.error(f"Scraping error: {e}")
                return None
            finally:
                if browser:
                    await browser.close()


def main():
    """Main function for command line usage."""
    import asyncio
    
    async def async_main():
        parser = argparse.ArgumentParser(description="MAM ASIN Scraper")
        parser.add_argument("url", help="MAM torrent URL to scrape")
        parser.add_argument("--force-login", action="store_true", help="Force re-login even if cookies exist")
        args = parser.parse_args()
        
        scraper = MAMScraper()
        asin = await scraper.scrape_asin_from_url(args.url, force_login=args.force_login)
        
        if asin:
            print(f"✅ ASIN found: {asin}")
            return asin
        else:
            print("❌ No ASIN found")
            return None
    
    return asyncio.run(async_main())


if __name__ == "__main__":
    main()
