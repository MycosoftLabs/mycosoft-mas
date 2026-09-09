#!/bin/bash
# Fail closed: Ollama/MYCA weights only on CIFS NAS myca tree. Never write to / or /home or /usr.
set -euo pipefail

NAS_MOUNT="${MYCOSOFT_NAS_MOUNT:-/mnt/mycosoft-nas}"
MYCA_DIR="${OLLAMA_MODELS:-/mnt/mycosoft-nas/models/myca/ollama}"
NLM_DIR="${NLM_MODEL_DIR:-/mnt/mycosoft-nas/models/nlm}"

if ! findmnt -n -t cifs "$NAS_MOUNT" >/dev/null 2>&1; then
  echo "FAIL_CLOSED: NAS $NAS_MOUNT is not a CIFS mount. Refusing model I/O on local disk." >&2
  exit 78
fi

if [[ ! -d "$MYCA_DIR" ]]; then
  echo "FAIL_CLOSED: MYCA model dir missing: $MYCA_DIR" >&2
  exit 78
fi

myca_src="$(findmnt -n -o SOURCE --target "$MYCA_DIR" 2>/dev/null || true)"
nas_src="$(findmnt -n -o SOURCE --target "$NAS_MOUNT" 2>/dev/null || true)"
if [[ -z "$myca_src" || "$myca_src" != "$nas_src" ]]; then
  echo "FAIL_CLOSED: $MYCA_DIR is not on the NAS CIFS share. Refusing local fallback." >&2
  exit 78
fi

if [[ -d "$NLM_DIR" ]]; then
  nlm_src="$(findmnt -n -o SOURCE --target "$NLM_DIR" 2>/dev/null || true)"
  if [[ -n "$nlm_src" && "$nlm_src" != "$nas_src" ]]; then
    echo "WARN: NLM tree is not on the same NAS mount (owned by FormSpace). Not mixing." >&2
  fi
fi

exit 0
