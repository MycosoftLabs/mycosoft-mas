# Gap Agent — Cross-Repo Gap Detection

**Date:** February 10, 2026  
**Purpose:** Continuously find gaps between repos and agents: missing connections, TODOs, stubs, and “bridge” work so a third agent or integration isn’t forgotten when two projects are worked on by two agents.

---

## What the Gap Agent Does

The **Gap Agent** is a MAS agent that:

1. **Scans for TODOs / FIXMEs** — Finds `TODO`, `FIXME`, `XXX`, `HACK`, `BUG` in `.py`, `.ts`, `.tsx`, `.js`, `.md` across workspace roots.
2. **Finds stubs and placeholders** — Detects `NotImplementedError`, `# stub`, `# placeholder`, `return {"status": "success"}`-only implementations.
3. **Finds 501 / “Not implemented” routes** — Flags API routes that return 501 or “Not implemented”.
4. **Infers bridge gaps** — Looks in docs for “bridge”, “integration”, “missing”, “gap” to suggest where a connection or third service is needed (e.g. Website ↔ MAS ↔ MINDEX but no bridge).
5. **Suggests plans** — Turns the above into suggested plan items (e.g. “Address TODOs”, “Implement 501 routes”, “Add missing bridges”).

It is designed for **multi-repo workspaces** and **multi-agent work**: when you have two agents on two projects, the Gap Agent helps surface the “third thing” (bridge, API, or shared component) that’s missing.

---

## Configuration

- **Workspace roots:** By default the agent scans the MAS repo only. To scan multiple repos (e.g. MAS + Website + MINDEX), set **`workspace_roots`** in the agent config to a list of absolute paths:
  ```json
  { "workspace_roots": ["/path/to/MAS/mycosoft-mas", "/path/to/WEBSITE/website", "/path/to/MINDEX/mindex"] }
  ```
- On the MAS VM, only the MAS root is usually available; for full cross-repo scanning, run MAS in an environment where all repo paths are mounted or set in config.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/agents/gap/scan?full=false` | Run gap scan; returns TODOs, stubs, 501 routes, bridge_gaps, suggested_plans. Use `full=true` for a larger scan. |
| GET | `/agents/gap/plans` | Return suggested plans from last scan (or run a quick scan). |
| GET | `/agents/gap/summary` | Return summary counts (todos_fixmes_count, stubs_count, routes_501_count, etc.). |

Base URL: `http://192.168.0.188:8001` (MAS Orchestrator).

---

## Task Types (process_task)

- **`scan`** — Lightweight scan (default limits).
- **`full_scan`** — Deeper scan (more TODOs/stubs).
- **`suggest_plans`** — Return suggested plans (uses last report or runs scan).

---

## 24/7 Runner

GapAgent is registered in the core agent registry and is loaded into the 24/7 agent runner. Each cycle it runs a lightweight scan and stores the report; other agents or the API can use the last report.

---

## Voice / Orchestrator

Keywords and voice triggers: **gap**, **find gaps**, **missing connections**, **todo**, **what needs to be done**, **bridge**. You can ask MYCA to “find gaps” or “what needs to be done” and have it delegate to the Gap Agent.

---

## Files

| File | Purpose |
|------|---------|
| `mycosoft_mas/agents/gap_agent.py` | GapAgent implementation. |
| `mycosoft_mas/core/routers/gap_api.py` | REST API for scan, plans, summary. |
| `mycosoft_mas/core/agent_registry.py` | Core registry entry (gap_agent). |
| `mycosoft_mas/registry/agent_registry.py` | AGENT_CATALOG entry (utility). |
| `mycosoft_mas/agents/__init__.py` | Export GapAgent. |

---

## Cursor: Same Behavior in All Chats (Background)

The same gap-finding behavior runs **in Cursor in the background of every chat**:

- **Cursor agent:** `.cursor/agents/gap-agent.md` — @-invoke **gap-agent** in any chat for a gap scan and plan suggestions. The agent instructions tell the model to consider cross-repo gaps proactively when planning or when the user asks "what's missing" or "find gaps."
- **Cursor rule:** `.cursor/rules/gap-agent-background.mdc` — In **every** chat, the model is expected to consider cross-repo gaps, missing connections, and the "third agent or bridge" problem; when relevant, mention gaps or read the gap report files if present.

### Index-based GAP equivalent (Cursor development)

**Missing work in indexed files** — During Cursor development, the GAP equivalent is to find work that is **referenced in the document index but not yet done**:

- **Script:** `scripts/gap_scan_cursor_index.py` — Parses `docs/MASTER_DOCUMENT_INDEX.md` (and optionally `MEMORY_DOCUMENTATION_INDEX`, `SYSTEM_REGISTRY`) for all referenced file paths, then scans those files for TODO/FIXME/Status: pending/- [ ]/501/Not implemented/stub. Writes `.cursor/gap_report_index.json`.
- **Report:** `.cursor/gap_report_index.json` — Contains `referenced_files_with_gaps` (path, gaps per file), `summary.index_gaps_total`, and `suggested_plans`. The Gap Agent and all chats use this **first** when the user asks "what's missing" so that high-impact, index-referenced work is surfaced.
- **Refresh:** Run `python scripts/gap_scan_cursor_index.py` at the start of a dev session or when the index changes. The background script (below) can also run it and merge the result into the latest report.

- **Background report (optional):** Run `python scripts/gap_scan_cursor_background.py` periodically (e.g. every 15–30 min). It (1) fetches from MAS `/agents/gap/scan` or runs a local repo-wide scan → `.cursor/gap_report_latest.json`, and (2) runs the index scan and merges it into the report as `index_gaps`. Set `GAP_SKIP_INDEX=1` to skip the index scan. See `.cursor/rules/autostart-services.mdc` optional service #6.

## Related Docs

- `docs/VISION_VS_IMPLEMENTATION_GAP_ANALYSIS_FEB10_2026.md` — Vision vs implementation gaps (FCI, HPL, MINDEX, etc.).
- `docs/MASTER_DOCUMENT_INDEX.md` — Index entry for this doc.
