# Signal Spam Fix — MYCA Health Alerts

**Date:** March 4, 2026  
**Status:** Complete  
**Issue:** MYCA repeatedly sent "CRITICAL: MINDEX databases unreachable" on Signal every 5 minutes, spamming Morgan.

---

## Problem

The MYCA OS heartbeat loop (`_heartbeat_loop` in `mycosoft_mas/myca/os/core.py`) was sending critical health issues to Signal every 30 seconds when a system (e.g., MINDEX) was unreachable. This caused continuous spam instead of back-and-forth conversation.

**User expectation:** Signal is for actual two-way communication with Morgan, not automated health alerts.

---

## Root Cause

```python
# Before (problematic)
if issue.get("severity") == "critical":
    await self.comms.send_to_morgan(
        f"CRITICAL: {issue['description']}",
        channel="signal"  # Sent every 30 seconds = spam
    )
```

`HEARTBEAT_INTERVAL = 30` seconds. Every heartbeat, every critical issue was resent to Signal.

---

## Fix

Health alerts are now **logged only**. No `send_to_morgan` from the heartbeat loop.

- **Signal:** Back-and-forth conversation only. No automated health spam.
- **Health issues:** Logged via `logger.warning()`. Use dashboards, logs, or Slack for visibility.
- **Slack/Discord:** Remain available for actual conversation and intentional alerts, not heartbeat spam.

---

## File Changed

| File | Change |
|------|--------|
| `mycosoft_mas/myca/os/core.py` | `_heartbeat_loop()` — removed `send_to_morgan(..., channel="signal")` for health issues; only log |

---

## Signal Usage Policy

| Use Signal for | Do NOT use Signal for |
|----------------|------------------------|
| Replies to Morgan's messages | Automated health check alerts |
| Proactive conversation | Repeated status updates |
| Direct questions/answers | Heartbeat/health spam |

---

## Verification

After deploying MYCA OS on VM 191:

1. Confirm MINDEX is reachable from 191 (fix underlying connectivity if needed).
2. Signal should no longer receive "CRITICAL: MINDEX databases unreachable" every 5 minutes.
3. Health issues still appear in MYCA OS logs for debugging.
