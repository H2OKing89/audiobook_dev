# Backend Endpoint Security Check

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from fastapi.testclient import TestClient
from src.main import app
from src.security import reset_rate_limit_buckets
import json

# Reset rate limits for clean testing
reset_rate_limit_buckets()

client = TestClient(app)

def test_endpoint_discovery():
    """Discover all available endpoints"""
    print("🔍 ENDPOINT DISCOVERY")
    print("=" * 50)
    
    # Check main endpoints
    endpoints = [
        ("/", "GET"),
        ("/webhook/audiobook-requests", "POST"),
        ("/approve/test-token", "GET"),
        ("/reject/test-token", "GET"),
        ("/admin", "GET"),
        ("/test-approval", "GET"),
        ("/static/css/style.css", "GET"),
        ("/health", "GET"),
        ("/api/admin", "GET"),
        ("/config", "GET"),
        ("/logs", "GET"),
        ("/stats", "GET"),
        ("/debug", "GET"),
    ]
    
    for endpoint, method in endpoints:
        try:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={"test": "data"})
            
            status = response.status_code
            status_emoji = "✅" if status < 400 else "❌" if status >= 500 else "⚠️"
            print(f"{status_emoji} {method} {endpoint}: {status}")
            
        except Exception as e:
            print(f"❌ {method} {endpoint}: ERROR - {e}")
    
    print()

def test_authentication_bypass():
    """Test for authentication bypass vulnerabilities"""
    print("🔐 AUTHENTICATION BYPASS TESTS")
    print("=" * 50)
    
    # Test protected endpoints without auth
    protected_endpoints = [
        "/admin",
        "/api/admin", 
        "/config",
        "/logs",
        "/stats",
        "/debug"
    ]
    
    for endpoint in protected_endpoints:
        response = client.get(endpoint)
        if response.status_code == 200:
            print(f"❌ SECURITY ISSUE: {endpoint} accessible without auth (200)")
        elif response.status_code == 401:
            print(f"✅ {endpoint}: Properly protected (401)")
        elif response.status_code == 403:
            print(f"✅ {endpoint}: Properly protected (403)")
        else:
            print(f"⚠️ {endpoint}: Unexpected response ({response.status_code})")
    
    print()

def test_authorization_headers():
    """Test various authorization header bypasses"""
    print("🔑 AUTHORIZATION HEADER TESTS") 
    print("=" * 50)
    
    bypass_headers = [
        {"X-API-Key": "admin"},
        {"X-API-Key": "test"},
        {"X-API-Key": ""},
        {"Authorization": "Bearer admin"},
        {"Authorization": "Basic YWRtaW46YWRtaW4="},  # admin:admin
        {"X-Forwarded-For": "127.0.0.1"},
        {"X-Real-IP": "127.0.0.1"},
        {"X-Admin": "true"},
        {"X-Debug": "true"},
    ]
    
    for headers in bypass_headers:
        response = client.get("/admin", headers=headers)
        header_name = list(headers.keys())[0]
        header_value = list(headers.values())[0]
        
        if response.status_code == 200:
            print(f"❌ BYPASS: /admin accessible with {header_name}: {header_value}")
        else:
            print(f"✅ {header_name}: {header_value} -> {response.status_code}")
    
    print()

def test_path_traversal():
    """Test for path traversal vulnerabilities"""
    print("📁 PATH TRAVERSAL TESTS")
    print("=" * 50)
    
    traversal_paths = [
        "/approve/../admin",
        "/approve/../../admin",
        "/approve/%2e%2e/admin",
        "/approve/..%2fadmin", 
        "/static/../src/config.py",
        "/static/../../config/config.yaml",
        "/static/%2e%2e%2fsrc%2fconfig.py",
    ]
    
    for path in traversal_paths:
        response = client.get(path)
        if response.status_code == 200:
            print(f"❌ TRAVERSAL: {path} -> 200 (potential issue)")
        elif response.status_code == 404:
            print(f"✅ {path} -> 404 (blocked)")
        else:
            print(f"⚠️ {path} -> {response.status_code}")
    
    print()

def test_http_methods():
    """Test HTTP method security"""
    print("🔧 HTTP METHOD TESTS")
    print("=" * 50)
    
    methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "TRACE"]
    test_endpoint = "/admin"
    
    for method in methods:
        try:
            response = client.request(method, test_endpoint)
            if method in ["GET", "POST"] and response.status_code == 200:
                print(f"❌ {method} {test_endpoint}: Unexpectedly accessible (200)")
            elif method not in ["GET", "POST"] and response.status_code == 200:
                print(f"❌ {method} {test_endpoint}: Unexpected method allowed (200)")
            elif response.status_code == 405:
                print(f"✅ {method} {test_endpoint}: Method not allowed (405)")
            elif response.status_code in [401, 403]:
                print(f"✅ {method} {test_endpoint}: Properly protected ({response.status_code})")
            else:
                print(f"⚠️ {method} {test_endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {method} {test_endpoint}: ERROR - {e}")
    
    print()

def test_injection_attacks():
    """Test for injection vulnerabilities"""
    print("💉 INJECTION ATTACK TESTS")
    print("=" * 50)
    
    # Test SQL injection in token parameter
    sql_payloads = [
        "' OR '1'='1",
        "1; DROP TABLE requests; --",
        "' UNION SELECT * FROM requests --",
        "admin'--",
        "' OR 1=1 #"
    ]
    
    for payload in sql_payloads:
        response = client.get(f"/approve/{payload}")
        if response.status_code == 200:
            print(f"❌ SQL INJECTION: /approve/{payload} -> 200")
        elif response.status_code == 500:
            print(f"⚠️ /approve/{payload} -> 500 (potential issue)")
        else:
            print(f"✅ /approve/{payload} -> {response.status_code}")
    
    print()

def test_webhook_security():
    """Test webhook endpoint security"""
    print("🔗 WEBHOOK SECURITY TESTS")
    print("=" * 50)
    
    # Test without required fields
    response = client.post("/webhook/audiobook-requests", json={})
    print(f"Empty payload: {response.status_code}")
    
    # Test with malicious payloads
    malicious_payloads = [
        {"name": "<script>alert('xss')</script>", "url": "http://test.com", "download_url": "http://test.com/file"},
        {"name": "'; DROP TABLE requests; --", "url": "http://test.com", "download_url": "http://test.com/file"},
        {"name": "Test", "url": "javascript:alert('xss')", "download_url": "http://test.com/file"},
        {"name": "A" * 10000, "url": "http://test.com", "download_url": "http://test.com/file"},  # Large input
    ]
    
    for i, payload in enumerate(malicious_payloads):
        response = client.post("/webhook/audiobook-requests", json=payload)
        print(f"Malicious payload {i+1}: {response.status_code}")
    
    print()

def test_csrf_protection():
    """Test CSRF protection"""
    print("🛡️ CSRF PROTECTION TESTS")
    print("=" * 50)
    
    # Test POST endpoints without CSRF tokens
    csrf_endpoints = [
        ("/approve/test-token", {"action": "approve"}),
        ("/reject/test-token", {"reason": "test"})
    ]
    
    for endpoint, data in csrf_endpoints:
        response = client.post(endpoint, data=data)
        if response.status_code == 200:
            print(f"⚠️ {endpoint}: POST allowed without CSRF token")
        elif response.status_code == 403:
            print(f"✅ {endpoint}: CSRF protection active (403)")
        else:
            print(f"⚠️ {endpoint}: {response.status_code}")
    
    print()

def test_rate_limiting():
    """Test rate limiting effectiveness"""
    print("🚦 RATE LIMITING TESTS")
    print("=" * 50)
    
    # Reset rate limits first
    reset_rate_limit_buckets()
    
    # Test webhook rate limiting
    webhook_url = "/webhook/audiobook-requests"
    payload = {"name": "Test", "url": "http://test.com", "download_url": "http://test.com/file"}
    
    # Make multiple requests to trigger rate limiting
    for i in range(12):  # Exceeds the 10 request limit
        response = client.post(webhook_url, json=payload)
        if response.status_code == 429:
            print(f"✅ Request {i+1}: Rate limited (429)")
            break
        elif i < 10:
            print(f"✅ Request {i+1}: Allowed ({response.status_code})")
        else:
            print(f"❌ Request {i+1}: Should be rate limited but got {response.status_code}")
    
    print()

def test_security_headers():
    """Test security headers"""
    print("🔒 SECURITY HEADERS TEST")
    print("=" * 50)
    
    response = client.get("/")
    headers = response.headers
    
    security_headers = [
        "X-Content-Type-Options",
        "X-Frame-Options", 
        "X-XSS-Protection",
        "Strict-Transport-Security",
        "Content-Security-Policy",
        "Referrer-Policy"
    ]
    
    for header in security_headers:
        if header in headers:
            print(f"✅ {header}: {headers[header]}")
        else:
            print(f"❌ {header}: Missing")
    
    print()

if __name__ == "__main__":
    print("🔍 BACKEND ENDPOINT SECURITY AUDIT")
    print("=" * 50)
    print("Starting comprehensive security check...")
    print()
    
    test_endpoint_discovery()
    test_authentication_bypass()
    test_authorization_headers()
    test_path_traversal()
    test_http_methods()
    test_injection_attacks()
    test_webhook_security()
    test_csrf_protection()
    test_rate_limiting()
    test_security_headers()
    
    print("🏁 SECURITY AUDIT COMPLETE")
    print("=" * 50)
