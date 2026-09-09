#!/bin/bash
# Intercept Ollama CLI. Serve/list require NAS. Pull/create also require root disk guard.
set -euo pipefail

REAL="${OLLAMA_REAL_BIN:-/usr/libexec/ollama-bin}"
if [[ ! -x "$REAL" ]]; then
  echo "ollama real binary missing: $REAL" >&2
  exit 127
fi

cmd="${1:-}"
case "$cmd" in
  pull|cp|create|push)
    /usr/local/sbin/mycosoft-require-nas-models.sh
    /usr/local/sbin/mycosoft-disk-guard.sh
    ;;
  serve|runner|"")
    /usr/local/sbin/mycosoft-require-nas-models.sh
    ;;
  *)
    /usr/local/sbin/mycosoft-require-nas-models.sh
    ;;
esac

exec "$REAL" "$@"
