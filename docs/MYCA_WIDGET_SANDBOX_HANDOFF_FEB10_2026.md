# MYCA Widget Sandbox Deployment Handoff

**Date**: February 10, 2026  
**Status**: Ready for Deployment Agent  
**Prepared By**: Cursor Agent

---

## Summary

All MYCA AI widget and voice changes are prepared for sandbox live testing. Code is committed. **Deployment will be executed by another agent.**

---

## What Was Prepared

### Website Repo (WEBSITE/website)

| Status | Notes |
|--------|-------|
| ✅ Committed | MYCA panel mic, voice commands, search context, test cases |
| ✅ Pushed to GitHub | `origin/main` is up to date |
| **Commit** | `397b43e` – Sandbox prep: MYCA widget docs, search/voice panel and context |

**Files changed:**
- `hooks/use-voice-search.ts` – Voice command priority
- `components/search/panels/MYCAChatPanel.tsx` – Mic button
- `components/search/SearchContextProvider.tsx` – Voice state
- `components/search/fluid/FluidSearchCanvas.tsx` – Voice event handling
- `docs/MYCA_WIDGET_TEST_CASES_FEB10_2026.md` – Test checklist
- `docs/MYCA_WIDGET_SANDBOX_DEPLOYMENT_PREP_FEB10_2026.md` – Website prep doc

### MAS Repo (MAS/mycosoft-mas)

| Status | Notes |
|--------|-------|
| ✅ Committed | Deployment prep doc, MASTER_DOCUMENT_INDEX update |
| ⚠️ Push pending | Push failed (OAuth workflow scope). Deploy agent or user must push with workflow scope, or push from a client with full permissions. |
| **Commit** | `81de43f` – docs: MYCA widget sandbox deployment prep for deploy agent |

**Files changed:**
- `docs/MYCA_WIDGET_SANDBOX_DEPLOYMENT_PREP_FEB10_2026.md` – Full deploy handoff
- `docs/MASTER_DOCUMENT_INDEX.md` – Doc index update

---

## Deployment Agent Instructions

1. **Ensure MAS is pushed** (if not already): Push MAS `main` to GitHub with credentials that have `workflow` scope, or use a client with full repo access.

2. **Deploy website to Sandbox** (192.168.0.187):
   - Pull from `origin/main`
   - Rebuild Docker image (no-cache)
   - Restart container with NAS mount
   - Purge Cloudflare cache

3. **Verify**:
   - MAS health: `http://192.168.0.188:8001/health`
   - MINDEX health: `http://192.168.0.189:8000/health`
   - Website: `https://sandbox.mycosoft.com/search`

**Full steps:** `docs/MYCA_WIDGET_SANDBOX_DEPLOYMENT_PREP_FEB10_2026.md`  
**Primary runbook:** `docs/SANDBOX_LIVE_TESTING_PREP_FEB18_2026.md`

---

## VM Layout

| VM | IP | Role |
|----|-----|------|
| Sandbox | 192.168.0.187 | Website (Docker), port 3000 |
| MAS | 192.168.0.188 | MYCA Consciousness, Brain, port 8001 |
| MINDEX | 192.168.0.189 | API, Postgres, Redis, Qdrant, port 8000 |

---

## Test Document

`WEBSITE/website/docs/MYCA_WIDGET_TEST_CASES_FEB10_2026.md` – Full regression checklist (text + voice, math, fungi, documents, locations, all voice commands).
