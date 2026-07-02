# Cursor Handoff — Defense License + CI (Amended)

**Date:** 2026-07-02  
**Status:** Executed per Morgan's amended scope  
**Original source:** `C:\Users\Owner1\Downloads\CURSOR_HANDOFF.md` (Claude Code, 2026-07-02)

---

## Amendment summary (Morgan decision — overrides original)

| Phase | Original handoff | **Executed** |
|-------|------------------|--------------|
| **1** | Mark ready + merge 25 license PRs | **Done** — all 25 squash-merged |
| **2** | Forks: NOTICE only, no proprietary LICENSE | **Skipped** — no fork PRs created |
| **3** | Flip 24 public repos **private** | **SKIPPED** — repos stay **PUBLIC** |
| **4** | Fix 3 CI failures | **Done** — see completion doc |
| **5–6** | Private-repo CI tokens + AI re-auth | **Not applicable** while public |

**Completion doc:** [DEFENSE_LICENSE_CI_HANDOFF_JUN25_2026.md](./DEFENSE_LICENSE_CI_HANDOFF_JUN25_2026.md)

---

## What was executed

### License sweep (Phase 1)

- Branch: `claude/mycosoftlabs-license-sweep-hk68z8`
- 25 repos: `LICENSE`, `NOTICE`, `SECURITY.md` (proprietary + export-control headers)
- All PRs marked ready and squash-merged with `--admin`
- **6 forks not touched:** AgaricFlight, MycaControl, Mycowallet-android, mycelium-library, intersection_observer, Agaric

### CI fixes (Phase 4)

1. **mycosoft-mas** — `poetry lock` regenerated (`808d19beb`)
2. **NatureOS** — `saved.Id` → `saved.WorkflowId` (`0bd67f3`)
3. **mycobrain** — `-I../common` + `file://../common` in `lib_deps` for gateway/side_b

### NOT executed

- No `gh repo edit --visibility private`
- No CI gate changes
- No deployment/API neutering
- No GitHub App / PAT org secrets for private cross-repo access

---

## Verification checklist (amended)

- [x] All 25 license PRs merged
- [x] **No** visibility changes — repos remain PUBLIC
- [x] CI fixes pushed to `main` on mycosoft-mas, NatureOS, mycobrain
- [ ] Confirm CI green on all three (monitor GitHub Actions after linker fix push)
- [x] AI agents (Cursor, etc.) unaffected — public repos need no re-auth
- [ ] Optional: fork NOTICE PRs (Morgan decision)

---

## Commands reference (from original handoff, amended)

### Merge license PRs (already done)

```bash
BRANCH=claude/mycosoftlabs-license-sweep-hk68z8
# See DEFENSE_LICENSE_CI_HANDOFF_JUN25_2026.md for full PR table
gh pr merge <num> --repo MycosoftLabs/<repo> --squash --admin
```

### Phase 3 — DO NOT RUN until Morgan requests

```bash
# ORIGINAL HANDOFF — NOT EXECUTED
# gh repo edit "MycosoftLabs/$r" --visibility private ...
```

### CI verification

See [DEFENSE_LICENSE_CI_HANDOFF_JUN25_2026.md](./DEFENSE_LICENSE_CI_HANDOFF_JUN25_2026.md#ci-verification-commands-quick-smoke).

---

## For future private flip (when Morgan approves)

Re-read original handoff sections 3, 5, 6 in `C:\Users\Owner1\Downloads\CURSOR_HANDOFF.md`:

- GitHub App or fine-grained PAT for cross-repo CI
- Per-tool GitHub org re-authorization (Cursor, Codex, Claude, Perplexity)
- Org third-party access approval

Until then: **LICENSE + NOTICE protect code legally; public visibility preserves tooling.**
