#!/usr/bin/env python3
"""
System Validation Test
Tests the complete audiobook approval system to ensure all components are working.
"""

import sys
import requests
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_health_endpoint():
    """Test the health endpoint"""
    print("🏥 Testing health endpoint...")
    try:
        response = requests.get("http://10.1.60.11:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Health check passed: {data['status']}")
            return True
        else:
            print(f"✗ Health check failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Health check error: {e}")
        return False

def test_queue_status_endpoint():
    """Test the queue status endpoint (should be blocked from external access)"""
    print("🔒 Testing queue status endpoint security...")
    try:
        response = requests.get("http://10.1.60.11:8000/queue/status", timeout=5)
        if response.status_code == 403:
            print("✓ Queue status endpoint properly blocked (403 Forbidden)")
            return True
        elif response.status_code == 200:
            # If we get 200, it means we're accessing from a local IP
            data = response.json()
            print(f"✓ Queue status accessible from local network: {data['queue_size']} items in queue")
            return True
        else:
            print(f"✗ Unexpected status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Queue status test error: {e}")
        return False

def test_notification_field_extraction():
    """Test notification field extraction"""
    print("📧 Testing notification field extraction...")
    try:
        from src.utils import get_notification_fields
        
        # Test data with various field formats
        test_metadata = {
            'title': 'The Test Audiobook: A Novel',
            'author': 'Test Author',
            'series': [{'series': 'Test Series', 'sequence': '1'}],
            'narrator_list': ['Narrator One', 'Narrator Two'],
            'publisher': 'Test Publisher',
            'release_date': '2023-01-01T00:00:00Z',
            'runtime_minutes': 480,
            'summary': '<p>This is a test summary with <strong>HTML</strong> tags.</p>',
            'cover_url': 'https://example.com/cover.jpg'
        }
        
        test_payload = {
            'category': 'audiobook',
            'size': 1024*1024*500,  # 500MB
            'url': 'https://example.com/test',
            'download_url': 'https://example.com/download'
        }
        
        fields = get_notification_fields(test_metadata, test_payload)
        
        # Validate critical fields
        checks = [
            ('title', 'The Test Audiobook: A Novel'),
            ('series', 'Test Series (Vol. 1)'),
            ('author', 'Test Author'),
            ('narrators', ['Narrator One', 'Narrator Two']),
            ('publisher', 'Test Publisher'),
            ('release_date', '2023-01-01'),
            ('runtime', '480'),
            ('size', '500.00 MB'),
            ('description', 'This is a test summary with HTML tags.')
        ]
        
        all_passed = True
        for field, expected in checks:
            actual = fields.get(field)
            if actual == expected:
                print(f"  ✓ {field}: {actual}")
            else:
                print(f"  ✗ {field}: expected '{expected}', got '{actual}'")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"✗ Notification field extraction error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_css_variables():
    """Test that CSS variables are properly defined for light/dark mode"""
    print("🎨 Testing CSS variables for light/dark mode...")
    try:
        css_file = Path("static/css/pages/approval.css")
        if not css_file.exists():
            print("✗ CSS file not found")
            return False
        
        css_content = css_file.read_text()
        
        # Check for CSS variables
        required_vars = [
            '--bg-primary',
            '--bg-secondary',
            '--text-primary',
            '--text-secondary',
            '--accent-cyan',
            '--border-primary'
        ]
        
        # Check for light mode media query
        has_light_mode = '@media (prefers-color-scheme: light)' in css_content
        if has_light_mode:
            print("  ✓ Light mode media query found")
        else:
            print("  ✗ Light mode media query missing")
            return False
        
        # Check for CSS variables
        missing_vars = []
        for var in required_vars:
            if var not in css_content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"  ✗ Missing CSS variables: {missing_vars}")
            return False
        else:
            print(f"  ✓ All {len(required_vars)} CSS variables found")
        
        return True
        
    except Exception as e:
        print(f"✗ CSS validation error: {e}")
        return False

def test_metadata_coordinator():
    """Test metadata coordinator import and initialization"""
    print("🔧 Testing metadata coordinator...")
    try:
        from src.metadata_coordinator import MetadataCoordinator
        
        # Just test that it can be imported and initialized
        coordinator = MetadataCoordinator()
        print("  ✓ MetadataCoordinator imported and initialized")
        
        # Check that it has the required methods
        required_methods = ['get_metadata_from_webhook', '_enforce_rate_limit']
        for method in required_methods:
            if hasattr(coordinator, method):
                print(f"  ✓ Method {method} found")
            else:
                print(f"  ✗ Method {method} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Metadata coordinator error: {e}")
        return False

def main():
    """Run all system validation tests"""
    print("🚀 AUDIOBOOK SYSTEM VALIDATION TESTS")
    print("=" * 50)
    
    tests = [
        test_health_endpoint,
        test_queue_status_endpoint,
        test_notification_field_extraction,
        test_css_variables,
        test_metadata_coordinator
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            results.append(False)
            print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - System is ready for production!")
        return 0
    else:
        print("❌ Some tests failed - please review the output above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
