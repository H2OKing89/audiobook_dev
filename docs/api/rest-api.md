# 🔌 REST API Reference

This document provides comprehensive documentation for the Audiobook Automation System REST API.

## 🌐 Base URL

```
http://localhost:8000
```

*Replace with your actual server URL and port*

## 📋 API Overview

The API provides endpoints for:
- **Request Management** - Creating and managing audiobook requests
- **Status Checking** - Monitoring request status
- **Approval/Rejection** - Token-based approval workflow
- **System Information** - Health checks and system status

## 🔐 Authentication

The API uses **token-based authentication** for approval/rejection actions. Most read operations are public, while write operations require valid tokens.

### Token Format
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Tokens are:
- **URL-safe** - Can be included in URLs
- **Time-limited** - Expire after configured duration
- **Single-use** - Become invalid after use

## 📖 Endpoints

### 🏠 Home & Static Pages

#### `GET /`
Returns the main homepage.

**Response:**
- **Content-Type:** `text/html`
- **Status:** `200 OK`

---

### 📚 Request Management

#### `POST /audiobook-requests`
Submit a new audiobook request.

**Request Body:**
```json
{
    "title": "The Hitchhiker's Guide to the Galaxy",
    "author": "Douglas Adams",
    "isbn": "9780345391803",
    "description": "A science fiction comedy series",
    "priority": "normal",
    "format": "mp3",
    "narrator": "Stephen Fry"
}
```

**Required Fields:**
- `title` (string) - Book title
- `author` (string) - Author name

**Optional Fields:**
- `isbn` (string) - ISBN number
- `description` (string) - Book description
- `priority` (enum) - `low`, `normal`, `high`
- `format` (enum) - `mp3`, `m4a`, `flac`
- `narrator` (string) - Preferred narrator

**Response:**
```json
{
    "status": "success",
    "message": "Request submitted successfully",
    "request_id": 123,
    "approval_token": "abc123...",
    "rejection_token": "def456..."
}
```

**Status Codes:**
- `200 OK` - Request submitted successfully
- `400 Bad Request` - Invalid request data
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

---

#### `GET /requests`
List all audiobook requests (paginated).

**Query Parameters:**
- `page` (integer, default: 1) - Page number
- `limit` (integer, default: 20, max: 100) - Items per page
- `status` (enum) - Filter by status: `pending`, `approved`, `rejected`
- `sort` (enum) - Sort order: `newest`, `oldest`, `title`, `author`

**Response:**
```json
{
    "requests": [
        {
            "id": 123,
            "title": "The Hitchhiker's Guide to the Galaxy",
            "author": "Douglas Adams",
            "status": "pending",
            "created_at": "2025-06-16T10:30:00Z",
            "updated_at": "2025-06-16T10:30:00Z"
        }
    ],
    "pagination": {
        "page": 1,
        "limit": 20,
        "total": 45,
        "total_pages": 3
    }
}
```

---

#### `GET /requests/{request_id}`
Get details for a specific request.

**Path Parameters:**
- `request_id` (integer) - Request ID

**Response:**
```json
{
    "id": 123,
    "title": "The Hitchhiker's Guide to the Galaxy",
    "author": "Douglas Adams",
    "isbn": "9780345391803",
    "description": "A science fiction comedy series",
    "status": "pending",
    "priority": "normal",
    "format": "mp3",
    "narrator": "Stephen Fry",
    "created_at": "2025-06-16T10:30:00Z",
    "updated_at": "2025-06-16T10:30:00Z",
    "approved_at": null,
    "rejected_at": null
}
```

**Status Codes:**
- `200 OK` - Request found
- `404 Not Found` - Request doesn't exist

---

### ✅ Approval/Rejection

#### `GET /approve/{token}`
Approve a request using a valid approval token.

**Path Parameters:**
- `token` (string) - Approval token

**Response:**
- **Content-Type:** `text/html`
- **Status:** `200 OK` - Success page
- **Status:** `400 Bad Request` - Invalid/expired token
- **Status:** `404 Not Found` - Token not found

---

#### `GET /reject/{token}`
Reject a request using a valid rejection token.

**Path Parameters:**
- `token` (string) - Rejection token

**Response:**
- **Content-Type:** `text/html`
- **Status:** `200 OK` - Rejection page
- **Status:** `400 Bad Request` - Invalid/expired token
- **Status:** `404 Not Found` - Token not found

---

### 📊 System Information

#### `GET /health`
Health check endpoint for monitoring.

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2025-06-16T10:30:00Z",
    "version": "1.0.0",
    "database": "connected",
    "notifications": "enabled"
}
```

**Status Codes:**
- `200 OK` - System healthy
- `503 Service Unavailable` - System issues

---

#### `GET /stats`
System statistics and metrics.

**Response:**
```json
{
    "requests": {
        "total": 1247,
        "pending": 23,
        "approved": 1089,
        "rejected": 135
    },
    "activity": {
        "requests_today": 15,
        "requests_this_week": 89,
        "requests_this_month": 312
    },
    "system": {
        "uptime_seconds": 3600,
        "database_size_mb": 12.4,
        "log_size_mb": 2.1
    }
}
```

---

## 🚨 Error Responses

All error responses follow a consistent format:

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "The title field is required",
        "details": {
            "field": "title",
            "constraint": "required"
        }
    },
    "timestamp": "2025-06-16T10:30:00Z",
    "request_id": "req_abc123"
}
```

### Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Invalid request data |
| `TOKEN_EXPIRED` | Approval/rejection token expired |
| `TOKEN_USED` | Token already used |
| `TOKEN_INVALID` | Token format invalid |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `DATABASE_ERROR` | Database operation failed |
| `NOTIFICATION_ERROR` | Notification delivery failed |
| `INTERNAL_ERROR` | Unexpected server error |

---

## 📝 Request Examples

### Submit New Request (cURL)

```bash
curl -X POST http://localhost:8000/audiobook-requests \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Dune",
    "author": "Frank Herbert",
    "description": "Epic science fiction novel",
    "priority": "high",
    "format": "mp3"
  }'
```

### List Requests (cURL)

```bash
curl "http://localhost:8000/requests?status=pending&limit=10"
```

### Python Example

```python
import httpx

# Submit a new request
response = httpx.post('http://localhost:8000/audiobook-requests', json={
    'title': 'The Martian',
    'author': 'Andy Weir',
    'description': 'Survival story on Mars',
    'priority': 'normal'
})

if response.status_code == 200:
    data = response.json()
    print(f"Request submitted with ID: {data['request_id']}")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

### JavaScript Example

```javascript
// Submit a new request
fetch('/audiobook-requests', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        title: 'Ready Player One',
        author: 'Ernest Cline',
        description: 'Virtual reality adventure',
        priority: 'normal'
    })
})
.then(response => response.json())
.then(data => {
    console.log('Request submitted:', data.request_id);
})
.catch(error => {
    console.error('Error:', error);
});
```

---

## 🔄 Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Request submission:** 10 requests per hour per IP
- **Status queries:** 100 requests per hour per IP
- **General endpoints:** 1000 requests per hour per IP

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1640995200
```

---

## 📡 Webhooks

The system can send webhooks for various events. See [Webhooks Documentation](webhooks.md) for details.

---

## 🧪 Testing the API

### Using the Test Suite

```bash
# Run API tests
python -m pytest tests/test_webui.py -v

# Run specific endpoint tests
python -m pytest tests/test_webui.py::test_submit_request -v
```

### Manual Testing

The system includes a built-in API test page at `/api-test` (when `debug` mode is enabled) for manual testing of endpoints.

---

## 📚 Related Documentation

- [Configuration Reference](config-reference.md) - Complete configuration options
- [Webhooks](webhooks.md) - Webhook configuration and payloads
- [Database Schema](database.md) - Database structure and queries
- [Security](../development/SECURITY.md) - Security considerations

---

**Need help?** Check the [troubleshooting guide](../user-guide/troubleshooting.md) or open an issue on GitHub!
