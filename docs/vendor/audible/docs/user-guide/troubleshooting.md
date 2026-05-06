# 🔧 Troubleshooting Guide

Common issues and solutions for the Audiobook Automation System.

## 🚨 System Won't Start

### Port Already in Use

**Error:** `Address already in use: 8080`

**Solution:**

```bash
# Find process using port 8080
sudo lsof -i :8080

# Kill the process (replace PID)
sudo kill -9 <PID>

# Or use a different port in config.yaml
server:
  port: 8081
```

### Missing Configuration

**Error:** `Config file not found`

**Solution:**

```bash
# Copy example config
cp config/config.yaml.example config/config.yaml

# Create .env file
cp .env.example .env
# Edit .env with your tokens
```

### Python Dependencies

**Error:** `ModuleNotFoundError: No module named 'xyz'`

**Solution:**

```bash
# Install dependencies
pip install -r requirements.txt

# Or use virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

## 🔐 Authentication Issues

### Webhook Token Mismatch

**Error:** `401 Unauthorized` on webhook requests

**Solution:**

1. Check `AUTOBRR_TOKEN` in `.env` file
2. Verify autobrr webhook configuration
3. Test token manually:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8080/webhook/test
```

### CSRF Token Issues

**Error:** `CSRF token mismatch`

**Solution:**

1. Clear browser cache and cookies
2. Refresh the page
3. Check if `csrf_enabled: true` in config.yaml
4. Verify browser accepts cookies

## 🌐 Web Interface Problems

### Page Not Loading

**Symptoms:** Blank page or 404 errors

**Solutions:**

1. **Check server status:**

```bash
# Verify server is running
ps aux | grep python
```

2. **Check logs:**

```bash
tail -f logs/audiobook_requests.log
```

3. **Test direct access:**

```bash
curl http://localhost:8080
```

### JavaScript Errors

**Symptoms:** Buttons not working, keyboard shortcuts broken

**Solutions:**

1. **Open browser console** (F12)
2. **Clear browser cache**
3. **Check for JavaScript errors:**
   - Look for red errors in console
   - Verify static files are loading
4. **Test in incognito mode**

### Mobile Interface Issues

**Symptoms:** Interface not responsive on mobile

**Solutions:**

1. **Clear mobile browser cache**
2. **Test in different mobile browsers**
3. **Check viewport meta tag** in templates
4. **Verify CSS media queries** are working

## 📊 Metadata Workflow Issues

### MAM API Auth Failed

**Error:** `MAM API authentication failed; update MAM_ID`

**Solutions:**

1. **Check API cookie:**

```bash
# Confirm MAM_ID is present without printing the value
test -n "$MAM_ID" && echo "MAM_ID is set"

pytest tests/test_mam_api.py -k Integration --no-cov
```

2. **Refresh the cookie value:**

Verify the account is active, log in to MAM in your browser, copy the current `mam_id` cookie value into `.env` as `MAM_ID`, and restart the app so the environment reloads.

### ASIN Not Found

**Error:** `No ASIN found on MAM page`

**This is normal behavior:**

- Not all MAM torrents have ASINs
- System will fallback to Audible search
- Check logs for fallback success

### Audnex API Timeout

**Error:** `Audnex API timeout` or `Connection failed`

**Solutions:**

1. **Check Audnex status:**

```bash
curl https://api.audnex.us/books/health
```

2. **Increase timeout:**

```yaml
# In config.yaml
metadata:
  sources:
    audnex:
      timeout_seconds: 30  # Increase from 10
```

3. **Check network connectivity:**

```bash
ping api.audnex.us
```

### Rate Limiting Too Slow

**Issue:** Metadata workflow takes too long

**Solutions:**

1. **Adjust rate limit for testing:**

```yaml
# In config.yaml (testing only)
metadata:
  rate_limit_seconds: 30  # Instead of 120
```

2. **Check last API call time:**

```bash
# View coordinator logs
tail -f logs/metadata_coordinator.log
```

## 🔔 Notification Issues

### Discord Webhook Not Working

**Error:** Discord notifications not received

**Solutions:**

1. **Test webhook URL:**

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"content":"Test message"}' \
  YOUR_DISCORD_WEBHOOK_URL
```

2. **Check webhook permissions:**
   - Verify webhook has send message permissions
   - Check channel permissions

3. **Verify configuration:**

```bash
# Check .env file
if grep -q '^DISCORD_WEBHOOK_URL=' .env; then echo 'DISCORD_WEBHOOK_URL set'; else echo 'DISCORD_WEBHOOK_URL unset'; fi

# Test notification system
python -c "import os; print('DISCORD_WEBHOOK_URL set' if os.environ.get('DISCORD_WEBHOOK_URL') else 'DISCORD_WEBHOOK_URL unset')"
```

### Pushover Not Working

**Error:** Pushover notifications not received

**Solutions:**

1. **Verify credentials:**
   - Check User Key and API Token
   - Test on Pushover website

2. **Check device registration:**
   - Install Pushover app
   - Register device with account

3. **Test API:**

```bash
curl -s -F "token=YOUR_API_TOKEN" \
  -F "user=YOUR_USER_KEY" \
  -F "message=Test message" \
  https://api.pushover.net/1/messages.json
```

## 💾 Database Issues

### Database Locked

**Error:** `Database is locked`

**Solutions:**

1. **Check for hung processes:**

```bash
# Find processes using database
lsof db.sqlite
```

1. **Restart application:**

```bash
# Stop only the audiobook service process
pkill -f "src/main.py"

# Start fresh
python src/main.py
```

If `pkill` is too broad for your environment, use the specific PID you identified earlier with `kill <PID>` or stop the relevant service/container instead.

1. **Backup and recreate:**

```bash
# Backup database
cp db.sqlite db.sqlite.backup

# Remove lock files
rm -f db.sqlite-shm db.sqlite-wal
```

### Database Corruption

**Error:** `Database disk image is malformed`

**Solutions:**

1. **Check database integrity:**

```bash
sqlite3 db.sqlite "PRAGMA integrity_check;"
```

1. **Restore from backup:**

```bash
# Find latest backup
ls -la db.sqlite*

# Restore
cp db.sqlite.backup db.sqlite
```

1. **Recreate database:**

```bash
# Last resort: recreate (loses data)
rm db.sqlite
python src/db.py  # Recreates tables
```

## 🐳 Docker Issues

### Container Won't Start

**Error:** Docker container exits immediately

**Solutions:**

1. **Check container logs:**

```bash
docker logs audiobook-automation
```

1. **Verify volume mounts:**

```bash
# Check config files exist
ls -la config/
```

1. **Test without Docker:**

```bash
# Run directly to see errors
python src/main.py
```

### Port Mapping Issues

**Error:** Cannot access web interface

**Solutions:**

1. **Check port mapping:**

```bash
docker ps  # Verify ports are mapped
```

1. **Test container networking:**

```bash
# Access from within container
docker exec -it audiobook-automation curl localhost:8080
```

## 📝 Log Analysis

### Enable Debug Logging

```yaml
# In config.yaml
server:
  debug: true

logging:
  level: DEBUG
```

### Key Log Files

```bash
# Main application log
tail -f logs/audiobook_requests.log

# Metadata workflow
tail -f logs/metadata_coordinator.log

# MAM API client
tail -f logs/audiobook_requests.log

# Notifications
tail -f logs/notifications.log
```

### Log Patterns to Look For

```bash
# Errors
grep -i "error" logs/*.log

# Authentication issues
grep -i "auth\|token" logs/*.log

# Rate limiting
grep -i "rate" logs/*.log

# Database issues
grep -i "database\|sqlite" logs/*.log
```

## 🆘 Getting Help

### Information to Gather

Before seeking help, collect:

1. **System Information:**

```bash
# Python version
python --version

# OS information
uname -a

# Package versions
pip freeze | grep -E "(fastapi|httpx|pydantic)"
```

1. **Configuration (sanitized):**

```bash
# Remove sensitive data before sharing
cp config/config.yaml config/config-debug.yaml
# Edit config-debug.yaml to remove secrets
```

1. **Log Excerpts:**

```bash
# Last 50 lines of relevant logs
tail -50 logs/audiobook_requests.log
tail -50 logs/metadata_coordinator.log
```

1. **Error Messages:**
   - Full error text
   - Steps to reproduce
   - Expected vs actual behavior

### Support Channels

- Check documentation first
- Search existing issues
- Create detailed bug reports
- Include system information and logs

## 📋 Troubleshooting Checklist

- [ ] System requirements met
- [ ] Configuration files exist and valid
- [ ] Environment variables set
- [ ] Dependencies installed
- [ ] Ports available
- [ ] Network connectivity working
- [ ] Authentication tokens valid
- [ ] Database accessible
- [ ] Log files readable
- [ ] Error messages documented
