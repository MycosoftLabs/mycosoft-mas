#!/usr/bin/env python3
"""Start PersonaPlex Moshi server WITHOUT CUDA graphs.

This version disables CUDA graphs which may be causing the server to hang.
Trade-off: Slower inference (~200ms/step instead of ~30ms) but more stable.
"""

import sys
import os

# =============================================================================
# DEPENDENCY: personaplex-repo
# =============================================================================
# This script requires the personaplex-repo directory (not tracked in git).
# If missing, clone it:
#   cd c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
#   git clone https://github.com/mycosoft/personaplex-repo.git personaplex-repo
# Or copy from an existing installation.
# =============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
personaplex_path = os.path.join(SCRIPT_DIR, "personaplex-repo", "moshi")

if not os.path.isdir(personaplex_path):
    print("=" * 70)
    print("ERROR: personaplex-repo directory not found!")
    print("=" * 70)
    print(f"Expected path: {personaplex_path}")
    print()
    print("The personaplex-repo directory is not tracked in git.")
    print("To set it up, run:")
    print()
    print("  cd c:\\Users\\admin2\\Desktop\\MYCOSOFT\\CODE\\MAS\\mycosoft-mas")
    print("  git clone https://github.com/mycosoft/personaplex-repo.git personaplex-repo")
    print()
    print("Or copy the personaplex-repo folder from an existing installation.")
    print("=" * 70)
    sys.exit(1)

# DISABLE CUDA graphs and torch.compile for stability testing
os.environ['NO_TORCH_COMPILE'] = '1'  # Disable torch.compile
os.environ['NO_CUDA_GRAPH'] = '1'     # Disable CUDA graphs

# Set CUDA device
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

# Add PersonaPlex moshi to path (personaplex_path already set above)
sys.path.insert(0, personaplex_path)

# Voice prompts directory - use local models dir or HuggingFace cache
model_dir = os.path.join(SCRIPT_DIR, "models", "personaplex-7b-v1")
voice_prompt_dir = os.path.join(model_dir, "voices")
hf_cache_voice_dir = os.path.expanduser(
    r"~\.cache\huggingface\hub\models--nvidia--personaplex-7b-v1\snapshots\3343b641d663e4c851120b3575cbdfa4cc33e7fa\voices"
)

if not os.path.isdir(voice_prompt_dir):
    # Try HuggingFace cache fallback
    voice_prompt_dir = hf_cache_voice_dir

# Validate voice prompts directory exists
if not os.path.isdir(voice_prompt_dir):
    print("=" * 70)
    print("ERROR: Voice prompts directory not found!")
    print("=" * 70)
    print("Checked locations:")
    print(f"  1. Local: {os.path.join(model_dir, 'voices')}")
    print(f"  2. HuggingFace cache: {hf_cache_voice_dir}")
    print()
    print("To download the model, run:")
    print("  pip install huggingface_hub")
    print("  huggingface-cli download nvidia/personaplex-7b-v1 --local-dir models/personaplex-7b-v1")
    print()
    print("Or copy models/personaplex-7b-v1/voices from an existing installation.")
    print("=" * 70)
    sys.exit(1)

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
