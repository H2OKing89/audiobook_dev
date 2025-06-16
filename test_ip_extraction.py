#!/usr/bin/env python3
"""
Test script to verify IP extraction works correctly with reverse proxy headers
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import Mock
from src.security import get_client_ip

def test_ip_extraction():
    """Test IP extraction with various header configurations"""
    
    print("🧪 Testing IP extraction with reverse proxy headers")
    print("=" * 60)
    
    # Test 1: X-Forwarded-For with single IP
    print("\n1. Testing X-Forwarded-For with single IP")
    request = Mock()
    request.headers = {"x-forwarded-for": "192.168.1.100"}
    request.client = Mock()
    request.client.host = "10.1.60.20"
    
    ip = get_client_ip(request)
    print(f"   Headers: x-forwarded-for: 192.168.1.100")
    print(f"   Direct IP: 10.1.60.20")
    print(f"   Result: {ip}")
    assert ip == "192.168.1.100", f"Expected 192.168.1.100, got {ip}"
    print("   ✅ PASS")
    
    # Test 2: X-Forwarded-For with multiple IPs (comma-separated)
    print("\n2. Testing X-Forwarded-For with multiple IPs")
    request = Mock()
    request.headers = {"x-forwarded-for": "203.0.113.195, 70.41.3.18, 150.172.238.178"}
    request.client = Mock()
    request.client.host = "10.1.60.20"
    
    ip = get_client_ip(request)
    print(f"   Headers: x-forwarded-for: 203.0.113.195, 70.41.3.18, 150.172.238.178")
    print(f"   Direct IP: 10.1.60.20")
    print(f"   Result: {ip}")
    assert ip == "203.0.113.195", f"Expected 203.0.113.195, got {ip}"
    print("   ✅ PASS")
    
    # Test 3: X-Real-IP (Nginx)
    print("\n3. Testing X-Real-IP (Nginx)")
    request = Mock()
    request.headers = {"x-real-ip": "198.51.100.178"}
    request.client = Mock()
    request.client.host = "10.1.60.20"
    
    ip = get_client_ip(request)
    print(f"   Headers: x-real-ip: 198.51.100.178")
    print(f"   Direct IP: 10.1.60.20")
    print(f"   Result: {ip}")
    assert ip == "198.51.100.178", f"Expected 198.51.100.178, got {ip}"
    print("   ✅ PASS")
    
    # Test 4: CF-Connecting-IP (Cloudflare)
    print("\n4. Testing CF-Connecting-IP (Cloudflare)")
    request = Mock()
    request.headers = {"cf-connecting-ip": "203.0.113.12"}
    request.client = Mock()
    request.client.host = "10.1.60.20"
    
    ip = get_client_ip(request)
    print(f"   Headers: cf-connecting-ip: 203.0.113.12")
    print(f"   Direct IP: 10.1.60.20")
    print(f"   Result: {ip}")
    assert ip == "203.0.113.12", f"Expected 203.0.113.12, got {ip}"
    print("   ✅ PASS")
    
    # Test 5: No proxy headers (direct connection)
    print("\n5. Testing direct connection (no proxy headers)")
    request = Mock()
    request.headers = {}
    request.client = Mock()
    request.client.host = "192.168.1.50"
    
    ip = get_client_ip(request)
    print(f"   Headers: (none)")
    print(f"   Direct IP: 192.168.1.50")
    print(f"   Result: {ip}")
    assert ip == "192.168.1.50", f"Expected 192.168.1.50, got {ip}"
    print("   ✅ PASS")
    
    # Test 6: Priority order (X-Forwarded-For should win over X-Real-IP)
    print("\n6. Testing header priority (X-Forwarded-For vs X-Real-IP)")
    request = Mock()
    request.headers = {
        "x-forwarded-for": "203.0.113.195",
        "x-real-ip": "198.51.100.178"
    }
    request.client = Mock()
    request.client.host = "10.1.60.20"
    
    ip = get_client_ip(request)
    print(f"   Headers: x-forwarded-for: 203.0.113.195, x-real-ip: 198.51.100.178")
    print(f"   Direct IP: 10.1.60.20")
    print(f"   Result: {ip}")
    assert ip == "203.0.113.195", f"Expected 203.0.113.195 (X-Forwarded-For priority), got {ip}"
    print("   ✅ PASS")
    
    # Test 7: Edge case - no client object
    print("\n7. Testing edge case (no client object)")
    request = Mock()
    request.headers = {}
    request.client = None
    
    ip = get_client_ip(request)
    print(f"   Headers: (none)")
    print(f"   Direct IP: (none)")
    print(f"   Result: {ip}")
    assert ip == "unknown", f"Expected 'unknown', got {ip}"
    print("   ✅ PASS")
    
    print("\n" + "=" * 60)
    print("🎉 All IP extraction tests passed!")
    print("\nThe centralized get_client_ip() function correctly:")
    print("✅ Extracts IP from X-Forwarded-For (first IP in list)")
    print("✅ Extracts IP from X-Real-IP (Nginx)")
    print("✅ Extracts IP from CF-Connecting-IP (Cloudflare)")
    print("✅ Falls back to direct connection IP")
    print("✅ Follows correct priority order")
    print("✅ Handles edge cases gracefully")
    print("\nThis should resolve the IP inconsistency issue you observed in the logs.")

if __name__ == "__main__":
    test_ip_extraction()
