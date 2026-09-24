# FormSpace + NLM Ship Outcome — September 23–24, 2026

**Date:** September 23–24, 2026 (PT)  
**Status:** Partial — **GitHub merged**; **public site restored 200** on pre-scrub `mkt2`; **feature cutover to `75d8e690` deferred** (Sandbox OOM during `next build`)  
**Related:** `docs/FORMSPACE_NLM_SESSION_COMPLETE_SEP23_2026.md`, `docs/BLUE_GREEN_NEVER_502_SOLE_OWNER_SEP23_2026.md`

---

## What completed

| Step | Result |
|------|--------|
| Verify MAS / MINDEX / FormSpace / NLM training+ingest / Merkle | **Pass** (see session complete doc) |
| Docs + Host-aware HEALTHCHECK | Merged website **PR #334** → `75d8e690`; MAS **PR #162** → `fd133ef99` |
| MINDEX FormSpace spine | Already on main `b1137e9` (PR #16) — no extra delta |
| Sole-owner freeze clear (Morgan-ordered) | Done at ship start |
| Candidate build from `origin/main` | Reached Next.js “Creating an optimized production build…” then **host RAM exhaustion** |
| Primary during build | Remained on `mycosoft-website-candidate-mkt2` until OOM made origin **000** briefly |
| Emergency restore (never-502) | Killed build; proved `mkt2` IP **200**; nginx → `mkt2`; freeze re-armed |
| Origin + sandbox + apex after restore | **200** |

## What did **not** cut over

- Live image remains **`mycosoft-website:mkt2-978fdcb`** (`mycosoft-website-candidate-mkt2`).
- Intended candidate image **`mycosoft-website:fnlm923-75d8e690`** was **not** produced / not cut over.
- Zero intentional 502 cutover path; brief origin **000** was OOM under concurrent `next build`, not an nginx mis-point.

## Follow-up (recommended)

1. Build `75d8e690` on a host with **≥16 GB RAM** (or add Sandbox swap / stop non-website containers for the build window only).  
2. Prefer **cached** BuildKit build (avoid `--no-cache` unless required).  
3. Start candidate **alongside** healthy `mkt2`, probe candidate **IP** 200 (Host-aware), then single nginx cutover.  
4. Keep `mkt2` as rollback until post-cutover public 200 streak.

## Current sole upstream

```
SOLE_UPSTREAM=mycosoft-website-candidate-mkt2
CUTOVER_FROZEN=1 (restore lock)
active-slot=mycosoft-website-candidate-mkt2
```

## SHAs

| Repo | SHA |
|------|-----|
| Website main (merged ship docs/healthcheck) | `75d8e690` |
| MAS main | `fd133ef99` |
| MINDEX main | `b1137e9` |
| Live container image | `mkt2-978fdcb` (pre-feature cutover) |
