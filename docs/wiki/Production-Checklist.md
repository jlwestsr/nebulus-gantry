# Production Checklist

This comprehensive checklist ensures your Nebulus Gantry deployment is secure, reliable, and production-ready. Follow these steps before exposing your instance to users or the internet.

---

## Security Hardening

### Authentication & Sessions

- [ ] **Change default SECRET_KEY**

  ```bash
  # Generate a cryptographically secure key
  openssl rand -hex 32
  ```

  Update in `.env`:

  ```bash
  SECRET_KEY=your-generated-key-here-32-characters-minimum
  ```

- [ ] **Enforce strong password policy**

  Backend validates passwords with minimum requirements:
  - 8+ characters
  - Mixed case
  - Numbers
  - Special characters

  Consider increasing to 12+ for production.

- [ ] **Set reasonable session timeout**

  ```bash
  # Default: 24 hours
  SESSION_EXPIRE_HOURS=8  # More secure for production
  ```

- [ ] **Enable httponly and secure cookies**

  Check `backend/routers/auth.py`:

  ```python
  response.set_cookie(
      key="session_id",
      value=session_id,
      httponly=True,      # ✅ Prevents XSS
      secure=True,        # ✅ HTTPS only (add this)
      samesite="lax",     # ✅ CSRF protection
      max_age=session_duration
  )
  ```

- [ ] **Disable password autofill**

  Already implemented in frontend forms with `autoComplete="off"`.

### Network Security

- [ ] **Configure firewall rules**

  ```bash
  # Allow only necessary ports
  sudo ufw allow 80/tcp    # HTTP (redirect to HTTPS)
  sudo ufw allow 443/tcp   # HTTPS
  sudo ufw enable

  # Block direct access to backend
  sudo ufw deny 8000/tcp
  ```

- [ ] **Use reverse proxy for SSL termination**

  Never expose backend directly. Always use Nginx/Caddy/Traefik.

  See [Reverse Proxy Setup](Reverse-Proxy-Setup) guide.

- [ ] **Configure CORS properly**

  Update `backend/main.py`:

  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=[
          "https://yourdomain.com",  # Production domain only
      ],
      allow_credentials=True,
      allow_methods=["GET", "POST", "PUT", "DELETE"],
      allow_headers=["*"],
  )
  ```

- [ ] **Set up rate limiting**

  Install and configure `slowapi`:

  ```bash
  pip install slowapi
  ```

  Add to `backend/main.py`:

  ```python
  from slowapi import Limiter, _rate_limit_exceeded_handler
  from slowapi.util import get_remote_address
  from slowapi.errors import RateLimitExceeded

  limiter = Limiter(key_func=get_remote_address)
  app.state.limiter = limiter
  app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

  # Apply to routes:
  @router.post("/chat")
  @limiter.limit("10/minute")
  async def chat_endpoint(...):
      ...
  ```

### Database Security

- [ ] **Move SQLite outside container**

  Mount persistent volume:

  ```yaml
  # docker-compose.yml
  services:
    backend:
      volumes:
        - ./data:/app/data:rw  # Persistent storage
  ```

- [ ] **Set proper file permissions**

  ```bash
  chmod 600 data/gantry.db  # Owner read/write only
  chmod 700 data            # Owner access only
  ```

- [ ] **Consider PostgreSQL for production**

  SQLite is great for single-server deployments but PostgreSQL is recommended for:
  - High concurrency
  - Multi-server setups
  - Better backup tools

  Migration guide:

  ```bash
  # Install PostgreSQL driver
  pip install psycopg2-binary

  # Update .env
  DATABASE_URL=postgresql://user:pass@db-host:5432/gantry
  ```

### Secrets Management

- [ ] **Never commit .env files**

  Verify `.gitignore`:

  ```bash
  # Should contain:
  .env
  .env.*
  !.env.example
  ```

- [ ] **Use environment-specific configs**

  ```bash
  .env.production
  .env.staging
  .env.development
  ```

- [ ] **Rotate secrets regularly**

  - SECRET_KEY: Every 90 days
  - Admin passwords: Every 90 days
  - API keys: Per vendor recommendations

- [ ] **Use secrets manager for sensitive data**

  For cloud deployments, use:
  - AWS Secrets Manager
  - HashiCorp Vault
  - Azure Key Vault
  - Google Secret Manager

### Container Security

- [ ] **Run containers as non-root user**

  Update `Dockerfile.backend`:

  ```dockerfile
  FROM python:3.12-slim

  # Create non-root user
  RUN groupadd -r gantry && useradd -r -g gantry gantry

  # Install deps as root
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt

  # Switch to non-root
  USER gantry

  WORKDIR /app
  COPY --chown=gantry:gantry . .

  CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```

- [ ] **Scan images for vulnerabilities**

  ```bash
  # Using Trivy
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy image nebulus-gantry-backend:latest

  # Using Docker Scout
  docker scout cves nebulus-gantry-backend:latest
  ```

- [ ] **Use minimal base images**

  Already using `python:3.12-slim` and `node:20-alpine` - good baseline.

- [ ] **Pin dependency versions**

  Update `requirements.txt` with exact versions:

  ```txt
  fastapi==0.115.12
  uvicorn==0.34.0
  sqlalchemy==2.0.36
  # etc...
  ```

### API Security

- [ ] **Validate all inputs**

  Already using Pydantic schemas - verify comprehensive coverage.

- [ ] **Implement request size limits**

  Add to `backend/main.py`:

  ```python
  from fastapi.middleware.trustedhost import TrustedHostMiddleware
  from starlette.middleware import Middleware
  from starlette.middleware.base import BaseHTTPMiddleware

  # Limit request body size
  app.add_middleware(
      BaseHTTPMiddleware,
      # Add custom middleware to check content-length
  )
  ```

- [ ] **Enable API authentication on sensitive endpoints**

  Verify all admin routes require authentication:

  ```python
  from backend.dependencies import require_admin

  @router.get("/admin/users", dependencies=[Depends(require_admin)])
  async def list_users(...):
      ...
  ```

- [ ] **Log API access and errors**

  Already implemented - verify logs are being captured.

---

## HTTPS Configuration

### SSL Certificate Options

#### Option 1: Let's Encrypt (Recommended)

**Free, automated, trusted by all browsers.**

Using Certbot:

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal (already enabled by default)
sudo certbot renew --dry-run
```

Using Docker with Caddy (automatic HTTPS):

```yaml
# docker-compose.yml
services:
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - nebulus

volumes:
  caddy_data:
  caddy_config:
```

```caddy
# Caddyfile
yourdomain.com {
    reverse_proxy frontend:3000
    reverse_proxy /api/* backend:8000
}
```

#### Option 2: Self-Signed (Development Only)

```bash
# Generate certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout selfsigned.key -out selfsigned.crt

# Use in Nginx config (see Reverse Proxy Setup)
```

#### Option 3: Commercial Certificate

Purchase from:

- DigiCert
- Sectigo
- GlobalSign

Follow vendor instructions for installation.

### HTTPS Checklist

- [ ] **Certificate obtained and installed**
- [ ] **HTTP to HTTPS redirect configured**
- [ ] **HSTS header enabled**

  ```nginx
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
  ```

- [ ] **TLS 1.2+ only**

  ```nginx
  ssl_protocols TLSv1.2 TLSv1.3;
  ```

- [ ] **Strong cipher suites**

  ```nginx
  ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
  ssl_prefer_server_ciphers off;
  ```

- [ ] **Certificate auto-renewal configured**
- [ ] **Test SSL configuration**

  Use [SSL Labs](https://www.ssllabs.com/ssltest/) - aim for A+ rating.

---

## Backup Strategy

### Database Backups

#### Automated SQLite Backups

```bash
#!/bin/bash
# backup-db.sh

BACKUP_DIR="/backups/gantry"
DATE=$(date +%Y%m%d-%H%M%S)
DB_PATH="./data/gantry.db"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup with timestamp
sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/gantry-$DATE.db'"

# Keep only last 30 days
find "$BACKUP_DIR" -name "gantry-*.db" -mtime +30 -delete

echo "Backup complete: gantry-$DATE.db"
```

Schedule with cron:

```bash
# Backup daily at 2 AM
0 2 * * * /path/to/backup-db.sh >> /var/log/gantry-backup.log 2>&1
```

#### PostgreSQL Backups

```bash
#!/bin/bash
# backup-pg.sh

BACKUP_DIR="/backups/gantry"
DATE=$(date +%Y%m%d-%H%M%S)

pg_dump -h localhost -U gantry_user gantry | gzip > "$BACKUP_DIR/gantry-$DATE.sql.gz"

# Retention: 30 days
find "$BACKUP_DIR" -name "gantry-*.sql.gz" -mtime +30 -delete
```

### Document Storage Backups

```bash
#!/bin/bash
# backup-documents.sh

BACKUP_DIR="/backups/gantry-docs"
DATE=$(date +%Y%m%d-%H%M%S)
DOCS_DIR="./data/documents"

# Tar with compression
tar -czf "$BACKUP_DIR/documents-$DATE.tar.gz" -C "$DOCS_DIR" .

# Retention: 30 days
find "$BACKUP_DIR" -name "documents-*.tar.gz" -mtime +30 -delete
```

### ChromaDB Vector Store Backups

```bash
#!/bin/bash
# backup-chroma.sh

BACKUP_DIR="/backups/chromadb"
DATE=$(date +%Y%m%d-%H%M%S)

# Export collections via API
docker compose exec backend python -c "
from backend.services.memory_service import MemoryService
from backend.database import get_engine, get_session_maker

# Export collections to JSON
# (Implement export functionality in MemoryService)
"

# Or backup entire ChromaDB volume
docker run --rm -v chromadb-data:/data -v "$BACKUP_DIR":/backup \
  alpine tar czf /backup/chromadb-$DATE.tar.gz -C /data .
```

### Backup Checklist

- [ ] **Automated daily backups configured**
- [ ] **Backups stored on separate disk/server**
- [ ] **Backup retention policy implemented**
- [ ] **Backup restoration tested monthly**
- [ ] **Off-site backup copy maintained**
- [ ] **Backup monitoring/alerting configured**

### Backup Restoration Test

```bash
# Test database restoration
cp backups/gantry-20260206-020000.db data/gantry-test.db
DATABASE_URL=sqlite:///./data/gantry-test.db docker compose up backend

# Verify data integrity
docker compose exec backend python -c "
from backend.database import get_engine, get_session_maker
from backend.models import User

engine = get_engine()
Session = get_session_maker(engine)
db = Session()

users = db.query(User).count()
print(f'Restored {users} users successfully')
"
```

---

## Monitoring & Observability

### Application Monitoring

#### Health Check Endpoint

Already implemented at `/health`. Monitor with:

```bash
# Simple uptime monitoring
*/5 * * * * curl -f http://localhost:8000/health || echo "Backend down" | mail -s "Alert" admin@example.com
```

#### Structured Logging

Update `backend/main.py`:

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        return json.dumps(log_obj)

# Configure logging
logging.basicConfig(level=logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("gantry")
logger.addHandler(handler)
```

#### Metrics Collection

Install Prometheus exporter:

```bash
pip install prometheus-fastapi-instrumentator
```

```python
# backend/main.py
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

# Expose metrics at /metrics
Instrumentator().instrument(app).expose(app)
```

### External Monitoring Services

#### Uptime Monitoring

Free options:

- [UptimeRobot](https://uptimerobot.com/) - 50 monitors free
- [Healthchecks.io](https://healthchecks.io/) - Cron job monitoring
- [Cronitor](https://cronitor.io/) - Comprehensive monitoring

#### Application Performance Monitoring (APM)

- **Sentry** - Error tracking

  ```bash
  pip install sentry-sdk[fastapi]
  ```

  ```python
  import sentry_sdk

  sentry_sdk.init(
      dsn="your-sentry-dsn",
      environment="production",
      traces_sample_rate=0.1,
  )
  ```

- **New Relic** - Full-stack monitoring
- **Datadog** - Infrastructure + APM

### Log Management

#### Centralized Logging with Loki

```yaml
# docker-compose.yml
services:
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yaml:/etc/loki/local-config.yaml
      - loki-data:/loki

  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yaml:/etc/promtail/config.yaml
      - /var/lib/docker/containers:/var/lib/docker/containers:ro

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

#### Log Rotation

```bash
# /etc/logrotate.d/gantry
/var/log/gantry/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 gantry gantry
    sharedscripts
    postrotate
        docker compose restart backend
    endscript
}
```

### Monitoring Checklist

- [ ] **Health check endpoint monitored**
- [ ] **Error tracking configured (Sentry)**
- [ ] **Log aggregation setup (Loki/ELK)**
- [ ] **Metrics collection enabled (Prometheus)**
- [ ] **Uptime monitoring service configured**
- [ ] **Alerting rules defined**
- [ ] **Dashboard created (Grafana)**
- [ ] **Log rotation configured**

---

## Performance Optimization

### Backend Optimization

- [ ] **Enable Uvicorn workers**

  ```bash
  # docker-compose.yml
  command: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
  ```

- [ ] **Configure connection pooling**

  ```python
  # backend/database.py
  engine = create_engine(
      DATABASE_URL,
      pool_size=20,
      max_overflow=40,
      pool_pre_ping=True,
  )
  ```

- [ ] **Enable response compression**

  ```python
  from fastapi.middleware.gzip import GZipMiddleware

  app.add_middleware(GZipMiddleware, minimum_size=1000)
  ```

### Frontend Optimization

- [ ] **Enable production build**

  Already configured in `frontend/vite.config.ts`.

- [ ] **Configure CDN for static assets**
- [ ] **Enable browser caching**

  ```nginx
  location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
      expires 1y;
      add_header Cache-Control "public, immutable";
  }
  ```

### Database Optimization

See [Scaling & Performance](Scaling-Performance) guide for detailed tuning.

---

## Deployment Checklist

### Pre-Deployment

- [ ] **All tests passing**

  ```bash
  docker compose exec backend pytest
  ```

- [ ] **Code review completed**
- [ ] **Environment variables set correctly**
- [ ] **Database migrations applied**
- [ ] **Dependencies updated and audited**

  ```bash
  npm audit
  pip list --outdated
  ```

### Deployment Steps

- [ ] **Backup current production database**
- [ ] **Pull latest code**

  ```bash
  git pull origin main
  ```

- [ ] **Rebuild containers**

  ```bash
  docker compose up -d --build
  ```

- [ ] **Verify health checks pass**

  ```bash
  curl http://localhost:8000/health
  ```

- [ ] **Test critical user flows**
  - Login
  - Send chat message
  - Upload document
  - Admin dashboard access

### Post-Deployment

- [ ] **Monitor error rates for 1 hour**
- [ ] **Check application logs**

  ```bash
  docker compose logs -f --tail=100
  ```

- [ ] **Verify monitoring alerts working**
- [ ] **Update status page (if applicable)**

---

## Compliance & Legal

### Data Privacy

- [ ] **Privacy policy displayed**
- [ ] **Terms of service available**
- [ ] **Cookie consent implemented (if required)**
- [ ] **Data retention policy documented**
- [ ] **User data export functionality**

  Already implemented via conversation export.

- [ ] **User data deletion process**

  Admin can delete users via dashboard.

### GDPR Compliance (EU)

- [ ] **Data processing agreement in place**
- [ ] **Right to access implemented**
- [ ] **Right to erasure implemented**
- [ ] **Data breach notification procedure**
- [ ] **Data protection officer assigned (if required)**

### HIPAA Compliance (Healthcare)

If handling health information:

- [ ] **Business associate agreement signed**
- [ ] **Encryption at rest enabled**
- [ ] **Encryption in transit enabled (HTTPS)**
- [ ] **Access audit logs maintained**
- [ ] **Automatic session timeout configured**
- [ ] **Regular security risk assessments**

---

## Disaster Recovery

### Recovery Plan

Document your recovery procedures:

1. **Database corruption**
   - Restore from most recent backup
   - Verify data integrity
   - Resume normal operations

2. **Server failure**
   - Provision new server
   - Restore from backups
   - Update DNS records
   - Verify services

3. **Security breach**
   - Isolate affected systems
   - Rotate all secrets
   - Audit access logs
   - Notify users (if required)

### Recovery Checklist

- [ ] **RTO (Recovery Time Objective) defined**

  How long can you be down? 1 hour? 24 hours?

- [ ] **RPO (Recovery Point Objective) defined**

  How much data loss is acceptable? 15 minutes? 1 day?

- [ ] **Backup restoration procedure documented**
- [ ] **DR runbook created**
- [ ] **Emergency contact list maintained**
- [ ] **DR test conducted annually**

---

## Security Audit

### Regular Security Reviews

- [ ] **Quarterly dependency updates**

  ```bash
  npm audit fix
  pip install --upgrade -r requirements.txt
  ```

- [ ] **Annual penetration testing**
- [ ] **Code security scanning**

  ```bash
  # Using Bandit for Python
  pip install bandit
  bandit -r backend/

  # Using npm audit
  npm audit
  ```

- [ ] **Access control review**

  Audit who has admin access.

### Security Scanning Tools

```bash
# Container scanning
docker scan nebulus-gantry-backend:latest

# Dependency scanning
pip install safety
safety check

# SAST (Static Analysis)
pip install semgrep
semgrep --config=auto backend/
```

---

## Final Production Checklist

Before going live:

- [ ] All security hardening steps completed
- [ ] HTTPS configured with valid certificate
- [ ] Automated backups running and tested
- [ ] Monitoring and alerting configured
- [ ] Performance optimization applied
- [ ] Disaster recovery plan documented
- [ ] Legal compliance requirements met
- [ ] Security audit passed
- [ ] Team trained on operations procedures
- [ ] Runbook and documentation complete

---

## Next Steps

- **[Reverse Proxy Setup](Reverse-Proxy-Setup)** - Configure Nginx/Caddy/Traefik
- **[Scaling & Performance](Scaling-Performance)** - Optimize for production load
- **[Monitoring & Logging](Debugging-Guide)** - Set up observability

---

**[← Back to Docker Deployment](Docker-Deployment)** | **[Next: Reverse Proxy Setup →](Reverse-Proxy-Setup)**
