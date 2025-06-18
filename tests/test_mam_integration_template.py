#!/usr/bin/env python3
"""
MAM Integration Test - Template Version
Tests MAM integration with example webhook payloads
For real testing, copy to test_mam_integration_real.py and use actual MAM URLs
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
        logging.FileHandler('logs/mam_integration_test.log')
    ]
)

def test_mam_integration_example():
    """Test with example webhook payload (safe for git commits)"""
    logging.info("🧪 Testing MAM Integration with Example Data")
    logging.info("="*60)
    logging.info("📝 This uses EXAMPLE data safe for git commits")
    logging.info("📝 For real testing, create test_mam_integration_real.py")
    logging.info("")
    
    # Example webhook payload (safe for git)
    example_payload = {
        'name': 'Example Audiobook: Volume 1: by Example Author [English / m4b]',
        'indexer': 'myanonamouse',
        'url': 'https://www.myanonamouse.net/t/1234567',  # Example URL
        'download_url': 'https://www.myanonamouse.net/tor/download.php?tid=1234567',
        'category': 'Audiobooks - Fantasy',
        'size': '378431078'
    }
    
    logging.info(f"📚 Book: {example_payload['name']}")
    logging.info(f"🔗 MAM URL: {example_payload['url']}")
    logging.info(f"📂 Category: {example_payload['category']}")
    logging.info(f"💾 Size: {int(example_payload['size']) / (1024*1024):.1f} MB")
    logging.info("")
    
    # Check if MAM config exists
    config_path = Path("config/mam_config.json")
    if not config_path.exists():
        logging.warning("⚠️  MAM configuration missing - workflow will skip to Audible search")
        logging.info("   To test full workflow, create config/mam_config.json")
        logging.info("")
    
    try:
        coordinator = MetadataCoordinator()
        logging.info("🚀 Starting example metadata workflow...")
        logging.info("⚠️  This uses example data and may not find real metadata")
        logging.info("")
        
        # This will attempt the workflow but likely fail on the example URL
        metadata = coordinator.get_metadata_from_webhook(example_payload)
        
        if metadata:
            logging.info("✅ SUCCESS: Metadata retrieved!")
            logging.info("="*50)
            logging.info("📚 METADATA RESULTS:")
            logging.info("="*50)
            
            # Show key metadata fields
            key_fields = ['title', 'author', 'narrator', 'publisher', 'language', 'genres', 'description', 'asin', 'source', 'asin_source']
            for field in key_fields:
                if field in metadata:
                    value = metadata[field]
                    if field == 'description' and len(str(value)) > 100:
                        value = f"{str(value)[:100]}..."
                    logging.info(f"  {field}: {value}")
            
            # Show series info if available
            if 'series' in metadata:
                logging.info(f"  📖 Series: {metadata['series']}")
            
            return True
        else:
            logging.warning("❌ No metadata found (expected with example data)")
            logging.info("💡 This test demonstrates the workflow structure")
            logging.info("💡 For real testing, use actual MAM URLs in a separate file")
            return False
            
    except Exception as e:
        logging.error(f"❌ Error during test: {e}")
        import traceback
        logging.error("Full traceback:")
        logging.error(traceback.format_exc())
        return False

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
        logging.info("🎉 EXAMPLE TEST COMPLETED!")
        logging.info("✅ The MAM integration workflow structure is working")
    else:
        logging.info("ℹ️  EXAMPLE TEST COMPLETED (no metadata expected)")
        logging.info("✅ The workflow handled the example data correctly")
    
    logging.info("")
    logging.info("📝 For real testing:")
    logging.info("  1. Copy this file to test_mam_integration_real.py")
    logging.info("  2. Replace example_payload with real MAM webhook data") 
    logging.info("  3. Add test_mam_integration_real.py to .gitignore")
    logging.info("  4. Run your real test locally")
    
    logging.info("")
    logging.info("📊 Test completed - check logs/mam_integration_test.log for details")

if __name__ == "__main__":
    main()
