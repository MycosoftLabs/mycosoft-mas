# CTO VM Blueprint Plan Audit — Mar 7, 2026

**Status:** Audit complete. Recommended updates documented below.

**Plan:** `C:\Users\admin2\.cursor\plans\cto_vm_blueprint_bc9af924.plan.md`

---

## Conflicts

| Issue | Location | Resolution |
|-------|----------|------------|
| **Stale Proxmox 90 references** | `csuite_rollout_build_079379c6.plan.md` references `proxmox90_csuite.yaml`, `192.168.0.90`, `validate_proxmox90_feasibility.py` | `proxmox90_csuite.yaml` does not exist. Canonical config is `proxmox202_csuite.yaml` (Proxmox 202). CTO plan correctly identifies retiring Proxmox 90—add explicit note: "Ignore csuite_rollout_build plan's Proxmox 90 references; they are stale." |
| **proxmox202 config comment** | `config/proxmox202_csuite.yaml` line 31: `validate_proxmox90_feasibility.py` | Script name in comment is stale. Rename or update comment to `validate_proxmox202_feasibility.py` (or equivalent) when implementing. |

---

## Errors

| Error | Location | Fix |
|-------|----------|-----|
| **VS Code winget ID wrong** | `config/csuite_role_manifests.yaml` CTO apps: `Microsoft.VisualCode` | Change to `Microsoft.VisualStudioCode` (correct winget ID). |
| **apply_role_manifest.ps1 fallback** | Line 20: `Microsoft.VisualCode` | Same fix: use `Microsoft.VisualStudioCode`. |
| **GitHub CLI winget ID** | Manifest: `GitHub.cli` | Verify: correct ID is `GitHub.cli` (lowercase). |

---

## Bad Logic / Gaps

| Item | Notes |
|------|-------|
| **Clone chain order** | Config has CTO clone_from CEO (192), CFO clone_from CTO (194), COO clone_from CFO (193). Phase 2 correctly plans neutral base. No logic error. |
| **COO watchdog reuse** | Plan says "Reuse COO continuity pattern" for CTO—correct. It means reuse the *pattern* (scheduled task + watchdog), not the Cowork scripts. CTO needs Cursor/OpenClaw watchdog, not Cowork. |
| **CFO plan completeness** | CFO MCP Connector plan is complete. CTO blueprint correctly references Meridian adapter as the *reference* for building Forge. |
| **Proxmox 90 vs 202** | Only `proxmox202_csuite.yaml` exists. Any script named `validate_proxmox90_*` should be updated to 202 or made config-agnostic. |

---

## Recommended Updates to CTO Plan

Add these before handing to another agent:

1. **Phase 8 (Verification)** — Add bullet:
   - "Validate winget IDs in `csuite_role_manifests.yaml` (e.g. `Microsoft.VisualStudioCode` not `Microsoft.VisualCode`)."

2. **Explicit Gaps** — Add:
   - "Winget IDs in manifests may be incorrect; verify before bootstrap."

3. **Stale plan cross-reference** — In "Current Truth" or Phase 1, add:
   - "Note: `csuite_rollout_build` plan still references Proxmox 90 and `proxmox90_csuite.yaml`. These are obsolete. Use `proxmox202_csuite.yaml` and Proxmox 202 (192.168.0.202) only."

4. **Optional** — Add implementation note in Phase 4:
   - "During bootstrap, verify winget installs succeed; fix IDs in manifests if needed."

---

## Summary

- **Conflicts:** Proxmox 90 vs 202 (config is 202; some docs/plans stale).
- **Errors:** VS Code winget ID wrong in manifests and fallback.
- **Logic:** Plan structure is sound. Reuse patterns are correct.
- **Recommendation:** Apply the four updates above, fix winget IDs in config/manifests, then proceed with implementation.
