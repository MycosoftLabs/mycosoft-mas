# NLM weights on 188 — 09 September 2026

**Date:** 09 September 2026  
**Status:** Ollama NLM adapter **reverted**. Handed to **3529fe33**.  
**CMMC:** Mycosoft is **pursuing** CMMC L2 — not compliant. **RJ Ricasata is CFO.**  
**CUI:** This surface is outside the CUI boundary. No FOUO.

---

## Morgan stop-order (same day)

Llama + Nemotron on MAS VM **192.168.0.188** stay for **MYCA chat only** (`:11434`).  
**NLM is a separate scientific model on NAS.** Do not wire `/api/nlm` to Ollama.

If `/api/nlm` was pointed at `127.0.0.1:11434`, that bind is **reverted**.

---

## What is true on 188

| Item | Fact |
|---|---|
| Hugging Face NLM checkpoint | **None** on NAS-mounted 188 paths or sibling VMs (eb8ec0f7). Do not search again. Do not download a second Llama. |
| `~/.mycosoft/nlm/models` | Training JSON / `training_runs.json` only — **not** weights |
| Ollama on 188 | `llama3.2:3b` (~1.9 GB) and `nemotron-3-nano:4b` (~2.7 GB) under `/usr/share/ollama/.ollama/models` — **MYCA chat**, not NLM |
| Standalone `:8200` | Sensory NLM API if present — **not** MAS `/api/nlm` and **not** a Llama load |
| Disk | ~94% / ~6.4 GB free — do not pull another GGUF |

---

## MAS `/api/nlm` after revert

- Loader restored to repo HEAD (no `backends.py`, no Ollama generate).
- Situation-assessment **ecology** stays **UNQUALIFIED** `p=null` until 3529fe33 binds the **NAS scientific** checkpoint.
- Stub **0.85 / 0.5** is never Fusarium `p`.
- Skip-startup stays **ON**. No 187 cutover. No full GBIF.
- `maps.env` not touched (Google Fusarium key is **6fe8797b**).

Reload after a real NAS checkpoint: `POST /api/nlm/load` or restart `mas-orchestrator`. Do **not** set `NLM_OLLAMA_URL` / do **not** inherit `OLLAMA_HOST` for NLM.

---

## NAS layout (09 September 2026, same day)

188 must **not** store model blobs on VM disk. One shared CIFS mount:

| Subtree | Owner | Contents |
|---|---|---|
| `/mnt/mycosoft-nas/models/nlm/` | FormSpace / scientific NLM | Empty except README until Morgan drops `incoming/weights.pt` + `model.json` |
| `/mnt/mycosoft-nas/models/myca/` | Sibling | Ollama Llama / Nemotron GGUF. Never in the nlm folder. |

`NLM_HOME` / `NLM_MODEL_DIR` point at the **nlm** subtree only. No Ollama bind. Skip-startup stays **ON**.

Stage A map: `docs/FORMSPACE_NLM_REPOSITORY_MAP_SEP09_2026.md`  
Stage B status: `docs/FORMSPACE_NLM_IMPLEMENTATION_STATUS_SEP09_2026.md`

`GET /api/nlm/health` stays `model_loaded=false` until real forecast artifacts load. Frozen ITDX v1.4 SHA `1d3fe486…` is **legacy_reference** only.

## Handoff to 3529fe33 (updated)

1. Do **not** copy GGUF or v1.4 synthetic `weights.pt` onto 188 disk or into `models/nlm`.
2. When Morgan sends forecast weights, drop them on NAS `models/nlm/incoming/`.
3. `GET http://192.168.0.188:8001/api/nlm/health` → `model_loaded=true` only from those artifacts.
4. Ecology **SCORED** only from a usable scientific score; else UNQUALIFIED `p=null`.
5. Leave `:11434` / `models/myca` for MYCA chat.
