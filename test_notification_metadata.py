#!/usr/bin/env python3
"""
Test that notifications now have comprehensive metadata fields
"""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

async def test_notification_metadata():
    """Test that notification context has comprehensive metadata"""
    from src.metadata_coordinator import MetadataCoordinator
    from src.utils import build_notification_message
    from src.config import load_config
    
    # Real working webhook payload
    webhook_payload = {
        "name": "In Another World with My Smartphone: Volume 6: by Patora Fuyuhara [English / m4b]",
        "indexer": "myanonamouse",
        "url": "https://www.myanonamouse.net/t/1156932",
        "download_url": "https://www.myanonamouse.net/tor/download.php?tid=1156932",
        "category": "Audiobooks - Fantasy",
        "size": "378431078"
    }
    
    print("Testing notification with comprehensive metadata...")
    
    # Get metadata using the coordinator (same as main.py does now)
    coordinator = MetadataCoordinator()
    metadata = await coordinator.get_metadata_from_webhook(webhook_payload)
    
    if not metadata:
        print("❌ No metadata found - cannot test notifications")
        return
    
    # Enhance metadata (same as main.py does now)
    enhanced_metadata = coordinator.get_enhanced_metadata(metadata)
    
    # Load config for notification templates
    config = load_config()
    
    # Test notification message building with the enhanced metadata
    try:
        # Simulate the notification context like main.py does
        token = "test-token"
        base_url = config.get('server', {}).get('base_url', 'http://localhost:8080')
        message = build_notification_message(enhanced_metadata, config, token, base_url)
        print("✅ Notification message built successfully!")
        print("Message preview:")
        print(message[:500] + "..." if len(message) > 500 else message)
        
        # Check if the message contains comprehensive fields
        comprehensive_fields = [
            enhanced_metadata.get('title', ''),
            enhanced_metadata.get('author', ''),
            enhanced_metadata.get('narrator', ''), 
            enhanced_metadata.get('publisher', ''),
            enhanced_metadata.get('duration', 0),
            enhanced_metadata.get('book_series_info', ''),
            enhanced_metadata.get('book_genres', '')
        ]
        
        fields_in_message = sum(1 for field in comprehensive_fields if field and str(field) in message)
        print(f"✅ Found {fields_in_message}/{len([f for f in comprehensive_fields if f])} metadata fields in notification")
        
        # Show some key fields that should now be available
        print(f"\nKey metadata fields available for notifications:")
        print(f"  Title: {enhanced_metadata.get('title')}")
        print(f"  Author: {enhanced_metadata.get('author')}")
        print(f"  Narrator: {enhanced_metadata.get('narrator')}")
        print(f"  Publisher: {enhanced_metadata.get('publisher')}")
        print(f"  Duration: {enhanced_metadata.get('duration')} minutes")
        print(f"  Series: {enhanced_metadata.get('book_series_info')}")
        print(f"  Genres: {enhanced_metadata.get('book_genres')}")
        print(f"  Description: {(enhanced_metadata.get('description') or '')[:100]}...")
        print(f"  Cover URL: {enhanced_metadata.get('cover')}")
        print(f"  Rating: {enhanced_metadata.get('rating')}")
        print(f"  ASIN: {enhanced_metadata.get('asin')}")
        
    except Exception as e:
        print(f"❌ Error building notification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_notification_metadata())
