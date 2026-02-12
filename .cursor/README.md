# Mycosoft Cursor (Rules, Agents, Skills)

This folder is the **workspace** source for Cursor rules, agents, and skills. So that they are **fully implemented in the Cursor system** (available globally, not only when this workspace is open), sync them to the user Cursor directory after any change.

## After creating or updating

From the **MAS repo root** (mycosoft-mas):

```bash
python scripts/sync_cursor_system.py
```

This copies:

- `rules/*.mdc` → `%USERPROFILE%\.cursor\rules\`
- `agents/*.md` → `%USERPROFILE%\.cursor\agents\`
- `skills/<name>/` → `%USERPROFILE%\.cursor\skills\<name>\`

See `.cursor/rules/cursor-system-registration.mdc` for the full rule.
