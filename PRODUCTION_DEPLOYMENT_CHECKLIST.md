# Production Deployment Checklist

**Last Updated:** December 22, 2025  
**Status:** ✅ System tested and ready

---

## Pre-Deployment Validation

### ✅ Automated Tests (MUST PASS)

```powershell
# Run from project root
.\scripts\run_prod_checks.ps1 -DashboardUrl "https://your-production-url.com" -RunE2E
```

**Expected:** All smoke tests + E2E tests pass

---

## Environment Configuration

### 1. Dashboard Environment Variables

Create `.env.production` or set in your hosting platform:

```bash
# Production URLs
NEXT_PUBLIC_MAS_URL=https://mas.mycosoft.com
MAS_BACKEND_URL=https://mas.mycosoft.com

# n8n (if using cloud or self-hosted)
N8N_JARVIS_URL=https://n8n.mycosoft.com/webhook/myca/jarvis
N8N_WEBHOOK_URL=https://n8n.mycosoft.com/webhook/myca/speech

# ElevenLabs
ELEVENLABS_API_KEY=<from-secret-manager>
ELEVENLABS_VOICE_ID=aEO01A4wXwd1O8GPgGlF
ELEVENLABS_PROXY_URL=https://tts-proxy.mycosoft.com

# Optional fallbacks
OPENEDAI_SPEECH_URL=https://tts-fallback.mycosoft.com
LITELLM_URL=https://llm.mycosoft.com
```

### 2. Docker Volumes (Persistence)

Ensure these are configured in `docker-compose.prod.yml`:

```yaml
volumes:
  myca_n8n_data:  # n8n workflows + credentials
  mas_postgres_data:  # Database
  mas_redis_data:  # Cache
  mas_qdrant_data:  # Vector DB
```

### 3. n8n Production Setup

**Option A: n8n Cloud (Recommended)**
- Sign up at https://n8n.io/cloud
- Import workflows from `n8n/backup/`
- Configure credentials
- Update dashboard env vars with cloud webhook URLs

**Option B: Self-Hosted n8n**
- Pin n8n version in Docker
- Set `WEBHOOK_URL=https://n8n.mycosoft.com/`
- Set `N8N_HOST=n8n.mycosoft.com`
- Set `N8N_PROTOCOL=https`
- Ensure workflows are imported and activated

---

## Deployment Steps

### Step 1: Build Dashboard

```powershell
cd unifi-dashboard
npm run build
```

### Step 2: Deploy Services

**Option A: Docker Compose (Self-Hosted)**
```powershell
docker-compose -f docker-compose.prod.yml up -d
```

**Option B: Platform-Specific**
- **Vercel/Netlify:** Connect repo, set env vars, deploy
- **Azure:** Use Azure Container Instances or App Service
- **AWS:** Use ECS, EKS, or App Runner

### Step 3: Verify Deployment

```powershell
# Test production URLs
.\scripts\prod_smoke_test.ps1 -DashboardUrl "https://dashboard.mycosoft.com"
```

---

## Post-Deployment Verification

### Immediate Checks

- [ ] Dashboard loads at production URL
- [ ] "Talk to MYCA" panel opens
- [ ] Chat responds with "MYCA (my-kah)" identity
- [ ] TTS generates audio
- [ ] Theme toggle works
- [ ] No console errors in browser

### 24-Hour Monitoring

- [ ] Check error logs
- [ ] Monitor API response times
- [ ] Verify fallback mechanisms work if services go down
- [ ] Check ElevenLabs quota usage
- [ ] Verify n8n workflows executing (if using)

---

## Rollback Plan

If issues occur:

1. **Revert deployment** (platform-specific)
2. **Check logs:** `docker logs <container-name> --tail 100`
3. **Run smoke test** against previous version
4. **Review** `PRODUCTION_READINESS_REPORT.md` for known issues

---

## Support Resources

- **Test Documentation:** `scripts/prod_readiness_test.md`
- **Quick Reference:** `scripts/QUICK_TEST_GUIDE.md`
- **Full Report:** `PRODUCTION_READINESS_REPORT.md`
- **n8n Setup:** `n8n/N8N_SETUP_STATUS.md`

---

## Success Criteria

✅ All smoke tests pass  
✅ All E2E tests pass  
✅ MYCA identity correctly enforced  
✅ Audio generation working  
✅ Fallback mechanisms verified  
✅ No secrets in git  
✅ Docker volumes persistent  

**If all criteria met → PRODUCTION READY** ✅
