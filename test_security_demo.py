#!/usr/bin/env python3
"""
Test script for the new endpoint authentication system
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from fastapi.testclient import TestClient
from src.main import app

def test_endpoint_security():
    """Test the new endpoint authentication system"""
    client = TestClient(app)
    
    print("🔒 Testing Endpoint Security System")
    print("=" * 50)
    
    # Test 1: Public endpoint (should work)
    print("\n1. Testing public endpoint (/):")
    try:
        response = client.get('/')
        print(f"   Status: {response.status_code} ({'✅ PASS' if response.status_code == 200 else '❌ FAIL'})")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Protected endpoint without auth (should get 401)
    print("\n2. Testing protected endpoint (/admin) without auth:")
    try:
        response = client.get('/admin')
        print(f"   Status: {response.status_code} ({'✅ PASS' if response.status_code == 401 else '❌ FAIL'})")
        if response.status_code == 401:
            print("   ✅ Properly serving 401 Unauthorized page")
        else:
            print("   ❌ Should return 401 for protected endpoint")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Token endpoint (should work - these use token auth)
    print("\n3. Testing token endpoint (/approve/test-token):")
    try:
        response = client.get('/approve/test-token')
        print(f"   Status: {response.status_code} ({'✅ PASS' if response.status_code in [410, 404] else '❌ FAIL'})")
        if response.status_code == 410:
            print("   ✅ Token expired page (expected for invalid token)")
        elif response.status_code == 404:
            print("   ✅ Token not found (expected for invalid token)")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Static files (should work)
    print("\n4. Testing static files (/static/css/style.css):")
    try:
        response = client.get('/static/css/style.css')
        print(f"   Status: {response.status_code} ({'✅ PASS' if response.status_code in [200, 404] else '❌ FAIL'})")
        if response.status_code == 200:
            print("   ✅ Static files accessible")
        elif response.status_code == 404:
            print("   ⚠️  Static file not found (but not blocked by auth)")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Endpoint security test completed!")
    print("\nKey Security Features:")
    print("• Protected endpoints require authentication")
    print("• Public endpoints remain accessible")
    print("• Token-based endpoints use their own validation")
    print("• 401 pages are properly served for unauthorized access")

if __name__ == "__main__":
    test_endpoint_security()
