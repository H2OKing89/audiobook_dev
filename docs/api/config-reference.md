# 📋 Configuration Reference

Complete reference for all configuration options in the Audiobook Automation System.

## 📝 Configuration File Structure

The main configuration is stored in `config/config.yaml` using YAML format.

```yaml
# Example complete configuration
server:
  host: "0.0.0.0"
  port: 8000
  debug: false
  workers: 1

database:
  path: "db.sqlite"
  backup_enabled: true
  backup_interval_hours: 24

security:
  token_expiry_hours: 24
  max_requests_per_hour: 10
  allowed_hosts: []
  cors_enabled: false

notifications:
  enabled: true
  discord:
    enabled: false
    webhook_url: ""
    username: "Audiobook Bot"
    color: 0xFF69B4
  
  gotify:
    enabled: false
    server_url: ""
    app_token: ""
    priority: 5
  
  ntfy:
    enabled: false
    server_url: "https://ntfy.sh"
    topic: ""
    priority: "default"
  
  pushover:
    enabled: false
    user_key: ""
    api_token: ""
    priority: 0

qbittorrent:
  enabled: false
  host: "localhost"
  port: 8080
  username: ""
  password: ""
  download_path: "/downloads"
  category: "audiobooks"

metadata:
  audnex_enabled: true
  audible_enabled: true
  cache_expiry_hours: 168

logging:
  level: "INFO"
  file_enabled: true
  file_path: "logs/audiobook_requests.log"
  max_file_size_mb: 10
  backup_count: 5
  console_enabled: true
```

## 🌐 Server Configuration

### `server.host`
- **Type:** String
- **Default:** `"0.0.0.0"`
- **Description:** Host address to bind the server to
- **Examples:**
  - `"localhost"` - Local access only
  - `"0.0.0.0"` - All interfaces
  - `"192.168.1.100"` - Specific IP address

### `server.port`
- **Type:** Integer
- **Default:** `8000`
- **Range:** 1-65535
- **Description:** Port number for the web server

### `server.debug`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable debug mode with enhanced logging and error details
- **⚠️ Warning:** Never enable in production

### `server.workers`
- **Type:** Integer
- **Default:** `1`
- **Description:** Number of worker processes (for production deployment)

---

## 💾 Database Configuration

### `database.path`
- **Type:** String
- **Default:** `"db.sqlite"`
- **Description:** Path to SQLite database file
- **Examples:**
  - `"db.sqlite"` - Relative path
  - `"/var/lib/audiobook/db.sqlite"` - Absolute path
  - `":memory:"` - In-memory database (testing only)

### `database.backup_enabled`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable automatic database backups

### `database.backup_interval_hours`
- **Type:** Integer
- **Default:** `24`
- **Description:** Hours between automatic backups

---

## 🔐 Security Configuration

### `security.token_expiry_hours`
- **Type:** Integer
- **Default:** `24`
- **Range:** 1-168 (1 week max)
- **Description:** Hours before approval/rejection tokens expire

### `security.max_requests_per_hour`
- **Type:** Integer
- **Default:** `10`
- **Description:** Maximum requests per IP address per hour

### `security.allowed_hosts`
- **Type:** Array of Strings
- **Default:** `[]` (all hosts allowed)
- **Description:** Restrict access to specific hostnames
- **Example:**
  ```yaml
  allowed_hosts:
    - "audiobooks.example.com"
    - "localhost"
  ```

### `security.cors_enabled`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable Cross-Origin Resource Sharing

---

## 📱 Notification Configuration

### Global Notification Settings

#### `notifications.enabled`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable/disable all notifications

### Discord Notifications

#### `notifications.discord.enabled`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable Discord notifications

#### `notifications.discord.webhook_url`
- **Type:** String
- **Required:** Yes (if Discord enabled)
- **Description:** Discord webhook URL
- **Example:** `"https://discord.com/api/webhooks/123456789/abcdef..."`

#### `notifications.discord.username`
- **Type:** String
- **Default:** `"Audiobook Bot"`
- **Description:** Bot username for Discord messages

#### `notifications.discord.color`
- **Type:** Integer (Hex)
- **Default:** `0xFF69B4`
- **Description:** Embed color for Discord messages
- **Examples:**
  - `0xFF69B4` - Hot pink
  - `0x00FF00` - Green
  - `0x0099FF` - Blue

### Gotify Notifications

#### `notifications.gotify.enabled`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable Gotify notifications

#### `notifications.gotify.server_url`
- **Type:** String
- **Required:** Yes (if Gotify enabled)
- **Description:** Gotify server URL
- **Example:** `"https://gotify.example.com"`

#### `notifications.gotify.app_token`
- **Type:** String
- **Required:** Yes (if Gotify enabled)
- **Description:** Gotify application token

#### `notifications.gotify.priority`
- **Type:** Integer
- **Default:** `5`
- **Range:** 0-10
- **Description:** Message priority level

### Ntfy Notifications

#### `notifications.ntfy.enabled`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable Ntfy notifications

#### `notifications.ntfy.server_url`
- **Type:** String
- **Default:** `"https://ntfy.sh"`
- **Description:** Ntfy server URL

#### `notifications.ntfy.topic`
- **Type:** String
- **Required:** Yes (if Ntfy enabled)
- **Description:** Ntfy topic name
- **Example:** `"audiobook_requests"`

#### `notifications.ntfy.priority`
- **Type:** String
- **Default:** `"default"`
- **Options:** `"max"`, `"high"`, `"default"`, `"low"`, `"min"`
- **Description:** Message priority

### Pushover Notifications

#### `notifications.pushover.enabled`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable Pushover notifications

#### `notifications.pushover.user_key`
- **Type:** String
- **Required:** Yes (if Pushover enabled)
- **Description:** Pushover user key

#### `notifications.pushover.api_token`
- **Type:** String
- **Required:** Yes (if Pushover enabled)
- **Description:** Pushover API token

#### `notifications.pushover.priority`
- **Type:** Integer
- **Default:** `0`
- **Range:** -2 to 2
- **Description:** Message priority (-2=lowest, 2=emergency)

---

## ⚙️ qBittorrent Configuration

### `qbittorrent.enabled`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable qBittorrent integration

### `qbittorrent.host`
- **Type:** String
- **Default:** `"localhost"`
- **Description:** qBittorrent server hostname/IP

### `qbittorrent.port`
- **Type:** Integer
- **Default:** `8080`
- **Description:** qBittorrent web UI port

### `qbittorrent.username`
- **Type:** String
- **Required:** Yes (if qBittorrent enabled)
- **Description:** qBittorrent web UI username

### `qbittorrent.password`
- **Type:** String
- **Required:** Yes (if qBittorrent enabled)
- **Description:** qBittorrent web UI password

### `qbittorrent.download_path`
- **Type:** String
- **Default:** `"/downloads"`
- **Description:** Download directory path

### `qbittorrent.category`
- **Type:** String
- **Default:** `"audiobooks"`
- **Description:** Category for audiobook torrents

---

## 📖 Metadata Configuration

### `metadata.audnex_enabled`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable Audnex API for metadata

### `metadata.audible_enabled`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable Audible scraping for metadata

### `metadata.cache_expiry_hours`
- **Type:** Integer
- **Default:** `168` (1 week)
- **Description:** Hours to cache metadata responses

---

## 📋 Logging Configuration

### `logging.level`
- **Type:** String
- **Default:** `"INFO"`
- **Options:** `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`
- **Description:** Minimum log level to record

### `logging.file_enabled`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable logging to file

### `logging.file_path`
- **Type:** String
- **Default:** `"logs/audiobook_requests.log"`
- **Description:** Log file path

### `logging.max_file_size_mb`
- **Type:** Integer
- **Default:** `10`
- **Description:** Maximum log file size before rotation

### `logging.backup_count`
- **Type:** Integer
- **Default:** `5`
- **Description:** Number of backup log files to keep

### `logging.console_enabled`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable logging to console/stdout

---

## 🌍 Environment Variables

Sensitive configuration can be provided via environment variables:

```bash
# Database
export DB_PATH="/var/lib/audiobook/db.sqlite"

# Discord
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."

# Gotify
export GOTIFY_SERVER_URL="https://gotify.example.com"
export GOTIFY_APP_TOKEN="AbCdEf123456"

# Ntfy
export NTFY_TOPIC="audiobook_requests"

# Pushover
export PUSHOVER_USER_KEY="abc123..."
export PUSHOVER_API_TOKEN="def456..."

# qBittorrent
export QB_HOST="qbittorrent.local"
export QB_USERNAME="admin"
export QB_PASSWORD="password123"
```

Environment variables take precedence over YAML configuration.

---

## 📋 Configuration Examples

### Minimal Configuration
```yaml
server:
  port: 8000

notifications:
  enabled: false

qbittorrent:
  enabled: false
```

### Production Configuration
```yaml
server:
  host: "0.0.0.0"
  port: 8000
  debug: false
  workers: 4

database:
  path: "/var/lib/audiobook/db.sqlite"
  backup_enabled: true

security:
  token_expiry_hours: 12
  max_requests_per_hour: 20
  allowed_hosts:
    - "audiobooks.company.com"

notifications:
  enabled: true
  discord:
    enabled: true
    webhook_url: "${DISCORD_WEBHOOK_URL}"
    username: "Audiobook Bot"

logging:
  level: "INFO"
  file_path: "/var/log/audiobook/requests.log"
  max_file_size_mb: 50
  backup_count: 10
```

### Development Configuration
```yaml
server:
  host: "localhost"
  port: 8001
  debug: true

database:
  path: "dev_db.sqlite"

notifications:
  enabled: false

logging:
  level: "DEBUG"
  console_enabled: true
```

---

## ✅ Configuration Validation

The system validates configuration on startup:

- **Required fields** - Ensures all mandatory settings are present
- **Type checking** - Validates data types (string, integer, boolean)
- **Range validation** - Checks numeric values are within acceptable ranges
- **Format validation** - Validates URLs, file paths, etc.
- **Dependency checking** - Ensures required settings for enabled features

### Validation Errors
Configuration errors are reported clearly:

```
Configuration Error: notifications.discord.webhook_url is required when Discord is enabled
Configuration Error: server.port must be between 1 and 65535
Configuration Error: security.token_expiry_hours cannot exceed 168 (1 week)
```

---

## 🔄 Dynamic Configuration

Some settings can be updated without restarting:

- **Notification settings** - Webhook URLs, priorities
- **Logging levels** - Change verbosity on the fly  
- **Rate limits** - Adjust request limits
- **Metadata cache** - Clear or update cache settings

Send a `SIGHUP` signal to reload configuration:
```bash
kill -HUP $(pgrep -f "python.*main.py")
```

---

**Need help with configuration?** Check the [Getting Started Guide](../user-guide/getting-started.md) or [Troubleshooting Guide](../user-guide/troubleshooting.md)!
