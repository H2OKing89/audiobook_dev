# Metadata Workflow Rate Limiting Implementation

## Summary

The audiobook metadata workflow has been updated to respect API rate limits to avoid hammering external websites and APIs. This was implemented across all metadata sources as requested.

## Configuration

**File**: `config/config.yaml`

```yaml
metadata:
  rate_limit_seconds: 120  # 2 minutes between API calls
```

## Implementation Details

### 1. **Global Rate Limiting (120 seconds)**

- Applied across **all** metadata sources
- Enforced by the metadata coordinator
- Prevents overwhelming external APIs

### 2. **Source-Specific Rate Limiting**

#### **MAM Scraper** (`src/mam_scraper.py`)

- ✅ Global rate limiting: 120 seconds between requests
- Applied before navigating to MAM pages
- Prevents hammering myanonamouse.net

#### **Audnex API** (`src/audnex_metadata.py`)

- ✅ Local rate limiting: 150ms between requests
- ✅ Global rate limiting: 120 seconds between API calls
- Double protection for api.audnex.us

#### **Audible Scraper** (`src/audible_scraper.py`)

- ✅ Global rate limiting: 120 seconds between requests
- Applied before searching Audible
- Protects both Audible API and fallback to Audnex

#### **Metadata Coordinator** (`src/metadata_coordinator.py`)

- ✅ Orchestrates global rate limiting across all sources
- Ensures 2-minute gaps between any API calls
- Logs rate limiting actions for transparency

## Key Features

### 1. **Configurable Rate Limits**

- Rate limits read from `config.yaml`
- Easy to adjust without code changes
- Default: 2 minutes (120 seconds)

### 2. **Comprehensive Logging**

- All rate limiting actions are logged
- Shows wait times and enforcement
- Helps with debugging and monitoring

### 3. **Respectful API Usage**

- Prevents overwhelming external services
- Follows best practices for web scraping
- Reduces risk of IP bans or rate limiting

## Workflow Protection

The complete metadata workflow now enforces rate limiting at each step:

1. **MAM ASIN Extraction** → 2-minute wait before scraping
2. **Audnex Metadata Fetch** → 2-minute wait + 150ms local limit
3. **Audible Fallback Search** → 2-minute wait before searching

## Testing

A test script (`simple_rate_test.py`) verifies:

- ✅ Configuration is loaded correctly
- ✅ Rate limit is set to 120 seconds
- ✅ All components read the configuration

## Usage Notes

- **Testing**: Use extreme caution when testing to avoid hitting rate limits
- **Production**: The 2-minute delay ensures respectful API usage
- **Monitoring**: Check logs for rate limiting enforcement messages
- **Adjustment**: Modify `config.yaml` to change rate limits if needed

## Error Prevention

This implementation prevents:

- ❌ Hammering external APIs
- ❌ IP bans from excessive requests
- ❌ Service degradation for other users
- ❌ Potential legal issues from aggressive scraping

The metadata workflow now operates as a "good citizen" of the web, respecting external services while still providing the needed functionality.
