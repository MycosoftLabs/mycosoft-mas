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

# Model directory
model_dir = os.path.join(SCRIPT_DIR, "models", "personaplex-7b-v1")

if not os.path.isdir(model_dir):
    print("=" * 70)
    print("ERROR: PersonaPlex model directory not found!")
    print("=" * 70)
    print(f"Expected path: {model_dir}")
    print()
    print("The NVIDIA PersonaPlex model files are required.")
    print("To download them, run:")
    print()
    print("  pip install huggingface_hub")
    print("  huggingface-cli download nvidia/personaplex-7b-v1 --local-dir models/personaplex-7b-v1")
    print()
    print("Or copy the models/personaplex-7b-v1 folder from an existing installation.")
    print("=" * 70)
    sys.exit(1)

moshi_weight = os.path.join(model_dir, "model.safetensors")
tokenizer = os.path.join(model_dir, "tokenizer_spm_32k_3.model")
voice_prompt_dir = os.path.join(model_dir, "voices")

def _find_mimi_weight(directory: str) -> str:
    """Discover the Mimi tokenizer weight file by pattern rather than hardcoded name.
    Matches tokenizer-*-checkpoint*.safetensors — works across model versions.
    Returns the path if exactly one candidate found, or the newest by mtime if multiple."""
    import glob as _glob
    candidates = _glob.glob(os.path.join(directory, "tokenizer-*checkpoint*.safetensors"))
    if not candidates:
        return ""
    if len(candidates) == 1:
        return candidates[0]
    # Multiple checkpoint versions — use the most recently modified
    return max(candidates, key=os.path.getmtime)

mimi_weight = _find_mimi_weight(model_dir)

# Validate required model files exist
missing_files = []
for fpath, fname in [
    (moshi_weight, "Moshi weights (model.safetensors)"),
    (mimi_weight, "Mimi tokenizer weights (tokenizer-*checkpoint*.safetensors)"),
    (tokenizer, "Tokenizer model (tokenizer_spm_32k_3.model)"),
]:
    if not fpath or not os.path.isfile(fpath):
        loc = fpath if fpath else f"not found in {model_dir}"
        missing_files.append(f"  - {fname}: {loc}")

if missing_files:
    print("=" * 70)
    print("ERROR: Required model files missing!")
    print("=" * 70)
    print("The following files are missing from the model directory:")
    print()
    for mf in missing_files:
        print(mf)
    print()
    print("Re-download the model with:")
    print("  huggingface-cli download nvidia/personaplex-7b-v1 --local-dir models/personaplex-7b-v1")
    print("=" * 70)
    sys.exit(1)

def _find_hf_cache_voices() -> str:
    """Search HuggingFace snapshots directory for any snapshot containing a voices/ folder.
    Returns the path if found, empty string otherwise. Never hardcodes a snapshot hash."""
    hf_snapshots = os.path.expanduser(
        os.path.join("~", ".cache", "huggingface", "hub",
                     "models--nvidia--personaplex-7b-v1", "snapshots")
    )
    if not os.path.isdir(hf_snapshots):
        return ""
    for snapshot_hash in os.listdir(hf_snapshots):
        candidate = os.path.join(hf_snapshots, snapshot_hash, "voices")
        if os.path.isdir(candidate):
            return candidate
    return ""

if not os.path.isdir(voice_prompt_dir):
    # Search HuggingFace cache across all snapshots (no hardcoded hash)
    hf_found = _find_hf_cache_voices()
    if hf_found:
        voice_prompt_dir = hf_found

# Validate voice prompts directory exists
if not os.path.isdir(voice_prompt_dir):
    hf_snapshots_path = os.path.expanduser(
        os.path.join("~", ".cache", "huggingface", "hub",
                     "models--nvidia--personaplex-7b-v1", "snapshots")
    )
    print("=" * 70)
    print("ERROR: Voice prompts directory not found!")
    print("=" * 70)
    print("Checked locations:")
    print(f"  1. Local: {os.path.join(model_dir, 'voices')}")
    print(f"  2. HuggingFace cache (all snapshots): {hf_snapshots_path}")
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
print(f"Model: NVIDIA PersonaPlex (LOCAL)")
print(f"  Moshi weights: {moshi_weight}")
print(f"  Mimi weights: {mimi_weight}")
print(f"  Tokenizer: {tokenizer}")
print(f"  Voice prompts: {voice_prompt_dir}")
print("=" * 60)
print("CUDA graphs DISABLED - expect ~200ms/step (slower but stable)")
print("Starting PersonaPlex...")
print("=" * 60)

# Start server with explicit model file paths (same as performance mode)
sys.argv = [
    'moshi.server',
    '--host', '0.0.0.0',
    '--port', '8998',
    '--moshi-weight', moshi_weight,
    '--mimi-weight', mimi_weight,
    '--tokenizer', tokenizer,
    '--voice-prompt-dir', voice_prompt_dir,
    '--static', 'none',
]

# Import and run the server
from moshi.server import main
main()
