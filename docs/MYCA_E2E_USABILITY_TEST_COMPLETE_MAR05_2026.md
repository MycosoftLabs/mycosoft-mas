# MYCA End-to-End Usability Test Complete

**Date:** March 5, 2026  
**Status:** USABLE — Pipeline verified, you can ask MYCA to do work on her PC (VM 191)

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| MAS Orchestrator | ✓ | Healthy, Postgres connected |
| MAS Agents API | ✓ | 46 agents at `/agents/registry/` |
| MAS MYCA Chat | ✓ | `/api/myca/chat` responds |
| MINDEX API | ✓ | Healthy |
| VM 191 SSH | ✓ | Port 22 open |
| MYCA Workspace API | ✓ | Port 8100 |
| MYCA OS Daemon | ✓ | systemd `myca-os` active |
| 191 → 188 (MAS) | ✓ | VM 191 can reach MAS |
| 191 → 189 (MINDEX) | ✓ | VM 191 can reach MINDEX |
| Workspace /think | ✓ | Sends to MAS brain |
| n8n 191:5679 | ⚠ | May be Docker-internal only |

**PASSED:** 10  
**FAILED:** 0  
**WARNINGS:** 1 (n8n 5679)

---

## How to Ask MYCA to Do Work

### 1. Via Workspace API (VM 191)

```bash
# Send a message to MYCA's brain
curl -X POST http://192.168.0.191:8100/workspace/think \
  -H "Content-Type: application/json" \
  -d '{"message": "Create an Asana task: Review Q1 metrics", "session_id": "morgan"}'
```

### 2. Via MAS Chat (direct)

```bash
curl -X POST http://192.168.0.188:8001/api/myca/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What tasks do I have today?", "stream": false}'
```

### 3. Via Website

Use the MYCA chat on the website — it routes through MAS.

---

## What Works Right Now

- **Request flow:** Workspace (191:8100) → MAS (188:8001) → MYCA consciousness
- **MYCA OS daemon:** Running on VM 191, polling/processing tasks
- **Workspace tools:** Email, Discord, Asana endpoints at 191:8100
- **Agent dispatch:** MAS has 46 registered agents for specialist tasks

---

## LLM Fallback (If You See "I'm having a moment of difficulty")

MYCA returns a polite fallback when the LLM call fails (e.g. missing `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` on VM 188). The pipeline still works; you just get the fallback instead of a real LLM reply.

**Fix:** Ensure `ANTHROPIC_API_KEY` and/or `OPENAI_API_KEY` are set in the MAS container env on VM 188.

---

## Test Script

Run the full E2E test anytime:

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python scripts/_test_myca_e2e.py
```

---

## Related Docs

- `docs/MYCA_PIPELINE_STATUS_MAR05_2026.md` — Full diagnostic
- `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md` — VM layout
- `mycosoft_mas/agents/workspace/workspace_api.py` — Workspace API routes
