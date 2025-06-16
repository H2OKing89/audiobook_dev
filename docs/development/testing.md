# 🧪 Testing Guide

This guide covers testing strategies, running tests, and contributing test coverage to the audiobook automation system.

## 🏗️ Test Architecture

The test suite is organized into several categories:

### 📊 Test Types

```
tests/
├── conftest.py                    # Pytest configuration and fixtures
├── test_config.py                 # Configuration testing
├── test_database_integration.py   # Database operations
├── test_end_to_end.py             # Full workflow testing
├── test_main_integration.py       # Application integration
├── test_webui.py                  # Web interface testing
├── test_metadata_extended.py      # Metadata handling
├── test_notify_formatting.py      # Notification formatting
├── test_qbittorrent.py           # qBittorrent integration
├── test_security.py              # Security features
├── test_token_gen.py             # Token generation/validation
└── test_utils_*.py               # Utility function tests
```

### 🎯 Test Categories

1. **Unit Tests** - Individual component testing
2. **Integration Tests** - Cross-component functionality
3. **End-to-End Tests** - Complete workflow validation
4. **Security Tests** - Authentication and authorization
5. **Performance Tests** - Load and response time testing

## 🚀 Running Tests

### All Tests
```bash
# Run the complete test suite
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src --cov-report=html
```

### Specific Test Categories
```bash
# Unit tests only
pytest tests/test_config.py tests/test_token_gen.py -v

# Integration tests
pytest tests/test_database_integration.py tests/test_main_integration.py -v

# Web interface tests
pytest tests/test_webui.py -v

# End-to-end tests
pytest tests/test_end_to_end.py -v
```

### Specific Test Functions
```bash
# Run a specific test
pytest tests/test_webui.py::test_rejection_endpoint -v

# Run tests matching a pattern
pytest -k "test_token" -v

# Run tests with specific markers
pytest -m "slow" -v
```

## 🔧 Test Configuration

### Environment Setup
```bash
# Create test environment
python -m venv .venv-test
source .venv-test/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio
```

### Test Configuration (`conftest.py`)
```python
import pytest
from fastapi.testclient import TestClient
import tempfile
import os

@pytest.fixture
def test_client():
    """FastAPI test client with test configuration"""
    from src.webui import app
    return TestClient(app)

@pytest.fixture
def test_db():
    """Temporary test database"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        test_db_path = f.name
    
    # Initialize test database
    os.environ['TEST_DB_PATH'] = test_db_path
    
    yield test_db_path
    
    # Cleanup
    if os.path.exists(test_db_path):
        os.unlink(test_db_path)

@pytest.fixture
def sample_request_data():
    """Sample audiobook request data for testing"""
    return {
        "title": "Test Audiobook",
        "author": "Test Author",
        "isbn": "9781234567890",
        "description": "A test audiobook for automated testing"
    }
```

## 📝 Writing Tests

### Test Structure Template
```python
import pytest
from fastapi.testclient import TestClient

class TestFeatureName:
    """Test suite for specific feature"""
    
    def setup_method(self):
        """Setup before each test method"""
        self.test_data = {"key": "value"}
    
    def test_positive_case(self, test_client):
        """Test the happy path"""
        response = test_client.get("/endpoint")
        assert response.status_code == 200
        assert "expected_content" in response.text
    
    def test_negative_case(self, test_client):
        """Test error conditions"""
        response = test_client.post("/endpoint", json={})
        assert response.status_code == 400
    
    def test_edge_case(self, test_client):
        """Test boundary conditions"""
        # Test implementation
        pass
    
    @pytest.mark.slow
    def test_performance_case(self, test_client):
        """Test performance-sensitive operations"""
        # Test implementation
        pass
```

### Web Interface Testing
```python
def test_home_page(test_client):
    """Test home page renders correctly"""
    response = test_client.get("/")
    assert response.status_code == 200
    assert "home-page" in response.text
    assert "Audiobook HQ" in response.text

def test_request_submission(test_client, sample_request_data):
    """Test audiobook request submission"""
    response = test_client.post("/audiobook-requests", json=sample_request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    assert "request_id" in data
```

### Database Testing
```python
def test_database_operations(test_db):
    """Test database CRUD operations"""
    from src.db import Database
    
    db = Database(test_db)
    
    # Test create
    request_id = db.create_request({
        "title": "Test Book",
        "author": "Test Author"
    })
    assert request_id is not None
    
    # Test read
    request = db.get_request(request_id)
    assert request["title"] == "Test Book"
    
    # Test update
    db.update_request(request_id, {"status": "approved"})
    updated_request = db.get_request(request_id)
    assert updated_request["status"] == "approved"
```

### Security Testing
```python
def test_token_validation():
    """Test token generation and validation"""
    from src.token_gen import generate_token, validate_token
    
    # Generate valid token
    token = generate_token(request_id=123, action="approve")
    assert token is not None
    assert len(token) > 20
    
    # Validate token
    is_valid, data = validate_token(token)
    assert is_valid
    assert data["request_id"] == 123
    assert data["action"] == "approve"

def test_token_expiration():
    """Test token expiration handling"""
    # Test with expired token
    # Implementation depends on token system
    pass
```

### Notification Testing
```python
@pytest.mark.asyncio
async def test_notification_sending():
    """Test notification delivery"""
    from src.notify.discord import DiscordNotifier
    
    notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/test")
    
    # Mock the HTTP request
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        
        result = await notifier.send_approval_request({
            "title": "Test Book",
            "author": "Test Author"
        })
        
        assert result is True
        mock_post.assert_called_once()
```

## 🎭 Test Fixtures and Mocking

### Common Fixtures
```python
@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    return {
        "server": {"host": "localhost", "port": 8000},
        "database": {"path": ":memory:"},
        "notifications": {"enabled": False}
    }

@pytest.fixture
def mock_metadata_response():
    """Mock metadata API response"""
    return {
        "title": "Test Audiobook",
        "author": "Test Author",
        "description": "Test description",
        "cover_url": "https://example.com/cover.jpg"
    }
```

### Mocking External Services
```python
from unittest.mock import patch, Mock

def test_metadata_lookup():
    """Test metadata lookup with mocked API"""
    with patch('src.metadata.fetch_audnex_data') as mock_fetch:
        mock_fetch.return_value = {
            "title": "Mocked Title",
            "author": "Mocked Author"
        }
        
        from src.metadata import get_book_metadata
        result = get_book_metadata("test-isbn")
        
        assert result["title"] == "Mocked Title"
        mock_fetch.assert_called_once_with("test-isbn")
```

## 📊 Test Coverage

### Coverage Reports
```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Generate terminal coverage report
pytest --cov=src --cov-report=term-missing

# Generate XML coverage report (for CI)
pytest --cov=src --cov-report=xml
```

### Coverage Goals
- **Overall Coverage:** >85%
- **Critical Components:** >95%
  - Authentication/authorization
  - Database operations
  - Token generation/validation
  - Security functions

### Viewing Coverage
```bash
# Open HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## 🔄 Continuous Integration

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.8
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1
      with:
        file: ./coverage.xml
```

## 🐛 Debugging Tests

### Running Tests in Debug Mode
```bash
# Run with Python debugger
pytest --pdb

# Run specific test with debugger
pytest tests/test_webui.py::test_rejection_endpoint --pdb

# Run with verbose output and no capture
pytest -v -s
```

### Debug Configuration
```python
# Add to test files for debugging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use print statements (will show with -s flag)
def test_debug_example():
    print("Debug information here")
    assert True
```

## 📈 Performance Testing

### Load Testing Example
```python
import time
import concurrent.futures

def test_concurrent_requests():
    """Test system under concurrent load"""
    def make_request():
        response = test_client.get("/")
        return response.status_code
    
    # Test with 10 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # All requests should succeed
    assert all(status == 200 for status in results)
```

## 🎯 Best Practices

### Test Writing Guidelines
1. **Clear Names** - Test names should describe what they test
2. **Single Responsibility** - One test per behavior
3. **Independent Tests** - Tests shouldn't depend on each other
4. **Proper Setup/Teardown** - Use fixtures for test data
5. **Meaningful Assertions** - Assert on specific expected behavior

### Test Organization
1. **Group Related Tests** - Use classes to group related functionality
2. **Use Descriptive Comments** - Explain complex test logic
3. **Test Edge Cases** - Include boundary condition testing
4. **Mock External Dependencies** - Don't rely on external services

### Performance Considerations
1. **Fast Tests** - Keep unit tests under 100ms
2. **Parallel Execution** - Use pytest-xdist for faster runs
3. **Selective Testing** - Use markers for slow tests
4. **Efficient Fixtures** - Reuse expensive setup operations

---

**Happy Testing!** 🧪✨

For more information, see the [Architecture Documentation](architecture.md) and [Contributing Guidelines](contributing.md).
