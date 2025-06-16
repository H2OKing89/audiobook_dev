# Security Implementation Guide

## Overview

This document outlines the security measures implemented in the Audiobook Approval System.

## Content Security Policy (CSP)

### Current Implementation
- **Stricter CSP**: `default-src 'self'; img-src 'self' https:; style-src 'self' 'unsafe-inline'; script-src 'self';`
- External JavaScript files are served from `/static/js/`
- External CSS files are served from `/static/css/`
- No inline scripts allowed (except when `use_external_js: false`)

### Configuration Options
In `config/config.yaml`:
```yaml
security:
  use_external_js: true  # Use external JS files for stricter CSP (recommended)
```

### Benefits
- Prevents XSS attacks from inline scripts
- Reduces attack surface
- Better code organization
- Cached static assets improve performance

## Rate Limiting

### Implementation
- Token bucket algorithm for API rate limiting
- Configurable limits per IP address
- Separate limits for different endpoints

### Configuration
```yaml
security:
  rate_limit_window: 3600  # Time window in seconds (1 hour)
  max_tokens_per_window: 10  # Maximum tokens per IP per window
```

## CSRF Protection

### Implementation
- CSRF tokens generated for all forms
- Token validation on POST requests
- Configurable protection level

### Configuration
```yaml
security:
  csrf_protection: true  # Enable CSRF protection for forms
```

## Security Headers

The following security headers are automatically added:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: <dynamic>`
- `Referrer-Policy: strict-origin-when-cross-origin`

## Input Validation

### Features
- HTML sanitization to prevent XSS
- Payload size limits
- Required field validation
- Type checking for security-critical inputs

### Configuration
```yaml
security:
  max_payload_size: 1048576  # 1MB max payload size
  sanitize_inputs: true  # Sanitize inputs to prevent XSS
```

## API Security

### Features
- Optional API key authentication for admin endpoints
- Token-based authentication for webhook endpoints
- IP address logging for security monitoring

### Configuration
```yaml
security:
  api_key_enabled: false  # Enable API key requirement for admin endpoints
  # api_key: "your-secure-api-key"  # Uncomment and set a strong API key
```

## Allowed Domains

### Image Sources
Images are allowed from specific trusted domains:
```yaml
security:
  allowed_image_domains:
    - "picsur.kingpaging.com"
    - "ptpimg.me"
    - "i.imgur.com"
    - "audnex.us"
    - "m.media-amazon.com"
```

## Best Practices

1. **Keep CSP Strict**: Use external files instead of inline scripts/styles
2. **Regular Updates**: Keep dependencies updated
3. **Monitor Logs**: Watch for security events in logs
4. **Rate Limiting**: Adjust limits based on legitimate usage patterns
5. **API Keys**: Use strong, randomly generated API keys
6. **HTTPS Only**: Always use HTTPS in production

## Development vs Production

### Development
- More permissive CSP for debugging
- Detailed error messages
- Debug logging enabled

### Production
- Strict CSP enforcement
- Generic error messages
- Security event logging
- Rate limiting active

## Security Checklist

- [ ] HTTPS enabled in production
- [ ] Strong API keys configured
- [ ] Rate limits configured appropriately
- [ ] CSRF protection enabled
- [ ] External JS/CSS files used (stricter CSP)
- [ ] Security headers verified
- [ ] Input validation tested
- [ ] Error handling doesn't leak information
- [ ] Logs monitored for security events

## Reporting Security Issues

Security issues should be reported privately to the system administrator.
