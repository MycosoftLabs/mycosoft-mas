# Defense License + CI Handoff — Jun 25, 2026

**Date:** 2026-07-02  
**Status:** Complete (amended scope — public repos retained)  
**Related:** `C:\Users\Owner1\Downloads\CURSOR_HANDOFF.md` (original Claude Code handoff)  
**Amended doc:** `docs/CURSOR_HANDOFF_DEFENSE_LICENSE_JUN25_2026.md`

---

## Morgan's decision (overrides original handoff Phase 3)

| Original handoff | Amended decision |
|------------------|------------------|
| Flip 24 public repos to **private** | **SKIP** — all repos stay **PUBLIC** |
| Add GitHub App / PAT for private cross-repo CI | **Not needed** while public |
| Re-auth Cursor/Codex/Claude/Perplexity for private repos | **Not needed** — public = no OAuth blockers |

**Rationale:** Code stays public for AI tooling (Cursor, Perplexity, Codex, Claude) and existing CI tokens. Legal protection is via **LICENSE + NOTICE + SECURITY.md**, not repo visibility.

---

## What was fixed (CI — pre-existing failures on `main`)

### 1. `mycosoft-mas` — `poetry lock`

**Failure:** `pyproject.toml changed significantly since poetry.lock was last generated`  
**Fix:** Regenerated `poetry.lock` with `poetry lock`  
**Commit:** `808d19beb` — `chore(ci): regenerate poetry.lock to match pyproject.toml`  
**Verify:**
```bash
cd mycosoft-mas && poetry lock --check && poetry install --no-interaction
```

### 2. `NatureOS` — `WorkflowDefinition.Id`

**Failure:** `CS1061 'WorkflowDefinition' does not contain a definition for 'Id'` at `WorkflowController.cs:105`  
**Root cause:** Model property is `WorkflowId`, not `Id`  
**Fix:** Changed `saved.Id` → `saved.WorkflowId` in deep-agent publish context  
**Commit:** `0bd67f3` — `fix(ci): use WorkflowId on WorkflowDefinition in save event`  
**Verify:**
```bash
cd NatureOS && dotnet build src/core-api/NatureOS.CoreApi.csproj
```

### 3. `mycobrain` — `mdp_types.h`

**Failure:** `fatal error: mdp_types.h: No such file or directory` in gateway CI build  
**Root cause:** Header exists in `firmware/common/` but PlatformIO LDF did not add include path in CI  
**Fix:** Added `-I../common` to `build_flags` in `firmware/gateway/platformio.ini` and `firmware/side_b/platformio.ini`  
**Commit:** `e35055e` — `fix(ci): add ../common include path for MDP headers`  
**Verify:**
```bash
cd mycobrain/firmware/gateway && pio run
cd mycobrain/firmware/side_b && pio run
```

---

## License / NOTICE / SECURITY sweep (25 repos)

**Branch:** `claude/mycosoftlabs-license-sweep-hk68z8`  
**Action taken:** All 25 draft PRs marked **ready for review** and **squash-merged** to `main` (2026-07-02).

| Repo | PR | Files added |
|------|-----|-------------|
| MycosoftLabs | #1 | LICENSE, NOTICE, SECURITY.md |
| mycobrain | #9 | LICENSE, NOTICE, SECURITY.md |
| NatureOS | #13 | LICENSE, NOTICE, SECURITY.md |
| website | #231 | LICENSE, NOTICE, SECURITY.md |
| mycosoft-mas | #118 | LICENSE, NOTICE, SECURITY.md |
| NLM | #5 | LICENSE, NOTICE, SECURITY.md |
| mycelium-sim | #1 | LICENSE, NOTICE, SECURITY.md |
| myceliumsim | #1 | LICENSE, NOTICE, SECURITY.md |
| petridishsim | #1 | LICENSE, NOTICE, SECURITY.md |
| mycosoft-embodiment | #1 | LICENSE, NOTICE, SECURITY.md |
| sdk | #1 | LICENSE, NOTICE, SECURITY.md |
| BtcOrdinalsPlugin | #1 | LICENSE, NOTICE, SECURITY.md |
| security-app | #1 | LICENSE, NOTICE, SECURITY.md |
| Mycorrhizae | #1 | LICENSE, NOTICE, SECURITY.md |
| mycodao-app | #1 | LICENSE, NOTICE, SECURITY.md |
| mindex | #11 | LICENSE, NOTICE, SECURITY.md |
| MYCODAO | #1 | LICENSE, NOTICE, SECURITY.md |
| mycalab | #1 | LICENSE, NOTICE, SECURITY.md |
| mycoforge | #1 | LICENSE, NOTICE, SECURITY.md |
| Fusarium | #1 | LICENSE, NOTICE, SECURITY.md |
| BertoFirmware-Sandbox | #1 | LICENSE, NOTICE, SECURITY.md |
| myco-marketing-site | #1 | LICENSE, NOTICE, SECURITY.md |
| jetson-workspace | #1 | LICENSE, NOTICE, SECURITY.md |
| claude-skills-library | #1 | LICENSE, NOTICE, SECURITY.md |
| Myco-hardware-RD | #1 | LICENSE, NOTICE, SECURITY.md |

**License type:** Proprietary / all-rights-reserved with export-control and confidentiality language (see PR branch or merged files on `main`).

### Six third-party forks — NOT relicensed

Left upstream OSS `LICENSE` intact. **NOTICE only** if ownership signaling is needed later:

- AgaricFlight
- MycaControl
- Mycowallet-android
- mycelium-library
- intersection_observer
- Agaric

---

## What stays public and why

- All MycosoftLabs repos remain **PUBLIC** (verified via `gh repo view --json visibility`).
- **No** `gh repo edit --visibility private` was executed.
- Public visibility preserves:
  - Cursor / GitHub integration without org OAuth re-approval
  - Default `GITHUB_TOKEN` cross-repo access in Actions (while public)
  - Existing deploy pipelines, webhooks, and third-party CI
- **Legal posture:** Proprietary LICENSE asserts no use without written authorization; NOTICE documents ownership and export-control awareness. This is **not** ITAR/CMMC/CUI classification — it is standard proprietary + export-control header language.

---

## What NOT to do (until Morgan explicitly requests)

1. **Do not** flip repos to private (Phase 3 of original handoff).
2. **Do not** add CI gates that block existing pipelines.
3. **Do not** neuter deployments, routes, or APIs.
4. **Do not** put proprietary LICENSE on the six third-party forks.
5. **Do not** rotate or replace GitHub tokens for private-repo access (not needed while public).

---

## CI verification commands (quick smoke)

```powershell
# MAS
cd MAS/mycosoft-mas
poetry lock --check

# NatureOS
cd NATUREOS/NatureOS
dotnet build src/core-api/NatureOS.CoreApi.csproj

# mycobrain
cd mycobrain/firmware/gateway
pio run

# GitHub Actions (remote)
gh run list --repo MycosoftLabs/mycosoft-mas --workflow mas-ci --limit 1
gh run list --repo MycosoftLabs/NatureOS --limit 3
gh run list --repo MycosoftLabs/mycobrain --workflow ci.yml --limit 1

# Visibility spot-check (must say PUBLIC)
gh repo view MycosoftLabs/mycosoft-mas --json visibility
gh repo view MycosoftLabs/NatureOS --json visibility
gh repo view MycosoftLabs/mycobrain --json visibility
```

---

## Agent access notes

| Tool | Public repos | Action needed |
|------|--------------|---------------|
| **Cursor** | Works | None — GitHub App already has org access |
| **Claude Code / Desktop** | Works | None while public |
| **Codex** | Works | None while public |
| **Perplexity** | Works | None while public |
| **GitHub Actions** | Works | Default `GITHUB_TOKEN` sufficient for public sibling repos |

If Morgan later requests private visibility, revisit original handoff **Phase 3 + Section 5 + Section 6** for GitHub App/PAT and per-tool re-authorization.

---

## Remaining for Morgan (human decisions)

1. **Private flip timing** — when/if to execute Phase 3 (not done).
2. **Fork NOTICE PRs** — optional separate PRs for 6 forks (NOTICE only).
3. **Deploy workflow failures** — NatureOS `Deploy to Production` may fail independently of build; review if deploy should run on every push.
4. **Dependabot backlog** — separate from this handoff; MAS/NatureOS have open vulnerability alerts.

---

## Lessons learned

- License sweep PRs are docs-only and can merge independently of CI fixes.
- `mdp_types.h` was always in-repo; CI needed explicit `-I../common`, not a private submodule.
- Keeping repos public avoids a large re-auth and cross-repo token project while LICENSE still restricts unauthorized use.
