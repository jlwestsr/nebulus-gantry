# Docker Deployment

Production Docker deployment guide for Nebulus Gantry including compose configuration, networking, volumes, and best practices.

---

## Overview

Docker Compose is the **recommended deployment method** for Gantry in production environments.

**Benefits:**

- Consistent environments (dev, staging, production)
- Easy updates (`docker compose pull && docker compose up -d`)
- Isolated services with proper networking
- Volume persistence for data
- Simple scaling (add more backend workers)

**This guide covers:**

- Production Docker Compose setup
- Network configuration
- Volume management
- Multi-stage builds
- Security hardening
- Health checks and monitoring

---

## Production Docker Compose

### Complete Configuration

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    image: nebulus-gantry-backend:latest
    container_name: gantry-backend
    restart: unless-stopped
    env_file:
      - .env.production
    ports:
      - "127.0.0.1:8000:8000"  # Bind to localhost only
    volumes:
      - ./data:/app/data:rw
      - backend-logs:/app/logs:rw
    networks:
      - nebulus
      - internal
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    command: >
      uvicorn backend.main:app
      --host 0.0.0.0
      --port 8000
      --workers 4
      --log-level info
      --no-access-log
    depends_on:
      - chromadb

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: production
      args:
        VITE_API_URL: ${VITE_API_URL}
    image: nebulus-gantry-frontend:latest
    container_name: gantry-frontend
    restart: unless-stopped
    ports:
      - "127.0.0.1:3001:3000"  # Bind to localhost only
    networks:
      - internal
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    depends_on:
      - backend

  chromadb:
    image: chromadb/chroma:latest
    container_name: gantry-chromadb
    restart: unless-stopped
    ports:
      - "127.0.0.1:8001:8000"
    volumes:
      - chromadb-data:/chroma/chroma:rw
    networks:
      - nebulus
      - internal
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 30s
      timeout: 10s
      retries: 3
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE

networks:
  nebulus:
    external: true
    name: nebulus-prime_ai-network
  internal:
    driver: bridge
    internal: false  # Set to true for isolation

volumes:
  chromadb-data:
    driver: local
  backend-logs:
    driver: local
```

### Key Configuration Choices

**Port binding:**

```yaml
ports:
  - "127.0.0.1:8000:8000"  # Only accessible from localhost
```

**Why:** Never expose backend directly to internet. Use reverse proxy (nginx/Caddy).

**Restart policy:**

```yaml
restart: unless-stopped
```

**Options:**

- `no` - Never restart
- `always` - Always restart
- `on-failure` - Only on error
- `unless-stopped` - Restart except when manually stopped

**Health checks:**

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

**Purpose:** Docker monitors service health, restarts if unhealthy.

---

## Multi-Stage Dockerfiles

### Backend Dockerfile

```dockerfile
# Stage 1: Base
FROM python:3.12-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Development
FROM base as development

ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=development

# Copy code
COPY . .

# Expose port
EXPOSE 8000

# Development command (with reload)
CMD ["uvicorn", "backend.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]

# Stage 3: Production
FROM base as production

ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Create non-root user
RUN useradd -m -u 1000 gantry && \
    mkdir -p /app/data /app/logs && \
    chown -R gantry:gantry /app

# Copy code
COPY --chown=gantry:gantry . .

# Switch to non-root user
USER gantry

# Expose port
EXPOSE 8000

# Production command (multiple workers, no reload)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Frontend Dockerfile

```dockerfile
# Stage 1: Build
FROM node:20-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source
COPY . .

# Build argument for API URL
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Build app
RUN npm run build

# Stage 2: Production
FROM nginx:alpine as production

# Copy built files
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget --quiet --tries=1 --spider http://localhost:3000 || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
```

### Frontend nginx.conf

```nginx
server {
    listen 3000;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    gzip_comp_level 6;
    gzip_min_length 1000;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # No cache for index.html
    location = /index.html {
        add_header Cache-Control "no-cache, must-revalidate";
    }
}
```

---

## Network Configuration

### External Network

**Create network** (if not exists):

```bash
docker network create nebulus-prime_ai-network
```

**Benefits:**

- Connect to external services (TabbyAPI, LM Studio)
- Shared between multiple projects
- Persistent across compose down/up

### Internal Network

**Bridge network** for inter-service communication:

```yaml
networks:
  internal:
    driver: bridge
    internal: false  # true = no external access
```

**Use cases:**

- Backend ↔ ChromaDB communication
- Frontend ↔ Backend communication
- Isolate from internet if `internal: true`

### Network Isolation

**Full isolation** (no internet access):

```yaml
networks:
  internal:
    driver: bridge
    internal: true  # Block external access

services:
  backend:
    networks:
      - nebulus      # External (for TabbyAPI)
      - internal     # Internal (for ChromaDB, Frontend)
```

**Partial isolation:**

```yaml
  frontend:
    networks:
      - internal  # Only internal network
```

Frontend can't reach external services directly.

---

## Volume Management

### Volume Types

**Named volumes** (Docker-managed):

```yaml
volumes:
  chromadb-data:
    driver: local
```

**Bind mounts** (host directory):

```yaml
volumes:
  - ./data:/app/data:rw
```

**tmpfs mounts** (in-memory):

```yaml
volumes:
  - type: tmpfs
    target: /tmp
    tmpfs:
      size: 1G
```

### Data Persistence

**SQLite database:**

```yaml
services:
  backend:
    volumes:
      - ./data:/app/data:rw
```

**ChromaDB vectors:**

```yaml
services:
  chromadb:
    volumes:
      - chromadb-data:/chroma/chroma:rw

volumes:
  chromadb-data:
    driver: local
```

**Backup strategy:**

```bash
# Backup bind mount
tar czf backup-$(date +%Y%m%d).tar.gz ./data

# Backup named volume
docker run --rm \
  -v nebulus-gantry_chromadb-data:/data \
  -v $(pwd):/backup \
  ubuntu tar czf /backup/chromadb-$(date +%Y%m%d).tar.gz /data
```

### Volume Permissions

**Issue:** Permission denied errors

**Fix:** Match container user UID to host user

```dockerfile
# In Dockerfile
RUN useradd -m -u 1000 gantry
USER gantry
```

**On host:**

```bash
# Check your UID
id -u  # Should be 1000

# Fix permissions
sudo chown -R $(id -u):$(id -g) ./data
```

---

## Environment Variables

### Production `.env`

```bash
# Database
DATABASE_URL=postgresql://gantry:secure-password@postgres:5432/gantry

# External Services
CHROMA_HOST=http://chromadb:8000
TABBY_HOST=http://tabbyapi:5000

# Security
SECRET_KEY=<generated-with-openssl-rand-hex-32>
SESSION_EXPIRE_HOURS=8

# Frontend (build-time)
VITE_API_URL=https://yourdomain.com/api

# Logging
LOG_LEVEL=info
ACCESS_LOG_ENABLED=false

# Workers
UVICORN_WORKERS=4
```

### Environment File Loading

```bash
# Development
docker compose --env-file .env up

# Production
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
```

### Secrets Management

**Don't commit `.env.production`** to git!

**Use Docker secrets** (Swarm mode):

```yaml
secrets:
  db_password:
    external: true

services:
  backend:
    secrets:
      - db_password
    environment:
      DATABASE_PASSWORD_FILE: /run/secrets/db_password
```

**Or use external secrets manager:**

- AWS Secrets Manager
- HashiCorp Vault
- Kubernetes Secrets

---

## Scaling

### Horizontal Scaling (Multiple Backends)

```yaml
services:
  backend:
    deploy:
      replicas: 3
    # OR scale manually:
    # docker compose up -d --scale backend=3
```

**Add load balancer** (nginx):

```nginx
upstream backend {
    server localhost:8001;
    server localhost:8002;
    server localhost:8003;
}

server {
    listen 80;
    location /api {
        proxy_pass http://backend;
    }
}
```

### Vertical Scaling (Resource Limits)

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

**Benefits:**

- Prevent resource exhaustion
- Fair sharing in multi-tenant environments
- Predictable performance

---

## Monitoring

### Health Checks

**Check service health:**

```bash
docker compose ps

# Expected output:
# NAME              STATUS              HEALTH
# gantry-backend    Up 2 hours          healthy
# gantry-frontend   Up 2 hours          healthy
# gantry-chromadb   Up 2 hours          healthy
```

**Unhealthy service:**

- Docker auto-restarts
- Check logs: `docker compose logs backend`

### Logging

**View logs:**

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend

# Last 100 lines
docker compose logs --tail=100 backend

# Since timestamp
docker compose logs --since 2026-02-06T10:00:00 backend
```

**Log rotation:**

```yaml
services:
  backend:
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

**Centralized logging:**

```yaml
services:
  backend:
    logging:
      driver: syslog
      options:
        syslog-address: "tcp://logs.example.com:514"
        tag: "gantry-backend"
```

### Metrics (Future)

**Prometheus + Grafana** (planned):

```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
```

---

## Updates & Maintenance

### Update Process

```bash
# 1. Pull latest code
git pull origin main

# 2. Pull latest images
docker compose pull

# 3. Rebuild and restart
docker compose up -d --build

# 4. Check health
docker compose ps
docker compose logs -f
```

### Rolling Updates

**Zero-downtime updates:**

```bash
# 1. Scale up with new version
docker compose up -d --scale backend=4 --no-recreate

# 2. Wait for new containers to be healthy
sleep 30

# 3. Scale down old containers
docker compose up -d --scale backend=2

# 4. Finally, use only new version
docker compose up -d
```

### Rollback

```bash
# 1. Check available images
docker images nebulus-gantry-backend

# 2. Tag old version
docker tag nebulus-gantry-backend:v1.2.0 nebulus-gantry-backend:latest

# 3. Restart with old image
docker compose up -d
```

### Database Migrations

**Before updating:**

```bash
# 1. Backup database
cp data/gantry.db data/gantry.db.backup

# 2. Test migration (dry run)
docker compose run --rm backend alembic upgrade head --sql

# 3. Apply migration
docker compose run --rm backend alembic upgrade head

# 4. Restart services
docker compose restart backend
```

---

## Security Hardening

### Container Security

**Run as non-root:**

```dockerfile
RUN useradd -m -u 1000 gantry
USER gantry
```

**Read-only root filesystem:**

```yaml
services:
  backend:
    read_only: true
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=100m
```

**Drop capabilities:**

```yaml
services:
  backend:
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
```

**Security scanning:**

```bash
# Scan images for vulnerabilities
docker scan nebulus-gantry-backend:latest
```

### Network Security

**Restrict ports:**

```yaml
ports:
  - "127.0.0.1:8000:8000"  # Only localhost
```

**Internal networks:**

```yaml
networks:
  internal:
    driver: bridge
    internal: true  # No internet access
```

**Firewall rules:**

```bash
# UFW (Ubuntu)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 8000/tcp  # Block direct backend access
sudo ufw deny 3001/tcp  # Block direct frontend access
```

---

## Troubleshooting

### Container Won't Start

**Check logs:**

```bash
docker compose logs backend
```

**Common issues:**

- Port already in use
- Missing environment variables
- Volume permission errors
- Network conflicts

**Fix:**

```bash
# Kill conflicting processes
sudo lsof -ti:8000 | xargs kill -9

# Recreate network
docker network rm nebulus-prime_ai-network
docker network create nebulus-prime_ai-network

# Fix permissions
sudo chown -R $(id -u):$(id -g) ./data
```

### Unhealthy Status

**Check health:**

```bash
docker inspect gantry-backend | jq '.[0].State.Health'
```

**Common causes:**

- Service not fully started (wait longer)
- Health check URL wrong
- Dependency not available (ChromaDB, database)

**Fix:**

```bash
# Increase start_period
healthcheck:
  start_period: 60s  # Give more time

# Check dependencies
curl http://localhost:8001/api/v1/heartbeat  # ChromaDB
```

### Network Issues

**Can't connect to TabbyAPI:**

```bash
# Check network connectivity
docker compose exec backend ping tabbyapi

# Check network membership
docker network inspect nebulus-prime_ai-network
```

**Fix:**

```bash
# Reconnect to network
docker network connect nebulus-prime_ai-network gantry-backend
```

### Volume Issues

**Data not persisting:**

```bash
# Check volume exists
docker volume ls | grep chroma

# Inspect volume
docker volume inspect nebulus-gantry_chromadb-data
```

**Fix:**

```bash
# Remove orphan volumes
docker volume prune

# Recreate volume
docker volume rm nebulus-gantry_chromadb-data
docker compose up -d
```

---

## Best Practices

**1. Use multi-stage builds** - Smaller images, faster deploys

**2. Pin image versions:**

```yaml
services:
  chromadb:
    image: chromadb/chroma:0.4.22  # Not :latest
```

**3. Health checks everywhere** - Early detection of issues

**4. Resource limits** - Prevent resource exhaustion

**5. Log rotation** - Prevent disk fills

**6. Regular backups** - Automated daily backups

**7. Monitoring** - Prometheus + Grafana for metrics

**8. Security scanning** - Regular vulnerability scans

**9. Secrets management** - Never commit secrets

**10. Documentation** - Keep deployment docs updated

---

## Next Steps

- **[Production Checklist](Production-Checklist)** - Security hardening checklist
- **[Reverse Proxy Setup](Reverse-Proxy-Setup)** - HTTPS with nginx/Caddy
- **[Scaling & Performance](Scaling-Performance)** - Optimization guide

---

**[← Back to Home](Home)** | **[Production Checklist →](Production-Checklist)**
