# Mycosoft SOC - Comprehensive Test Suite

**Version:** 2.0.0  
**Last Updated:** January 18, 2026  
**Environments:** Development (localhost), Sandbox (sandbox.mycosoft.com)

---

## Table of Contents

1. [Test Overview](#test-overview)
2. [Pre-Test Setup](#pre-test-setup)
3. [Unit Tests](#unit-tests)
4. [Integration Tests](#integration-tests)
5. [End-to-End Tests](#end-to-end-tests)
6. [API Tests](#api-tests)
7. [UI Tests](#ui-tests)
8. [Security Tests](#security-tests)
9. [Performance Tests](#performance-tests)
10. [Environment-Specific Tests](#environment-specific-tests)
11. [Test Execution Scripts](#test-execution-scripts)
12. [Test Results Template](#test-results-template)

---

## Test Overview

### Test Categories

| Category | Purpose | Frequency |
|----------|---------|-----------|
| Unit | Individual function testing | Every commit |
| Integration | Component interaction | Every PR |
| E2E | Full user workflows | Daily |
| API | Endpoint validation | Every deployment |
| UI | Visual/functional | Every release |
| Security | Vulnerability detection | Weekly |
| Performance | Load/stress testing | Weekly |

### Test Coverage Goals

| Component | Target Coverage |
|-----------|-----------------|
| API Routes | 80% |
| UI Components | 70% |
| Security Libraries | 90% |
| Integration Points | 85% |

---

## Pre-Test Setup

### Development Environment

```powershell
# 1. Navigate to project
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website

# 2. Install dependencies
npm install

# 3. Verify environment
cat .env.local | Select-String "UNIFI"

# 4. Start development server
npm run dev

# 5. Note the port (usually 3000-3004)
# Check terminal output for actual port
```

### Sandbox Environment

```bash
# 1. Verify sandbox is accessible
curl -I https://sandbox.mycosoft.com/security

# 2. Check SSL certificate
openssl s_client -connect sandbox.mycosoft.com:443 -servername sandbox.mycosoft.com

# 3. Verify API endpoints
curl https://sandbox.mycosoft.com/api/security?action=status
```

### Test Data Setup

```json
// Test IP addresses
{
  "safe_us_ip": "8.8.8.8",
  "safe_us_ip_2": "1.1.1.1",
  "high_risk_cn_ip": "223.5.5.5",
  "high_risk_ru_ip": "77.88.8.8",
  "tor_exit_example": "185.220.101.1",
  "private_ip": "192.168.0.100",
  "invalid_ip": "999.999.999.999"
}
```

---

## Unit Tests

### UT-001: Threat Level Calculation

**File:** `lib/security/threat-intel.ts`

| Test ID | Description | Input | Expected Output | Status |
|---------|-------------|-------|-----------------|--------|
| UT-001-1 | Score 0 returns safe | `score: 0` | `threatLevel: 'safe'` | ☐ |
| UT-001-2 | Score 15 returns low | `score: 15` | `threatLevel: 'low'` | ☐ |
| UT-001-3 | Score 35 returns medium | `score: 35` | `threatLevel: 'medium'` | ☐ |
| UT-001-4 | Score 65 returns high | `score: 65` | `threatLevel: 'high'` | ☐ |
| UT-001-5 | Score 95 returns critical | `score: 95` | `threatLevel: 'critical'` | ☐ |

**Test Code:**
```typescript
// __tests__/threat-intel.test.ts
import { calculateThreatLevel } from '@/lib/security/threat-intel';

describe('calculateThreatLevel', () => {
  it('should return safe for score 0', () => {
    expect(calculateThreatLevel(0)).toBe('safe');
  });
  
  it('should return low for score 1-20', () => {
    expect(calculateThreatLevel(15)).toBe('low');
  });
  
  it('should return medium for score 21-50', () => {
    expect(calculateThreatLevel(35)).toBe('medium');
  });
  
  it('should return high for score 51-80', () => {
    expect(calculateThreatLevel(65)).toBe('high');
  });
  
  it('should return critical for score 81+', () => {
    expect(calculateThreatLevel(95)).toBe('critical');
  });
});
```

---

### UT-002: High-Risk Country Detection

| Test ID | Description | Input | Expected Output | Status |
|---------|-------------|-------|-----------------|--------|
| UT-002-1 | CN is high risk | `'CN'` | `true` | ☐ |
| UT-002-2 | RU is high risk | `'RU'` | `true` | ☐ |
| UT-002-3 | US is not high risk | `'US'` | `false` | ☐ |
| UT-002-4 | Case insensitive | `'cn'` | `true` | ☐ |

---

### UT-003: Playbook Trigger Matching

| Test ID | Description | Input | Expected Output | Status |
|---------|-------------|-------|-----------------|--------|
| UT-003-1 | Brute force matches | Event type: brute_force | Playbook: RB-001 | ☐ |
| UT-003-2 | Port scan matches | Event type: port_scan | Playbook: RB-004 | ☐ |
| UT-003-3 | No match returns null | Event type: info | null | ☐ |

---

## Integration Tests

### IT-001: UniFi API Integration

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| IT-001-1 | Dashboard data loads | Call `/api/unifi?action=dashboard` | Returns WAN, clients, devices | ☐ |
| IT-001-2 | Devices list loads | Call `/api/unifi?action=devices` | Returns array of devices | ☐ |
| IT-001-3 | Clients list loads | Call `/api/unifi?action=clients` | Returns array of clients | ☐ |
| IT-001-4 | Traffic stats load | Call `/api/unifi?action=traffic` | Returns traffic data | ☐ |
| IT-001-5 | Alarms list loads | Call `/api/unifi?action=alarms` | Returns array of alarms | ☐ |
| IT-001-6 | Invalid action handled | Call `/api/unifi?action=invalid` | Returns error gracefully | ☐ |

**Test Script:**
```bash
#!/bin/bash
# test-unifi-integration.sh

BASE_URL="${1:-http://localhost:3000}"

echo "Testing UniFi Integration..."

# Test dashboard
echo -n "Dashboard: "
RESP=$(curl -s "$BASE_URL/api/unifi?action=dashboard")
if echo "$RESP" | jq -e '.wan' > /dev/null 2>&1; then
  echo "✅ PASS"
else
  echo "❌ FAIL"
fi

# Test devices
echo -n "Devices: "
RESP=$(curl -s "$BASE_URL/api/unifi?action=devices")
if echo "$RESP" | jq -e '.devices' > /dev/null 2>&1; then
  echo "✅ PASS"
else
  echo "❌ FAIL"
fi

# Test clients
echo -n "Clients: "
RESP=$(curl -s "$BASE_URL/api/unifi?action=clients")
if echo "$RESP" | jq -e '.clients' > /dev/null 2>&1; then
  echo "✅ PASS"
else
  echo "❌ FAIL"
fi

# Test alarms
echo -n "Alarms: "
RESP=$(curl -s "$BASE_URL/api/unifi?action=alarms")
if echo "$RESP" | jq -e '.alarms' > /dev/null 2>&1; then
  echo "✅ PASS"
else
  echo "❌ FAIL"
fi

echo "Integration tests complete."
```

---

### IT-002: Security API Integration

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| IT-002-1 | Status endpoint | GET /api/security?action=status | Returns status object | ☐ |
| IT-002-2 | Users endpoint | GET /api/security?action=users | Returns 5 authorized users | ☐ |
| IT-002-3 | Events endpoint | GET /api/security?action=events | Returns events array | ☐ |
| IT-002-4 | Geo-lookup US IP | GET /api/security?action=geo-lookup&ip=8.8.8.8 | Returns US, allowed | ☐ |
| IT-002-5 | Geo-lookup CN IP | GET /api/security?action=geo-lookup&ip=223.5.5.5 | Returns CN, high risk | ☐ |
| IT-002-6 | Invalid IP handled | GET /api/security?action=geo-lookup&ip=invalid | Returns error | ☐ |

---

### IT-003: Threat Intelligence Integration

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| IT-003-1 | Tor exit check | Check known Tor IP | Returns is_tor: true | ☐ |
| IT-003-2 | Cache works | Query same IP twice | Second faster | ☐ |
| IT-003-3 | AbuseIPDB query | Query known bad IP | Returns abuse score | ☐ |
| IT-003-4 | Graceful API failure | Disconnect network | Returns cached/default | ☐ |

---

## End-to-End Tests

### E2E-001: SOC Dashboard Flow

| Test ID | Step | Action | Expected Result | Status |
|---------|------|--------|-----------------|--------|
| E2E-001-1 | Navigate | Go to /security | Page loads | ☐ |
| E2E-001-2 | View status | Check threat level | Shows "low" | ☐ |
| E2E-001-3 | View users | Check authorized users | Shows 5 users | ☐ |
| E2E-001-4 | IP lookup | Enter 8.8.8.8, click Lookup | Shows Google, US | ☐ |
| E2E-001-5 | Navigation | Click Network Monitor | Goes to /security/network | ☐ |

**Playwright Test:**
```typescript
// e2e/soc-dashboard.spec.ts
import { test, expect } from '@playwright/test';

test.describe('SOC Dashboard', () => {
  test('should load and display security status', async ({ page }) => {
    await page.goto('/security');
    
    // Wait for loading to complete
    await expect(page.getByText('Security Operations Center')).toBeVisible();
    
    // Check threat level
    await expect(page.getByText(/threat level/i)).toBeVisible();
    
    // Check monitoring status
    await expect(page.getByText('ACTIVE')).toBeVisible();
    
    // Check authorized users
    await expect(page.getByText('Morgan')).toBeVisible();
    await expect(page.getByText('Chris')).toBeVisible();
    await expect(page.getByText('Garrett')).toBeVisible();
    await expect(page.getByText('RJ')).toBeVisible();
    await expect(page.getByText('Beto')).toBeVisible();
  });
  
  test('should perform IP lookup', async ({ page }) => {
    await page.goto('/security');
    
    // Wait for page load
    await expect(page.getByText('IP Lookup')).toBeVisible();
    
    // Enter IP
    await page.getByPlaceholder('Enter IP address').fill('8.8.8.8');
    
    // Click lookup
    await page.getByRole('button', { name: 'Lookup' }).click();
    
    // Verify results
    await expect(page.getByText('Google LLC')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('LOW')).toBeVisible();
  });
});
```

---

### E2E-002: Network Monitor Flow

| Test ID | Step | Action | Expected Result | Status |
|---------|------|--------|-----------------|--------|
| E2E-002-1 | Navigate | Go to /security/network | Page loads | ☐ |
| E2E-002-2 | View WAN | Check WAN status | Shows IP address | ☐ |
| E2E-002-3 | View devices | Check network devices | Shows 3 devices | ☐ |
| E2E-002-4 | View clients | Check connected clients | Shows client list | ☐ |
| E2E-002-5 | View alarms | Check recent alarms | Shows alarm list | ☐ |
| E2E-002-6 | Tab switch | Click Devices tab | Shows device view | ☐ |

---

### E2E-003: Incident Management Flow

| Test ID | Step | Action | Expected Result | Status |
|---------|------|--------|-----------------|--------|
| E2E-003-1 | Navigate | Go to /security/incidents | Page loads | ☐ |
| E2E-003-2 | View stats | Check incident counts | Shows statistics | ☐ |
| E2E-003-3 | Filter | Click "Investigating" | Shows filtered list | ☐ |
| E2E-003-4 | View incident | Click incident card | Shows details | ☐ |

---

### E2E-004: Red Team Dashboard Flow

| Test ID | Step | Action | Expected Result | Status |
|---------|------|--------|-----------------|--------|
| E2E-004-1 | Navigate | Go to /security/redteam | Page loads | ☐ |
| E2E-004-2 | View form | Check scanner form | Shows target input | ☐ |
| E2E-004-3 | Select scan | Choose "SYN Scan" | Dropdown updates | ☐ |
| E2E-004-4 | View tabs | Check available tabs | Shows all 4 tabs | ☐ |

---

### E2E-005: Compliance Dashboard Flow

| Test ID | Step | Action | Expected Result | Status |
|---------|------|--------|-----------------|--------|
| E2E-005-1 | Navigate | Go to /security/compliance | Page loads | ☐ |
| E2E-005-2 | View score | Check compliance score | Shows 95% | ☐ |
| E2E-005-3 | View controls | Check NIST controls | Shows 11 controls | ☐ |
| E2E-005-4 | Filter controls | Click "Access Control" | Filters to AC controls | ☐ |
| E2E-005-5 | Export | Click "Export PDF" | Initiates download | ☐ |

---

## API Tests

### API-001: Security API Endpoints

**Test Script (PowerShell):**
```powershell
# test-security-api.ps1
param(
    [string]$BaseUrl = "http://localhost:3000"
)

Write-Host "=== Security API Tests ===" -ForegroundColor Cyan

# Test 1: Status
Write-Host -NoNewline "API-001-1 Status: "
try {
    $resp = Invoke-RestMethod "$BaseUrl/api/security?action=status"
    if ($resp.status -eq "active") {
        Write-Host "PASS" -ForegroundColor Green
    } else {
        Write-Host "FAIL - status not active" -ForegroundColor Red
    }
} catch {
    Write-Host "FAIL - $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Users
Write-Host -NoNewline "API-001-2 Users: "
try {
    $resp = Invoke-RestMethod "$BaseUrl/api/security?action=users"
    if ($resp.users.Count -eq 5) {
        Write-Host "PASS" -ForegroundColor Green
    } else {
        Write-Host "FAIL - expected 5 users, got $($resp.users.Count)" -ForegroundColor Red
    }
} catch {
    Write-Host "FAIL - $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Geo-lookup US
Write-Host -NoNewline "API-001-3 Geo-lookup US: "
try {
    $resp = Invoke-RestMethod "$BaseUrl/api/security?action=geo-lookup&ip=8.8.8.8"
    if ($resp.country_code -eq "US" -and $resp.is_allowed_country -eq $true) {
        Write-Host "PASS" -ForegroundColor Green
    } else {
        Write-Host "FAIL - unexpected result" -ForegroundColor Red
    }
} catch {
    Write-Host "FAIL - $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Geo-lookup High Risk
Write-Host -NoNewline "API-001-4 Geo-lookup High Risk: "
try {
    $resp = Invoke-RestMethod "$BaseUrl/api/security?action=geo-lookup&ip=223.5.5.5"
    if ($resp.is_high_risk -eq $true) {
        Write-Host "PASS" -ForegroundColor Green
    } else {
        Write-Host "FAIL - should be high risk" -ForegroundColor Red
    }
} catch {
    Write-Host "FAIL - $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Events
Write-Host -NoNewline "API-001-5 Events: "
try {
    $resp = Invoke-RestMethod "$BaseUrl/api/security?action=events"
    if ($null -ne $resp.events) {
        Write-Host "PASS" -ForegroundColor Green
    } else {
        Write-Host "FAIL - no events array" -ForegroundColor Red
    }
} catch {
    Write-Host "FAIL - $($_.Exception.Message)" -ForegroundColor Red
}

# Test 6: Incidents
Write-Host -NoNewline "API-001-6 Incidents: "
try {
    $resp = Invoke-RestMethod "$BaseUrl/api/security?action=incidents"
    if ($null -ne $resp.incidents) {
        Write-Host "PASS" -ForegroundColor Green
    } else {
        Write-Host "FAIL - no incidents array" -ForegroundColor Red
    }
} catch {
    Write-Host "FAIL - $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Tests Complete ===" -ForegroundColor Cyan
```

---

### API-002: UniFi API Endpoints

| Test ID | Endpoint | Method | Expected Status | Expected Data |
|---------|----------|--------|-----------------|---------------|
| API-002-1 | /api/unifi?action=dashboard | GET | 200 | wan, clients, devices |
| API-002-2 | /api/unifi?action=devices | GET | 200 | devices array |
| API-002-3 | /api/unifi?action=clients | GET | 200 | clients array |
| API-002-4 | /api/unifi?action=traffic | GET | 200 | traffic object |
| API-002-5 | /api/unifi?action=alarms | GET | 200 | alarms array |
| API-002-6 | /api/unifi?action=wlans | GET | 200 | wlans array |
| API-002-7 | /api/unifi?action=topology | GET | 200 | nodes, links |

---

## UI Tests

### UI-001: Visual Regression Tests

| Test ID | Page | Element | Check |
|---------|------|---------|-------|
| UI-001-1 | /security | Header | Logo, title visible |
| UI-001-2 | /security | Status cards | 4 cards displayed |
| UI-001-3 | /security | User list | 5 users with roles |
| UI-001-4 | /security/network | Live indicator | Animated pulse |
| UI-001-5 | /security/incidents | Filter buttons | 5 filter options |
| UI-001-6 | /security/redteam | Warning banner | Authorization warning |
| UI-001-7 | /security/compliance | Score display | Large percentage |

---

### UI-002: Responsive Design Tests

| Test ID | Page | Viewport | Check |
|---------|------|----------|-------|
| UI-002-1 | /security | Desktop (1920x1080) | Full layout |
| UI-002-2 | /security | Tablet (768x1024) | Adapted grid |
| UI-002-3 | /security | Mobile (375x667) | Single column |
| UI-002-4 | /security/network | Desktop | All panels visible |
| UI-002-5 | /security/network | Mobile | Scrollable panels |

---

### UI-003: Accessibility Tests

| Test ID | Check | Tool | Standard |
|---------|-------|------|----------|
| UI-003-1 | Color contrast | axe-core | WCAG 2.1 AA |
| UI-003-2 | Keyboard navigation | Manual | All interactive elements |
| UI-003-3 | Screen reader | NVDA | Proper labels |
| UI-003-4 | Focus indicators | Visual | Visible focus states |

---

## Security Tests

### SEC-001: Authentication Tests

| Test ID | Test | Steps | Expected | Status |
|---------|------|-------|----------|--------|
| SEC-001-1 | No auth required (dev) | Access /security | Allowed in dev | ☐ |
| SEC-001-2 | Session validation | Check auth headers | Valid session | ☐ |
| SEC-001-3 | Token expiry | Use expired token | 401 response | ☐ |

---

### SEC-002: Input Validation Tests

| Test ID | Endpoint | Input | Expected | Status |
|---------|----------|-------|----------|--------|
| SEC-002-1 | geo-lookup | XSS payload | Sanitized/rejected | ☐ |
| SEC-002-2 | geo-lookup | SQL injection | Rejected | ☐ |
| SEC-002-3 | geo-lookup | Very long string | Rejected | ☐ |
| SEC-002-4 | scan | Invalid target | Error message | ☐ |

**Test Script:**
```bash
#!/bin/bash
# test-input-validation.sh

BASE_URL="${1:-http://localhost:3000}"

echo "=== Input Validation Tests ==="

# XSS test
echo -n "SEC-002-1 XSS: "
RESP=$(curl -s "$BASE_URL/api/security?action=geo-lookup&ip=<script>alert(1)</script>")
if echo "$RESP" | grep -q "error\|invalid"; then
  echo "✅ PASS - XSS rejected"
else
  echo "❌ FAIL - XSS not handled"
fi

# SQL injection test
echo -n "SEC-002-2 SQLi: "
RESP=$(curl -s "$BASE_URL/api/security?action=geo-lookup&ip=1.1.1.1'; DROP TABLE users;--")
if echo "$RESP" | grep -q "error\|invalid"; then
  echo "✅ PASS - SQLi rejected"
else
  echo "❌ FAIL - SQLi not handled"
fi

# Long string test
echo -n "SEC-002-3 Long string: "
LONG_STRING=$(python3 -c "print('A'*10000)")
RESP=$(curl -s "$BASE_URL/api/security?action=geo-lookup&ip=$LONG_STRING" 2>&1)
if [[ $? -eq 0 ]] && echo "$RESP" | grep -q "error\|invalid"; then
  echo "✅ PASS - Long string rejected"
else
  echo "❌ FAIL - Long string not handled"
fi
```

---

### SEC-003: Rate Limiting Tests

| Test ID | Test | Method | Expected | Status |
|---------|------|--------|----------|--------|
| SEC-003-1 | Normal usage | 10 req/min | All succeed | ☐ |
| SEC-003-2 | Excessive usage | 100 req/min | Rate limited | ☐ |
| SEC-003-3 | After limit | Wait 1 min | Allowed again | ☐ |

---

### SEC-004: Data Exposure Tests

| Test ID | Check | Method | Expected | Status |
|---------|-------|--------|----------|--------|
| SEC-004-1 | No API keys in response | Inspect JSON | No keys visible | ☐ |
| SEC-004-2 | No internal IPs exposed | Check responses | Masked/hidden | ☐ |
| SEC-004-3 | Error messages safe | Trigger errors | No stack traces | ☐ |

---

## Performance Tests

### PERF-001: Response Time Tests

| Test ID | Endpoint | Target | Acceptable | Status |
|---------|----------|--------|------------|--------|
| PERF-001-1 | /security | < 2s | < 5s | ☐ |
| PERF-001-2 | /api/security?action=status | < 100ms | < 500ms | ☐ |
| PERF-001-3 | /api/unifi?action=dashboard | < 500ms | < 2s | ☐ |
| PERF-001-4 | /api/security?action=geo-lookup | < 1s | < 3s | ☐ |
| PERF-001-5 | /security/network | < 3s | < 6s | ☐ |

**Test Script:**
```bash
#!/bin/bash
# test-performance.sh

BASE_URL="${1:-http://localhost:3000}"

echo "=== Performance Tests ==="

# Test API response time
test_endpoint() {
    local name=$1
    local url=$2
    local target=$3
    
    local start=$(date +%s%N)
    curl -s -o /dev/null "$url"
    local end=$(date +%s%N)
    local duration=$(( (end - start) / 1000000 ))
    
    if [ $duration -lt $target ]; then
        echo "✅ $name: ${duration}ms (target: ${target}ms)"
    else
        echo "❌ $name: ${duration}ms (target: ${target}ms) - SLOW"
    fi
}

test_endpoint "Status API" "$BASE_URL/api/security?action=status" 500
test_endpoint "Users API" "$BASE_URL/api/security?action=users" 500
test_endpoint "UniFi Dashboard" "$BASE_URL/api/unifi?action=dashboard" 2000
test_endpoint "Geo Lookup" "$BASE_URL/api/security?action=geo-lookup&ip=8.8.8.8" 3000
```

---

### PERF-002: Load Tests

| Test ID | Scenario | Concurrent Users | Duration | Target |
|---------|----------|------------------|----------|--------|
| PERF-002-1 | Normal load | 10 | 5 min | 95% < 2s |
| PERF-002-2 | Peak load | 50 | 5 min | 90% < 5s |
| PERF-002-3 | Stress test | 100 | 5 min | No crashes |

---

## Environment-Specific Tests

### Development (localhost)

| Test ID | Test | Command | Expected | Status |
|---------|------|---------|----------|--------|
| DEV-001 | Server starts | `npm run dev` | No errors | ☐ |
| DEV-002 | Hot reload works | Edit file | Auto-refresh | ☐ |
| DEV-003 | Mock data available | Disconnect UniFi | Falls back to mock | ☐ |
| DEV-004 | Error boundaries work | Throw error | Graceful handling | ☐ |
| DEV-005 | All pages accessible | Navigate all routes | 200 responses | ☐ |

### Sandbox (sandbox.mycosoft.com)

| Test ID | Test | Command | Expected | Status |
|---------|------|---------|----------|--------|
| SBX-001 | HTTPS works | curl -I https://... | 200 + valid cert | ☐ |
| SBX-002 | Real UniFi data | Check /security/network | Live data shown | ☐ |
| SBX-003 | Auth required (if enabled) | Access without login | Redirect to login | ☐ |
| SBX-004 | Performance acceptable | Load test | < 3s response | ☐ |
| SBX-005 | No mock data | Check responses | Real data only | ☐ |
| SBX-006 | Logging works | Trigger event | Appears in logs | ☐ |

---

## Test Execution Scripts

### Master Test Script (PowerShell)

```powershell
# run-all-tests.ps1
param(
    [string]$Environment = "dev",
    [string]$BaseUrl = ""
)

# Set base URL based on environment
if ($BaseUrl -eq "") {
    switch ($Environment) {
        "dev" { $BaseUrl = "http://localhost:3000" }
        "sandbox" { $BaseUrl = "https://sandbox.mycosoft.com" }
        default { $BaseUrl = "http://localhost:3000" }
    }
}

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  MYCOSOFT SOC TEST SUITE v2.0" -ForegroundColor Cyan
Write-Host "  Environment: $Environment" -ForegroundColor Cyan
Write-Host "  Base URL: $BaseUrl" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

$passed = 0
$failed = 0

# Helper function
function Test-Endpoint {
    param($Name, $Url, $ExpectedProperty)
    
    Write-Host -NoNewline "$Name`: "
    try {
        $resp = Invoke-RestMethod $Url -TimeoutSec 10
        if ($null -ne $resp.$ExpectedProperty -or $resp -is [array]) {
            Write-Host "PASS" -ForegroundColor Green
            return $true
        } else {
            Write-Host "FAIL - missing $ExpectedProperty" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "FAIL - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# API Tests
Write-Host "`n--- API Tests ---" -ForegroundColor Yellow

if (Test-Endpoint "Security Status" "$BaseUrl/api/security?action=status" "status") { $passed++ } else { $failed++ }
if (Test-Endpoint "Security Users" "$BaseUrl/api/security?action=users" "users") { $passed++ } else { $failed++ }
if (Test-Endpoint "Security Events" "$BaseUrl/api/security?action=events" "events") { $passed++ } else { $failed++ }
if (Test-Endpoint "Geo Lookup" "$BaseUrl/api/security?action=geo-lookup&ip=8.8.8.8" "ip") { $passed++ } else { $failed++ }
if (Test-Endpoint "UniFi Dashboard" "$BaseUrl/api/unifi?action=dashboard" "wan") { $passed++ } else { $failed++ }
if (Test-Endpoint "UniFi Devices" "$BaseUrl/api/unifi?action=devices" "devices") { $passed++ } else { $failed++ }
if (Test-Endpoint "UniFi Clients" "$BaseUrl/api/unifi?action=clients" "clients") { $passed++ } else { $failed++ }

# Page Tests
Write-Host "`n--- Page Tests ---" -ForegroundColor Yellow

$pages = @(
    @{Name="SOC Dashboard"; Path="/security"},
    @{Name="Network Monitor"; Path="/security/network"},
    @{Name="Incidents"; Path="/security/incidents"},
    @{Name="Red Team"; Path="/security/redteam"},
    @{Name="Compliance"; Path="/security/compliance"}
)

foreach ($page in $pages) {
    Write-Host -NoNewline "$($page.Name): "
    try {
        $resp = Invoke-WebRequest "$BaseUrl$($page.Path)" -TimeoutSec 10
        if ($resp.StatusCode -eq 200) {
            Write-Host "PASS" -ForegroundColor Green
            $passed++
        } else {
            Write-Host "FAIL - Status $($resp.StatusCode)" -ForegroundColor Red
            $failed++
        }
    } catch {
        Write-Host "FAIL - $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
}

# Summary
Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host "  TEST RESULTS" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Passed: $passed" -ForegroundColor Green
Write-Host "  Failed: $failed" -ForegroundColor Red
Write-Host "  Total:  $($passed + $failed)" -ForegroundColor White
Write-Host "======================================" -ForegroundColor Cyan

if ($failed -gt 0) {
    exit 1
} else {
    exit 0
}
```

### Quick Smoke Test

```powershell
# smoke-test.ps1
param([string]$BaseUrl = "http://localhost:3000")

Write-Host "Quick Smoke Test for $BaseUrl" -ForegroundColor Cyan

$endpoints = @(
    "/api/security?action=status",
    "/api/unifi?action=dashboard",
    "/security"
)

$allPassed = $true

foreach ($endpoint in $endpoints) {
    Write-Host -NoNewline "Testing $endpoint... "
    try {
        $resp = Invoke-WebRequest "$BaseUrl$endpoint" -TimeoutSec 5
        if ($resp.StatusCode -eq 200) {
            Write-Host "OK" -ForegroundColor Green
        } else {
            Write-Host "FAIL ($($resp.StatusCode))" -ForegroundColor Red
            $allPassed = $false
        }
    } catch {
        Write-Host "FAIL" -ForegroundColor Red
        $allPassed = $false
    }
}

if ($allPassed) {
    Write-Host "`nSmoke test PASSED" -ForegroundColor Green
} else {
    Write-Host "`nSmoke test FAILED" -ForegroundColor Red
}
```

---

## Test Results Template

### Test Run Report

```markdown
# Test Run Report

**Date:** YYYY-MM-DD HH:MM
**Environment:** [dev/sandbox/production]
**Tester:** [Name]
**Version:** 2.0.0

## Summary

| Category | Passed | Failed | Skipped | Total |
|----------|--------|--------|---------|-------|
| Unit | 0 | 0 | 0 | 0 |
| Integration | 0 | 0 | 0 | 0 |
| E2E | 0 | 0 | 0 | 0 |
| API | 0 | 0 | 0 | 0 |
| UI | 0 | 0 | 0 | 0 |
| Security | 0 | 0 | 0 | 0 |
| Performance | 0 | 0 | 0 | 0 |
| **TOTAL** | **0** | **0** | **0** | **0** |

## Failed Tests

| Test ID | Name | Error | Priority |
|---------|------|-------|----------|
| | | | |

## Notes

- 

## Sign-off

- [ ] All critical tests passed
- [ ] No blocking issues
- [ ] Ready for deployment

Approved by: _________________ Date: _________
```

---

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test-soc.yml
name: SOC Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'
          
      - name: Install dependencies
        run: npm ci
        working-directory: ./website
        
      - name: Run linter
        run: npm run lint
        working-directory: ./website
        
      - name: Run type check
        run: npx tsc --noEmit
        working-directory: ./website
        
      - name: Build
        run: npm run build
        working-directory: ./website
        env:
          UNIFI_HOST: mock
          UNIFI_API_KEY: mock
          
      - name: Run unit tests
        run: npm test
        working-directory: ./website
        
      - name: Start server
        run: npm start &
        working-directory: ./website
        
      - name: Wait for server
        run: sleep 10
        
      - name: Run API tests
        run: |
          curl -f http://localhost:3000/api/security?action=status
          curl -f http://localhost:3000/api/security?action=users
```

---

**Document Control:**
- Created: January 18, 2026
- Owner: Security Team
- Review Cycle: Monthly
- Next Review: February 18, 2026
