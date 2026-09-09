#!/bin/bash
# Refuse HF/Ollama pulls when root is already tight. 188 is compute, not a weight store.
set -euo pipefail

ROOT_USE_PCT="${MYCOSOFT_ROOT_MAX_PCT:-80}"
ROOT_MIN_AVAIL_GB="${MYCOSOFT_ROOT_MIN_FREE_GB:-15}"

read -r _use avail_kb <<<"$(df -P / | awk 'NR==2 {gsub(/%/,"",$5); print $5, $4}')"
avail_gb=$((avail_kb / 1024 / 1024))

if (( _use >= ROOT_USE_PCT )); then
  echo "REFUSE_PULL: root filesystem ${_use}% used (>= ${ROOT_USE_PCT}%). Models go on NAS only." >&2
  exit 79
fi

if (( avail_gb < ROOT_MIN_AVAIL_GB )); then
  echo "REFUSE_PULL: root has ${avail_gb}G free (< ${ROOT_MIN_AVAIL_GB}G). Models go on NAS only." >&2
  exit 79
fi

exit 0
