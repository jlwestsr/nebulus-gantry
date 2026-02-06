# Reverse Proxy Setup

A reverse proxy sits between your users and Nebulus Gantry, handling HTTPS/SSL termination, load balancing, and security. This guide covers three popular options: Nginx, Caddy, and Traefik.

---

## Why Use a Reverse Proxy?

### Benefits

- **SSL/TLS Termination** - Handle HTTPS encryption/decryption
- **Security** - Hide backend infrastructure, prevent direct access
- **Performance** - Static file caching, compression, connection pooling
- **Flexibility** - Easy service updates without changing user-facing URLs
- **Load Balancing** - Distribute traffic across multiple backend instances

### Architecture

```text
┌──────────────────────────────────────────────────────────┐
│                        Internet                           │
└─────────────────────┬────────────────────────────────────┘
                      │ HTTPS (443)
┌─────────────────────▼────────────────────────────────────┐
│              Reverse Proxy (Nginx/Caddy/Traefik)         │
│  - SSL Termination                                        │
│  - Request routing                                        │
│  - Static file caching                                    │
└───────┬──────────────────────────────┬───────────────────┘
        │ HTTP (3000)                  │ HTTP (8000)
┌───────▼──────────┐          ┌────────▼──────────┐
│  Frontend        │          │  Backend          │
│  React SPA       │          │  FastAPI          │
└──────────────────┘          └───────────────────┘
```

---

## Nginx Configuration

### Installation

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx

# CentOS/RHEL
sudo yum install nginx

# macOS
brew install nginx
```

### Basic Configuration

Create `/etc/nginx/sites-available/gantry`:

```nginx
# HTTP server - redirect all traffic to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name gantry.example.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name gantry.example.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/gantry.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/gantry.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/gantry-access.log;
    error_log /var/log/nginx/gantry-error.log;

    # API endpoints
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Timeouts for SSE streaming
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;

        # Disable buffering for SSE
        proxy_buffering off;
        proxy_cache off;
    }

    # Frontend SPA
    location / {
        proxy_pass http://localhost:3001/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Static file caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        proxy_pass http://localhost:3001;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Enable Configuration

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/gantry /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Enable autostart
sudo systemctl enable nginx
```

### SSL Certificate with Certbot

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d gantry.example.com

# Auto-renewal is configured automatically
# Test renewal:
sudo certbot renew --dry-run
```

### Advanced Configuration

#### Rate Limiting

```nginx
# Add to http block in /etc/nginx/nginx.conf
http {
    # Define rate limit zone (10MB stores ~160k IP addresses)
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;

    # ... other config
}

# Add to server block
server {
    # ... other config

    # Apply rate limiting to API
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        # ... rest of config
    }

    # Stricter limits on auth endpoints
    location /api/auth/login {
        limit_req zone=login_limit burst=3 nodelay;
        # ... rest of config
    }
}
```

#### Load Balancing

For multiple backend instances:

```nginx
# Define upstream
upstream gantry_backend {
    least_conn;  # Load balancing method
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
}

# Use in location block
location /api/ {
    proxy_pass http://gantry_backend/;
    # ... rest of config
}
```

#### WebSocket Support

Already configured in the basic setup with:

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection 'upgrade';
```

#### Gzip Compression

```nginx
server {
    # ... other config

    # Enable compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss;
}
```

---

## Caddy Configuration

Caddy automatically handles SSL certificates via Let's Encrypt. Zero configuration HTTPS!

### Installation

```bash
# Ubuntu/Debian
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy

# macOS
brew install caddy

# Docker (recommended)
docker pull caddy:2-alpine
```

### Basic Configuration

Create `/etc/caddy/Caddyfile`:

```caddy
gantry.example.com {
    # Automatic HTTPS with Let's Encrypt
    # (Caddy handles this automatically!)

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
    }

    # API endpoints
    handle /api/* {
        reverse_proxy localhost:8000 {
            # Headers
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-Proto {scheme}

            # SSE streaming support
            flush_interval -1
        }
    }

    # Frontend SPA
    handle {
        reverse_proxy localhost:3001
    }

    # Logging
    log {
        output file /var/log/caddy/gantry.log {
            roll_size 100mb
            roll_keep 10
        }
    }
}
```

### Docker Compose Integration

```yaml
# docker-compose.yml
version: '3.8'

services:
  caddy:
    image: caddy:2-alpine
    container_name: gantry-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - nebulus

  backend:
    # ... existing config
    expose:
      - "8000"  # Don't expose to host

  frontend:
    # ... existing config
    expose:
      - "3000"  # Don't expose to host

networks:
  nebulus:
    external: true
    name: nebulus-prime_ai-network

volumes:
  caddy_data:
    driver: local
  caddy_config:
    driver: local
```

### Start Caddy

```bash
# System service
sudo systemctl start caddy
sudo systemctl enable caddy

# Docker
docker compose up -d caddy

# Manual
caddy run --config /etc/caddy/Caddyfile
```

### Advanced Configuration

#### Rate Limiting

Caddy requires a plugin. Add to Caddyfile:

```caddy
gantry.example.com {
    # Install rate limit plugin first:
    # xcaddy build --with github.com/mholt/caddy-ratelimit

    rate_limit {
        zone api {
            key {remote_host}
            events 100
            window 1m
        }
        zone login {
            key {remote_host}
            events 5
            window 1m
        }
    }

    handle /api/* {
        rate_limit api
        reverse_proxy localhost:8000
    }

    handle /api/auth/login {
        rate_limit login
        reverse_proxy localhost:8000
    }
}
```

#### Load Balancing

```caddy
gantry.example.com {
    handle /api/* {
        reverse_proxy localhost:8000 localhost:8001 localhost:8002 {
            lb_policy least_conn
            health_uri /health
            health_interval 10s
        }
    }
}
```

#### Custom SSL Certificate

```caddy
gantry.example.com {
    tls /path/to/cert.pem /path/to/key.pem

    # ... rest of config
}
```

---

## Traefik Configuration

Traefik is designed for containerized environments with automatic service discovery.

### Installation

Best used with Docker:

```yaml
# docker-compose.yml
version: '3.8'

services:
  traefik:
    image: traefik:v2.11
    container_name: gantry-traefik
    restart: unless-stopped
    command:
      # API and dashboard
      - "--api.dashboard=true"
      - "--api.insecure=true"  # Only for testing!

      # Docker provider
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"

      # Entrypoints
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"

      # Let's Encrypt
      - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@example.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"

      # Logging
      - "--log.level=INFO"
      - "--accesslog=true"

    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"  # Dashboard (secure this in production!)

    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik_letsencrypt:/letsencrypt

    networks:
      - nebulus

  backend:
    # ... existing config
    labels:
      - "traefik.enable=true"

      # HTTP router
      - "traefik.http.routers.gantry-backend.rule=Host(`gantry.example.com`) && PathPrefix(`/api`)"
      - "traefik.http.routers.gantry-backend.entrypoints=websecure"
      - "traefik.http.routers.gantry-backend.tls.certresolver=letsencrypt"

      # Strip /api prefix
      - "traefik.http.middlewares.gantry-strip-api.stripprefix.prefixes=/api"
      - "traefik.http.routers.gantry-backend.middlewares=gantry-strip-api"

      # Service
      - "traefik.http.services.gantry-backend.loadbalancer.server.port=8000"

    expose:
      - "8000"

  frontend:
    # ... existing config
    labels:
      - "traefik.enable=true"

      # HTTP router
      - "traefik.http.routers.gantry-frontend.rule=Host(`gantry.example.com`)"
      - "traefik.http.routers.gantry-frontend.entrypoints=websecure"
      - "traefik.http.routers.gantry-frontend.tls.certresolver=letsencrypt"

      # Service
      - "traefik.http.services.gantry-frontend.loadbalancer.server.port=3000"

    expose:
      - "3000"

  # Middleware for redirecting HTTP to HTTPS
  http-redirect:
    image: traefik:v2.11
    command:
      - "--providers.docker=true"
    labels:
      - "traefik.http.routers.http-catchall.rule=hostregexp(`{host:.+}`)"
      - "traefik.http.routers.http-catchall.entrypoints=web"
      - "traefik.http.routers.http-catchall.middlewares=redirect-to-https"
      - "traefik.http.middlewares.redirect-to-https.redirectscheme.scheme=https"

networks:
  nebulus:
    external: true
    name: nebulus-prime_ai-network

volumes:
  traefik_letsencrypt:
    driver: local
```

### Advanced Configuration

#### Rate Limiting

```yaml
# Add to backend service labels
labels:
  - "traefik.http.middlewares.gantry-ratelimit.ratelimit.average=100"
  - "traefik.http.middlewares.gantry-ratelimit.ratelimit.burst=50"
  - "traefik.http.routers.gantry-backend.middlewares=gantry-ratelimit"
```

#### Security Headers

```yaml
# Add to service labels
labels:
  - "traefik.http.middlewares.gantry-headers.headers.stsSeconds=31536000"
  - "traefik.http.middlewares.gantry-headers.headers.stsIncludeSubdomains=true"
  - "traefik.http.middlewares.gantry-headers.headers.frameDeny=true"
  - "traefik.http.middlewares.gantry-headers.headers.contentTypeNosniff=true"
  - "traefik.http.routers.gantry-frontend.middlewares=gantry-headers"
```

#### Load Balancing

Scale backend service:

```bash
docker compose up -d --scale backend=3
```

Traefik automatically distributes traffic.

#### Basic Auth for Dashboard

```bash
# Generate password
htpasswd -nb admin your-secure-password

# Add to traefik service
command:
  - "--api.dashboard=true"
  # Remove insecure flag
labels:
  - "traefik.http.routers.dashboard.rule=Host(`traefik.example.com`)"
  - "traefik.http.routers.dashboard.service=api@internal"
  - "traefik.http.routers.dashboard.middlewares=auth"
  - "traefik.http.middlewares.auth.basicauth.users=admin:$$apr1$$..."
```

---

## Comparison Matrix

| Feature | Nginx | Caddy | Traefik |
|---------|-------|-------|---------|
| **Auto HTTPS** | ❌ (manual) | ✅ Built-in | ✅ Built-in |
| **Configuration** | Complex | Simple | Labels-based |
| **Performance** | Excellent | Very Good | Very Good |
| **Docker Integration** | Manual | Manual | Native |
| **Learning Curve** | Steep | Easy | Medium |
| **Static Files** | Excellent | Good | Good |
| **Load Balancing** | ✅ Advanced | ✅ Good | ✅ Excellent |
| **Maturity** | Very Mature | Mature | Mature |
| **Community** | Huge | Growing | Large |
| **Best For** | Traditional VMs | Simple deployments | Container environments |

---

## Testing Your Setup

### 1. Test HTTP to HTTPS Redirect

```bash
curl -I http://gantry.example.com
# Should return 301 or 308 redirect to HTTPS
```

### 2. Test SSL Certificate

```bash
# Check certificate
openssl s_client -connect gantry.example.com:443 -servername gantry.example.com

# Or use SSL Labs
# https://www.ssllabs.com/ssltest/analyze.html?d=gantry.example.com
```

### 3. Test Backend API

```bash
curl https://gantry.example.com/api/health
# Should return: {"status":"healthy"}
```

### 4. Test Frontend

Open <https://gantry.example.com> in browser - should load login page.

### 5. Test SSE Streaming

```bash
curl -N -H "Cookie: session_id=your-session" \
  https://gantry.example.com/api/chat/stream/your-conversation-id
# Should stream events
```

### 6. Check Headers

```bash
curl -I https://gantry.example.com
# Verify security headers:
# - Strict-Transport-Security
# - X-Frame-Options
# - X-Content-Type-Options
```

---

## Troubleshooting

### SSL Certificate Issues

**Error:** `ERR_CERT_AUTHORITY_INVALID`

- **Fix:** Certificate not trusted. Check:
  - Let's Encrypt renewal status: `sudo certbot renew --dry-run`
  - Certificate paths in config
  - Clock sync on server

**Error:** `ERR_CERT_COMMON_NAME_INVALID`

- **Fix:** Domain mismatch. Ensure certificate matches your domain.

### 502 Bad Gateway

**Cause:** Reverse proxy can't reach backend.

- **Fix:** Check backend is running: `curl http://localhost:8000/health`
- **Fix:** Verify `proxy_pass` URL in config
- **Fix:** Check Docker network connectivity

### 504 Gateway Timeout

**Cause:** Backend not responding in time.

- **Fix:** Increase timeouts:

  ```nginx
  # Nginx
  proxy_read_timeout 300s;
  proxy_connect_timeout 75s;
  ```

  ```caddy
  # Caddy
  reverse_proxy localhost:8000 {
      timeout 300s
  }
  ```

### SSE Streaming Not Working

**Cause:** Buffering enabled.

- **Fix:** Disable buffering:

  ```nginx
  # Nginx
  proxy_buffering off;
  proxy_cache off;
  ```

  ```caddy
  # Caddy
  reverse_proxy localhost:8000 {
      flush_interval -1
  }
  ```

### Rate Limiting Too Aggressive

- **Fix:** Adjust limits in config
- **Fix:** Whitelist trusted IPs

### WebSocket Connection Failed

- **Fix:** Ensure headers are set:

  ```nginx
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection 'upgrade';
  ```

---

## Security Best Practices

### 1. Hide Version Information

```nginx
# Nginx - add to http block
server_tokens off;
```

```caddy
# Caddy - add to site block
header Server ""
```

### 2. Enable OCSP Stapling

```nginx
# Nginx
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/letsencrypt/live/gantry.example.com/chain.pem;
```

Caddy does this automatically.

### 3. Disable Weak SSL Ciphers

```nginx
# Nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
ssl_prefer_server_ciphers off;
```

### 4. Implement IP Whitelisting (Optional)

```nginx
# Nginx - restrict admin panel
location /api/admin/ {
    allow 192.168.1.0/24;  # Internal network
    allow 10.0.0.5;        # VPN IP
    deny all;

    proxy_pass http://localhost:8000/admin/;
}
```

### 5. DDoS Protection

Use Cloudflare or similar CDN for additional protection.

---

## Performance Tuning

### Nginx Worker Processes

```nginx
# /etc/nginx/nginx.conf
worker_processes auto;  # One per CPU core
worker_connections 1024;
```

### Enable HTTP/2

```nginx
listen 443 ssl http2;
```

Already included in basic configs.

### Connection Pooling

```nginx
upstream gantry_backend {
    server localhost:8000;
    keepalive 32;  # Persistent connections
}

location /api/ {
    proxy_pass http://gantry_backend/;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
}
```

### Static Asset Caching

```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    access_log off;
}
```

---

## Next Steps

- **[Production Checklist](Production-Checklist)** - Complete security hardening
- **[Scaling & Performance](Scaling-Performance)** - Optimize for high traffic
- **[Monitoring](Debugging-Guide)** - Set up observability

---

**[← Back to Production Checklist](Production-Checklist)** | **[Next: Scaling & Performance →](Scaling-Performance)**
