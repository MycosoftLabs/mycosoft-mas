# Repo LICENSE / NOTICE / README Sweep Complete — Jun 25, 2026

**Date:** 2026-07-02  
**Status:** Complete (local working copies)  
**Related:** `docs/DEFENSE_LICENSE_CI_HANDOFF_JUN25_2026.md`, `docs/ITAR_EXPORT_CONTROL_INVENTORY_JUN25_2026.md`, `C:\Users\Owner1\Downloads\CURSOR_HANDOFF.md`

---

## Scope

Aligned local Mycosoft repos with proprietary licensing and export-control notice language. **Docs/LICENSE/NOTICE/README only** — no CI, deployment, or application code changes.

**Morgan overrides applied:**

- **No repo visibility changes** (all remain as-is on GitHub; spot-check showed PUBLIC for core repos).
- **Six third-party forks** not touched (NOTICE-only if needed later).
- Did not duplicate merged GitHub PR work where remote `main` already had LICENSE/NOTICE; local copies were behind and are now synced/enhanced.

---

## Standard files applied

| File | Content |
|------|---------|
| `LICENSE` | Proprietary all-rights-reserved; EAR/ITAR export-control; DoD/government use; NIST/CMMC organizational alignment (no certification claim) |
| `NOTICE` | Proprietary header; marine/acoustic/defense sensing export-awareness |
| `README.md` | Header block + `## License and export control` section linking LICENSE/NOTICE |

Script: `scripts/apply_repo_license_notice_sweep.py`

---

## Per-repo status

| Repo (local path) | LICENSE | NOTICE | README section | Notes |
|-------------------|---------|--------|----------------|-------|
| `MAS/mycosoft-mas` | Added/updated | Added | Updated | Remote main already had LICENSE/NOTICE; local synced + CMMC/NIST lines |
| `WEBSITE/website` | Added | Added | Updated | Replaced minimal copyright footer with full export-control section |
| `MINDEX/mindex` | Added | Added | Updated | Includes sine-acoustic-classifier tree (flagged in ITAR inventory) |
| `mycobrain` | Updated | Updated | Updated | Had prior proprietary files; aligned to canonical text |
| `NATUREOS/NatureOS` | Added | Added | Updated | |
| `Mycorrhizae/mycorrhizae-protocol` | Added | Added | Updated | |
| `MAS/NLM` | Replaced MIT → proprietary | Added | Updated | Local had MIT; aligned to org standard |
| `MAS/sdk` | Replaced MIT → proprietary | Added | Updated | Local had MIT; aligned to org standard |
| `platform-infra` | Added | Added | Updated | No MycosoftLabs remote match found |
| `MYCODAO` | Added | Added | Updated | |
| `Devices/psathyrella-jetson` | Added | Added | Updated | Local-only path; flagged REVIEW in ITAR inventory |

---

## Alignment with 25 license PRs (Claude Code handoff)

`CURSOR_HANDOFF.md` documents branch `claude/mycosoftlabs-license-sweep-hk68z8` with draft PRs for 25 org repos. `docs/DEFENSE_LICENSE_CI_HANDOFF_JUN25_2026.md` records those PRs as merged on 2026-07-02.

This sweep:

- **Did not** re-open or duplicate those PRs.
- **Did** bring **local dev copies** in sync where they lacked LICENSE/NOTICE.
- **Did** add README license sections (not present on remote READMEs at sweep time).
- **Did** extend LICENSE with explicit NIST/CMMC organizational language and DoD use clause.

---

## Third-party forks (unchanged)

| Fork | LICENSE action |
|------|----------------|
| AgaricFlight | Upstream OSS — no change |
| MycaControl | Upstream OSS — no change |
| Mycowallet-android | Upstream OSS — no change |
| mycelium-library | Upstream OSS — no change |
| intersection_observer | Upstream OSS — no change |
| Agaric | Upstream OSS — no change |

---

## Git commits (local)

Commits created per repo on branch `chore/license-notice-readme-sweep-jun25-2026` (or `main` where no branch existed). **Not pushed** — Morgan review first.

See agent output / `git log` in each repo for commit SHAs.

---

## Verification

```powershell
# Spot-check files exist
$repos = @(
  "MAS\mycosoft-mas","WEBSITE\website","MINDEX\mindex","mycobrain",
  "NATUREOS\NatureOS","Mycorrhizae\mycorrhizae-protocol","MAS\NLM","MAS\sdk",
  "platform-infra","MYCODAO","Devices\psathyrella-jetson"
)
$base = "D:\Users\admin2\Desktop\MYCOSOFT\CODE"
foreach ($r in $repos) {
  $p = Join-Path $base $r
  "$r LICENSE=$(Test-Path $p\LICENSE) NOTICE=$(Test-Path $p\NOTICE)"
}

# Visibility unchanged
gh repo view MycosoftLabs/mycosoft-mas --json visibility
gh repo view MycosoftLabs/website --json visibility
```

---

## Follow-up for Morgan

1. Review `docs/ITAR_EXPORT_CONTROL_INVENTORY_JUN25_2026.md` before any private flip.
2. Approve push of per-repo commits (or squash into existing license PR follow-ups).
3. Optional: NOTICE-only PRs for six forks.
4. If README sections should also land on GitHub `main`, push website/MAS README commits after review.
