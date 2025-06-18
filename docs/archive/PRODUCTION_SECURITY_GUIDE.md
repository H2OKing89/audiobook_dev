# Production Security Guide

## Pre-Deployment Security Checklist

### 1. Environment Configuration ✅
- [ ] Copy `.env.example` to `.env`
- [ ] Generate strong, unique API keys and tokens
- [ ] Set `FORCE_HTTPS=true`
- [ ] Configure production database path
- [ ] Set appropriate `LOG_LEVEL` (INFO or WARNING)

### 2. File Permissions 🔒
```bash
# Secure the environment file
chmod 600 .env

# Secure the config file
chmod 600 config/config.yaml

# Secure the database
chmod 600 db.sqlite

# Secure log files
chmod 644 logs/*.log
```

### 3. HTTPS Configuration 🔐
```yaml
# config/config.yaml
security:
  force_https: true  # CRITICAL: Enable in production

server:
  base_url: "https://your-domain.com"  # Use HTTPS URL
```

### 4. Reverse Proxy Configuration 🌐

#### Nginx Example
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Configuration
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Security Headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # Proxy Settings
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-SSL on;
    }
}
```

#### Apache Example
```apache
<VirtualHost *:80>
    ServerName your-domain.com
    Redirect permanent / https://your-domain.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName your-domain.com
    
    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /path/to/your/certificate.crt
    SSLCertificateKeyFile /path/to/your/private.key
    SSLProtocol TLSv1.2 TLSv1.3
    
    # Security Headers
    Header always set X-Content-Type-Options nosniff
    Header always set X-Frame-Options DENY
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
    
    # Proxy Settings
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/
    ProxyPreserveHost On
    ProxyAddHeaders On
</VirtualHost>
```

### 5. Systemd Service Configuration 🔧

Create `/etc/systemd/system/audiobook-approval.service`:
```ini
[Unit]
Description=Audiobook Approval Service
After=network.target

[Service]
Type=simple
User=audiobook
Group=audiobook
WorkingDirectory=/opt/audiobook-approval
Environment=PATH=/opt/audiobook-approval/.venv/bin
ExecStart=/opt/audiobook-approval/.venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/opt/audiobook-approval/logs /opt/audiobook-approval/db.sqlite

[Install]
WantedBy=multi-user.target
```

### 6. Database Security 🗃️
```bash
# Create dedicated user
sudo useradd -r -s /bin/false audiobook-user

# Secure database directory
sudo mkdir -p /var/lib/audiobook
sudo chown audiobook-user:audiobook-user /var/lib/audiobook
sudo chmod 700 /var/lib/audiobook

# Move database
sudo mv db.sqlite /var/lib/audiobook/
sudo chown audiobook-user:audiobook-user /var/lib/audiobook/db.sqlite
sudo chmod 600 /var/lib/audiobook/db.sqlite
```

### 7. Log Security 📝
```bash
# Create log directory
sudo mkdir -p /var/log/audiobook-approval
sudo chown audiobook-user:audiobook-user /var/log/audiobook-approval
sudo chmod 755 /var/log/audiobook-approval

# Configure log rotation
sudo tee /etc/logrotate.d/audiobook-approval << EOF
/var/log/audiobook-approval/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 audiobook-user audiobook-user
    postrotate
        systemctl reload audiobook-approval
    endscript
}
EOF
```

### 8. Firewall Configuration 🔥
```bash
# UFW (Ubuntu/Debian)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'  # or Apache
sudo ufw enable

# iptables example
sudo iptables -A INPUT -i lo -j ACCEPT
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -j DROP
```

## Security Monitoring 📊

### 1. Log Monitoring
Monitor these log patterns for security events:
```bash
# Failed authentication attempts
grep "Invalid Autobrr token" /var/log/audiobook-approval/*.log

# Rate limiting triggers
grep "Rate limit exceeded" /var/log/audiobook-approval/*.log

# Suspicious requests
grep "HTTPException" /var/log/audiobook-approval/*.log

# CSRF attacks
grep "CSRF" /var/log/audiobook-approval/*.log
```

### 2. Automated Monitoring Script
```bash
#!/bin/bash
# /usr/local/bin/audiobook-security-monitor.sh

LOG_FILE="/var/log/audiobook-approval/audiobook_requests.log"
ALERT_EMAIL="admin@example.com"

# Check for security events in last hour
SECURITY_EVENTS=$(grep -E "(Rate limit exceeded|Invalid.*token|CSRF|HTTPException)" "$LOG_FILE" | grep "$(date -d '1 hour ago' '+%Y-%m-%d %H')")

if [ -n "$SECURITY_EVENTS" ]; then
    echo "Security events detected in Audiobook Approval System:" | mail -s "Security Alert" "$ALERT_EMAIL"
    echo "$SECURITY_EVENTS" | mail -s "Security Alert Details" "$ALERT_EMAIL"
fi
```

### 3. Health Check Endpoint
```bash
# Add to monitoring system
curl -f https://your-domain.com/health || alert_admin
```

## Backup and Recovery 💾

### 1. Database Backup
```bash
#!/bin/bash
# /usr/local/bin/audiobook-backup.sh

DB_PATH="/var/lib/audiobook/db.sqlite"
BACKUP_DIR="/var/backups/audiobook"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
sqlite3 "$DB_PATH" ".backup $BACKUP_DIR/db_$DATE.sqlite"

# Encrypt backup
gpg --symmetric --cipher-algo AES256 "$BACKUP_DIR/db_$DATE.sqlite"
rm "$BACKUP_DIR/db_$DATE.sqlite"

# Clean old backups (keep 30 days)
find "$BACKUP_DIR" -name "*.gpg" -mtime +30 -delete
```

### 2. Configuration Backup
```bash
# Backup configuration (without secrets)
cp config/config.yaml.example /var/backups/audiobook/config_$(date +%Y%m%d).yaml
```

## Incident Response 🚨

### 1. Security Incident Checklist
- [ ] Identify the nature of the security incident
- [ ] Isolate affected systems
- [ ] Document the incident
- [ ] Analyze logs for extent of compromise
- [ ] Notify relevant stakeholders
- [ ] Implement containment measures
- [ ] Plan recovery steps
- [ ] Conduct post-incident review

### 2. Emergency Commands
```bash
# Stop the service immediately
sudo systemctl stop audiobook-approval

# Block all traffic to the service
sudo ufw deny 8000

# Backup current logs
cp -r /var/log/audiobook-approval /var/log/audiobook-approval.incident.$(date +%Y%m%d_%H%M%S)

# Review recent access
sudo tail -1000 /var/log/audiobook-approval/audiobook_requests.log
```

## Regular Security Maintenance 🔄

### Weekly Tasks
- [ ] Review security logs
- [ ] Check for failed authentication attempts
- [ ] Verify backup integrity
- [ ] Update dependencies with security patches

### Monthly Tasks  
- [ ] Review and rotate API keys
- [ ] Analyze security metrics
- [ ] Test incident response procedures
- [ ] Update security documentation

### Quarterly Tasks
- [ ] Conduct security assessment
- [ ] Review access controls
- [ ] Update security policies
- [ ] Plan security training

---

**Remember**: Security is an ongoing process, not a one-time setup. Regular monitoring, updates, and reviews are essential for maintaining a secure production environment.
