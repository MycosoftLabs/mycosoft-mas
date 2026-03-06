# MYCA→n8n Trigger Pattern — March 7, 2026

**Status:** Documentation  
**Purpose:** Standard way for MYCA to trigger n8n workflows (e.g. "deploy when Morgan approves").  
**Related:** `docs/MYCA_SUPPORT_UPGRADE_AUDIT_MAR07_2026.md`

---

## Overview

MYCA can trigger n8n workflows via:

1. **MAS API** — `POST /api/workflows/trigger` (if implemented)
2. **n8n Webhook** — MYCA calls n8n webhook URL directly
3. **MAS n8n bridge** — MAS proxies to n8n

## Recommended Pattern

When MYCA needs to execute an action that has an n8n workflow:

1. MYCA proposes action (e.g. "Deploy to sandbox")
2. Morgan confirms in MYCA chat
3. MYCA calls MAS `/api/workflows/trigger` with workflow ID and payload
4. MAS forwards to n8n webhook or executes workflow
5. Result flows back to MYCA (or notification)

## MAS Workflow APIs

| Endpoint | Purpose |
|----------|---------|
| `GET /api/workflows/registry` | List available workflows |
| `POST /api/workflows/sync-both` | Sync repo to local and cloud n8n |
| (Future) `POST /api/workflows/trigger` | Trigger workflow by ID |

## n8n Webhook Direct

Workflows can expose webhook triggers. MYCA (or MAS) calls:

```
POST https://n8n.example.com/webhook/{workflow-id}
Body: { "action": "deploy", "target": "sandbox", "approved_by": "morgan" }
```

## Implementation Notes

- Store workflow webhook URLs in env or MAS config
- Morgan approval must complete before trigger
- Log trigger for audit
- Handle timeouts and retries

## Related

- `n8n_workflows_api.py` — MAS n8n integration
- `docs/N8N_WORKFLOW_SYNC_AND_REGISTRY_FEB18_2026.md`
