# MAM (MyAnonamouse) API Migration

**Status**: 🚧 In Progress  
**Branch**: `mam-api-migration`  
**Created**: December 23, 2025  
**Last Updated**: December 23, 2025

## Overview

This document tracks the migration from HTML scraping to MAM's JSON API for torrent metadata retrieval.

### Why This Change?

1. **Stability**: JSON API is more stable than HTML scraping (less brittle to UI changes)
2. **Efficiency**: Direct API calls are faster than rendering/parsing HTML
3. **Simplicity**: No more Playwright/browser automation needed for basic queries
4. **Maintainability**: Structured JSON responses with Pydantic models

### What's Changing

| Before | After |
|--------|-------|
| HTML scraping via Playwright | JSON API via httpx (HTTP/2) |
| `mam_config.json` with credentials | `MAM_ID` cookie from `.env` |
| Complex browser session management | Simple cookie-based auth |
| Fragile DOM parsing | Structured Pydantic models |

---

## Technical Details

### API Endpoint

- **URL**: `https://www.myanonamouse.net/tor/js/loadSearchJSONbasic.php`
- **Auth**: Session cookie `mam_id=<value>`
- **Transport**: httpx with HTTP/2 enabled

### IRC → Torrent ID Mapping

IRC announces include links like:

```text
https://www.myanonamouse.net/t/1207719
```

The number in `/t/<number>` is the torrent ID (`tid`), which is the key for:

- Single-torrent lookup via JSON endpoint (`tor[id]=<tid>`)
- Torrent download via `download.php?tid=<tid>`

### Critical Discovery: `id` Must Be Inside `tor[...]`

Using `?id=1207719` alone can be ignored. The correct form is:

**GET (query params)**:

```text
?tor[id]=1207719
```

**POST JSON**:

```json
{
  "tor": { "id": 1207719, ... },
  "mediaInfo": "",
  "isbn": ""
}
```

### Response Structure

```json
{
  "perpage": 5,
  "start": 0,
  "data": [ { ...torrent object... } ],
  "total": 1,
  "found": 1
}
```

### JSON-Inside-Strings (Important!)

Several fields are JSON-encoded strings that must be parsed:

- `author_info` → JSON string mapping id→name
- `narrator_info` → JSON string mapping id→name  
- `series_info` → JSON string mapping id→[name, numStr, numFloat]
- `mediainfo` → JSON string with General, Audio1, menu
- `ownership` → JSON string list [user_id, "username"]

---

## Implementation Plan

### Phase 1: Core API Client ✅

- [x] Create `src/mam_api/` directory structure
- [x] Implement Pydantic models (`models.py`)
- [x] Implement httpx client (`client.py`)

### Phase 2: Configuration Updates

- [ ] Add `MAM_ID` to `.env.example`
- [ ] Update `src/config.py` to read `MAM_ID` from environment
- [ ] Remove dependency on `config/mam_config.json`

### Phase 3: Integration

- [ ] Update `src/mam_scraper.py` to use new API client
- [ ] Update metadata coordinator to use normalized responses
- [ ] Remove Playwright-based MAM scraping code

### Phase 4: Cleanup

- [ ] Remove `config/mam_config.json` (contains sensitive data!)
- [ ] Remove `mam_login_only.py` (no longer needed)
- [ ] Update documentation

### Phase 5: Testing

- [ ] Add unit tests for Pydantic models
- [ ] Add integration tests for API client
- [ ] Verify torrent download functionality

---

## File Changes

### New Files

- `src/mam_api/__init__.py`
- `src/mam_api/models.py` - Pydantic models for API responses
- `src/mam_api/client.py` - httpx HTTP/2 client

### Modified Files

- `.env.example` - Add `MAM_ID`
- `src/config.py` - Read MAM_ID from env
- `src/mam_scraper.py` - Use new API client

### Removed Files

- `config/mam_config.json` - Sensitive! Contains credentials
- `src/mam_login_only.py` - No longer needed

---

## Security Notes

⚠️ **CRITICAL**: The `mam_id` cookie value should **NEVER** be logged.

The `mam_id` cookie is a session token that grants full access to the MAM account. It should be:

- Stored only in `.env` (which is gitignored)
- Never printed in logs or error messages
- Treated with the same security as a password

---

## Usage Example

```python
from src.mam_api.client import MamClient, extract_tid_from_irc

# Extract tid from IRC announcement
irc_line = "[2025-12-22 21:28:06] MouseBot: New Torrent: ... Link: ( https://www.myanonamouse.net/t/1207719 ) VIP"
tid = extract_tid_from_irc(irc_line)

# Fetch torrent metadata
with MamClient(mam_id=os.getenv("MAM_ID")) as mam:
    raw = mam.get_torrent(tid, media_info=True, isbn=True)
    normalized = raw.to_normalized()
    
    print(normalized.title)
    print(normalized.author)
    print(normalized.asin)
    
    # Download .torrent file
    torrent_bytes = mam.download_torrent_by_tid(tid)
```

---

## Progress Log

### December 23, 2025

- Created `mam-api-migration` branch
- Created migration documentation
- Implemented core Pydantic models
- Implemented httpx client (sync + async)
