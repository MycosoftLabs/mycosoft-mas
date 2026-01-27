#!/bin/bash
# PersonaPlex Server Startup Script - January 27, 2026

set -e

echo "Starting PersonaPlex Server..."
echo "Voice Prompt: ${VOICE_PROMPT:-NATF2.pt}"
echo "CPU Offload: ${CPU_OFFLOAD:-false}"

SSL_DIR=$(mktemp -d)
CMD="python3 -m moshi.server --ssl $SSL_DIR"

if [ -n "$VOICE_PROMPT" ]; then
    CMD="$CMD --voice-prompt $VOICE_PROMPT"
fi

if [ -f "$TEXT_PROMPT_FILE" ]; then
    TEXT_PROMPT=$(cat "$TEXT_PROMPT_FILE")
    CMD="$CMD --text-prompt \"$TEXT_PROMPT\""
fi

if [ "$CPU_OFFLOAD" = "true" ]; then
    CMD="$CMD --cpu-offload"
fi

CMD="$CMD --host 0.0.0.0"

cd /app/personaplex
exec $CMD
