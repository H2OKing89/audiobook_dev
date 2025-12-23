# 🔔 Notifications Guide

Set up notifications to stay informed about audiobook request processing, approvals, and system status.

## 📱 Supported Notification Services

### 1. Discord Webhooks 🎮

Send notifications to Discord channels with rich embeds.

### 2. Pushover 📨

Cross-platform push notifications to mobile devices.

### 3. Gotify 🔔

Self-hosted notification service.

### 4. NTFY 📡

Simple HTTP-based notification service.

## ⚙️ Configuration

### Discord Setup

1. **Create Discord Webhook:**
   - Go to your Discord server settings
   - Navigate to Integrations → Webhooks
   - Click "New Webhook"
   - Copy the webhook URL

2. **Configure in `.env`:**

   ```bash
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your/webhook/url
   ```

3. **Enable in `config.yaml`:**

   ```yaml
   notifications:
     discord:
       enabled: true
       include_cover_art: true
       include_metadata: true
   ```

### Pushover Setup

1. **Create Pushover Account:**
   - Sign up at <https://pushover.net>
   - Note your User Key
   - Create an application for API Token

2. **Configure in `.env`:**

   ```bash
   PUSHOVER_USER_KEY=your-pushover-user-key
   PUSHOVER_API_TOKEN=your-pushover-api-token
   ```

3. **Enable in `config.yaml`:**

   ```yaml
   notifications:
     pushover:
       enabled: true
       priority: 0                # -2 to 2 priority level
       sound: "pushover"          # Notification sound
   ```

### Gotify Setup

1. **Install Gotify Server:**

   ```bash
   # Docker example
   docker run -d -p 80:80 -v gotify-data:/app/data gotify/server
   ```

2. **Configure in `.env`:**

   ```bash
   GOTIFY_URL=https://gotify.example.com
   GOTIFY_TOKEN=your-gotify-application-token
   ```

3. **Enable in `config.yaml`:**

   ```yaml
   notifications:
     gotify:
       enabled: true
       priority: 5              # 0-10 priority level
   ```

### NTFY Setup

1. **Choose NTFY Service:**
   - Use public service: <https://ntfy.sh>
   - Or self-host: <https://github.com/binwiederhier/ntfy>

2. **Configure in `.env`:**

   ```bash
   NTFY_URL=https://ntfy.sh/your-unique-topic-name
   ```

3. **Enable in `config.yaml`:**

   ```yaml
   notifications:
     ntfy:
       enabled: true
       priority: 3              # 1-5 priority level
   ```

## 📨 Notification Types

### Request Approved ✅

Sent when an audiobook request is approved:

```
📚 Audiobook Approved
Title: The Wolf's Advance
Author: Shane Purdy
Status: Approved for download
```

### Request Rejected ❌

Sent when a request is rejected:

```
❌ Audiobook Rejected
Title: Example Book
Reason: Poor quality / Duplicate
```

### System Alerts 🚨

Sent for system issues:

```
🚨 System Alert
Issue: MAM login failed
Action: Check MAM credentials
```

### Processing Updates 📊

Sent for workflow status:

```
🔄 Processing Update
Title: Book Title
Status: Metadata retrieved from Audnex
ASIN: B0123456789
```

## 🎨 Notification Formatting

### Discord Rich Embeds

Discord notifications include:

- **Cover Art** - Book cover thumbnail
- **Metadata Fields** - Author, narrator, publisher
- **Series Information** - Series name and number
- **Color Coding** - Green (approved), red (rejected)
- **Direct Links** - Links to MAM page and admin interface

### Pushover Rich Notifications

Pushover notifications include:

- **Custom Icons** - Book-specific icons
- **Priority Levels** - Important requests get higher priority
- **Action Buttons** - Quick approve/reject buttons
- **Images** - Book cover attachments

## ⚙️ Advanced Configuration

### Notification Filtering

```yaml
notifications:
  filters:
    min_file_size_mb: 100        # Only notify for files > 100MB
    exclude_categories:          # Skip notifications for these
      - "Low Quality"
    include_series_only: true    # Only notify for series books
```

### Rate Limiting

```yaml
notifications:
  rate_limiting:
    max_per_hour: 10            # Max notifications per hour
    cooldown_minutes: 5         # Min time between notifications
```

### Custom Templates

```yaml
notifications:
  templates:
    approved: "✅ {title} by {author} - Approved!"
    rejected: "❌ {title} - Rejected: {reason}"
    error: "🚨 System Error: {error}"
```

## 🧪 Testing Notifications

### Test All Services

```bash
# Test all configured notification services
python -c "from src.notify import test_all_notifications; test_all_notifications()"
```

### Test Individual Services

```bash
# Test Discord
python -c "from src.notify.discord import DiscordNotifier; DiscordNotifier().test()"

# Test Pushover
python -c "from src.notify.pushover import PushoverNotifier; PushoverNotifier().test()"
```

### Manual Test Notification

```bash
# Send test notification
python -c "
from src.notify import send_notification
send_notification(
    title='Test Notification',
    message='This is a test from the audiobook system',
    type='info'
)
"
```

## 🔧 Troubleshooting

### Common Issues

**Discord webhook not working:**

- Verify webhook URL is correct
- Check Discord server permissions
- Test webhook URL manually with curl

**Pushover notifications not received:**

- Verify User Key and API Token
- Check Pushover app is installed on device
- Test with Pushover website's test feature

**Gotify connection failed:**

- Verify Gotify server is running
- Check network connectivity
- Validate application token

**NTFY messages not received:**

- Verify topic name is unique
- Check NTFY server status
- Test with curl or browser

### Debug Mode

Enable notification debugging:

```yaml
notifications:
  debug: true                   # Enable verbose logging
  log_payloads: true           # Log notification payloads
```

### Notification Logs

Check notification logs:

```bash
# View notification logs
tail -f logs/notifications.log

# View specific service logs
grep "discord" logs/notifications.log
grep "pushover" logs/notifications.log
```

## 📊 Monitoring

### Notification Statistics

Track notification performance:

- **Delivery Rate** - Percentage of successful notifications
- **Response Time** - Time to send notifications
- **Error Rate** - Failed notification attempts
- **Service Health** - Status of each notification service

### Metrics Dashboard

View notification metrics in the web interface:

- **Recent Notifications** - Last 24 hours of notifications
- **Service Status** - Health check for each service
- **Delivery Success** - Success/failure rates
- **Queue Status** - Pending notifications

## 📋 Notification Checklist

- [ ] Choose notification service(s)
- [ ] Configure service credentials in `.env`
- [ ] Enable service(s) in `config.yaml`
- [ ] Test notifications with test script
- [ ] Verify notifications received on devices
- [ ] Configure notification filtering (optional)
- [ ] Set up monitoring and alerts
- [ ] Document notification setup for team
