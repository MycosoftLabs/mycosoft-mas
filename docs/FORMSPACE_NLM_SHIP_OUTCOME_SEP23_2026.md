# FormSpace + NLM Ship Outcome — September 23–24, 2026

**Date:** September 23–24, 2026 (PT)  
**Status:** Partial — **GitHub merged**; **public site restored 200** on pre-scrub `mkt2`; **feature cutover to `75d8e690` deferred** (Sandbox OOM during `next build`)  
**Related:** `docs/FORMSPACE_NLM_SESSION_COMPLETE_SEP23_2026.md`, `docs/BLUE_GREEN_NEVER_502_SOLE_OWNER_SEP23_2026.md`

---

## What completed

| Step | Result |
|------|--------|
| Verify MAS / MINDEX / FormSpace / NLM training+ingest / security | **Pass** |
| Docs + Host-aware HEALTHCHECK | Website **PR #334** → `75d8e690`; MAS **PR #162** → `fd133ef99` |
| Ship outcome docs | Website **PR #335** → `ffd7c4e2`; MAS **PR #163** → `6f77fa978` |
| MINDEX FormSpace spine | Already on main `b1137e9` (PR #16) |
| Sole-owner freeze clear (Morgan-ordered) | Done at ship start |
| Candidate build from `origin/main` | Reached Next.js production build then **host RAM exhaustion** |
| Primary during build | Remained on `mycosoft-website-candidate-mkt2` until OOM made origin briefly unavailable |
| Emergency restore (never-502) | Killed build; proved `mkt2` candidate IP **200**; nginx → `mkt2`; freeze re-armed at `/opt/mycosoft/state/CUTOVER_FROZEN` |
| Origin + sandbox + apex after restore | **200** (incl. `/myca/nlm`, `/ai/formspace`, favicon) |

## What did **not** cut over

- Live image remains **`mycosoft-website:mkt2-978fdcb`** (`mycosoft-website-candidate-mkt2`).
- Intended candidate **`mycosoft-website:fnlm923-75d8e690`** was **not** produced / not cut over.
- Zero intentional 502 cutover; brief origin outage was OOM under concurrent `next build`, not nginx mis-point.

## Current sole upstream (re-armed 2026-09-24)

```
SOLE_UPSTREAM=mycosoft-website-candidate-mkt2
CUTOVER_FROZEN=FROZEN=1 @ /opt/mycosoft/state/CUTOVER_FROZEN
active-slot=mycosoft-website-candidate-mkt2
nginx set $upstream_host mycosoft-website-candidate-mkt2
candidate IP 172.28.0.6 → 200 (Host-aware)
```

## Follow-up

1. Build `75d8e690`/`ffd7c4e2` on ≥16GB RAM host (or add Sandbox swap; prefer cached BuildKit).
2. Start candidate alongside healthy `mkt2`, probe candidate **IP** 200, single nginx cutover.
3. Keep `mkt2` as rollback until public 200 streak.

## SHAs

| Repo | SHA |
|------|-----|
| Website main | `ffd7c4e2` (includes ship outcome doc) |
| Website feature tip (pre-outcome) | `75d8e690` |
| MAS main | `6f77fa978` |
| MINDEX main | `b1137e9` |
| Live container / image | `mycosoft-website-candidate-mkt2` / `mkt2-978fdcb` |
