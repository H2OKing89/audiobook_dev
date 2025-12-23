# ⚙️ Configuration Guide

This guide covers all configuration options for the Audiobook Automation System.

## 📁 Configuration Files

All configuration files are located in the `config/` directory:

```
config/
├── config.yaml                    # Main application configuration
├── config.yaml.example           # Template for main config
├── mam_config.json               # MAM credentials (optional)
└── mam_config.json.example       # Template for MAM config
```

## 🔧 Main Configuration (`config.yaml`)

### Server Settings

```yaml
server:
  host: "127.0.0.1"
  port: 8080
  debug: false
```

### Database

```yaml
database:
  path: "db.sqlite"
  backup_enabled: true
  backup_interval_hours: 24
```

### Security

```yaml
security:
  csrf_enabled: true
  token_length: 32
  rate_limit:
    enabled: true
    max_requests: 10
    window_hours: 1
```

### Metadata Workflow

```yaml
metadata:
  rate_limit_seconds: 120          # Production: 120s, Testing: 30s
  sources:
    mam:
      enabled: true
      timeout_seconds: 30
    audnex:
      enabled: true
      base_url: "https://api.audnex.us"
      timeout_seconds: 10
    audible:
      enabled: true
      timeout_seconds: 15
```

### Notifications

```yaml
notifications:
  discord:
    enabled: false
    webhook_url: ""                # Set in .env as DISCORD_WEBHOOK_URL

  pushover:
    enabled: false
    user_key: ""                   # Set in .env as PUSHOVER_USER_KEY
    api_token: ""                  # Set in .env as PUSHOVER_API_TOKEN
```

## 🔐 Environment Variables (`.env`)

Create a `.env` file for sensitive configuration:

```bash
# Required for webhook authentication
AUTOBRR_TOKEN=your-autobrr-webhook-token

# Notification services (optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your/webhook/url
PUSHOVER_USER_KEY=your-pushover-user-key
PUSHOVER_API_TOKEN=your-pushover-api-token
GOTIFY_URL=https://gotify.example.com
GOTIFY_TOKEN=your-gotify-token
NTFY_URL=https://ntfy.sh/your-topic
```

## 🔍 MAM Configuration (Optional)

For full MAM integration with ASIN extraction:

### 1. Setup MAM Config

```bash
# Copy the example
cp config/mam_config.json.example config/mam_config.json

# Or use the setup helper
python setup_mam_config.py
```

### 2. Configure MAM Credentials

Edit `config/mam_config.json`:

```json
{
  "email": "your-mam-email@example.com",
  "password": "your-mam-password",
  "base_url": "https://www.myanonamouse.net",
  "timeout_seconds": 30,
  "browser_settings": {
    "headless": true,
    "user_agent": "Mozilla/5.0 (compatible; AudiobookBot/1.0)"
  }
}
```

⚠️ **Security Note**: `mam_config.json` is excluded from git for security.

## 🎯 Configuration Examples

### Development/Testing

```yaml
metadata:
  rate_limit_seconds: 30           # Faster testing
server:
  debug: true                      # Enable debug mode
```

### Production

```yaml
metadata:
  rate_limit_seconds: 120          # Respectful API usage
server:
  debug: false                     # Disable debug mode
security:
  rate_limit:
    max_requests: 5                # Stricter rate limiting
```

## ✅ Configuration Validation

Test your configuration:

```bash
# Test main config
python -c "from src.config import load_config; print('✅ Config valid')"

# Test MAM config (if configured)
python test_mam_login.py

# Test metadata workflow
python tests/test_metadata_workflow.py
```

## 🔧 Troubleshooting

### Common Issues

**Config file not found:**

```bash
cp config/config.yaml.example config/config.yaml
```

**MAM login fails:**

- Verify credentials in `config/mam_config.json`
- Check if MAM requires 2FA (not currently supported)
- Test login manually on MAM website

**Rate limiting too slow:**

- Adjust `metadata.rate_limit_seconds` in config.yaml
- Use 30s for testing, 120s for production

**Webhook authentication fails:**

- Verify `AUTOBRR_TOKEN` in `.env` file
- Check autobrr webhook configuration

## 📋 Configuration Checklist

- [ ] `config/config.yaml` created and configured
- [ ] `.env` file created with required tokens
- [ ] `config/mam_config.json` created (if using MAM)
- [ ] Configuration validated with test scripts
- [ ] Notification services tested (if enabled)
- [ ] Rate limiting configured appropriately
