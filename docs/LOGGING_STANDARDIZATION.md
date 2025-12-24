# Logging Standardization Summary

## Overview

The codebase has been migrated from inconsistent Python `logging` module usage to **structlog** with **orjson** for structured, JSON-formatted logging in production.

## Key Changes

### Dependencies Added

- `structlog>=24.4.0` - Structured logging library
- `orjson>=3.10.0` - Fast JSON serialization
- `rich` (dev dependency) - Pretty console output during development

### New Files Created

- `src/logging_setup.py` - Centralized logging configuration
- `src/request_id_middleware.py` - FastAPI middleware for request correlation

### Migration Pattern

**Before:**

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Processing request for user=%s with status=%s", user, status)
logger.exception("Failed to process request")
```

**After:**

```python
from src.logging_setup import get_logger

log = get_logger(__name__)

log.info("request.processing", user=user, status=status)
log.exception("request.failed")
```

## Event Naming Convention

Events follow the `module.action.status` pattern:

- `http.request.complete`
- `notify.discord.success`
- `coordinator.step1.asin_found`
- `qbittorrent.torrent.uploaded`
- `mam.api.rate_limited`

## Features

### 1. Automatic Redaction

Sensitive fields are automatically redacted in logs:

- `password`, `token`, `api_key`, `secret`
- `cookie`, `mam_id`, `session`, `auth`
- `authorization`, `x-api-key`, `bearer`
- `credit_card`, `ssn`

### 2. Request Correlation

The `RequestIdMiddleware` adds `X-Request-ID` headers and binds request IDs to log context for tracing requests across services.

### 3. Dual Output Modes

- **JSON mode** (production): Machine-readable JSON output for Loki/ELK
- **Console mode** (development): Human-readable colored output with Rich

Set via `LOG_FORMAT=console` environment variable (defaults to JSON).

### 4. Third-Party Log Quieting

Noisy loggers (httpx, httpcore, uvicorn.access, hpack, etc.) are automatically set to WARNING level.

## Files Converted

### Core Infrastructure

- ✅ `src/main.py`
- ✅ `src/db.py`
- ✅ `src/utils.py`
- ✅ `src/security.py`
- ✅ `src/token_gen.py`
- ✅ `src/template_helpers.py`

### Web UI

- ✅ `src/webui.py`

### Metadata Fetching

- ✅ `src/metadata.py`
- ✅ `src/metadata_coordinator.py`
- ✅ `src/audible_scraper.py`
- ✅ `src/audnex_metadata.py`

### HTTP & qBittorrent

- ✅ `src/http_client.py`
- ✅ `src/qbittorrent.py`

### Notifiers

- ✅ `src/notify/discord.py`
- ✅ `src/notify/ntfy.py`
- ✅ `src/notify/gotify.py`
- ✅ `src/notify/pushover.py`

### MAM API

- ✅ `src/mam_api/client.py`
- ✅ `src/mam_api/adapter.py`
- ✅ `src/mam_api/models.py` (unused logger removed)

### Intentionally Using stdlib logging

- `src/config.py` - Loads before structlog is configured (bootstrap)

## Configuration

Logging is configured via environment variables:

- `LOG_LEVEL` - Set log level (DEBUG, INFO, WARNING, ERROR) - default: INFO
- `LOG_FORMAT` - Output format (json, console) - default: json
- `LOG_FILE` - Log file path - default: logs/audiobook.log
- `SERVICE_NAME` - Service name in logs - default: audiobook_dev

## Usage

### Basic Usage

```python
from src.logging_setup import get_logger

log = get_logger(__name__)

log.info("operation.started", item_id=123)
log.debug("operation.detail", data={"key": "value"})
log.warning("operation.slow", duration_ms=5000)
log.error("operation.failed", error="timeout")
log.exception("operation.crashed")  # includes stack trace
```

### With Context Binding

```python
log = log.bind(user_id=user.id, session_id=session.id)
log.info("user.action")  # automatically includes user_id and session_id
```

### Application Startup

```python
from src.logging_setup import configure_logging

configure_logging()  # Call once at application startup
```

## Output Examples

### JSON Mode (Production)

```json
{"event":"http.request.complete","method":"POST","path":"/webhook","status":200,"duration_ms":142,"logger":"main","level":"info","service":"audiobook_dev","timestamp":"2024-12-24T00:30:00.000Z","request_id":"abc123"}
```

### Console Mode (Development)

```text
2024-12-24 00:30:00 [info     ] http.request.complete          method=POST path=/webhook status=200 duration_ms=142
```
