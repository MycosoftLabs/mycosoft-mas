#!/usr/bin/env bash
# =============================================================================
# WSL2 Ubuntu GPU node setup — Earth2 OR Voice (PersonaPlex / Moshi / TTS / STT)
# Run INSIDE WSL:  bash scripts/gpu-node/wsl/wsl-gpu-node-setup.sh --role earth2
#
# Prerequisites (Windows host):
#   - Latest NVIDIA Game Ready / Studio driver (nvidia-smi works in PowerShell)
#   - WSL2 + Ubuntu 22.04
#   - Do NOT install Linux .run NVIDIA drivers in WSL — use Windows driver + CUDA user libs below
#
# Date: April 15, 2026
# =============================================================================
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

ROLE=""
AUTO_YES=false
REPO_URL="${MYCOSOFT_REPO_URL:-https://github.com/MycosoftLabs/mycosoft-mas.git}"
REPO_DIR="${MYCOSOFT_REPO_DIR:-$HOME/mycosoft-mas}"
VENV_BASE="${MYCOSOFT_VENV_BASE:-$HOME/mycosoft-venvs}"
CUDA_INDEX="${CUDA_INDEX_URL:-https://download.pytorch.org/whl/cu124}"

while [[ $# -gt 0 ]]; do
  case $1 in
    --role) ROLE="$2"; shift 2 ;;
    --yes|-y) AUTO_YES=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [[ "$ROLE" != "earth2" && "$ROLE" != "voice" ]]; then
  echo "Usage: $0 --role earth2|voice [--yes]"
  exit 1
fi

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log() { echo -e "${GREEN}[wsl-gpu]${NC} $*"; }
warn() { echo -e "${YELLOW}[wsl-gpu]${NC} $*"; }
err() { echo -e "${RED}[wsl-gpu]${NC} $*"; }

if ! command -v nvidia-smi &>/dev/null; then
  err "nvidia-smi not found in WSL. Install/update NVIDIA drivers on WINDOWS, reboot, then open WSL again."
  err "See: https://docs.nvidia.com/cuda/wsl-user-guide/index.html"
  exit 1
fi

log "GPU check:"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/wsl-mycosoft-data-layout.sh" ]]; then
  log "Storage layout (models, caches, data, memory artifacts)…"
  bash "$SCRIPT_DIR/wsl-mycosoft-data-layout.sh" --role "$ROLE" --yes
  if [[ -f "$HOME/mycosoft-data-env.sh" ]]; then
    # shellcheck source=/dev/null
    source "$HOME/mycosoft-data-env.sh"
  fi
fi

if [[ "$AUTO_YES" != true ]]; then
  read -r -p "Continue with apt installs and Python venvs? [y/N] " a
  if [[ ! "$a" =~ ^[Yy]$ ]]; then echo "Aborted."; exit 1; fi
fi

log "Installing system packages (sudo)..."
sudo apt-get update -y
sudo apt-get install -y \
  build-essential \
  git curl wget jq ca-certificates \
  ffmpeg \
  libsndfile1 \
  libopus0 \
  pkg-config \
  zstd \
  software-properties-common

if ! command -v python3.11 &>/dev/null; then
  warn "Installing Python 3.11 via deadsnakes PPA..."
  sudo add-apt-repository -y ppa:deadsnakes/ppa
  sudo apt-get update -y
fi
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev

# systemd in WSL2 (Ollama service) — Ubuntu 22.04 on Win11 often supports this
if [[ -f /etc/wsl.conf ]] && ! grep -q 'systemd=true' /etc/wsl.conf 2>/dev/null; then
  warn "Consider enabling systemd for Ollama: sudo tee /etc/wsl.conf <<'EOF'
[boot]
systemd=true
EOF
  Then: wsl --shutdown (from Windows), reopen Ubuntu."
fi

mkdir -p "$VENV_BASE"

PY=python3.11
if [[ "$ROLE" == "earth2" ]]; then
  VENV="$VENV_BASE/mycosoft-earth2-wsl"
else
  VENV="$VENV_BASE/mycosoft-voice-wsl"
fi

log "Python venv: $VENV"
if [[ ! -d "$VENV" ]]; then
  "$PY" -m venv "$VENV"
fi
# shellcheck source=/dev/null
source "$VENV/bin/activate"
pip install --upgrade pip wheel setuptools

log "Installing PyTorch (CUDA) from $CUDA_INDEX ..."
pip install torch torchvision torchaudio --index-url "$CUDA_INDEX"

python -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"

if [[ ! -d "$REPO_DIR/.git" ]]; then
  log "Cloning Mycosoft MAS repo → $REPO_DIR"
  git clone --depth 1 "$REPO_URL" "$REPO_DIR"
else
  log "Repo exists: $REPO_DIR (pull skipped; run git pull manually if needed)"
fi

if [[ "$ROLE" == "earth2" ]]; then
  log "Earth2 role: API + earth2studio (Linux wheels — full stack; real checkpoints per NVIDIA docs)"
  pip install 'fastapi>=0.109' 'uvicorn[standard]>=0.27' pydantic
  if ! pip install earth2studio; then
    warn "earth2studio pip failed — retry after CUDA/PyTorch verify; see NVIDIA Earth-2 install docs."
  fi
  pip install hf-transfer huggingface-hub || true
  cat <<EOF

${GREEN}Earth2 WSL venv ready.${NC}
  Activate: source $VENV/bin/activate
  API script (from repo): python $REPO_DIR/scripts/earth2_api_server.py
  (Configure real model paths / checkpoints — no placeholder inference in production.)

EOF

elif [[ "$ROLE" == "voice" ]]; then
  log "Voice role: Moshi + PersonaPlex bridge deps + HF tooling"
  pip install hf-transfer huggingface-hub numpy
  pip install moshi sphn sentencepiece websockets aiohttp

  PP="$REPO_DIR/services/personaplex-local"
  if [[ -f "$PP/requirements-personaplex.txt" ]]; then
    pip install -r "$PP/requirements-personaplex.txt"
  fi
  if [[ -f "$PP/requirements.txt" ]]; then
    pip install -r "$PP/requirements.txt"
  fi
  pip install --upgrade torch torchaudio --index-url "$CUDA_INDEX"

  cat <<EOF

${GREEN}Voice WSL venv ready.${NC}
  Activate: source $VENV/bin/activate
  Moshi (example): python -m moshi.server --host 0.0.0.0 --port 8998 --device cuda \\
    --hf-repo kyutai/moshika-pytorch-bf16
  Bridge: python $PP/bridge_api.py  (set env per .env.example)

EOF
fi

# Ollama: LLM inference for Nemotron/OpenAI-compatible flows (pull models after install)
if command -v ollama &>/dev/null; then
  log "Ollama already on PATH: $(command -v ollama)"
else
  log "Installing Ollama (Linux/WSL)..."
  curl -fsSL https://ollama.com/install.sh | sh || warn "Ollama install script failed — install manually from https://ollama.com"
fi

if command -v ollama &>/dev/null; then
  warn "Start Ollama: ollama serve   (or use systemd if enabled in WSL)"
  warn "Pull a model (examples — pick what your Nemotron/MYCA config uses):"
  echo "    ollama pull llama3.1:8b"
  echo "    # Or a Nemotron-tagged model when available in your registry"
fi

log "Installing Hugging Face CLI (optional)..."
pip install 'huggingface_hub[cli]' || true

log "Done. Verify: nvidia-smi && python -c 'import torch; print(torch.cuda.is_available())'"
deactivate || true
