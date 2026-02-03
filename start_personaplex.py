#!/usr/bin/env python3
"""Start PersonaPlex Moshi server with proper path setup for RTX 5090.

PERFORMANCE CRITICAL:
- CUDA graphs MUST be enabled for real-time performance
- Without CUDA graphs: ~200ms per step (TOO SLOW)
- With CUDA graphs: ~30ms per step (OK for 80ms target)
"""

import sys
import os

# PERFORMANCE: Enable CUDA graphs and torch.compile for real-time speed
# These are CRITICAL for RTX 5090 (sm_120) performance!
os.environ['NO_TORCH_COMPILE'] = '0'  # Enable torch.compile
os.environ['NO_CUDA_GRAPH'] = '0'     # Enable CUDA graphs (CRITICAL!)
# os.environ['TORCHDYNAMO_DISABLE'] = '1'  # Disabled - let dynamo work

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
print("PersonaPlex Server Startup - RTX 5090 OPTIMIZED")
print("=" * 60)
print(f"CUDA_VISIBLE_DEVICES = {os.environ.get('CUDA_VISIBLE_DEVICES')}")
print(f"NO_TORCH_COMPILE = {os.environ.get('NO_TORCH_COMPILE')} (0=enabled)")
print(f"NO_CUDA_GRAPH = {os.environ.get('NO_CUDA_GRAPH')} (0=enabled, CRITICAL!)")
print(f"Working directory: {personaplex_path}")
print(f"Voice prompts: {voice_prompt_dir}")
print("=" * 60)
print("CUDA graphs ENABLED - expect ~30ms/step (target: <80ms)")
print("Starting PersonaPlex on RTX 5090...")
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
