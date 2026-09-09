# VM 188 NAS model protection — 09 September 2026

**Date:** 09 September 2026  
**Status:** Live on MAS VM `192.168.0.188`  
**CMMC:** Mycosoft is **pursuing** CMMC L2 — not compliant. **RJ Ricasata is CFO.**  
**CUI:** This surface is outside the CUI boundary. No FOUO. No secrets in this file.

Related: `docs/NLM_WEIGHTS_ON_188_SEP09_2026.md` (3529fe33 owns scientific NLM). Do **not** bind `/api/nlm` to Ollama. Skip-startup stays **ON**. No 187 website cutover.

---

## Inventory (do not invent capacity)

| Store | What is actually there |
|---|---|
| **NAS `192.168.0.105`** | **8-bay chassis. Only two 8 TB drives populated now** (six bays empty). Not 28 TB free. |
| **Measured CIFS `df`** | `//192.168.0.105/mycosoft.com` on `/mnt/mycosoft-nas`: **7.3 T total, 142 G used, 7.2 T avail, 2%**. That is ~one 8 TB volume after RAID/filesystem overhead — treat usable as **~8 TB**, not 16 TB. |
| **UniFi Dream Machine `192.168.0.1`** | **27 TB** disk. **Protect-only.** SMB `445`/`139` and NFS `2049` are **closed**. HTTPS API is up. **No safe general share.** Do **not** wipe Protect recordings. Do **not** reformat. |
| **MAS 188 root** | Compute only. After the move: **98 G, 82 G used, 12 G avail, 89%**. Still too tight for multi-GB downloads. |

**Later (Morgan on site):** move the UDM 27 TB into an **empty NAS bay** (or replace/expand the pool). Until then, UDM storage is not a model volume.

---

## Mount (shared with FormSpace / 3529fe33)

| Item | Value |
|---|---|
| Share | `//192.168.0.105/mycosoft.com` |
| Mount | `/mnt/mycosoft-nas` |
| Persist | `/etc/fstab` (`_netdev`, credentials file, `noperm`) |
| Credentials | `/etc/samba/mycosoft-nas.creds` (mode `600`, not in git) |
| systemd `.mount` unit | **Not used.** A custom `mnt-mycosoft-nas.mount` fought the fstab generator and was **removed**. fstab is the persist path. |

```text
/mnt/mycosoft-nas/models/nlm/    FormSpace scientific NLM only (3529fe33)
/mnt/mycosoft-nas/models/myca/   MYCA chat/speech: Ollama GGUF, HF cache, speech
```

Never mix the two trees. Never copy Llama/Nemotron GGUF into `models/nlm`.

---

## What moved

| Before (188 root) | After (NAS) |
|---|---|
| `/usr/share/ollama/.ollama/models` ~4.6 G (`llama3.2:3b` + `nemotron-3-nano:4b`) | `/mnt/mycosoft-nas/models/myca/ollama` (blobs + manifests) |
| Checksums | `sha256sum --strict` on all 12 files — **OK** before local delete |
| Local leftover | Directory emptied and left **immutable** so a missed `OLLAMA_MODELS` cannot refill `/` |

Ollama drop-in: `/etc/systemd/system/ollama.service.d/nas-models.conf`

- `OLLAMA_MODELS=/mnt/mycosoft-nas/models/myca/ollama`
- `HF_HOME` / transformer caches → `/mnt/mycosoft-nas/models/myca/huggingface`
- `ExecStartPre=/usr/local/sbin/mycosoft-require-nas-models.sh`
- `ConditionPathIsMountPoint=/mnt/mycosoft-nas`
- Vendor `ExecStart=/usr/local/bin/ollama serve` (wrapper). Real binary: `/usr/libexec/ollama-bin`
- Existing `override.conf` still sets `OLLAMA_HOST=0.0.0.0:11434`

**Proved 09 September 2026 on `188:11434`:** `llama3.2:3b` and `nemotron-3-nano:4b` both `POST /api/generate` → `response_ok` with `eval_count=8`.

`mas-orchestrator` still has `MAS_SKIP_BACKGROUND_STARTUP=1`. No `NLM_OLLAMA_URL`. `/api/nlm` is not Ollama.

---

## Fail-closed (implemented, not just documented)

| Guard | Behavior |
|---|---|
| `mycosoft-require-nas-models.sh` | Exit **78** unless `/mnt/mycosoft-nas` is **CIFS** and `OLLAMA_MODELS` is on that share. No silent write to `/home` or `/usr`. |
| `mycosoft-disk-guard.sh` | Exit **79** if `df /` **≥ 80%** or root free **< 15 G**. Live check after move: **89% → REFUSE_PULL**. |
| `/usr/local/bin/ollama` wrapper | `pull` / `cp` / `create` / `push` require **both** guards. `serve` requires NAS only. |
| Hugging Face wrapper | Same NAS + disk guards; cache on `models/myca/huggingface`. |
| Local models dir | Immutable empty stub after verified copy. |
| If NAS unmounted | Ollama **does not start** (`ConditionPathIsMountPoint` + ExecStartPre). It does **not** recreate blobs on root. |

Repo copies (LF): `scripts/vm188_model_guards/`.

Once-only breathing room: journal vacuum freed ~293 M; `docker image prune` reclaimed 0 B. **Did not** prune Docker volumes (no Postgres/MINDEX data).

---

## How to recover

1. **NAS down / ollama dead:** confirm `findmnt -t cifs /mnt/mycosoft-nas`. If missing: `sudo mount /mnt/mycosoft-nas` (fstab). Then `sudo systemctl start ollama`.
2. **Mount works, models missing:** do **not** `ollama pull` while root is ≥ 80%. Re-rsync from a known-good NAS copy only.
3. **Emergency restore to 188 disk:** **forbidden** unless Morgan orders it. Would refill root and can kill the VM.
4. **Unlock the old path (debug only):** `sudo chattr -i /usr/share/ollama/.ollama/models` — then put immutability back.
5. **UDM 27 TB:** do not mount, format, or steal Protect. Physical move into a NAS bay is the expansion plan.
6. **NLM weights:** `models/nlm/incoming/` waits for Morgan’s files. He will send them; **we place them**. Do not tell him to copy. Never GGUF. Never bind `/api/nlm` to Ollama.

---

## Alert

188 root at **89% / 12 G free** is still the failure mode for anything that writes multi-GB to `/`. Pulls are **blocked**. Keep weights on NAS. Fill empty NAS bays or move the UDM disk into the NAS before growing the model set.
