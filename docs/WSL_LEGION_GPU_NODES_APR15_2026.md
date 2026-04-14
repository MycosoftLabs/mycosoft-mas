# WSL2 Legion GPU Nodes — Earth2 + Voice (Ollama / HF)

**Date**: April 15, 2026  
**Status**: Complete (runbook)  
**Scope**: 4080A = Earth-2 stack; 4080B = PersonaPlex / Moshi / STT-TTS / Nemotron via Ollama-compatible endpoints  

---

## Roles (one GPU per machine)

| Machine | LAN IP (typical) | Role | WSL venv |
|---------|------------------|------|----------|
| Legion 4080A | 192.168.0.249 | Earth2 + `earth2_api_server.py` | `~/mycosoft-venvs/mycosoft-earth2-wsl` |
| Legion 4080B | 192.168.0.241 | Voice + Moshi + bridge + Ollama | `~/mycosoft-venvs/mycosoft-voice-wsl` |

---

## Storage layout (models, cache, data, memory artifacts)

Run **`Initialize-MycosoftDataLayout.ps1`** on Windows (`scripts/gpu-node/windows`) so HF, PyTorch, Ollama, and checkpoint paths use one tree. WSL setup runs **`wsl-mycosoft-data-layout.sh`** automatically (`~/mycosoft-data`, `~/mycosoft-data-env.sh`). Full detail: **`docs/STORAGE_LAYOUT_LEGION_GPU_APR15_2026.md`**.

---

## Prerequisites (Windows on each Legion)

1. **NVIDIA driver** on Windows — `nvidia-smi` works in **PowerShell** (Game Ready or Studio).
2. **WSL2 + Ubuntu** — `wsl --install` or `Bootstrap-Legion-GPU.ps1` (Administrator).
3. **First boot of Ubuntu** — create UNIX user; **do not** install Linux `.run` NVIDIA drivers inside WSL for consumer GPUs; WSL uses the Windows driver ([CUDA on WSL](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)).
4. **VC++ Redistributable** — still useful for any **native Windows** Python; WSL Python does not need it.

---

## One-shot WSL setup (run on each Legion, logged in locally or RDP)

From an elevated or normal PowerShell **in the `mycosoft-mas` repo**:

```powershell
cd C:\path\to\mycosoft-mas\scripts\gpu-node\windows

# 4080A (Earth2)
.\Invoke-WSLGPUNodeSetup.ps1 -Role Earth2

# 4080B (Voice)
.\Invoke-WSLGPUNodeSetup.ps1 -Role Voice
```

Or **inside WSL** after copying `scripts/gpu-node/wsl/wsl-gpu-node-setup.sh`:

```bash
bash wsl-gpu-node-setup.sh --role earth2 --yes   # or voice
```

This installs: system packages, **PyTorch CUDA (cu124 wheels)**, clones `mycosoft-mas`, role-specific pip packages, **Ollama**, Hugging Face CLI tooling.

---

## What gets installed (real stacks — no mocks)

- **Earth2 role**: `torch`, `torchvision`, `torchaudio`, `fastapi`, `uvicorn`, **`earth2studio`** (Linux pip), `hf-transfer`. You still configure **real checkpoints** and data sources per NVIDIA Earth-2 documentation.
- **Voice role**: `torch`, Moshi-related wheels (`moshi`, `sphn`, …), `services/personaplex-local/requirements*.txt`, `hf-transfer`. Models download from Hugging Face / Kyutai repos on first run (network required).
- **Both**: **Ollama** — pull models after install, e.g. `ollama pull llama3.1:8b`. Point MAS `nemotron` / OpenAI-compatible URLs to this host if you serve Nemotron-compatible models via Ollama or another server on the same machine.

---

## Systemd (optional, recommended for Ollama)

In WSL, enable systemd (Windows 11 recent builds):

```ini
# /etc/wsl.conf
[boot]
systemd=true
```

Then `wsl --shutdown` from Windows and reopen Ubuntu.

---

## Verification (inside WSL)

```bash
nvidia-smi
source ~/mycosoft-venvs/mycosoft-earth2-wsl/bin/activate   # or mycosoft-voice-wsl
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
ollama --version
```

---

## Docker (optional)

Use **Docker Desktop** with **WSL2 integration** for the Ubuntu distro to run `Dockerfile.moshi` / other GPU containers with `--gpus all` after NVIDIA Container Toolkit is configured in Docker Desktop.

---

## Env integration (MAS)

See `GPU_VOICE_IP`, `GPU_EARTH2_IP`, `MOSHI_API_URL`, `EARTH2_API_URL` in `.env` and `gpu-node-deploy` skill.
