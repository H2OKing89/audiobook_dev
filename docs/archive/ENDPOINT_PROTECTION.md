# Endpoint Security Configuration

This document explains the new endpoint security features that prevent unauthorized access to sensitive endpoints and properly serve the 401 Unauthorized page.

## Overview

The security system now includes comprehensive endpoint protection that:

1. **Protects sensitive endpoints** from unauthorized access
2. **Serves proper 401 pages** instead of allowing access to all endpoints
3. **Maintains token-based authentication** for approve/reject workflows
4. **Provides configurable security settings** via `config.yaml`

## How It Works

### Protected Endpoints

By default, these endpoints require authentication:

- `/admin` - Admin dashboard and controls
- `/api/admin` - Admin API endpoints
- `/config` - Configuration management
- `/logs` - Log file access
- `/stats` - System statistics
- `/health/detailed` - Detailed health information
- `/debug` - Debug information

### Public Endpoints

These endpoints remain publicly accessible:

- `/` - Home page
- `/static/*` - Static assets (CSS, JS, images)
- `/approve/*` - Approval workflows (token-based auth)
- `/reject/*` - Rejection workflows (token-based auth)
- `/health` - Basic health check
- `/favicon.ico` - Browser favicon

### Webhook Endpoints

Webhook endpoints (like `/webhook/audiobook-requests`) use their own authentication via tokens and are not affected by this system.

## Configuration

### Enable/Disable Protection

```yaml
security:
  endpoint_protection_enabled: true  # Enable endpoint authorization checks
```

### Configure Protected Endpoints

Add additional endpoints that require authentication:

```yaml
security:
  protected_endpoints:
    - "/admin"
    - "/api/admin"
    - "/my-custom-admin-endpoint"
```

### Configure Public Endpoints

Add additional endpoints that should be publicly accessible:

```yaml
security:
  public_endpoints:
    - "/"
    - "/static"
    - "/my-public-endpoint"
```

### Authentication Method

Enable API key authentication for protected endpoints:

```yaml
security:
  api_key_enabled: true
  api_key: "your-secure-api-key-here"
```

## Usage Examples

### Accessing Protected Endpoints

Without authentication:

```bash
curl https://your-domain.com/admin
# Returns: 401 Unauthorized page
```

With API key in header:

```bash
curl -H "X-API-Key: your-secure-api-key" https://your-domain.com/admin
# Returns: Admin dashboard
```

With API key in query parameter:

```bash
curl https://your-domain.com/admin?api_key=your-secure-api-key
# Returns: Admin dashboard
```

### Public Endpoints

These work without authentication:

```bash
curl https://your-domain.com/
curl https://your-domain.com/health
curl https://your-domain.com/static/css/style.css
```

### Token-Based Endpoints

Approve/reject endpoints continue to use token-based authentication:

```bash
curl https://your-domain.com/approve/abc123token
# Returns: Approval page if token is valid, 410 if expired
```

## Security Features

### Rate Limiting

Token generation continues to use rate limiting to prevent abuse:

- Configurable time windows and limits
- Per-IP address tracking
- Automatic cleanup of old entries

### CSRF Protection

Forms include CSRF token validation when enabled:

```yaml
security:
  csrf_protection: true
```

### Content Security Policy

Strict CSP headers are applied automatically:

- Prevents inline script execution
- Controls resource loading sources
- Mitigates XSS attacks

## Testing the Setup

1. **Test public access:**

   ```bash
   curl -I https://your-domain.com/
   # Should return 200 OK
   ```

2. **Test protected endpoint without auth:**

   ```bash
   curl -I https://your-domain.com/admin
   # Should return 401 Unauthorized
   ```

3. **Test protected endpoint with auth:**

   ```bash
   curl -H "X-API-Key: your-key" -I https://your-domain.com/admin
   # Should return 200 OK (if API key is enabled and correct)
   ```

4. **Test token-based endpoints:**

   ```bash
   curl -I https://your-domain.com/approve/invalid-token
   # Should return 410 Gone (token expired page)
   ```

## Troubleshooting

### Common Issues

1. **All endpoints return 401:**
   - Check `endpoint_protection_enabled` setting
   - Verify `public_endpoints` configuration
   - Ensure static files are in public endpoints list

2. **Can't access admin with API key:**
   - Verify `api_key_enabled: true` in config
   - Check API key value matches configuration
   - Ensure header name is exactly `X-API-Key`

3. **Approve/reject workflows broken:**
   - These should work without API keys (token-based)
   - Check that `/approve` and `/reject` are in public endpoints
   - Verify token validation logic is working

### Logging

Security events are logged with appropriate levels:

- INFO: Successful authentications
- WARNING: Unauthorized access attempts
- ERROR: Configuration or system errors

Check logs at: `logs/audiobook_requests.log`

## Migration Notes

If upgrading from a previous version:

1. The new system is **enabled by default**
2. Existing approve/reject workflows continue to work
3. Add API key configuration if you need admin access
4. Review and customize endpoint lists as needed

## Best Practices

1. **Use strong API keys:** Generate random, long keys
2. **Limit protected endpoints:** Only protect what needs protection
3. **Monitor logs:** Watch for unauthorized access attempts
4. **Regular key rotation:** Change API keys periodically
5. **Test configurations:** Verify settings work as expected
