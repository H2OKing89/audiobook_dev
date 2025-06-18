#!/usr/bin/env python3
"""
Simple script to just handle MAM login and save cookies.
Use this if you want to login separately from the main scraping script.
"""

from playwright.sync_api import sync_playwright
import json
import logging
import sys
import re
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('login.log')
    ]
)

CONFIG_FILE = "mam_config.json"

def load_config():
    """Load configuration from JSON file."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        logging.info("Configuration loaded successfully")
        return config
    except FileNotFoundError:
        logging.error(f"Config file {CONFIG_FILE} not found")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in config file: {e}")
        raise

def save_config(config):
    """Save configuration to JSON file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        logging.info("Configuration saved successfully")
    except Exception as e:
        logging.error(f"Failed to save config: {e}")
        raise

def login_and_get_cookies(email, password):
    """Login to MAM and retrieve session cookies."""
    logging.info("Starting login process...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Visible for debugging
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
        
        try:
            page = context.new_page()
            
            # Go to login page
            login_url = "https://www.myanonamouse.net/loggedin.php"
            logging.info(f"Navigating to login page: {login_url}")
            page.goto(login_url)
            
            # Wait for page to load
            page.wait_for_load_state("networkidle")
            
            # Check if we're already on the login form or need to navigate
            if page.locator("input[name='email']").count() == 0:
                # Try going to the main login page
                login_url = "https://www.myanonamouse.net/"
                logging.info(f"Trying main page: {login_url}")
                page.goto(login_url)
                page.wait_for_load_state("networkidle")
            
            # Look for login form
            email_input = page.locator("input[name='email'], input[type='email'], input[name='username']")
            password_input = page.locator("input[name='password'], input[type='password']")
            
            if email_input.count() == 0:
                logging.error("Could not find email input field")
                # Save page for debugging
                with open('login_page_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page.content())
                logging.info("Login page saved to login_page_debug.html for inspection")
                raise Exception("Login form not found")
            
            logging.info("Found login form, filling credentials...")
            
            # Fill in credentials
            email_input.fill(email)
            password_input.fill(password)
            
            # Look for "Keep me logged in" checkbox
            keep_logged_in = page.locator("input[type='checkbox']").filter(
                has_text=re.compile("keep.*logged.*in", re.IGNORECASE)
            ).first
            
            if keep_logged_in.count() > 0:
                logging.info("Found 'Keep me logged in' checkbox, checking it")
                keep_logged_in.check()
            else:
                # Try alternative selectors for the checkbox
                alt_selectors = [
                    "input[name='autolog']",
                    "input[name='remember']", 
                    "input[name='stay_logged_in']",
                    "input[value*='keep']",
                    "input[id*='keep']",
                    "input[id*='remember']"
                ]
                
                for selector in alt_selectors:
                    checkbox = page.locator(selector)
                    if checkbox.count() > 0:
                        logging.info(f"Found keep-logged-in checkbox with selector: {selector}")
                        checkbox.check()
                        break
                else:
                    logging.warning("Could not find 'Keep me logged in' checkbox")
            
            # Submit the form
            submit_button = page.locator("input[type='submit'], button[type='submit']").filter(
                has_text=re.compile("log.*in", re.IGNORECASE)
            ).first
            
            if submit_button.count() == 0:
                # Try alternative submit methods
                submit_button = page.locator("input[type='submit'], button[type='submit']").first
            
            if submit_button.count() > 0:
                logging.info("Submitting login form...")
                submit_button.click()
            else:
                logging.info("No submit button found, trying form submission via Enter key")
                password_input.press("Enter")
            
            # Wait for navigation after login
            page.wait_for_load_state("networkidle", timeout=10000)
            
            # Check if login was successful
            current_url = page.url
            logging.info(f"After login, current URL: {current_url}")
            
            # Look for signs of successful login
            if page.locator("text=logout").count() > 0 or page.locator("text=Logout").count() > 0:
                logging.info("✅ Login successful! Found logout link")
            elif "login" in current_url.lower():
                logging.error("❌ Login failed - still on login page")
                # Save page for debugging
                with open('login_failed_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page.content())
                raise Exception("Login failed - check credentials")
            else:
                logging.info("Login appears successful (no logout link found but URL changed)")
            
            # Get all cookies
            cookies = context.cookies()
            logging.info(f"Retrieved {len(cookies)} cookies")
            
            # Extract the important session cookies
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
            browser.close()

def main():
    """Main function to handle login only."""
    # Load configuration
    config = load_config()
    
    email = config.get('email')
    password = config.get('password')
    
    if not email or not password:
        logging.error("Email or password not found in config file")
        print("Please make sure your mam_config.json has valid email and password")
        return
    
    # Login and get fresh cookies
    try:
        logging.info("Starting login process...")
        cookies = login_and_get_cookies(email, password)
        
        # Update config with new cookies
        config['cookies'] = cookies
        config['last_login'] = datetime.now().isoformat()
        save_config(config)
        
        print("✅ Login successful!")
        print(f"Saved {len(cookies)} cookies to config file")
        for cookie_name in cookies.keys():
            print(f"  - {cookie_name}")
        
    except Exception as e:
        print(f"❌ Login failed: {e}")
        logging.error(f"Login failed: {e}")

if __name__ == "__main__":
    main()
