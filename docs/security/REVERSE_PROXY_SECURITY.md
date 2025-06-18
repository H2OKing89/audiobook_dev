# Reverse Proxy Security Configuration

## Queue Status Endpoint Security

The `/queue/status` endpoint should **NOT** be publicly accessible as it exposes internal system information including:
- Queue sizes and capacity
- Worker status
- System timestamps
- Internal state information

## Recommended Nginx Configuration

Add this to your Nginx configuration to block the queue status endpoint:

```nginx
server {
    server_name audiobook-requests.kingpaging.com;
    
    # Block queue status endpoint from public access
    location /queue/status {
        deny all;
        return 403;
    }
    
    # Allow webhook endpoint (this is what Autobrr needs)
    location /webhook/audiobook-requests {
        proxy_pass http://10.1.60.11:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Rate limiting for webhook endpoint
        limit_req zone=webhook_limit burst=10 nodelay;
    }
    
    # Allow web UI endpoints
    location / {
        proxy_pass http://10.1.60.11:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Rate limiting zone for webhook (add to http block)
http {
    limit_req_zone $binary_remote_addr zone=webhook_limit:10m rate=10r/m;
    # ... other config
}
```

## Alternative: Internal-Only Access

If you need to monitor the queue status, you can:

1. **Access from internal network only**:
   ```bash
   curl http://10.1.60.11:8000/queue/status
   ```

2. **Set up an internal API key** (optional extra security):
   ```bash
   export INTERNAL_API_KEY="your-secret-monitoring-key"
   ```
   
   Then access with:
   ```bash
   curl -H "X-API-Key: your-secret-monitoring-key" https://audiobook-requests.kingpaging.com/queue/status
   ```

## Apache Configuration (Alternative)

If using Apache instead of Nginx:

```apache
<VirtualHost *:443>
    ServerName audiobook-requests.kingpaging.com
    
    # Block queue status endpoint
    <Location "/queue/status">
        Require all denied
    </Location>
    
    # Proxy other requests
    ProxyPreserveHost On
    ProxyPass / http://10.1.60.11:8000/
    ProxyPassReverse / http://10.1.60.11:8000/
</VirtualHost>
```

## Security Benefits

Blocking `/queue/status` prevents:
- ✅ Information disclosure about system capacity
- ✅ Potential DoS reconnaissance (knowing queue limits)
- ✅ System state enumeration
- ✅ Internal timing/performance information leakage

## Monitoring Alternatives

For production monitoring, consider:
1. **Internal monitoring tools** (Prometheus, Grafana)
2. **Health check endpoint** (create a separate `/health` with minimal info)
3. **Log-based monitoring** (parse application logs)
4. **Infrastructure monitoring** (CPU, memory, network usage)
