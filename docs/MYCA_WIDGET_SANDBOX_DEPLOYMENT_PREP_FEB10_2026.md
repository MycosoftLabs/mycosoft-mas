# MYCA Widget Sandbox Deployment Prep

**Date**: February 10, 2026  
**Status**: Ready for Deployment Agent  
**Purpose**: Preparation documentation for deploying MYCA AI widget + voice changes to sandbox. All code committed and pushed to GitHub. Deployment will be executed by a separate agent.

---

## Summary of Changes

### Website Repo (`WEBSITE/website`)

| File | Change |
|------|--------|
| `hooks/use-voice-search.ts` | Voice command order fixed: specific patterns ("Show me a fungus…", "Show me documents…", "Show me mushrooms in…") now checked before general "show me" |
| `components/search/SearchContextProvider.tsx` | Added `voiceListening`, `setVoiceListening` for shared mic state |
| `components/search/fluid/FluidSearchCanvas.tsx` | Syncs voice state to context; subscribes to `voice:toggle` event; ref-based handler for panel mic |
| `components/search/panels/MYCAChatPanel.tsx` | Added mic button; emits `voice:toggle`; shows listening state (red pulse) |
| `docs/MYCA_WIDGET_TEST_CASES_FEB10_2026.md` | **NEW**: Full regression test checklist for AI widget + panel (text + voice) |

### MAS Repo (`MAS/mycosoft-mas`)

| File | Change |
|------|--------|
| `docs/MASTER_DOCUMENT_INDEX.md` | Added link to MYCA widget test cases doc |
| `docs/MYCA_WIDGET_SANDBOX_DEPLOYMENT_PREP_FEB10_2026.md` | **NEW**: This deployment prep doc |

---

## VM Layout (Sandbox / Production)

| VM | IP | Role | Port |
|----|-----|------|------|
| **Sandbox** | 192.168.0.187 | Website (Docker), optional services | Website 3000 |
| **MAS** | 192.168.0.188 | Multi-Agent System, MYCA Consciousness/Brain | 8001 |
| **MINDEX** | 192.168.0.189 | PostgreSQL, Redis, Qdrant, MINDEX API | 8000, 5432, 6379, 6333 |

---

## Deployment Steps (For Deployment Agent)

### 1. Website → Sandbox VM (192.168.0.187)

```bash
# SSH to Sandbox
ssh mycosoft@192.168.0.187

# Navigate to website
cd /opt/mycosoft/website

# Pull latest
git fetch origin
git reset --hard origin/main

# Rebuild Docker image (no cache)
docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache .

# Restart container (MUST include NAS mount for assets)
docker stop mycosoft-website 2>/dev/null || true
docker rm mycosoft-website 2>/dev/null || true
docker run -d --name mycosoft-website -p 3000:3000 \
  -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
  --restart unless-stopped mycosoft-always-on-mycosoft-website:latest
```

### 2. Cloudflare Cache Purge

After website deploy: **Purge Everything** in Cloudflare for mycosoft.com.

### 3. MAS VM (192.168.0.188)

No MAS code changes in this release. MAS must remain running for MYCA Consciousness and Brain APIs. Verify health:

```bash
curl -s http://192.168.0.188:8001/health
```

### 4. MINDEX VM (192.168.0.189)

No MINDEX code changes. Verify API health:

```bash
curl -s http://192.168.0.189:8000/health
```

---

## Environment Requirements

### Sandbox Website Container

- `MAS_API_URL` → `http://192.168.0.188:8001` (for MYCA Consciousness, Brain, intention tracking)
- `MINDEX_API_URL` → `http://192.168.0.189:8000`
- `NEXT_PUBLIC_MAS_API_URL` → same as MAS_API_URL for client-side calls

### MAS VM

- Must be reachable from Sandbox (187) for `/api/myca/consciousness/*`, `/api/myca/brain/*`, `/api/myca/intention`

---

## Verification Checklist (Post-Deploy)

1. **Website loads**: `https://sandbox.mycosoft.com/search` (or configured sandbox URL)
2. **Unified search**: Type `reishi` → species + AI answer
3. **AI widget**: Math `2+2` → answer in AI widget
4. **Left MYCA panel**: Open panel; type question; mic button visible
5. **Voice (if Web Speech available)**: Main mic and panel mic both toggle listening
6. **Voice commands**: "Show me reishi" → species widget; "Show me documents about psilocybin" → research widget

---

## Test Document Reference

Full regression checklist:  
`WEBSITE/website/docs/MYCA_WIDGET_TEST_CASES_FEB10_2026.md`

Covers: text input, voice input, math, fungi, documents, locations, all voice command patterns, both AI widget and MYCA panel.

---

## GitHub Push Status

- **Website**: Changes committed and pushed to `main`
- **MAS**: Changes committed and pushed to `main`

Deployment agent should pull from `origin/main` on each VM.

**Primary deployment reference:** See `docs/SANDBOX_LIVE_TESTING_PREP_FEB18_2026.md` for VM layout, image names, and full runbook. This doc adds MYCA widget–specific steps and verification.

---

## Related Documents

- [Sandbox Live Testing Prep](./SANDBOX_LIVE_TESTING_PREP_FEB18_2026.md) – Primary deployment runbook
- [MYCA Widget Test Cases](../WEBSITE/website/docs/MYCA_WIDGET_TEST_CASES_FEB10_2026.md)
- [MYCA Widget AI Integration](./MYCA_WIDGET_AI_INTEGRATION_FEB11_2026.md)
- [Deployment Checklist](../WEBSITE/website/.cursor/rules/deployment-checklist.mdc)
- [Dev to Sandbox Pipeline](../WEBSITE/website/docs/DEV_SANDBOX_KEYS_FLOW_FEB06_2026.md)
