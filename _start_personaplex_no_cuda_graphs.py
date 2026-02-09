#!/usr/bin/env python3
"""Start PersonaPlex Moshi server WITHOUT CUDA graphs.

This version disables CUDA graphs which may be causing the server to hang.
Trade-off: Slower inference (~200ms/step instead of ~30ms) but more stable.
"""

import sys
import os

# DISABLE CUDA graphs and torch.compile for stability testing
os.environ['NO_TORCH_COMPILE'] = '1'  # Disable torch.compile
os.environ['NO_CUDA_GRAPH'] = '1'     # Disable CUDA graphs

# Set CUDA device
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

# Add PersonaPlex moshi to path
personaplex_path = r"c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\personaplex-repo\moshi"
sys.path.insert(0, personaplex_path)

# Voice prompts directory (from HuggingFace cache)
voice_prompt_dir = r"C:\Users\admin2\.cache\huggingface\hub\models--nvidia--personaplex-7b-v1\snapshots\3343b641d663e4c851120b3575cbdfa4cc33e7fa\voices"

# Change to the moshi directory
os.chdir(personaplex_path)

print("=" * 60)
print("PersonaPlex Server - STABILITY MODE (No CUDA Graphs)")
print("=" * 60)
print(f"CUDA_VISIBLE_DEVICES = {os.environ.get('CUDA_VISIBLE_DEVICES')}")
print(f"NO_TORCH_COMPILE = {os.environ.get('NO_TORCH_COMPILE')} (1=disabled)")
print(f"NO_CUDA_GRAPH = {os.environ.get('NO_CUDA_GRAPH')} (1=disabled)")
print(f"Working directory: {personaplex_path}")
print(f"Voice prompts: {voice_prompt_dir}")
print("=" * 60)
print("CUDA graphs DISABLED - expect ~200ms/step (slower but stable)")
print("Starting PersonaPlex...")
print("=" * 60)

# Pass voice-prompt-dir via sys.argv
sys.argv = [
    'moshi.server',
    '--host', '0.0.0.0',
    '--port', '8998',
    '--voice-prompt-dir', voice_prompt_dir,
]

# Import and run the server
from moshi.server import main
main()
