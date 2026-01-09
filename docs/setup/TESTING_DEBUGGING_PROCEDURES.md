# Testing and Debugging Procedures

> **Version**: 1.0.0  
> **Last Updated**: January 2026  
> **Purpose**: Pre-launch testing and debugging for MYCA infrastructure

This document outlines testing and debugging procedures for the MYCA system before and after public launch. It covers local testing, staging validation, API verification, and common troubleshooting procedures.

---

## Table of Contents

1. [Testing Overview](#testing-overview)
2. [Local Testing](#local-testing)
3. [Cloudflare Tunnel Testing](#cloudflare-tunnel-testing)
4. [API Endpoint Verification](#api-endpoint-verification)
5. [Authentication Flow Testing](#authentication-flow-testing)
6. [Load Testing](#load-testing)
7. [Log Analysis](#log-analysis)
8. [Debug Mode Configuration](#debug-mode-configuration)
9. [Monitoring Dashboards](#monitoring-dashboards)
10. [Common Issues and Solutions](#common-issues-and-solutions)
11. [Pre-Launch Testing Checklist](#pre-launch-testing-checklist)

---

## Testing Overview

### Testing Phases

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TESTING PIPELINE                                 │
│                                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────┐ │
│  │   LOCAL     │───▶│  STAGING    │───▶│ PRE-LAUNCH  │───▶│  PROD    │ │
│  │   TESTING   │    │  TESTING    │    │  TESTING    │    │ MONITOR  │ │
│  └─────────────┘    └─────────────┘    └─────────────┘    └──────────┘ │
│                                                                          │
│  - Unit tests       - Tunnel test     - Security scan   - Real users   │
│  - Integration      - Public access   - Load test       - Analytics    │
│  - API tests        - SSL verify      - Failover test   - Alerts       │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Testing Environment Matrix

| Environment | URL | Purpose |
|-------------|-----|---------|
| Local (mycocomp) | http://localhost:3000 | Development testing |
| Staging | https://staging.mycosoft.com | Pre-production validation |
| Production | https://mycosoft.com | Live system |

---

## Local Testing

### Step 1: Start Local Services

```powershell
# On mycocomp
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas

# Start all services
docker compose up -d

# Verify running
docker compose ps
```

### Step 2: Website Testing

```powershell
# Open browser
Start-Process "http://localhost:3000"

# Or use curl for headless testing
curl http://localhost:3000
curl http://localhost:3000/api/health
```

**Website Test Cases:**

| Test | URL | Expected |
|------|-----|----------|
| Home page loads | / | 200 OK, renders content |
| Static assets | /_next/static/* | 200 OK, correct MIME type |
| API routes | /api/* | Appropriate response |
| 404 handling | /nonexistent | Custom 404 page |

### Step 3: API Testing

```powershell
# Health check
curl http://localhost:8001/health

# List agents
curl http://localhost:8001/agents

# Test with authentication
$token = "your-jwt-token"
curl -H "Authorization: Bearer $token" http://localhost:8001/agents/run
```

**API Test Cases:**

| Endpoint | Method | Expected |
|----------|--------|----------|
| /health | GET | {"status": "healthy"} |
| /agents | GET | List of agents |
| /agents/{id} | GET | Agent details |
| /agents/run | POST | Execution result |

### Step 4: Database Testing

```powershell
# PostgreSQL
docker exec mas-postgres psql -U mas -c "SELECT 1;"

# Redis
docker exec mas-redis redis-cli PING

# Qdrant
curl http://localhost:6345/collections
```

### Step 5: Integration Testing

```powershell
# Run integration test suite
python -m pytest tests/integration/ -v

# Or run specific tests
python -m pytest tests/integration/test_api.py -v
```

---

## Cloudflare Tunnel Testing

### Pre-Tunnel Checks

Before exposing to the internet:

1. **Verify local services running**
   ```bash
   curl http://localhost:3000  # Website
   curl http://localhost:8001/health  # API
   ```

2. **Check cloudflared configuration**
   ```bash
   cloudflared tunnel ingress validate /etc/cloudflared/config.yml
   ```

### Testing Tunnel Connection

```bash
# Start tunnel in foreground for debugging
cloudflared tunnel run mycosoft-tunnel

# In another terminal, watch logs
tail -f /var/log/cloudflared/cloudflared.log

# Or with systemd
sudo journalctl -u cloudflared -f
```

### External Access Testing

From a different network (e.g., mobile phone on cellular):

```bash
# Test website
curl -I https://mycosoft.com

# Test API
curl https://api.mycosoft.com/health

# Test with verbose output
curl -v https://mycosoft.com
```

### SSL/TLS Verification

```bash
# Check certificate
openssl s_client -connect mycosoft.com:443 -servername mycosoft.com

# Check SSL grade
# Use: https://www.ssllabs.com/ssltest/analyze.html?d=mycosoft.com

# Verify HSTS
curl -I https://mycosoft.com | grep -i strict-transport
```

### Tunnel Status Commands

```bash
# List all tunnels
cloudflared tunnel list

# Get tunnel info
cloudflared tunnel info mycosoft-tunnel

# Check connections
cloudflared tunnel connections mycosoft-tunnel
```

---

## API Endpoint Verification

### Systematic API Testing

Create a test script for all endpoints:

```python
#!/usr/bin/env python3
"""API Endpoint Verification Script"""

import requests
import sys

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"

endpoints = [
    ("GET", "/health", None, 200),
    ("GET", "/agents", None, 200),
    ("GET", "/agents/status", None, 200),
    ("GET", "/config", None, 200),
    ("POST", "/agents/run", {"agent_id": "test"}, [200, 202]),
]

def test_endpoint(method, path, data, expected_status):
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        
        status = response.status_code
        expected = expected_status if isinstance(expected_status, list) else [expected_status]
        
        if status in expected:
            print(f"[OK] {method} {path} -> {status}")
            return True
        else:
            print(f"[FAIL] {method} {path} -> {status} (expected {expected})")
            return False
    except Exception as e:
        print(f"[ERROR] {method} {path} -> {e}")
        return False

def main():
    print(f"Testing API at: {BASE_URL}\n")
    passed = 0
    failed = 0
    
    for method, path, data, expected in endpoints:
        if test_endpoint(method, path, data, expected):
            passed += 1
        else:
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
```

Run the script:

```bash
# Local testing
python test_api.py http://localhost:8001

# Production testing
python test_api.py https://api.mycosoft.com
```

### Response Validation

```python
# Test response content, not just status
def test_health_endpoint():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
    assert "version" in data
    assert "uptime" in data
```

### Rate Limiting Verification

```bash
# Test rate limiting (should get 429 after exceeding limit)
for i in {1..100}; do
    curl -s -o /dev/null -w "%{http_code}\n" https://api.mycosoft.com/health
done | sort | uniq -c
```

---

## Authentication Flow Testing

### JWT Token Flow

```python
# Test authentication flow

# 1. Login to get token
response = requests.post(f"{BASE_URL}/auth/login", json={
    "username": "test",
    "password": "test123"
})
token = response.json()["access_token"]

# 2. Use token for protected endpoint
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(f"{BASE_URL}/agents", headers=headers)
assert response.status_code == 200

# 3. Test with expired/invalid token
headers = {"Authorization": "Bearer invalid_token"}
response = requests.get(f"{BASE_URL}/agents", headers=headers)
assert response.status_code == 401
```

### Permission Testing

```python
# Test role-based access

# Admin user should access admin endpoints
admin_token = get_token("admin", "admin_pass")
response = requests.get(f"{BASE_URL}/admin/users", 
                       headers={"Authorization": f"Bearer {admin_token}"})
assert response.status_code == 200

# Regular user should be denied
user_token = get_token("user", "user_pass")
response = requests.get(f"{BASE_URL}/admin/users", 
                       headers={"Authorization": f"Bearer {user_token}"})
assert response.status_code == 403
```

---

## Load Testing

### Using hey (Go-based)

```bash
# Install hey
go install github.com/rakyll/hey@latest

# Basic load test
hey -n 1000 -c 50 https://mycosoft.com

# API load test with longer timeout
hey -n 500 -c 20 -t 60 https://api.mycosoft.com/health

# Test with authentication
hey -n 500 -c 20 \
    -H "Authorization: Bearer $TOKEN" \
    https://api.mycosoft.com/agents
```

### Using Apache Bench

```bash
# Simple load test
ab -n 1000 -c 50 https://mycosoft.com/

# With keep-alive
ab -n 1000 -c 50 -k https://mycosoft.com/
```

### Load Test Interpretation

| Metric | Acceptable | Warning | Critical |
|--------|------------|---------|----------|
| Avg response time | < 200ms | 200-500ms | > 500ms |
| 99th percentile | < 1000ms | 1-3s | > 3s |
| Error rate | < 0.1% | 0.1-1% | > 1% |
| Requests/sec | > 100 | 50-100 | < 50 |

### Example Output Analysis

```
Summary:
  Total:        10.0234 secs
  Slowest:      1.2340 secs
  Fastest:      0.0123 secs
  Average:      0.1234 secs
  Requests/sec: 99.7654
  
Response time histogram:
  0.012 [1]     |
  0.134 [850]   |########################################
  0.256 [100]   |####
  0.378 [30]    |#
  0.500 [15]    |
  0.622 [3]     |
  0.744 [1]     |

Status code distribution:
  [200] 997 responses
  [429] 3 responses  <- Rate limiting working
```

---

## Log Analysis

### Log Locations

| Service | Log Location |
|---------|-------------|
| MYCA API | docker logs mas-api |
| Website | docker logs mas-website |
| PostgreSQL | docker logs mas-postgres |
| Redis | docker logs mas-redis |
| Nginx | /var/log/nginx/*.log |
| cloudflared | journalctl -u cloudflared |
| System | /var/log/syslog |

### Real-Time Log Monitoring

```bash
# Follow all MYCA logs
docker compose logs -f

# Follow specific service
docker compose logs -f mas-api

# Filter for errors
docker compose logs -f | grep -i error

# Combine with timestamp
docker compose logs -f --timestamps
```

### Log Analysis with Loki

```bash
# Query Loki via Grafana or logcli

# Install logcli
curl -O https://github.com/grafana/loki/releases/download/v2.9.0/logcli-linux-amd64.zip

# Query recent errors
logcli query '{job="myca-api"} |= "error"' --limit=100

# Query by time range
logcli query '{job="myca-api"}' --from="2026-01-09T00:00:00Z" --to="2026-01-09T23:59:59Z"
```

### Common Log Patterns to Watch

```bash
# Authentication failures
grep -i "authentication failed\|unauthorized\|401" logs/*.log

# Database errors
grep -i "connection refused\|timeout\|deadlock" logs/*.log

# Rate limiting
grep -i "rate limit\|429\|too many requests" logs/*.log

# Memory issues
grep -i "out of memory\|oom\|killed" logs/*.log
```

---

## Debug Mode Configuration

### Enabling Debug Mode

**Development (mycocomp):**

```bash
# In .env
DEBUG_MODE=true
LOG_LEVEL=DEBUG
ENABLE_DEBUG_ENDPOINTS=true
```

**Production (temporarily for debugging):**

```bash
# SSH to production
ssh myca@192.168.20.10

# Enable debug temporarily
export DEBUG_MODE=true
docker compose restart mas-api

# After debugging, disable
export DEBUG_MODE=false
docker compose restart mas-api
```

### Debug Endpoints

When debug mode is enabled:

| Endpoint | Purpose |
|----------|---------|
| /debug/config | View current configuration |
| /debug/routes | List all registered routes |
| /debug/db | Database connection status |
| /debug/cache | Cache statistics |
| /debug/agents | Agent state dump |

**Warning**: Never enable debug endpoints in production facing the public internet!

### Adding Debug Output

```python
# In application code
import logging

logger = logging.getLogger(__name__)

def process_request(request):
    logger.debug(f"Processing request: {request.id}")
    logger.debug(f"Request headers: {request.headers}")
    
    try:
        result = do_something(request)
        logger.debug(f"Result: {result}")
        return result
    except Exception as e:
        logger.exception(f"Error processing request {request.id}")
        raise
```

---

## Monitoring Dashboards

### Grafana Dashboards

Access Grafana at http://localhost:3002 (development) or internal production URL.

**Key Dashboards:**

1. **MYCA Overview**
   - Service health status
   - Request rates
   - Error rates
   - Response times

2. **Infrastructure**
   - CPU/Memory usage
   - Disk I/O
   - Network traffic
   - Container stats

3. **Database**
   - PostgreSQL metrics
   - Connection pool status
   - Query performance
   - Redis memory

4. **Agents**
   - Agent execution count
   - Agent success/failure rates
   - Execution duration
   - Queue depth

### Prometheus Queries

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Response time (95th percentile)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Container memory usage
container_memory_usage_bytes{name=~"mas-.*"}

# PostgreSQL connections
pg_stat_activity_count{datname="mas"}
```

### Alert Configuration

```yaml
# alertmanager.yml
groups:
  - name: myca-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High error rate detected
          
      - alert: ServiceDown
        expr: up{job="myca-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: MYCA API is down
          
      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes{name=~"mas-.*"} > 1e9
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: High memory usage in container
```

---

## Common Issues and Solutions

### Issue: Website Returns 502 Bad Gateway

**Symptoms:**
- Browser shows 502 error
- Nginx logs show "upstream connect failed"

**Solutions:**

```bash
# 1. Check if upstream service is running
docker ps | grep website
curl http://localhost:3000

# 2. Check nginx config
sudo nginx -t

# 3. Check port binding
netstat -tlnp | grep 3000

# 4. Restart services
docker compose restart mas-website
sudo systemctl reload nginx
```

### Issue: API Returns 500 Internal Server Error

**Symptoms:**
- All API calls return 500
- Error in logs about database

**Solutions:**

```bash
# 1. Check API logs
docker logs mas-api --tail 100

# 2. Verify database connection
docker exec mas-api python -c "from mycosoft_mas.core.db import engine; engine.connect()"

# 3. Check database status
docker logs mas-postgres --tail 100

# 4. Verify environment variables
docker exec mas-api env | grep DATABASE

# 5. Restart API
docker compose restart mas-api
```

### Issue: Cloudflare Tunnel Not Connecting

**Symptoms:**
- External access not working
- cloudflared shows connection errors

**Solutions:**

```bash
# 1. Check cloudflared status
sudo systemctl status cloudflared

# 2. Verify tunnel config
cloudflared tunnel ingress validate /etc/cloudflared/config.yml

# 3. Check credentials
ls -la /etc/cloudflared/credentials.json

# 4. Test local connectivity
curl http://localhost:3000

# 5. Restart cloudflared
sudo systemctl restart cloudflared
sudo journalctl -u cloudflared -f
```

### Issue: Slow Response Times

**Symptoms:**
- Requests taking > 1 second
- Users complaining about slowness

**Solutions:**

```bash
# 1. Check resource usage
docker stats

# 2. Check database queries
docker exec mas-postgres psql -U mas -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# 3. Check for memory pressure
free -m

# 4. Check disk I/O
iostat -x 1

# 5. Scale up resources if needed
# In docker-compose.yml, increase memory/CPU limits
```

### Issue: Authentication Failures

**Symptoms:**
- Login fails with 401
- Token rejected

**Solutions:**

```bash
# 1. Verify JWT secret is set
docker exec mas-api env | grep JWT_SECRET

# 2. Check token expiration
# Decode token at jwt.io

# 3. Verify user exists
docker exec mas-postgres psql -U mas -c "SELECT * FROM users WHERE username = 'test';"

# 4. Check clock synchronization (JWT depends on time)
timedatectl

# 5. Regenerate JWT secret if compromised
# Update in Vault and restart API
```

### Issue: Database Connection Pool Exhausted

**Symptoms:**
- "too many connections" error
- Intermittent database failures

**Solutions:**

```bash
# 1. Check current connections
docker exec mas-postgres psql -U mas -c "SELECT count(*) FROM pg_stat_activity;"

# 2. Identify connection leaks
docker exec mas-postgres psql -U mas -c "SELECT client_addr, state, query FROM pg_stat_activity;"

# 3. Increase max connections
# In postgresql.conf: max_connections = 200

# 4. Configure connection pooling
# Use PgBouncer or SQLAlchemy pool settings
```

---

## Pre-Launch Testing Checklist

### Functional Testing

- [ ] Home page loads correctly
- [ ] All navigation links work
- [ ] Forms submit successfully
- [ ] Authentication works
- [ ] API endpoints respond correctly
- [ ] Database queries return data
- [ ] File uploads work
- [ ] Search functionality works

### Security Testing

- [ ] SSL certificate valid and Grade A+
- [ ] Security headers present
- [ ] No sensitive data in responses
- [ ] Rate limiting active
- [ ] Authentication required for protected routes
- [ ] CORS configured correctly
- [ ] No debug endpoints exposed

### Performance Testing

- [ ] Response time < 500ms for pages
- [ ] API response time < 200ms
- [ ] Load test passed (100+ concurrent users)
- [ ] No memory leaks detected
- [ ] Database queries optimized

### Infrastructure Testing

- [ ] All services start on boot
- [ ] Health checks passing
- [ ] Backups scheduled and tested
- [ ] Monitoring alerts configured
- [ ] Failover procedures tested

### External Access Testing

- [ ] Cloudflare tunnel active
- [ ] All subdomains resolving
- [ ] Mobile access working
- [ ] Different browsers tested
- [ ] Different geographic locations tested

### Documentation

- [ ] Runbooks updated
- [ ] API documentation current
- [ ] Incident response plan ready
- [ ] Contact list updated

---

## Testing Report Template

```markdown
# Testing Report - [Date]

## Summary
- **Environment**: [Development/Staging/Production]
- **Tested By**: [Name]
- **Duration**: [Start - End time]
- **Overall Status**: [Pass/Fail]

## Test Results

### Functional Tests
| Test | Status | Notes |
|------|--------|-------|
| | | |

### Security Tests
| Test | Status | Notes |
|------|--------|-------|
| | | |

### Performance Tests
| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| | | | |

## Issues Found
1. **Issue**: 
   **Severity**: 
   **Status**: 
   **Resolution**: 

## Recommendations
1. 

## Sign-off
- [ ] Ready for launch
- [ ] Needs fixes before launch
```

---

## Related Documents

- [MASTER_SETUP_GUIDE.md](./MASTER_SETUP_GUIDE.md) - Overall architecture
- [DOMAIN_CLOUDFLARE_SETUP.md](./DOMAIN_CLOUDFLARE_SETUP.md) - Cloudflare configuration
- [SECURITY_HARDENING_GUIDE.md](./SECURITY_HARDENING_GUIDE.md) - Security testing
- [MIGRATION_CHECKLIST.md](./MIGRATION_CHECKLIST.md) - Migration procedures

---

*Document maintained by MYCA Infrastructure Team*
