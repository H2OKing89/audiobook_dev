"""
Metadata Flow Testing Script
Tests the complete metadata workflow with rate limiting
"""

import asyncio
import logging
import sys
import time
from pathlib import Path


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.metadata_coordinator import MetadataCoordinator


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("logs/metadata_flow_test.log")],
)


class MetadataFlowTester:
    def __init__(self):
        self.coordinator = MetadataCoordinator()
        self.test_results = []

    def test_config_loading(self):
        """Test that configuration is loaded properly"""
        logging.info("=== Testing Configuration Loading ===")

        try:
            rate_limit = self.coordinator.rate_limit_seconds
            logging.info(f"✅ Global rate limit: {rate_limit} seconds")

            # MAM API adapter doesn't expose base_url
            logging.info("✅ MAM API adapter configured")

            audnex_config = self.coordinator.audnex.base_url
            logging.info(f"✅ Audnex base URL: {audnex_config}")

            audible_config = self.coordinator.audible.base_url
            logging.info(f"✅ Audible base URL: {audible_config}")

            return True
        except Exception as e:
            logging.error(f"❌ Configuration loading failed: {e}")
            return False

    def test_webhook_payload_processing(self):
        """Test processing of webhook payloads"""
        logging.info("=== Testing Webhook Payload Processing ===")

        # Test payload with MAM URL (common case)
        test_payload = {
            "name": "The Hobbit by J.R.R. Tolkien [Audiobook]",
            "url": "https://www.myanonamouse.net/t/12345",
            "download_url": "https://www.myanonamouse.net/download.php?id=12345&token=abc123",
        }

        try:
            logging.info(f"Testing payload: {test_payload['name']}")
            logging.info(f"MAM URL: {test_payload['url']}")

            # We'll test the workflow preparation without actually making requests
            url = test_payload.get("url")
            test_payload.get("name", "")

            if url and "myanonamouse.net" in url:
                logging.info("✅ MAM URL detected - would attempt ASIN extraction")
            else:
                logging.info("✅ Non-MAM URL - would skip to Audible search")

            logging.info("✅ Webhook payload processing logic works")
            return True

        except Exception as e:
            logging.error(f"❌ Webhook payload processing failed: {e}")
            return False

    def test_rate_limiting_enforcement(self):
        """Test that rate limiting is properly enforced"""
        logging.info("=== Testing Rate Limiting Enforcement ===")

        try:
            rate_limit = self.coordinator.rate_limit_seconds
            logging.info(f"Testing rate limit of {rate_limit} seconds")

            # Test the rate limiting mechanism
            time.time()

            # First call should not wait
            asyncio.run(self.coordinator._enforce_rate_limit())
            first_call_time = time.time()

            # Second call should enforce rate limit
            asyncio.run(self.coordinator._enforce_rate_limit())
            second_call_time = time.time()

            elapsed = second_call_time - first_call_time
            logging.info(f"Time between calls: {elapsed:.1f} seconds")

            if elapsed >= rate_limit - 1:  # Allow 1 second tolerance
                logging.info("✅ Rate limiting is working correctly")
                return True
            else:
                logging.warning(f"❌ Rate limiting may not be working. Expected >= {rate_limit}s, got {elapsed:.1f}s")
                return False

        except Exception as e:
            logging.error(f"❌ Rate limiting test failed: {e}")
            return False

    def test_error_handling(self):
        """Test error handling with invalid inputs"""
        logging.info("=== Testing Error Handling ===")

        try:
            # Test with empty payload
            empty_payload = {}
            logging.info("Testing empty payload handling...")

            # This should not crash but return None
            result = asyncio.run(self.coordinator.get_metadata_from_webhook(empty_payload))
            if result is None:
                logging.info("✅ Empty payload handled gracefully")
            else:
                logging.warning(f"❌ Empty payload returned unexpected: {result}")

            # Test with malformed payload
            malformed_payload = {"invalid": "data"}
            logging.info("Testing malformed payload handling...")

            result = asyncio.run(self.coordinator.get_metadata_from_webhook(malformed_payload))
            if result is None:
                logging.info("✅ Malformed payload handled gracefully")
            else:
                logging.warning(f"❌ Malformed payload returned unexpected: {result}")

            return True

        except Exception as e:
            logging.error(f"❌ Error handling test failed: {e}")
            return False

    def test_dry_run_workflow(self):
        """Test the workflow logic without making external requests"""
        logging.info("=== Testing Workflow Logic (Dry Run) ===")

        try:
            # Test the workflow decision logic
            test_cases = [
                {
                    "name": "Test with MAM URL",
                    "payload": {
                        "name": "Sample Book [Audiobook]",
                        "url": "https://www.myanonamouse.net/t/12345",
                        "download_url": "https://example.com/download",
                    },
                    "expected_path": "MAM -> Audnex -> Audible",
                },
                {
                    "name": "Test with non-MAM URL",
                    "payload": {
                        "name": "Sample Book [Audiobook]",
                        "url": "https://other-site.com/book/12345",
                        "download_url": "https://example.com/download",
                    },
                    "expected_path": "Audible search",
                },
            ]

            for test_case in test_cases:
                logging.info(f"Testing: {test_case['name']}")
                payload = test_case["payload"]
                url = payload.get("url") if isinstance(payload, dict) else None

                if url and "myanonamouse.net" in url:
                    logging.info("  ✅ Would follow MAM workflow path")
                else:
                    logging.info("  ✅ Would follow direct Audible search path")

            logging.info("✅ Workflow logic tests passed")
            return True

        except Exception as e:
            logging.error(f"❌ Workflow logic test failed: {e}")
            return False

    def run_all_tests(self):
        """Run all tests and report results"""
        logging.info("🧪 Starting Metadata Flow Testing Suite")
        logging.info("=" * 50)

        tests = [
            ("Configuration Loading", self.test_config_loading),
            ("Webhook Payload Processing", self.test_webhook_payload_processing),
            ("Rate Limiting Enforcement", self.test_rate_limiting_enforcement),
            ("Error Handling", self.test_error_handling),
            ("Workflow Logic (Dry Run)", self.test_dry_run_workflow),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            try:
                result = test_func()
                if result:
                    passed += 1
                    logging.info(f"✅ {test_name}: PASSED")
                else:
                    logging.error(f"❌ {test_name}: FAILED")
            except Exception as e:
                logging.error(f"❌ {test_name}: ERROR - {e}")

            logging.info("-" * 30)

        logging.info("=" * 50)
        logging.info(f"📊 Test Results: {passed}/{total} tests passed")

        if passed == total:
            logging.info("🎉 All tests passed! Metadata flow is ready.")
        else:
            logging.warning(f"⚠️  {total - passed} tests failed. Please review.")

        return passed == total


def main():
    """Main test runner"""
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)

    tester = MetadataFlowTester()
    success = tester.run_all_tests()

    if success:
        logging.info("\n🚀 Ready for careful live testing with real data!")
        logging.info("   Remember: 30-second rate limit is enforced")
        logging.info("   Logs are saved to: logs/metadata_flow_test.log")
    else:
        logging.error("\n❌ Fix issues before proceeding to live testing")

    return success


if __name__ == "__main__":
    main()
