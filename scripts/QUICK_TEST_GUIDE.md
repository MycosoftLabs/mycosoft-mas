# Quick Test Guide - MYCA Production Readiness

## 🚀 Quick Start

### Run All Tests (Recommended Before Deploy)

```powershell
cd C:\Users\admin2\.cursor\worktrees\mycosoft-mas\ams
.\scripts\run_prod_checks.ps1 -DashboardUrl "http://127.0.0.1:3000" -RunE2E
```

### Run Smoke Tests Only

```powershell
.\scripts\prod_smoke_test.ps1 -DashboardUrl "http://127.0.0.1:3000"
```

### Run E2E Tests Only

```powershell
cd unifi-dashboard
npm run test:e2e
```

---

## 📋 What Gets Tested

### Smoke Tests (HTTP Contracts)
- ✅ Dashboard homepage loads
- ✅ Chat API returns MYCA identity ("MYCA", "my-kah")
- ✅ TTS API returns valid audio
- ✅ ElevenLabs proxy working
- ✅ MAS backend health check

### E2E Tests (Browser)
- ✅ Dashboard loads and displays correctly
- ✅ Theme toggle (dark/light mode) works
- ✅ Talk to MYCA panel opens and responds correctly

---

## 🔧 Troubleshooting

### Dashboard Not Responding
```powershell
# Check if server is running
Get-NetTCPConnection -State Listen -LocalPort 3000

# Restart dashboard
cd unifi-dashboard
npm run dev
```

### Tests Failing
1. Ensure dashboard is running: `http://127.0.0.1:3000`
2. Check terminal output for errors
3. Clear `.next` cache: `Remove-Item -Recurse -Force .next`

### E2E Tests Failing
1. Install Playwright browsers: `npm exec playwright install chromium`
2. Ensure dashboard is accessible at configured URL
3. Check `playwright.config.ts` for correct `baseURL`

---

## 📊 Expected Results

**Smoke Test:** All 12 checks should pass  
**E2E Test:** All 3 tests should pass in ~2-3 seconds

If any test fails, check the error message and verify the corresponding service is running.
