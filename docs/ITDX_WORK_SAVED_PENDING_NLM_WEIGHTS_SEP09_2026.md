# ITDX work saved pending NLM weights — 09 September 2026

**Date:** 09 September 2026  
**Status:** Local commits only. **Push = NO. Deploy / blue-green = NO.** Live `mycosoft.com` was not touched.  
**CMMC:** Mycosoft is **pursuing** CMMC L2 — not compliant. **RJ Ricasata is CFO.**  
**CUI:** Outside the CUI boundary. No FOUO.

Morgan asked to save today's work so he can get to commit. FormSpace forecast weights are still outstanding. After he drops them, then push + production blue-green (NAS website assets mount required).

---

## Commits created this save (local only)

| Repo | Branch | SHA | Why |
|---|---|---|---|
| `MAS/mycosoft-mas` | `cursor/field-operator-live-observations-sep01` | `c945d7bc5` | Bind ITDX/FormSpace to real NAS NLM, never Ollama or stub 0.85 |
| `WEBSITE/website-itdx-codex-v13` | `cursor/itdx-codex-v13-connect-20260909` | `e197be61` | Keep today's Fusarium ITDX walkthrough proofs |
| `MAS/mycosoft-mas` (this note) | same as above | 65af353a4 | Record the save + next weights drop |

Website ITDX app code itself was already on `58384b2d` (`feat(itdx): ship Fusarium Intel Feed, Weka walkthrough, and owner-gated APIs`). Today's extra commit is proofs + verify scripts only.

---

## What was left uncommitted and why

| Location | Left dirty | Why |
|---|---|---|
| `WEBSITE/website` (`fix/launchpad-ingest-bearer-alias`) | Launchpad/auth/Fusarium MFA, `_bg_*` deploy scripts, August Psathyrella docs, `.codex-artifacts` | Unrelated main WIP. **No reset / checkout / discard.** Prefer the ITDX worktree. |
| `WEBSITE/website-itdx-codex-v13` | `next-env.d.ts` | Auto-generated Next types (`should not be edited`) |
| `MAS/NLM` | Entire `NLM Training/` Vite tree | Last write 05 May 2026 — not today's FormSpace work |
| MAS working tree | Poetry cache churn, Jetson/Psathyrella/CMMC July–Aug leftovers, `.secrets/`, `data/tmp_keys/`, July SOC routers (`security_evidence_api.py`, `soc_operating_history_api.py` + compliance emitters), `bluetracker_client.py`, `dsc_decoder_client.py`, binary `.gitignore` drift | Not 09 Sep ITDX/FormSpace. Secrets and keys stay out. July SOC imports were restored on `myca_main.py` after the save commit so that WIP is not lost. |

Never committed: `.credentials.local`, `.env`, `.env.local`, `.credentials.maps.env`, keys.

---

## Next (Morgan) — then push + blue-green

1. Drop FormSpace forecast artifacts on the shared NAS (do **not** copy blobs onto 188 disk):

   `\\192.168.0.105\mycosoft.com\models\nlm\incoming\weights.pt`  
   `\\192.168.0.105\mycosoft.com\models\nlm\incoming\model.json`

2. `model.json` should include `weights_sha256`, `model_sha256`, chart id, calibration id.
3. Then: push these local commits + production blue-green to the live site.
4. Website container must keep the NAS assets mount:  
   `-v /opt/mycosoft/media/website/assets:/app/public/assets:ro`
5. **NLM ≠ Ollama.** Llama/Nemotron on `:11434` stay MYCA chat (`/mnt/mycosoft-nas/models/myca`).  
   `GET /api/nlm/health` → `model_loaded=true` only from those NAS artifacts.  
   Stub **0.85 is never Fusarium p.** Frozen ITDX v1.4 synthetic `weights.pt` is legacy_reference only.

Related: `docs/NLM_WEIGHTS_ON_188_SEP09_2026.md`, `docs/FORMSPACE_NLM_REPOSITORY_MAP_SEP09_2026.md`, `docs/formspace_nlm_nas/README.md`.
