#!/bin/bash
# Go-Live Verification Script
# Run this to verify all systems before going live

set -e

echo "=================================================="
echo "  MYCA Go-Live Verification"
echo "=================================================="
echo ""

ERRORS=0
WARNINGS=0

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "  ${GREEN}[PASS]${NC} $1"
}

fail() {
    echo -e "  ${RED}[FAIL]${NC} $1"
    ((ERRORS++))
}

warn() {
    echo -e "  ${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
}

# Phase 1: Infrastructure
echo "Phase 1: Infrastructure"
echo "========================"

# Check VMs
for vm in "192.168.20.10" "192.168.20.11" "192.168.20.12"; do
    if ping -c 1 -W 2 $vm > /dev/null 2>&1; then
        pass "VM $vm is reachable"
    else
        fail "VM $vm is not reachable"
    fi
done

# Check NAS
if ping -c 1 -W 2 192.168.0.1 > /dev/null 2>&1; then
    pass "NAS (192.168.0.1) is reachable"
else
    fail "NAS is not reachable"
fi

echo ""

# Phase 2: Database Services
echo "Phase 2: Database Services"
echo "==========================="

# PostgreSQL
if nc -z 192.168.20.12 5432 2>/dev/null; then
    pass "PostgreSQL (5432) is listening"
else
    fail "PostgreSQL is not accessible"
fi

# Redis
if nc -z 192.168.20.12 6379 2>/dev/null; then
    pass "Redis (6379) is listening"
else
    fail "Redis is not accessible"
fi

# Qdrant
if nc -z 192.168.20.12 6333 2>/dev/null; then
    pass "Qdrant (6333) is listening"
else
    fail "Qdrant is not accessible"
fi

echo ""

# Phase 3: API Services
echo "Phase 3: API Services"
echo "======================"

# MAS API
if curl -sf http://192.168.20.10:8001/health > /dev/null 2>&1; then
    pass "MAS API (8001) is healthy"
else
    fail "MAS API is not responding"
fi

# MINDEX
if curl -sf http://192.168.20.10:8000/health > /dev/null 2>&1; then
    pass "MINDEX (8000) is healthy"
else
    warn "MINDEX may not be running"
fi

# n8n
if curl -sf http://192.168.20.10:5678/healthz > /dev/null 2>&1; then
    pass "n8n (5678) is healthy"
else
    warn "n8n may not be running"
fi

# Dashboard
if curl -sf http://192.168.20.10:3100 > /dev/null 2>&1; then
    pass "Dashboard (3100) is accessible"
else
    warn "Dashboard may not be running"
fi

echo ""

# Phase 4: Website
echo "Phase 4: Website"
echo "================="

# Website internal
if curl -sf http://192.168.20.11:80 > /dev/null 2>&1; then
    pass "Website (internal) is accessible"
else
    fail "Website is not responding internally"
fi

# Website via Cloudflare
if curl -sf https://mycosoft.com > /dev/null 2>&1; then
    pass "https://mycosoft.com is accessible"
else
    fail "Website is not accessible via Cloudflare"
fi

# API via Cloudflare
if curl -sf https://api.mycosoft.com/health > /dev/null 2>&1; then
    pass "https://api.mycosoft.com is accessible"
else
    fail "API is not accessible via Cloudflare"
fi

echo ""

# Phase 5: SSL/Security
echo "Phase 5: SSL/Security"
echo "======================"

# Check SSL certificate
SSL_RESULT=$(echo | openssl s_client -servername mycosoft.com -connect mycosoft.com:443 2>/dev/null | openssl x509 -noout -dates 2>/dev/null)
if [ -n "$SSL_RESULT" ]; then
    pass "SSL certificate is valid"
else
    fail "SSL certificate issue"
fi

# Check security headers
HEADERS=$(curl -sI https://mycosoft.com 2>/dev/null)
if echo "$HEADERS" | grep -qi "x-frame-options"; then
    pass "X-Frame-Options header present"
else
    warn "X-Frame-Options header missing"
fi

if echo "$HEADERS" | grep -qi "x-content-type-options"; then
    pass "X-Content-Type-Options header present"
else
    warn "X-Content-Type-Options header missing"
fi

echo ""

# Phase 6: Monitoring
echo "Phase 6: Monitoring"
echo "===================="

# Prometheus
if curl -sf http://192.168.20.10:9090/-/healthy > /dev/null 2>&1; then
    pass "Prometheus is running"
else
    warn "Prometheus may not be running"
fi

# Grafana
if curl -sf http://192.168.20.10:3002/api/health > /dev/null 2>&1; then
    pass "Grafana is running"
else
    warn "Grafana may not be running"
fi

echo ""

# Phase 7: Backups
echo "Phase 7: Backups"
echo "================="

# Check backup directory
if [ -d "/mnt/mycosoft/backups" ]; then
    BACKUP_COUNT=$(find /mnt/mycosoft/backups -name "*.sql" -o -name "*.rdb" 2>/dev/null | wc -l)
    if [ "$BACKUP_COUNT" -gt 0 ]; then
        pass "Backups exist ($BACKUP_COUNT files)"
    else
        warn "No backup files found"
    fi
else
    warn "Backup directory not accessible from this host"
fi

echo ""

# Summary
echo "=================================================="
echo "  SUMMARY"
echo "=================================================="
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "  ${GREEN}ALL CHECKS PASSED!${NC}"
    echo "  System is ready for go-live."
elif [ $ERRORS -eq 0 ]; then
    echo -e "  ${YELLOW}PASSED WITH WARNINGS${NC}"
    echo "  Errors: 0, Warnings: $WARNINGS"
    echo "  Review warnings before go-live."
else
    echo -e "  ${RED}CHECKS FAILED${NC}"
    echo "  Errors: $ERRORS, Warnings: $WARNINGS"
    echo "  Fix errors before go-live!"
fi

echo ""
echo "=================================================="

exit $ERRORS
