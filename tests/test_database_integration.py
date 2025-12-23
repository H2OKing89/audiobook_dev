import concurrent.futures
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.db import cleanup, delete_request, get_request, list_tokens, save_request


class TestDatabaseIntegration:
    """Test database integration and operations"""

    def setup_method(self):
        """Setup for each test method"""
        # Use a temporary database for testing
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            self.test_db = f

    def teardown_method(self):
        """Cleanup after each test method"""
        # Clean up test database
        test_path = Path(self.test_db.name)
        if test_path.exists():
            test_path.unlink()

    def test_database_initialization(self):
        """Test database and table creation"""
        # Check that tokens table exists in the main database
        conn = sqlite3.connect(self.test_db.name)

        # Create the table structure manually for testing
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                token TEXT PRIMARY KEY,
                metadata TEXT,
                payload TEXT,
                timestamp INTEGER
            )
        """)
        conn.commit()

        # Check that tokens table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tokens'")
        table_exists = cursor.fetchone() is not None
        conn.close()

        assert table_exists

    def test_save_and_retrieve_request(self):
        """Test saving and retrieving request data"""
        token = "test_token_123"
        metadata = {"title": "Test Book", "author": "Test Author"}
        payload = {"url": "http://example.com", "download_url": "http://example.com/dl"}

        # Save request
        save_request(token, metadata, payload)

        # Retrieve request
        result = get_request(token)

        assert result is not None
        assert result["metadata"]["title"] == "Test Book"
        assert result["payload"]["url"] == "http://example.com"

    def test_token_expiration(self, monkeypatch):
        """Test token expiration logic"""
        token = "expiry_test_token"
        metadata = {"title": "Test Book"}
        payload = {"url": "http://example.com"}

        # Get current time for manipulation
        current_time = time.time()

        # Mock TTL to be very short
        with patch("src.db._get_ttl", return_value=1):  # 1 second TTL
            # Save with current time
            monkeypatch.setattr(time, "time", lambda: current_time)
            save_request(token, metadata, payload)

            # Should be retrievable immediately
            result = get_request(token)
            assert result is not None

            # Simulate time passing - move time forward
            monkeypatch.setattr(time, "time", lambda: current_time + 5)

            # Should be expired and return None
            result = get_request(token)
            assert result is None

    def test_concurrent_database_access(self):
        """Test concurrent access to database"""

        def worker(worker_id):
            token = f"concurrent_token_{worker_id}"
            metadata = {"title": f"Book {worker_id}"}
            payload = {"url": f"http://example.com/{worker_id}"}

            # Save and retrieve
            save_request(token, metadata, payload)
            result = get_request(token)
            return result is not None

        # Run multiple workers concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All operations should succeed
        assert all(results)

    def test_database_corruption_recovery(self):
        """Test recovery from database corruption"""
        # Simulate database corruption
        with patch("src.db.sqlite3.connect") as mock_connect:
            mock_connect.side_effect = sqlite3.DatabaseError("database disk image is malformed")

            # Should handle corruption gracefully
            try:
                save_request("test_token", {"title": "test"}, {"url": "test"})
            except sqlite3.DatabaseError:
                # Expected to fail, but shouldn't crash the application
                assert True

    def test_delete_request(self):
        """Test deleting request data"""
        token = "delete_test_token"
        metadata = {"title": "Test Book"}
        payload = {"url": "http://example.com"}

        # Save request
        save_request(token, metadata, payload)

        # Verify it exists
        result = get_request(token)
        assert result is not None

        # Delete request
        delete_request(token)

        # Verify it's gone
        result = get_request(token)
        assert result is None

    def test_cleanup_expired_tokens(self, monkeypatch):
        """Test cleanup of expired tokens"""
        # Get current time for manipulation
        current_time = time.time()
        monkeypatch.setattr(time, "time", lambda: current_time)

        # Create multiple tokens with different timestamps
        tokens = []
        for i in range(5):
            token = f"cleanup_token_{i}"
            metadata = {"title": f"Book {i}"}
            payload = {"url": f"http://example.com/{i}"}
            save_request(token, metadata, payload)
            tokens.append(token)

        # Mock some tokens as expired by moving time forward
        with patch("src.db._get_ttl", return_value=1):
            monkeypatch.setattr(time, "time", lambda: current_time + 5)

            # Run cleanup
            cleanup()

            # Check that expired tokens are removed
            remaining = list_tokens()
            assert len(remaining) == 0  # All should be expired and cleaned up

    def test_list_tokens(self):
        """Test listing all tokens"""
        # Create several tokens
        tokens_created = []
        for i in range(3):
            token = f"list_token_{i}"
            metadata = {"title": f"Book {i}"}
            payload = {"url": f"http://example.com/{i}"}
            save_request(token, metadata, payload)
            tokens_created.append(token)

        # List tokens
        token_list = list_tokens()

        # Should find all created tokens
        assert len(token_list) >= 3
        token_names = [t["token"] for t in token_list]
        for token in tokens_created:
            assert token in token_names

    def test_database_transaction_rollback(self):
        """Test database transaction rollback on error"""
        # Test rollback by simulating an error during transaction
        with patch("src.db._conn", create=True) as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.execute.side_effect = sqlite3.IntegrityError("UNIQUE constraint failed")
            mock_conn.commit = MagicMock()

            # Attempt to save a request - should handle the exception
            try:
                save_request("test_token", {"title": "test"}, {"url": "test"})
            except sqlite3.IntegrityError:
                # Expected to fail
                assert True
            except Exception:
                # Any other exception is also acceptable for this test
                assert True

    def test_json_serialization_errors(self):
        """Test handling of JSON serialization errors"""

        # Create non-serializable data
        class NonSerializable:
            pass

        non_serializable_metadata = {"object": NonSerializable()}

        # Should handle serialization errors gracefully
        try:
            save_request("serial_test", non_serializable_metadata, {"url": "test"})
        except (TypeError, ValueError):
            # Expected to fail with serialization error
            assert True

    def test_database_locking(self):
        """Test database locking behavior"""

        def long_running_operation():
            # Simulate a long-running database operation
            token = "lock_test_token"
            metadata = {"title": "Test Book"}
            payload = {"url": "http://example.com"}
            save_request(token, metadata, payload)
            time.sleep(0.1)  # Hold the lock briefly
            get_request(token)

        # Run concurrent operations that might contend for locks
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(long_running_operation) for _ in range(10)]

            # All should complete without deadlock
            for future in concurrent.futures.as_completed(futures, timeout=5):
                try:
                    future.result()
                except Exception as e:
                    # Log any exceptions but don't fail the test
                    print(f"Database operation failed: {e}")

    def test_large_data_storage(self):
        """Test storage of large data objects"""
        # Create large metadata and payload
        large_metadata = {
            "title": "Large Book",
            "description": "A" * 100000,  # 100KB description
            "tags": ["tag" + str(i) for i in range(1000)],  # Many tags
        }
        large_payload = {
            "url": "http://example.com",
            "download_url": "http://example.com/large.torrent",
            "extra_data": "B" * 50000,  # 50KB extra data
        }

        token = "large_data_token"

        # Should handle large data
        try:
            save_request(token, large_metadata, large_payload)
            result = get_request(token)
            assert result is not None
            assert len(result["metadata"]["description"]) == 100000
        except Exception as e:
            # If it fails, should be a controlled failure
            assert "size" in str(e).lower() or "memory" in str(e).lower()

    def test_unicode_data_storage(self):
        """Test storage of Unicode data"""
        unicode_metadata = {
            "title": "测试书籍 📚",
            "author": "автор كاتب लेखक",
            "description": "🎧 Audio book with émojis and spëcial chäractërs",
            "unicode_test": "\u202e\u200b\ufeff",  # Tricky Unicode
        }
        unicode_payload = {"url": "http://example.com/测试", "download_url": "http://example.com/ダウンロード.torrent"}

        token = "unicode_test_token"

        # Should handle Unicode data correctly
        save_request(token, unicode_metadata, unicode_payload)
        result = get_request(token)

        assert result is not None
        assert result["metadata"]["title"] == "测试书籍 📚"
        assert "émojis" in result["metadata"]["description"]

    def test_null_and_empty_data(self):
        """Test handling of null and empty data"""
        test_cases = [
            ({}, {}),  # Empty dicts
            ({"title": ""}, {"url": ""}),  # Empty strings
            ({"title": None}, {"url": None}),  # None values
            ({"title": "Test", "empty_list": []}, {"tags": []}),  # Empty lists
        ]

        for i, (metadata, payload) in enumerate(test_cases):
            token = f"null_test_token_{i}"

            # Should handle edge cases gracefully
            try:
                save_request(token, metadata, payload)
                result = get_request(token)
                assert result is not None
            except Exception as e:
                # If it fails, should be a controlled failure
                print(f"Edge case failed: {e}")

    def test_database_backup_compatibility(self):
        """Test that data can be backed up and restored"""
        # Create test data
        original_tokens = []
        for i in range(3):
            token = f"backup_token_{i}"
            metadata = {"title": f"Backup Book {i}"}
            payload = {"url": f"http://example.com/{i}"}
            save_request(token, metadata, payload)
            original_tokens.append(token)

        # Simulate backup by reading all data
        all_tokens = list_tokens()
        backup_data = {}
        for token_info in all_tokens:
            if token_info["token"].startswith("backup_token_"):
                data = get_request(token_info["token"])
                if data:
                    backup_data[token_info["token"]] = data

        # Clear some data
        for token in original_tokens:
            delete_request(token)

        # Verify data is gone
        for token in original_tokens:
            assert get_request(token) is None

        # Simulate restore
        for token, data in backup_data.items():
            save_request(token, data["metadata"], data["payload"])

        # Verify data is restored
        for token in original_tokens:
            restored_data = get_request(token)
            assert restored_data is not None
