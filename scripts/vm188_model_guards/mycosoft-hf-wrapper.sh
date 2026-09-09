#!/bin/bash
# Hugging Face downloads must land on NAS myca cache, never 188 root.
set -euo pipefail

REAL="${HF_REAL_BIN:-/usr/bin/huggingface-cli}"
export HF_HOME="${HF_HOME:-/mnt/mycosoft-nas/models/myca/huggingface}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-$HF_HOME}"
export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-$HF_HOME}"

/usr/local/sbin/mycosoft-require-nas-models.sh
case "${1:-}" in
  download|snapshot-download)
    /usr/local/sbin/mycosoft-disk-guard.sh
    ;;
esac

if [[ ! -x "$REAL" ]]; then
  echo "huggingface-cli not installed; refusing to download onto 188 root." >&2
  exit 127
fi
exec "$REAL" "$@"
