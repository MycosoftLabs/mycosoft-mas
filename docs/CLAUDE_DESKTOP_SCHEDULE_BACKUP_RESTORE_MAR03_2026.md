# Claude Desktop Schedule Backup & Restore (Mar 3, 2026)

**Purpose:** Preserve all Cowork scheduled tasks before reinstalling Claude Desktop on Windows. The virtiofs/Plan9 mount error may require a reinstall; this ensures schedules are not lost.

## Schedule Storage Locations

| Location | Contents |
|----------|----------|
| `%APPDATA%\Claude\local-agent-mode-sessions\<account>\<org>\scheduled-tasks.json` | Task definitions (cron, enabled, permissions, file paths) |
| `%USERPROFILE%\Documents\Claude\Scheduled\<task-name>\SKILL.md` | SKILL content for each scheduled task |
| `%APPDATA%\Claude\claude_desktop_config.json` | `coworkScheduledTasksEnabled`, `ccdScheduledTasksEnabled` |
| `%APPDATA%\Claude\claude-code-sessions\` | CCD (Claude Code) scheduled task state |

## Backup Before Reinstall

1. **Close Claude Desktop** (fully quit the app).
2. From MAS repo root:
   ```powershell
   .\scripts\claude-desktop-schedule-backup.ps1
   ```
3. A timestamped folder will be created on your Desktop, e.g.:
   `C:\Users\admin2\Desktop\ClaudeDesktopBackup_20260306_1500`
4. **Keep this folder** — do not delete it until after restore is verified.

## Reinstall Steps

1. Uninstall Claude Desktop (Settings → Apps → Claude → Uninstall).
2. Download and install the latest Claude Desktop from https://claude.ai/download.
3. **Log in at least once** so the account/org folder structure is recreated.
4. **Close Claude** before restoring.

## Restore After Reinstall

```powershell
.\scripts\claude-desktop-schedule-restore.ps1 -BackupPath "C:\Users\admin2\Desktop\ClaudeDesktopBackup_YYYYMMDD_HHmm"
```

Replace the path with your actual backup folder. Then start Claude Desktop — your schedules should appear and run as before.

## Log Files (for virtiofs/Plan9 debugging)

Claude Desktop logs are in:
`%APPDATA%\Claude\logs\`

| Log | Purpose |
|-----|---------|
| `main.log` | App lifecycle, ScheduledTasks, CCD init |
| `cowork_vm_node.log` | Cowork VM spawn, mounts, process lifecycle |
| `coworkd.log` | Cowork daemon |
| `cowork-service.log` | Cowork service |

The `RPC error -1: failed to ensure virtiofs mount: Plan9 mount failed: bad address` error is a known Windows Cowork issue (often WSL/virtiofs related). Reinstall resets VM state; schedules are preserved via this backup.

## Related

- Claude Desktop on Windows: https://claude.ai/download
- Cowork known issues: search Anthropic forums / GitHub for "virtiofs" or "Plan9" on Windows
