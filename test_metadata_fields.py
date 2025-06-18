#!/usr/bin/env python3
"""
Quick test to show enhanced metadata fields
"""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from src.metadata_coordinator import MetadataCoordinator

def test_metadata_fields():
    """Test the enhanced metadata field population"""
    print("🧪 TESTING ENHANCED METADATA FIELDS")
    print("="*50)
    
    # Example webhook payload
    test_payload = {
        'name': 'The Wolf\'s Advance by Shane Purdy [English / m4b]',
        'indexer': 'myanonamouse',
        'url': 'https://www.myanonamouse.net/t/1157045',
        'download_url': 'https://www.myanonamouse.net/tor/download.php?tid=1157045',
        'category': 'Audiobooks - Fantasy',
        'size': '948387840',  # ~905 MB
        'seeders': 12,
        'leechers': 3
    }
    
    coordinator = MetadataCoordinator()
    
    # Test webhook info extraction
    print("📋 Testing webhook info extraction...")
    webhook_info = coordinator._add_webhook_info(test_payload)
    
    print(f"✅ Extracted {len(webhook_info)} webhook fields:")
    print(f"  📚 Torrent Name: {webhook_info['torrent_name']}")
    print(f"  📂 Category: {webhook_info['torrent_category']}")  
    print(f"  💾 Size: {webhook_info['webhook_size_mb']} MB")
    print(f"  🌱 Seeders: {webhook_info['webhook_seeders']}")
    print(f"  🔗 URL: {webhook_info['torrent_url']}")
    print(f"  ⏰ Processing Time: {webhook_info['processing_date']}")
    
    print()
    print("📋 Fields available for notifications/templates:")
    template_fields = [k for k in webhook_info.keys() if k.startswith(('webhook_', 'torrent_', 'processing_'))]
    for field in sorted(template_fields):
        print(f"  • {field}")
    
    print()
    print("✅ Enhanced metadata system provides:")
    print("  📝 Complete book metadata (title, author, narrator, etc.)")
    print("  🔗 Webhook/torrent source information")
    print("  📊 Processing metadata and timestamps")
    print("  🎯 Template-friendly field names")
    print("  📱 Notification-ready data structure")

if __name__ == "__main__":
    test_metadata_fields()
