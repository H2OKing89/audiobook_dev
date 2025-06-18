#!/usr/bin/env python3
"""
Test script to verify that main.py now uses comprehensive metadata fields
"""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from src.main import app
from fastapi.testclient import TestClient

async def test_webhook_metadata_fields():
    """Test that webhook processing now includes all metadata fields"""
    client = TestClient(app)
    
    # Real working webhook payload from logs
    webhook_payload = {
        "name": "In Another World with My Smartphone: Volume 6: by Patora Fuyuhara [English / m4b]",
        "indexer": "myanonamouse",
        "url": "https://www.myanonamouse.net/t/1156932",
        "download_url": "https://www.myanonamouse.net/tor/download.php?tid=1156932",
        "category": "Audiobooks - Fantasy",
        "size": "378431078"
    }
    
    print("Testing webhook with comprehensive metadata...")
    print(f"Payload: {json.dumps(webhook_payload, indent=2)}")
    
    # This would normally trigger the webhook endpoint
    # But since we're testing locally, let's just test the metadata coordinator directly
    from src.metadata_coordinator import MetadataCoordinator
    
    coordinator = MetadataCoordinator()
    
    # Test the metadata workflow
    print("\n=== Testing Metadata Workflow ===")
    try:
        metadata = await coordinator.get_metadata_from_webhook(webhook_payload)
        
        if metadata:
            # Get enhanced metadata
            enhanced = coordinator.get_enhanced_metadata(metadata)
            
            print("✅ Metadata fetched successfully!")
            print(f"Title: {enhanced.get('title')}")
            print(f"Author: {enhanced.get('author')}")
            print(f"Narrator: {enhanced.get('narrator')}")
            print(f"Publisher: {enhanced.get('publisher')}")
            print(f"Description: {enhanced.get('description', '')[:100]}...")
            print(f"Duration: {enhanced.get('duration')} minutes")
            print(f"Published Year: {enhanced.get('publishedYear')}")
            print(f"Language: {enhanced.get('language')}")
            print(f"Rating: {enhanced.get('rating')}")
            print(f"ASIN: {enhanced.get('asin')}")
            print(f"Cover: {enhanced.get('cover')}")
            
            if enhanced.get('series'):
                for s in enhanced['series']:
                    print(f"Series: {s['series']} #{s['sequence']}")
            
            if enhanced.get('genres'):
                print(f"Genres: {', '.join(enhanced['genres'])}")
            
            if enhanced.get('tags'):
                print(f"Tags: {enhanced['tags']}")
                
            print(f"\nSource: {enhanced.get('source')}")
            print(f"Workflow Path: {enhanced.get('workflow_path')}")
            
            # Check webhook fields
            print(f"\nWebhook Info:")
            print(f"Webhook Name: {enhanced.get('webhook_name')}")
            print(f"Webhook URL: {enhanced.get('webhook_url')}")
            print(f"Webhook Size MB: {enhanced.get('webhook_size_mb')}")
            print(f"Torrent Name: {enhanced.get('torrent_name')}")
            print(f"Torrent Category: {enhanced.get('torrent_category')}")
            
            # Check notification-ready fields
            print(f"\nNotification Fields:")
            print(f"Book Title: {enhanced.get('book_title')}")
            print(f"Book Author: {enhanced.get('book_author')}")
            print(f"Book Narrator: {enhanced.get('book_narrator')}")
            print(f"Book Publisher: {enhanced.get('book_publisher')}")
            print(f"Book Series Info: {enhanced.get('book_series_info')}")
            print(f"Book Duration: {enhanced.get('book_duration')} minutes")
            print(f"Book Rating: {enhanced.get('book_rating')}")
            print(f"Book Genres: {enhanced.get('book_genres')}")
            
            # Check if all the expected fields are present
            expected_fields = [
                'title', 'author', 'narrator', 'publisher', 'description', 
                'duration', 'publishedYear', 'language', 'asin', 'cover',
                'source', 'workflow_path', 'webhook_name', 'webhook_url',
                'book_title', 'book_author', 'book_narrator', 'book_publisher'
            ]
            
            missing_fields = [field for field in expected_fields if enhanced.get(field) is None]
            
            if missing_fields:
                print(f"\n⚠️  Missing fields: {missing_fields}")
            else:
                print(f"\n✅ All expected metadata fields are present!")
                
            return enhanced
            
        else:
            print("❌ No metadata found")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_webhook_metadata_fields())
