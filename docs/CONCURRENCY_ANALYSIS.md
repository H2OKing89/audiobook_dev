# Webhook Concurrency Analysis & Recommendations

## Current Behavior: **Concurrent Processing** ⚠️

When two webhooks arrive simultaneously, here's what happens:

### 1. **FastAPI Async Handling**

```python
@app.post("/webhook")
async def webhook(request: Request):
    # Each webhook creates a NEW async task
    # They run CONCURRENTLY, not in a queue
```

### 2. **Multiple Coordinator Instances**

```python
coordinator = MetadataCoordinator()  # NEW instance per request
await coordinator.get_metadata_from_webhook(payload)
```

### 3. **Race Conditions in Rate Limiting**

```python
class MetadataCoordinator:
    def __init__(self):
        self.last_api_call = 0  # Each instance has its own timestamp!
```

## Problems This Causes

### ⚠️ **Rate Limiting Failures**

- Multiple coordinators have separate `last_api_call` timestamps
- Rate limits become ineffective with concurrent requests
- Could exceed API rate limits (Audnex, MAM)

### ⚠️ **Resource Contention**

- Multiple Playwright browser instances
- Concurrent MAM logins/cookie sharing conflicts
- Browser memory usage spikes

### ⚠️ **API Overload**

- Multiple simultaneous Audnex API calls
- Could trigger API rate limiting responses (429 errors)
- Unreliable metadata fetching

## Solutions

### Option 1: **Shared Rate Limiting (Quick Fix)**

```python
# Global singleton for rate limiting
class GlobalRateLimit:
    _instance = None
    _last_api_call = 0
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

### Option 2: **Request Queue (Recommended)**

```python
import asyncio

# Global queue for metadata requests
metadata_queue = asyncio.Queue(maxsize=10)
metadata_worker_running = False

async def metadata_worker():
    """Process metadata requests one at a time"""
    while True:
        request_data = await metadata_queue.get()
        # Process one request at a time
        await process_metadata_request(request_data)
        metadata_queue.task_done()

@app.post("/webhook")
async def webhook(request: Request):
    # Add to queue instead of processing immediately
    await metadata_queue.put({
        'payload': payload,
        'token': token,
        'timestamp': time.time()
    })
    # Return immediately - processing happens in background
```

### Option 3: **Database Queue (Production)**

```python
# Store requests in database with status
# Background worker processes them sequentially
# Web UI shows processing status
```

## Current Risk Level: **Medium** ⚠️

- **Low traffic**: Works fine (one request at a time)
- **High traffic**: Race conditions, rate limit failures
- **Burst traffic**: Potential system overload

## Recommended Action

**Implement Option 2 (Request Queue)** for proper sequential processing while maintaining fast webhook response times.
