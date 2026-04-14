# Storage layout — Legion GPU nodes (Windows + WSL)

**Date**: April 15, 2026  
**Status**: Complete  

---

## Purpose

One **predictable tree** on each machine for **weights**, **Hugging Face / PyTorch caches**, **Ollama models**, **datasets**, **scratch**, **logs**, and **local memory artifacts** (embeddings / RAG working files — not system RAM). All paths point at **real** storage; services read env vars below.

---

## Windows (native apps: Docker Desktop, some Python, Ollama Windows)

Run once per host (PowerShell):

```powershell
cd scripts\gpu-node\windows
.\Initialize-MycosoftDataLayout.ps1 -Role Earth2    # 4080A — tag only
# or
.\Initialize-MycosoftDataLayout.ps1 -Role Voice     # 4080B

# Large secondary drive (recommended):
.\Initialize-MycosoftDataLayout.ps1 -RootPath "D:\MycosoftData" -Role Voice
```

**Default root:** `%USERPROFILE%\MycosoftData`

### Directory tree

| Path (under root) | Use |
|-------------------|-----|
| `models/earth2` | Earth-2 / earth2studio checkpoints (set in API / NVIDIA config) |
| `models/voice` | Voice weights not stored only in HF hub cache |
| `models/shared` | Shared large artifacts |
| `weights` | Extra weight files or admin symlinks |
| `cache/huggingface` | `HF_HOME` — Hub + datasets cache |
| `cache/torch` | `TORCH_HOME` |
| `cache/pip` | `PIP_CACHE_DIR` |
| `ollama` | `OLLAMA_MODELS` (see Ollama docs; restart Ollama after changing) |
| `data`, `data/datasets` | NetCDF/Zarr/audio/training data |
| `memory/embeddings` | On-disk embedding / vector working set |
| `memory/working` | RAG or session-bound scratch |
| `scratch` | Ephemeral processing |
| `logs` | Service logs |

### Environment variables set (User scope)

`MYCOSOFT_DATA_ROOT`, `HF_HOME`, `HF_HUB_CACHE`, `HUGGINGFACE_HUB_CACHE`, `HF_DATASETS_CACHE`, `TRANSFORMERS_CACHE`, `TORCH_HOME`, `PIP_CACHE_DIR`, `XDG_CACHE_HOME`, `OLLAMA_MODELS`, `MYCOSOFT_EARTH2_CHECKPOINTS`, `MYCOSOFT_VOICE_MODELS`, `MYCOSOFT_LOCAL_MEMORY`

Open a **new** terminal (or sign out/in) after running so processes pick up env vars.

---

## WSL2 Ubuntu

`wsl-gpu-node-setup.sh` runs `wsl-mycosoft-data-layout.sh`, which creates **`~/mycosoft-data`** (or `$MYCOSOFT_DATA_ROOT` if preset) and writes **`~/mycosoft-data-env.sh`**, sourced from **`~/.bashrc`**.

To use the **same** files as Windows (single copy on fast NTFS), **before** first layout run in WSL:

```bash
export MYCOSOFT_DATA_ROOT=/mnt/d/MycosoftData   # example: D: drive
bash ~/mycosoft-wsl-setup/wsl-mycosoft-data-layout.sh --yes
```

Note: heavy training on `/mnt/c` or `/mnt/d` can be slower than `ext4` under `$HOME`; for maximum I/O, keep WSL-native `~/mycosoft-data` on the virtual disk and **sync** large blobs with `robocopy`/`rsync` if needed.

---

## Alignment with MAS / Earth2 / voice

- Point Earth2 API and earth2studio configs at **`MYCOSOFT_EARTH2_CHECKPOINTS`** (or `models/earth2` under `MYCOSOFT_DATA_ROOT`).
- PersonaPlex / Moshi: HF models respect **`HF_HOME`**; optional extra files under **`models/voice`**.
- Nemotron / Ollama: **`OLLAMA_MODELS`** + `ollama pull …` for real weights.

---

## Scripts

| Script | Role |
|--------|------|
| `scripts/gpu-node/windows/Initialize-MycosoftDataLayout.ps1` | Windows tree + User env |
| `scripts/gpu-node/wsl/wsl-mycosoft-data-layout.sh` | WSL tree + `~/mycosoft-data-env.sh` |
