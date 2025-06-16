import pytest
import time
import asyncio
import threading
import os
import requests
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.main import app
from src.db import save_request, get_request
from src.metadata import fetch_metadata
import concurrent.futures
import statistics

client = TestClient(app)


class TestPerformance:
    """Test performance and load handling"""

    def test_concurrent_webhook_performance(self):
        """Test performance under concurrent webhook requests"""
        # Use a payload with a valid ASIN in the name to avoid Audible scraping
        payload = {
            "name": "Test Audiobook B07X5VKZQL",  # Include valid ASIN format
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent"
        }
        
        def make_request():
            start_time = time.time()
            
            # Mock all external dependencies to avoid network calls
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": 1}
            mock_response.raise_for_status.return_value = None
            
            with patch.dict('os.environ', {
                'AUTOBRR_TOKEN': 'test_token',
                'PUSHOVER_TOKEN': 'mock_token',
                'PUSHOVER_USER': 'mock_user',
                'DISCORD_WEBHOOK_URL': 'https://discord.com/api/webhooks/mock',
                'GOTIFY_URL': 'https://gotify.example.com',
                'GOTIFY_TOKEN': 'mock_gotify_token',
                'NTFY_USER': 'mock_user',
                'NTFY_PASS': 'mock_pass'
            }), \
                 patch("src.metadata.get_cached_metadata", return_value={
                     "asin": "B07X5VKZQL",
                     "title": "Test Book",
                     "author": "Test Author",
                     "series": "Test Series",
                     "publisher": "Test Publisher",
                     "narrators": ["Test Narrator"],
                     "release_date": "2024-01-01",
                     "runtime": "10h 30m",
                     "category": "fiction",
                     "description": "Test description",
                     "cover_url": "https://example.com/cover.jpg"
                 }), \
                 patch("requests.get", return_value=mock_response), \
                 patch("requests.post", return_value=mock_response), \
                 patch("src.db.save_request"):  # Mock database save to avoid I/O
                
                resp = client.post(
                    "/webhook/audiobook-requests",
                    json=payload,
                    headers={"X-Autobrr-Token": "test_token"}
                )
                
                end_time = time.time()
                return {
                    'status_code': resp.status_code,
                    'response_time': end_time - start_time,
                    'success': resp.status_code == 200
                }
        
        # Test with increasing concurrency levels
        concurrency_levels = [1, 5, 10, 20]
        
        for concurrency in concurrency_levels:
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(make_request) for _ in range(concurrency * 2)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Calculate metrics
            response_times = [r['response_time'] for r in results]
            success_rate = sum(1 for r in results if r['success']) / len(results)
            avg_response_time = statistics.mean(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else response_times[0]
            
            print(f"Concurrency {concurrency}: Success rate: {success_rate:.2%}, "
                  f"Avg response: {avg_response_time:.3f}s, P95: {p95_response_time:.3f}s, "
                  f"Total time: {total_time:.3f}s")
            
            # Performance assertions with more reasonable thresholds for mocked environment
            assert success_rate >= 0.95  # At least 95% success rate (should be high with mocking)
            assert avg_response_time < 1.0  # Average response under 1 second (mocked)
            assert p95_response_time < 2.0  # P95 under 2 seconds (mocked)

    def test_memory_usage_under_load(self):
        """Test memory usage under sustained load (simplified without psutil)"""
        # Track object count as a proxy for memory usage
        import gc
        initial_objects = len(gc.get_objects())
        
        payload = {
            "name": "Memory Test Book B07X5VKZQL",  # Include valid ASIN format
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent"
        }
        
        # Make many requests with proper mocking
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": 1}
        mock_response.raise_for_status.return_value = None
        
        with patch.dict('os.environ', {
            'AUTOBRR_TOKEN': 'test_token',
            'PUSHOVER_TOKEN': 'mock_token',
            'PUSHOVER_USER': 'mock_user',
            'DISCORD_WEBHOOK_URL': 'https://discord.com/api/webhooks/mock',
            'GOTIFY_URL': 'https://gotify.example.com',
            'GOTIFY_TOKEN': 'mock_gotify_token'
        }), \
             patch("src.metadata.get_cached_metadata", return_value={
                 "asin": "B07X5VKZQL",
                 "title": "Memory Test Book",
                 "author": "Test Author"
             }), \
             patch("requests.get", return_value=mock_response), \
             patch("requests.post", return_value=mock_response), \
             patch("src.db.save_request"):
            
            for i in range(100):
                resp = client.post(
                    "/webhook/audiobook-requests",
                    json=payload,
                    headers={"X-Autobrr-Token": "test_token"}
                )
        
        # Force garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects
        
        print(f"Object count growth: {object_growth} objects")
        
        # Object count shouldn't grow excessively
        assert object_growth < 10000, f"Object count grew by {object_growth}"

    def test_database_query_performance(self):
        """Test database operation performance"""
        # Create test data
        test_tokens = []
        for i in range(1000):
            token = f"perf_token_{i:04d}"
            metadata = {"title": f"Performance Book {i}"}
            payload = {"url": f"http://example.com/{i}"}
            test_tokens.append(token)
        
        # Test bulk insert performance
        start_time = time.time()
        for i, token in enumerate(test_tokens):
            metadata = {"title": f"Performance Book {i}"}
            payload = {"url": f"http://example.com/{i}"}
            save_request(token, metadata, payload)
        insert_time = time.time() - start_time
        
        print(f"Bulk insert time for 1000 records: {insert_time:.3f}s")
        
        # Test bulk read performance
        start_time = time.time()
        retrieved_count = 0
        for token in test_tokens[:100]:  # Read first 100
            result = get_request(token)
            if result:
                retrieved_count += 1
        read_time = time.time() - start_time
        
        print(f"Bulk read time for 100 records: {read_time:.3f}s")
        
        # Performance assertions
        assert insert_time < 10.0  # Should insert 1000 records in under 10 seconds
        assert read_time < 1.0     # Should read 100 records in under 1 second
        assert retrieved_count == 100  # Should retrieve all requested records

    def test_notification_queue_performance(self):
        """Test notification sending performance"""
        metadata = {"title": "Queue Test Book", "author": "Test Author"}
        payload = {"url": "http://example.com", "download_url": "http://example.com/dl"}
        token = "queue_test_token"
        base_url = "http://localhost:8000"
        
        # Mock notification services for performance testing
        with patch("src.notify.pushover.requests.post") as mock_pushover, \
             patch("src.notify.discord.requests.post") as mock_discord, \
             patch("src.notify.gotify.requests.post") as mock_gotify:
            
            # Configure mocks for fast responses
            mock_pushover.return_value = MagicMock(status_code=200, json=lambda: {"status": 1})
            mock_discord.return_value = MagicMock(status_code=204)
            mock_gotify.return_value = MagicMock(status_code=200)
            
            # Test notification sending speed
            start_time = time.time()
            
            for i in range(50):
                # This would normally trigger notifications
                test_payload = {
                    "name": f"Test Book {i}",
                    "url": "http://example.com/view",
                    "download_url": "http://example.com/download.torrent"
                }
                
                with patch.dict('os.environ', {'AUTOBRR_TOKEN': 'test_token'}), \
                     patch("src.metadata.fetch_metadata", return_value=metadata):
                    
                    resp = client.post(
                        "/webhook/audiobook-requests",
                        json=test_payload,
                        headers={"X-Autobrr-Token": "test_token"}
                    )
            
            notification_time = time.time() - start_time
            
            print(f"Time to process 50 notifications: {notification_time:.3f}s")
            
            # Should process notifications reasonably quickly
            assert notification_time < 15.0  # Under 15 seconds for 50 notifications

    def test_metadata_caching_efficiency(self):
        """Test metadata caching performance"""
        # Test same metadata requests (should hit cache)
        asin = "B123456789"
        region = "us"
        api_url = "https://api.audnex.us/books"
        
        with patch("src.metadata.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"title": "Cached Book", "asin": asin}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            from src.metadata import get_cached_metadata
            
            # First request - should hit API
            start_time = time.time()
            result1 = get_cached_metadata(asin, region, api_url)
            first_request_time = time.time() - start_time
            
            # Subsequent requests - should hit cache
            start_time = time.time()
            for _ in range(10):
                result = get_cached_metadata(asin, region, api_url)
                assert result == result1  # Should return same data
            cached_requests_time = time.time() - start_time
            
            print(f"First request: {first_request_time:.3f}s, "
                  f"10 cached requests: {cached_requests_time:.3f}s")
            
            # Cache should be significantly faster
            assert cached_requests_time < first_request_time
            assert mock_get.call_count == 1  # Should only call API once

    def test_large_payload_handling(self):
        """Test handling of large payloads"""
        # Create increasingly large payloads
        payload_sizes = [1, 10, 100, 1000]  # KB
        
        for size_kb in payload_sizes:
            large_description = "A" * (size_kb * 1024)
            payload = {
                "name": f"Large Payload Test {size_kb}KB",
                "url": "http://example.com/view",
                "download_url": "http://example.com/download.torrent",
                "description": large_description
            }
            
            start_time = time.time()
            
            with patch.dict('os.environ', {'AUTOBRR_TOKEN': 'test_token'}), \
                 patch("src.metadata.fetch_metadata", return_value={"title": "Large Book"}):
                
                resp = client.post(
                    "/webhook/audiobook-requests",
                    json=payload,
                    headers={"X-Autobrr-Token": "test_token"}
                )
            
            processing_time = time.time() - start_time
            
            print(f"Payload size {size_kb}KB: {processing_time:.3f}s, "
                  f"Status: {resp.status_code}")
            
            # Should handle large payloads within reasonable time
            assert processing_time < 10.0
            assert resp.status_code in [200, 413, 422]  # Success or controlled failure

    def test_concurrent_database_performance(self):
        """Test database performance under concurrent load"""
        def database_worker(worker_id):
            operations = []
            
            for i in range(10):  # Each worker does 10 operations
                token = f"concurrent_{worker_id}_{i}"
                metadata = {"title": f"Worker {worker_id} Book {i}"}
                payload = {"url": f"http://example.com/{worker_id}/{i}"}
                
                # Save operation
                start_time = time.time()
                save_request(token, metadata, payload)
                save_time = time.time() - start_time
                
                # Read operation
                start_time = time.time()
                result = get_request(token)
                read_time = time.time() - start_time
                
                operations.append({
                    'save_time': save_time,
                    'read_time': read_time,
                    'success': result is not None
                })
            
            return operations
        
        # Run concurrent database operations
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(database_worker, i) for i in range(10)]
            all_operations = []
            for future in concurrent.futures.as_completed(futures):
                all_operations.extend(future.result())
        
        total_time = time.time() - start_time
        
        # Calculate performance metrics
        save_times = [op['save_time'] for op in all_operations]
        read_times = [op['read_time'] for op in all_operations]
        success_rate = sum(1 for op in all_operations if op['success']) / len(all_operations)
        
        avg_save_time = statistics.mean(save_times)
        avg_read_time = statistics.mean(read_times)
        
        print(f"Concurrent DB operations - Total time: {total_time:.3f}s, "
              f"Success rate: {success_rate:.2%}, "
              f"Avg save: {avg_save_time:.4f}s, Avg read: {avg_read_time:.4f}s")
        
        # Performance assertions
        assert success_rate >= 0.95  # At least 95% success rate
        assert avg_save_time < 0.1   # Average save under 100ms
        assert avg_read_time < 0.05  # Average read under 50ms

    def test_response_time_consistency(self):
        """Test consistency of response times"""
        payload = {
            "name": "Consistency Test Book",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent"
        }
        
        response_times = []
        
        for i in range(30):  # 30 requests
            start_time = time.time()
            
            with patch.dict('os.environ', {'AUTOBRR_TOKEN': 'test_token'}), \
                 patch("src.metadata.fetch_metadata", return_value={"title": "Consistent Book"}):
                
                resp = client.post(
                    "/webhook/audiobook-requests",
                    json=payload,
                    headers={"X-Autobrr-Token": "test_token"}
                )
            
            response_time = time.time() - start_time
            response_times.append(response_time)
            
            # Brief pause to avoid overwhelming
            time.sleep(0.1)
        
        # Calculate consistency metrics
        avg_time = statistics.mean(response_times)
        std_dev = statistics.stdev(response_times) if len(response_times) > 1 else 0
        min_time = min(response_times)
        max_time = max(response_times)
        
        print(f"Response time consistency - Avg: {avg_time:.3f}s, "
              f"StdDev: {std_dev:.3f}s, Min: {min_time:.3f}s, Max: {max_time:.3f}s")
        
        # Consistency assertions
        assert std_dev < avg_time * 0.5  # Standard deviation should be less than 50% of average
        assert max_time < avg_time * 3   # No response should be more than 3x the average

    def test_resource_cleanup_performance(self):
        """Test performance of cleanup operations"""
        # Create many tokens that will need cleanup
        cleanup_tokens = []
        for i in range(500):
            token = f"cleanup_perf_token_{i}"
            metadata = {"title": f"Cleanup Book {i}"}
            payload = {"url": f"http://example.com/{i}"}
            save_request(token, metadata, payload)
            cleanup_tokens.append(token)
        
        # Mock short TTL to make tokens eligible for cleanup
        with patch('src.db.TTL', 1):
            time.sleep(2)  # Wait for expiration
            
            # Time the cleanup operation
            start_time = time.time()
            from src.db import cleanup
            cleanup()
            cleanup_time = time.time() - start_time
            
            print(f"Cleanup time for 500 expired tokens: {cleanup_time:.3f}s")
            
            # Cleanup should be reasonably fast
            assert cleanup_time < 5.0  # Should cleanup 500 tokens in under 5 seconds

    def test_stress_test_endpoint(self):
        """Stress test the main endpoint"""
        payload = {
            "name": "Stress Test Book",
            "url": "http://example.com/view",
            "download_url": "http://example.com/download.torrent"
        }
        
        # Rapid fire requests
        start_time = time.time()
        success_count = 0
        error_count = 0
        
        for i in range(100):
            try:
                with patch.dict('os.environ', {'AUTOBRR_TOKEN': 'test_token'}), \
                     patch("src.metadata.fetch_metadata", return_value={"title": f"Stress Book {i}"}):
                    
                    resp = client.post(
                        "/webhook/audiobook-requests",
                        json=payload,
                        headers={"X-Autobrr-Token": "test_token"}
                    )
                    
                    if resp.status_code == 200:
                        success_count += 1
                    else:
                        error_count += 1
                        
            except Exception as e:
                error_count += 1
                print(f"Request {i} failed: {e}")
        
        total_time = time.time() - start_time
        throughput = 100 / total_time  # requests per second
        
        print(f"Stress test - {success_count} successes, {error_count} errors, "
              f"Throughput: {throughput:.1f} req/s")
        
        # Stress test assertions
        assert success_count >= 80  # At least 80% success under stress
        assert throughput >= 5      # At least 5 requests per second
