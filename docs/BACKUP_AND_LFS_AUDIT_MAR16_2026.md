# Backup and LFS Audit — Mar 16, 2026

**Status:** Chat backup working; LFS working; one duplicate backup task pending removal (requires Admin)

---

## Chat Backup

| Item | Status |
|------|--------|
| **Primary backup** | `Mycosoft-CursorChatBackup` — `scripts/cursor-chat-backup.ps1` @ 1 AM |
| **Destination** | `C:\Users\admin2\Desktop\MYCOSOFT\BACKUPS\cursor-chats` |
| **Scope** | ai-code-tracking.db, workspaceStorage, globalStorage, agents, plans, skills, rules |
| **Retention** | 30 days |
| **Last run** | Mar 16, 2026 (~11 GB) |

### Duplicate (to remove)

| Item | Action |
|------|--------|
| **Duplicate task** | `Mycosoft-Cursor-Chat-Backup` — `scripts/backup-cursor-chats.ps1` @ noon |
| **Destination** | `E:\CursorBackups` |

**To remove:** Run `scripts\remove-duplicate-backup-task.ps1` **as Administrator** (Right-click PowerShell → Run as Administrator).

---

## LFS Cleanup

| Item | Status |
|------|--------|
| **Task** | `Mycosoft-LFS-Cleanup` — `scripts/prevent-lfs-bloat.ps1` |
| **Schedule** | Hourly |
| **Last run** | Mar 16, 2026 7:54 PM, Result: 0 (success) |
| **MAS repo** | ~0 MB in `.git/lfs`, smudge/fetch skipped |

---

## Files Changed

- `scripts/remove-duplicate-backup-task.ps1` — New; run as Admin to remove duplicate task
- `scripts/backup-cursor-chats.ps1` — Deprecation notice added; points to primary backup
