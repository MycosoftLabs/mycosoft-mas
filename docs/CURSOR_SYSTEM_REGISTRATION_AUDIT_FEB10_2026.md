# Cursor System Registration Audit (Feb 10, 2026)

## Purpose

Ensure that **rules, agents, and skills** created in the Mycosoft workspace are **fully implemented in the Cursor system** (user-level), not only when the workspace is open. When you create new rules, agents, or commands, they must be automatically put into the Cursor system so Cursor itself uses them globally and all agents can talk to all sub-agents, use all rules, and have context.

## Audit outcome

### Implemented

1. **Sync script (full workspace)**  
   - `scripts/sync_cursor_system.py`  
   - Scans ALL 9 repos (MAS, WEBSITE, MINDEX, MycoBrain, NatureOS, Mycorrhizae, NLM, SDK, platform-infra)  
   - Merges `.cursor/rules`, `.cursor/agents`, `.cursor/skills` to `%USERPROFILE%\.cursor\`  
   - Supports `--watch` mode for continuous syncing every 30 seconds

2. **Autostart service**  
   - Added "Cursor System Sync" to `scripts/autostart-healthcheck.ps1`  
   - Registered in `.cursor/rules/autostart-services.mdc` as service #4  
   - Starts automatically with `.\scripts\autostart-healthcheck.ps1 -StartMissing`

3. **Always-apply rule**  
   - `.cursor/rules/cursor-system-registration.mdc`  
   - Documents automatic syncing, manual sync, and what this enables (all agents talk to sub-agents, all rules apply, all skills available, full context)

4. **Agent-creation reminder**  
   - `.cursor/rules/agent-creation-patterns.mdc`  
   - Added: when creating/updating a Cursor agent, run sync or let the watcher pick it up

5. **.cursor README**  
   - `.cursor/README.md`  
   - Explains that rules/agents/skills are synced to the Cursor system

### Current state (verified)

| Type | Count | Sources |
|------|-------|---------|
| Rules | 26 | MAS (21), WEBSITE (5) |
| Agents | 30 | MAS (29), WEBSITE (1) |
| Skills | 22 | MAS (17), WEBSITE (6), user-level (5) |

All agents can now:
- Talk to all 30 sub-agents
- Use all 26 rules
- Access all 22 skills
- Have full context across the entire Mycosoft platform

### Not changed (by design)

- **User-level create-rule / create-skill**  
  - Cursor's built-in skills live in `~/.cursor/skills-cursor/`, which is reserved  
  - The always-apply rule instructs agents to run the sync (or rely on the watcher)

### Commands

"Commands" are covered by the same flow: rules, agents, and skills define or invoke behavior. Syncing them into the user Cursor directory registers that behavior in the Cursor system.

## How to use

### Automatic (recommended)

Start the watcher daemon:

```powershell
python scripts/sync_cursor_system.py --watch
```

Or use autostart:

```powershell
.\scripts\autostart-healthcheck.ps1 -StartMissing
```

### Manual (one-time)

```bash
python scripts/sync_cursor_system.py
```

## References

- `scripts/sync_cursor_system.py` — sync implementation (full workspace, watch mode)  
- `.cursor/rules/cursor-system-registration.mdc` — rule that enforces the sync  
- `.cursor/rules/autostart-services.mdc` — autostart service registry (includes sync)  
- `scripts/autostart-healthcheck.ps1` — starts all autostart services  
- `.cursor/README.md` — short summary and command  
- `docs/MASTER_DOCUMENT_INDEX.md` — master doc index (this doc listed there)
