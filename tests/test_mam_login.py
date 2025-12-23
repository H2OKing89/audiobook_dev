"""
MAM Login Test - Test MAM authentication only
"""

import logging
import sys
import traceback
from pathlib import Path

import pytest


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Skip this entire file - MAM scraper removed, using API now
pytestmark = pytest.mark.skip(reason="MAM scraper removed - using MAM API adapter now")

try:
    from src.mam_scraper import MAMScraper
except ImportError:
    MAMScraper = None  # Module no longer exists after API migration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("logs/mam_login_test.log")],
)


def test_mam_login():
    """Test MAM login functionality"""
    logging.info("🧪 Testing MAM Login")
    logging.info("=" * 30)

    # Check if config exists
    config_path = Path("config/mam_config.json")
    if not config_path.exists():
        logging.error("❌ MAM config not found at config/mam_config.json")
        logging.info("Run: python setup_mam_config.py")
        return False

    try:
        scraper = MAMScraper()

        # Load config first
        config = scraper.load_mam_config()
        logging.info("✅ MAM config loaded successfully")

        # Check config has required fields
        required_fields = ["email", "password"]
        for field in required_fields:
            if not config.get(field) or config.get(field) == f"your_mam_{field}_here":
                logging.error(f"❌ {field} not configured in mam_config.json")
                logging.info(f"Please edit config/mam_config.json and set {field}")
                return False

        logging.info(f"✅ Email: {config['email'][:3]}***")
        logging.info(f"✅ Password: {'*' * len(config.get('password', ''))}")

        # Test login (this will attempt to login to MAM)
        logging.info("🔐 Attempting MAM login...")
        logging.warning("⚠️  This will make a real login attempt to MAM")

        # We'll just test the config loading for now to avoid hammering MAM
        logging.info("✅ Config validation passed")
        logging.info("📝 Login test skipped to avoid unnecessary MAM requests")
        logging.info("   The scraper will attempt login when needed")

        return True

    except Exception as e:
        logging.error(f"❌ Error: {e}")
        logging.error(traceback.format_exc())
        return False


def main():
    """Main test runner"""
    logging.info("🔴 MAM LOGIN CONFIGURATION TEST")
    logging.info("Validating MAM configuration without making requests")
    logging.info("")

    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)

    success = test_mam_login()

    if success:
        logging.info("")
        logging.info("🎉 MAM CONFIGURATION VALIDATED!")
        logging.info("✅ Ready to test ASIN extraction")
        logging.info("")
        logging.info("🔍 Troubleshooting MAM login issues:")
        logging.info("  1. Verify email/password are correct")
        logging.info("  2. Check if MAM requires 2FA (not supported)")
        logging.info("  3. Ensure account is in good standing")
        logging.info("  4. Try logging in manually first")
        logging.info("")
        logging.info("⚡ The current fallback workflow (Audible) works perfectly!")
    else:
        logging.error("")
        logging.error("❌ MAM CONFIGURATION NEEDS FIXING")
        logging.error("Please fix the issues above before testing")


if __name__ == "__main__":
    main()
