#!/usr/bin/env python3
"""
Test script to simulate a webhook POST to the main application
"""

import sys
import json
import requests
from pathlib import Path

def test_webhook_post():
    """Test webhook POST to the main application"""
    
    # Real working webhook payload from logs
    webhook_payload = {
        "name": "In Another World with My Smartphone: Volume 6: by Patora Fuyuhara [English / m4b]",
        "indexer": "myanonamouse",
        "url": "https://www.myanonamouse.net/t/1156932",
        "download_url": "https://www.myanonamouse.net/tor/download.php?tid=1156932",
        "category": "Audiobooks - Fantasy",
        "size": "378431078"
    }
    
    print("Testing webhook POST to main application...")
    print(f"Payload: {json.dumps(webhook_payload, indent=2)}")
    
    try:
        # Assuming the server is running on localhost:8080
        # This is just a test - you would normally have the server running
        response = requests.post(
            "http://localhost:8080/webhook",
            json=webhook_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Webhook processed successfully!")
        else:
            print(f"❌ Webhook failed with status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server - make sure it's running on localhost:8080")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_webhook_post()
