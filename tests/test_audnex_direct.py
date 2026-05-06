"""
Audnex Direct Test - Test Audnex API with known ASINs
This simulates what would happen if MAM extraction succeeded
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import aiofiles
import pytest


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from src.audnex_metadata import AudnexMetadata


# Configure logging (stdout only - no file creation on import)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


@pytest.mark.skipif(os.getenv("RUN_AUDNEX_DIRECT") != "1", reason="Audnex direct tests are skipped by default")
@pytest.mark.asyncio
async def test_audnex_with_known_asin():
    """Test Audnex API with ASINs we found from Audible search"""
    logging.info("🧪 Testing Audnex API with Known ASINs")
    logging.info("=" * 50)
    logging.info("This simulates what happens when MAM ASIN extraction succeeds")
    logging.info("")

    # ASINs from our previous tests
    test_cases = [
        {"name": "The Wolf's Advance", "asin": "B0F67KLM54", "expected": "Should find metadata + chapters"},
        {
            "name": "In Another World with My Smartphone Vol 6",
            "asin": "B0F8PKCTCW",
            "expected": "Should find metadata + chapters",
        },
        {
            "name": "Popular audiobook (known ASIN)",
            "asin": "B079LRSMNN",  # The Way of Kings (popular book, likely in Audnex)
            "expected": "Should find rich metadata",
        },
    ]

    async with AudnexMetadata() as audnex:
        results = []

        for i, test_case in enumerate(test_cases, 1):
            logging.info(f"📚 Test {i}/3: {test_case['name']}")
            logging.info(f"🔍 ASIN: {test_case['asin']}")
            logging.info(f"💭 Expected: {test_case['expected']}")

            try:
                start_time = datetime.now()

                # Test Audnex metadata fetch
                metadata = await audnex.get_book_by_asin(test_case["asin"])

                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                if metadata:
                    logging.info(f"✅ SUCCESS in {duration:.1f}s")

                    # Key information
                    title = metadata.get("title", "Unknown")
                    author = metadata.get("author", "Unknown")
                    chapters = metadata.get("chapters", [])

                    logging.info(f"   📖 Title: {title}")
                    logging.info(f"   ✍️  Author: {author}")
                    logging.info(f"   📚 Chapters: {len(chapters)} found")

                    if chapters:
                        logging.info(f"   📝 First chapter: {chapters[0].get('title', 'Untitled')}")
                        total_length = sum(ch.get("lengthMs", 0) for ch in chapters)
                        logging.info(f"   ⏱️  Total duration: {total_length / 1000 / 60:.1f} minutes")

                    # Check for rich metadata
                    rich_fields = ["description", "narrator", "publisher", "genres", "series"]
                    rich_count = sum(1 for field in rich_fields if metadata.get(field))
                    logging.info(f"   🎯 Rich metadata: {rich_count}/{len(rich_fields)} fields")

                    results.append(
                        {
                            "asin": test_case["asin"],
                            "success": True,
                            "chapters": len(chapters),
                            "duration": duration,
                            "title": title,
                        }
                    )

                else:
                    logging.warning(f"❌ Not found in Audnex in {duration:.1f}s")
                    results.append({"asin": test_case["asin"], "success": False, "duration": duration})

            except Exception as e:
                logging.error(f"❌ Error: {e}")
                results.append({"asin": test_case["asin"], "success": False, "error": str(e)})

            logging.info("-" * 40)

            # Rate limiting between tests
            if i < len(test_cases):
                logging.info("⏳ Rate limiting: waiting 30 seconds...")
                await asyncio.sleep(30)

        # Summary
        logging.info("")
        logging.info("📊 AUDNEX API TEST SUMMARY")
        logging.info("=" * 40)

        successful = sum(1 for r in results if r.get("success"))
        total_chapters = sum(r.get("chapters", 0) for r in results if r.get("success"))

        logging.info(f"📈 Success Rate: {successful}/{len(results)} tests")
        logging.info(f"📚 Total Chapters Found: {total_chapters}")

        if successful > 0:
            avg_duration = sum(r["duration"] for r in results if r.get("success")) / successful
            logging.info(f"⏱️  Average Response Time: {avg_duration:.1f}s")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"logs/audnex_test_results_{timestamp}.json"

        try:
            # Ensure logs directory exists
            Path("logs").mkdir(exist_ok=True)
            async with aiofiles.open(results_file, "w") as f:
                await f.write(json.dumps(results, indent=2, default=str))
            logging.info(f"💾 Results saved to: {results_file}")
        except OSError as e:
            logging.error(f"Failed to save results to {results_file}: {e}")

        if successful == len(results):
            logging.info("🎉 ALL AUDNEX TESTS PASSED!")
            logging.info("✅ Audnex API is working excellently")
            logging.info("✅ Rich metadata + chapters available")
        elif successful > 0:
            logging.info("🔶 PARTIAL SUCCESS")
            logging.info("✅ Audnex API is working for some books")
            logging.info("⚠️  Some ASINs not found in Audnex database")
        else:
            logging.warning("❌ ALL AUDNEX TESTS FAILED")
            logging.warning("Check network connectivity and Audnex API status")

        return successful > 0


def main():
    """Main test runner"""
    logging.info("🔴 AUDNEX DIRECT API TEST")
    logging.info("Testing Audnex API with known ASINs")
    logging.info("Rate limiting: 30 seconds between API calls")
    logging.info("")

    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)

    # Run the test
    success = test_audnex_with_known_asin()

    logging.info("")
    if success:
        logging.info("🎯 AUDNEX TESTING SUCCESSFUL!")
        logging.info("This demonstrates the enhanced metadata available when")
        logging.info("MAM ASIN extraction works properly")

    logging.info("")
    logging.info("📝 To get the full workflow working:")
    logging.info("1. Set MAM_ID in .env from your mam_id browser cookie")
    logging.info("2. Restart the app or shell so the environment reloads")
    logging.info("3. Test with: pytest tests/test_mam_api.py -k Integration --no-cov")


if __name__ == "__main__":
    main()
