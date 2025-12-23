# IP Extraction Fix Documentation

## Issue Identified

The application was inconsistently extracting client IP addresses, leading to different IPs being logged for the same request:

```
2025-06-16 06:17:26,929 - root - INFO - Incoming request: path=/reject/8ypiAG1QX-H2od3gGOoJiA ip=10.1.60.20 token=8a714efb402c40b6b2c457b50d72015c
2025-06-16 06:17:26,930 - root - DEBUG - Reject page accessed from IP: 10.1.60.2 for token: 8ypiAG1QX-H2od3gGOoJiA
```

## Root Cause

The application had **two different IP extraction methods**:

1. **Main application middleware** (`src/main.py`): Used `X-Forwarded-For` header correctly
2. **Individual route handlers** (`src/webui.py`): Used `request.client.host` directly (ignored reverse proxy headers)

This inconsistency caused different IPs to be logged for the same request when behind a reverse proxy.

## Solution Implemented

### 1. Centralized IP Extraction Function

Created a single `get_client_ip()` function in `src/security.py` that:

- **Checks reverse proxy headers in priority order**:
  1. `X-Forwarded-For` (most common, handles comma-separated IPs)
  2. `X-Real-IP` (Nginx specific)
  3. `X-Forwarded-Host` (some configurations)
  4. `CF-Connecting-IP` (Cloudflare)
  5. `X-Client-IP` (custom headers)
  6. Falls back to direct connection IP

- **Handles multiple IPs correctly**: For `X-Forwarded-For`, extracts the first IP (original client)
- **Provides debug logging**: Shows which header was used for IP determination
- **Graceful fallback**: Returns "unknown" if no IP can be determined

### 2. Updated All IP Extraction Points

Replaced all instances of direct `request.client.host` usage with `get_client_ip(request)`:

- ✅ `src/main.py` - Application middleware
- ✅ `src/webui.py` - All route handlers (7 locations)
- ✅ `src/security.py` - API key validation and endpoint protection

### 3. Function Implementation

```python
def get_client_ip(request: Request) -> str:
    """
    Get the real client IP address, respecting reverse proxy headers.

    Priority order:
    1. X-Forwarded-For (first IP if comma-separated)
    2. X-Real-IP (Nginx)
    3. X-Forwarded-Host
    4. CF-Connecting-IP (Cloudflare)
    5. X-Client-IP
    6. Direct connection IP
    """
    proxy_headers = [
        'x-forwarded-for', 'x-real-ip', 'x-forwarded-host',
        'cf-connecting-ip', 'x-client-ip'
    ]

    for header in proxy_headers:
        header_value = request.headers.get(header)
        if header_value:
            if header == 'x-forwarded-for':
                client_ip = header_value.split(',')[0].strip()
            else:
                client_ip = header_value.strip()

            if client_ip and client_ip != 'unknown':
                logging.debug(f"Client IP determined from {header}: {client_ip}")
                return client_ip

    # Fallback to direct connection
    direct_ip = request.client.host if request.client else 'unknown'
    logging.debug(f"Client IP determined from direct connection: {direct_ip}")
    return direct_ip
```

## Testing

Created comprehensive test suite (`test_ip_extraction.py`) that verifies:

- ✅ Single IP in X-Forwarded-For
- ✅ Multiple IPs in X-Forwarded-For (comma-separated)
- ✅ X-Real-IP header (Nginx)
- ✅ CF-Connecting-IP (Cloudflare)
- ✅ Direct connection fallback
- ✅ Header priority order
- ✅ Edge cases (no client object)

All tests pass, confirming the fix works correctly.

## Expected Result

After this fix, all log entries for the same request should show the **same consistent IP address**:

```
2025-06-16 06:17:26,929 - root - INFO - Incoming request: path=/reject/8ypiAG1QX-H2od3gGOoJiA ip=203.0.113.195 token=8a714efb402c40b6b2c457b50d72015c
2025-06-16 06:17:26,930 - root - DEBUG - Reject page accessed from IP: 203.0.113.195 for token: 8ypiAG1QX-H2od3gGOoJiA
```

## Reverse Proxy Configuration

For optimal results, ensure your reverse proxy sets the appropriate headers:

### Nginx

```nginx
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Real-IP $remote_addr;
```

### Apache

```apache
ProxyPreserveHost On
ProxyAddHeaders On
```

### Cloudflare

Automatically sets `CF-Connecting-IP` header.

## Security Benefits

This fix improves security by:

1. **Consistent audit logging**: All security events show the correct client IP
2. **Accurate rate limiting**: Rate limits apply to real client IPs, not proxy IPs
3. **Better incident response**: Security teams can correctly trace requests
4. **Improved monitoring**: Security alerts reference the actual client IPs

## Files Modified

- `src/security.py` - Added `get_client_ip()` function
- `src/webui.py` - Updated all route handlers (7 locations)
- `src/main.py` - Updated middleware
- `test_ip_extraction.py` - Added comprehensive test suite

## Migration Notes

- This is a **backwards-compatible** change
- No configuration changes required
- Works with and without reverse proxies
- Debug logging shows which method was used for IP determination

---

**Status**: ✅ **RESOLVED** - All IP extraction now uses consistent method with proper reverse proxy support.
