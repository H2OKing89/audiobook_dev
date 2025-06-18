#!/usr/bin/env python3
"""
MAM ASIN Test - In Another World with My Smartphone Volume 6
Test the full workflow including MAM ASIN extraction
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.metadata_coordinator import MetadataCoordinator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/mam_asin_test.log')
    ]
)

def test_mam_integration_example():
    """Test with example webhook payload (safe for git commits)"""
    logging.info("🧪 Testing MAM Integration with Example Data")
    logging.info("="*60)
    logging.info("📝 This uses EXAMPLE data safe for git commits")
    logging.info("📝 For real testing, copy to test_mam_integration_real.py")
    logging.info("")
    
    # Example webhook payload (safe for git commits)
    # For real testing, copy this file to test_mam_integration_real.py and use actual URLs
    example_payload = {
        'name': 'Example Light Novel: Volume 6: by Example Author [English / m4b]',
        'indexer': 'myanonamouse',
        'url': 'https://www.myanonamouse.net/t/EXAMPLE123',  # Placeholder URL
        'download_url': 'https://www.myanonamouse.net/tor/download.php?tid=EXAMPLE123',
        'category': 'Audiobooks - Fantasy',
        'size': '378431078'
    }
    
    logging.info(f"📚 Book: {example_payload['name']}")
    logging.info(f"🔗 MAM URL: {example_payload['url']}")
    logging.info(f"📂 Category: {example_payload['category']}")
    logging.info(f"💾 Size: {int(example_payload['size']) / (1024*1024):.1f} MB")
    logging.info("")
    logging.info("📝 This test will attempt the FULL workflow:")
    logging.info("   1. MAM ASIN extraction (if mam_config.json exists)")
    logging.info("   2. Audnex metadata fetch (if ASIN found)")
    logging.info("   3. Audible search fallback (if needed)")
    logging.info("")
    
    # Check if MAM config exists
    mam_config_path = Path("mam_config.json")
    if mam_config_path.exists():
        logging.info("✅ MAM configuration found - will attempt ASIN extraction")
    else:
        logging.warning("⚠️  MAM configuration missing - will skip to Audible search")
        logging.info("   To test full workflow, create mam_config.json from mam_config.json.example")
    
    logging.info("")
    
    coordinator = MetadataCoordinator()
    
    try:
        logging.info("🚀 Starting metadata workflow...")
        logging.info("⚠️  This will make real API requests with 30s rate limiting")
        logging.info("")
        
        start_time = datetime.now()
        
        # Run the full metadata workflow
        metadata = coordinator.get_metadata_from_webhook(example_payload)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logging.info("")
        logging.info(f"⏱️  Total workflow time: {duration:.1f} seconds")
        logging.info("")
        
        if metadata:
            logging.info("✅ SUCCESS: Metadata retrieved!")
            logging.info("="*60)
            logging.info("📚 METADATA RESULTS:")
            logging.info("="*60)
            
            # Display key metadata fields
            key_fields = [
                'title', 'author', 'narrator', 'publisher', 'publishDate',
                'language', 'genres', 'description', 'asin', 'source', 'asin_source'
            ]
            
            for field in key_fields:
                value = metadata.get(field)
                if value:
                    if isinstance(value, str) and len(value) > 100:
                        logging.info(f"  {field}: {value[:100]}...")
                    elif isinstance(value, list):
                        if len(value) <= 3:
                            logging.info(f"  {field}: {', '.join(map(str, value))}")
                        else:
                            logging.info(f"  {field}: {', '.join(map(str, value[:3]))} (+{len(value)-3} more)")
                    else:
                        logging.info(f"  {field}: {value}")
            
            # Check for chapters
            if 'chapters' in metadata:
                chapters = metadata['chapters']
                logging.info(f"  chapters: {len(chapters)} chapters found")
                if chapters:
                    logging.info(f"    First: {chapters[0].get('title', 'Untitled')}")
                    if len(chapters) > 1:
                        logging.info(f"    Last: {chapters[-1].get('title', 'Untitled')}")
            
            # Show series information (important for light novels)
            if 'series' in metadata:
                series_info = metadata['series']
                if isinstance(series_info, list) and series_info:
                    logging.info(f"  📖 Series: {series_info[0].get('series', 'Unknown')} #{series_info[0].get('sequence', 'Unknown')}")
                elif isinstance(series_info, str):
                    logging.info(f"  📖 Series: {series_info}")
            
            # Save complete results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = f"logs/smartphone_v6_metadata_{timestamp}.json"
            
            with open(results_file, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            logging.info("")
            logging.info(f"💾 Complete results saved to: {results_file}")
            
            # Analyze the workflow path taken
            source = metadata.get('source', 'unknown')
            asin_source = metadata.get('asin_source', 'unknown')
            asin = metadata.get('asin', 'not found')
            
            logging.info("")
            logging.info("📊 WORKFLOW ANALYSIS:")
            logging.info("="*40)
            logging.info(f"  📍 Final ASIN: {asin}")
            logging.info(f"  🔍 ASIN source: {asin_source}")
            logging.info(f"  📚 Metadata source: {source}")
            logging.info("")
            
            if source == 'audnex' and asin_source == 'mam':
                logging.info("  🎯 **PERFECT WORKFLOW**: MAM → ASIN → Audnex")
                logging.info("     ✅ ASIN successfully extracted from MAM")
                logging.info("     ✅ Rich metadata from Audnex API")
                if 'chapters' in metadata:
                    logging.info("     ✅ Chapter information included")
            elif source == 'audible' and asin_source == 'search':
                logging.info("  🔄 **FALLBACK WORKFLOW**: MAM failed → Audible search")
                logging.info("     ⚠️  MAM ASIN extraction failed or unavailable")
                logging.info("     ✅ Audible search found the book")
            elif source == 'audnex' and asin_source == 'search':
                logging.info("  🔄 **MIXED WORKFLOW**: MAM failed → Search → Audnex")
                logging.info("     ⚠️  MAM ASIN extraction failed")
                logging.info("     ✅ Audible search found ASIN")
                logging.info("     ✅ Audnex provided rich metadata")
            else:
                logging.info(f"  ℹ️  **CUSTOM WORKFLOW**: {asin_source} → {source}")
            
            # Quality assessment for light novel
            logging.info("")
            logging.info("📊 LIGHT NOVEL METADATA QUALITY:")
            logging.info("-" * 40)
            
            title = metadata.get('title', '')
            if 'smartphone' in title.lower():
                logging.info("  ✅ Title correctly identifies the series")
            
            if 'volume 6' in title.lower() or '6' in title:
                logging.info("  ✅ Volume number correctly identified")
            
            author = metadata.get('author', '')
            if 'fuyuhara' in author.lower():
                logging.info("  ✅ Author correctly identified")
            
            genres = metadata.get('genres', [])
            if isinstance(genres, list):
                genre_text = ', '.join(genres).lower()
            else:
                genre_text = str(genres).lower()
            
            if any(keyword in genre_text for keyword in ['fantasy', 'fiction', 'light novel', 'anime']):
                logging.info("  ✅ Genre classification appropriate")
                
        else:
            logging.warning("❌ No metadata found")
            logging.warning("Possible reasons:")
            logging.warning("  - MAM page doesn't contain ASIN (unlikely for popular series)")
            logging.warning("  - ASIN extraction failed due to page structure changes")
            logging.warning("  - Book not found in Audnex database")
            logging.warning("  - Audible search failed")
            logging.warning("  - Network/authentication issues")
            logging.warning("  - Rate limiting by external services")
        
    except Exception as e:
        logging.error(f"❌ Error during test: {e}")
        import traceback
        logging.error("Full traceback:")
        logging.error(traceback.format_exc())
        return False
    
    logging.info("")
    logging.info("="*80)
    logging.info("🏁 MAM ASIN test completed")
    
    return metadata is not None

def main():
    """Main test runner"""
    logging.info("🔴 MAM INTEGRATION TEST (EXAMPLE DATA)")
    logging.info("Testing MAM integration workflow with safe example data")
    logging.info("Rate limiting: 30 seconds between API calls")
    logging.info("")
    
    # Ensure logs directory exists
    Path('logs').mkdir(exist_ok=True)
    
    # Run the test
    success = test_mam_integration_example()
    
    logging.info("")
    if success:
        logging.info("🎉 MAM ASIN TEST SUCCESSFUL!")
        logging.info("✅ The metadata workflow processed the light novel successfully")
        logging.info("")
        logging.info("📝 Review the results to see if:")
        logging.info("  - ASIN was extracted from MAM (ideal)")
        logging.info("  - Audnex provided rich metadata + chapters")
        logging.info("  - Or Audible fallback worked correctly")
        logging.info("")
        logging.info("🎯 Next: Set up mam_config.json for full MAM integration")
    else:
        logging.warning("❌ MAM ASIN TEST FAILED")
        logging.warning("Review logs to identify issues")
    
    logging.info("")
    logging.info("📊 Test completed - check logs/mam_asin_test.log for details")

if __name__ == "__main__":
    main()
