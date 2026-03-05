# MYCA OS: Why You Don't See Activity on the Desktop

**Date:** March 5, 2026  
**Purpose:** Explain MYCA OS behavior and how to see/kickstart activity

---

## 1. MYCA OS Is a Headless Daemon — No Desktop UI

MYCA OS runs as a **background systemd service**. There is **no visible window, no desktop app, no visible Chrome or Cursor** when she's "working."

| What you might expect | What MYCA OS actually does |
|-----------------------|----------------------------|
| Chrome windows opening | Uses **Playwright headless** — invisible browser, no windows |
| Cursor IDE opening | Uses **Claude Code CLI** (terminal), not Cursor |
| Cloud Code, Google Workspace | **Not integrated** — MYCA uses IMAP for email, not Chrome |
| Visible "MYCA is working" | Logs to `/opt/myca/logs/myca_os.log` only |

**You will not see MYCA on the desktop.** She runs in the background like a server.

---

## 2. Where MYCA's Activity Shows Up

| Channel | Where to see it |
|---------|------------------|
| **Logs** | `tail -f /opt/myca/logs/myca_os.log` on VM 191 |
| **Discord** | Messages in your Discord server from MYCA |
| **Email** | Replies from schedule@mycosoft.org |
| **Asana** | Task comments (if PAT configured) |

---

## 3. What MYCA Needs to "Do Something"

MYCA is **reactive + scheduled**. She acts when:

1. **Messages arrive** — Email, Discord, Asana, Slack, Signal  
   - She polls every 5 seconds  
   - If no new messages → nothing to do
2. **Tasks in her queue** — From:
   - Morgan's messages (e.g. "Please review the PR")
   - Scheduler (myca_schedule table) — **migration was skipped** so this may be empty
   - Daily rhythm (8am, 12pm, 5pm, 10pm) — only at those hours
3. **Scheduled items** — Requires `myca_schedule` table in MINDEX; migration was skipped

**If the task queue is empty and there are no new messages, MYCA just loops quietly.** No visible activity.

---

## 4. How to Give MYCA Work (So She Does Something)

| Method | How |
|--------|-----|
| **Discord** | Send a message to MYCA in the configured Discord channel |
| **Email** | Email schedule@mycosoft.org with a request |
| **API** | POST to `http://192.168.0.191:8100` (if workspace API is running) |

Example: In Discord, say: *"Hey MYCA, check your email and summarize what needs attention."*

---

## 5. How to See That MYCA Is Alive

On VM 191, open a terminal and run:

```bash
# 1. Check service status
sudo systemctl status myca-os

# 2. Watch live logs (this is where you'll see activity)
tail -f /opt/myca/logs/myca_os.log

# 3. Health check
curl -s http://localhost:8100/health | jq
```

If you see log lines like `Message from X via discord`, `Working on: ...`, `Polling email...` — she's active.

---

## 6. Cursor, Chrome, Cloud Code — Not Used by MYCA

The tools you installed on VM 191:

| Tool | Used by MYCA? | What MYCA uses instead |
|------|---------------|-------------------------|
| Cursor (downloaded) | No | Claude Code CLI |
| Chrome (logged in) | No | Playwright headless (invisible) |
| Cloud Code | No | Not integrated |
| Google Workspace Client | No | IMAP for schedule@ email |

MYCA does **not** use your logged-in Chrome session. She has her own IMAP credentials for schedule@mycosoft.org and polls that. Your Gmail login in Chrome is separate.

---

## 7. Making Activity Visible (Optional)

If you want to **see** MYCA doing web tasks (e.g. research, form filling), we can:

1. **Launch visible Chrome** — When MYCA runs a browser task, use `headless=False` and `DISPLAY=:0` so you see it in noVNC (http://192.168.0.191:6080).
2. **Status dashboard** — A simple web page showing "Current task", "Messages today", etc.

This requires code changes. The current design is headless for stability and resource use.

---

## 8. Quick Diagnostic Commands (Run on VM 191)

```bash
# Is MYCA OS running?
systemctl is-active myca-os

# Last 50 log lines
tail -50 /opt/myca/logs/myca_os.log

# Any errors?
tail -50 /opt/myca/logs/myca_os_error.log

# Health (from VM 191)
curl -s http://localhost:8100/health
```

---

## 9. Summary

- **MYCA OS = background daemon** — no desktop UI
- **Activity = logs, Discord, email** — not visible windows
- **To get her working** — send her a message (Discord or email)
- **To watch her** — `tail -f /opt/myca/logs/myca_os.log`
