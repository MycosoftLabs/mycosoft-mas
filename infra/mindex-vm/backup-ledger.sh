#!/bin/bash
# Ledger backup script - copies chain.jsonl to NAS
LEDGER_DIR="data/ledger"
NAS_MOUNT="/opt/mycosoft/ledger"
mkdir -p ""
if [ -f "/chain.jsonl" ]; then
  cp -f "/chain.jsonl" "/chain.jsonl"
  echo "02/06/2026 16:34:48: Backed up ledger to "
else
  echo "02/06/2026 16:34:48: No chain.jsonl found at "
fi
