#!/usr/bin/env python3
"""Start PersonaPlex Moshi server with NVIDIA PersonaPlex model for RTX 5090.

CRITICAL: Always use NVIDIA PersonaPlex model - NEVER use Kyutai!
- NVIDIA PersonaPlex supports custom voices (NATF2.pt = Female)
- NVIDIA PersonaPlex supports persona text prompts (MYCA identity)
- Kyutai model has hardcoded "Moshi" identity and male voice - DO NOT USE

PERFORMANCE CRITICAL:
- CUDA graphs MUST be enabled for real-time performance
- Without CUDA graphs: ~200ms per step (TOO SLOW)
- With CUDA graphs: ~30ms per step (OK for 80ms target)
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

# CUDA GRAPHS STATUS:
# - CUDA graphs provide 30ms/step performance - REQUIRED for real-time voice
# - NEVER disable CUDA graphs - they are vital for PersonaPlex/NVIDIA performance
# - The brain engine handles intelligent responses via MYCA LLMs
# - Moshi handles immediate/conversational responses
#
# PERFORMANCE MODE (CUDA graphs ENABLED - MANDATORY):
os.environ['NO_TORCH_COMPILE'] = '0'  # Enable torch.compile for performance
os.environ['NO_CUDA_GRAPH'] = '0'     # CUDA graphs ENABLED (0 = enabled!)
os.environ['TORCHDYNAMO_DISABLE'] = '0'  # Enable dynamo for optimization

# Set CUDA device
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

# Add PersonaPlex moshi to path (personaplex_path already set above)
sys.path.insert(0, personaplex_path)

# ============================================================================
# NVIDIA PersonaPlex Model - LOCAL FILES (downloaded from nvidia/personaplex-7b-v1)
# ============================================================================
# CRITICAL: Use local NVIDIA model files, NOT Kyutai HuggingFace repo!
# The NVIDIA model supports:
#   - Custom voice embeddings (.pt files like NATF2.pt for female voice)
#   - Text prompts for persona/identity (MYCA, not Moshi)
# ============================================================================
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

# Validate voice prompts directory exists
if not os.path.isdir(voice_prompt_dir):
    print("=" * 70)
    print("ERROR: Voice prompts directory not found!")
    print("=" * 70)
    print(f"Expected path: {voice_prompt_dir}")
    print()
    print("The voices directory contains voice embeddings (e.g., NATF2.pt).")
    print("Re-download the model with:")
    print("  huggingface-cli download nvidia/personaplex-7b-v1 --local-dir models/personaplex-7b-v1")
    print()
    print("Or copy the voices folder from an existing installation.")
    print("=" * 70)
    sys.exit(1)

# Change to the moshi directory
os.chdir(personaplex_path)

print("=" * 60)
print("NVIDIA PersonaPlex Server - RTX 5090 PERFORMANCE MODE")
print("=" * 60)
print(f"CUDA_VISIBLE_DEVICES = {os.environ.get('CUDA_VISIBLE_DEVICES')}")
print(f"NO_TORCH_COMPILE = {os.environ.get('NO_TORCH_COMPILE')} (0=enabled)")
print(f"NO_CUDA_GRAPH = {os.environ.get('NO_CUDA_GRAPH')} (0=enabled)")
print(f"Working directory: {personaplex_path}")
print(f"Model: NVIDIA PersonaPlex (LOCAL)")
print(f"  Moshi weights: {moshi_weight}")
print(f"  Mimi weights: {mimi_weight}")
print(f"  Tokenizer: {tokenizer}")
print(f"  Voice prompts: {voice_prompt_dir}")
print("=" * 60)
print("CUDA graphs ENABLED - 30ms/step (REQUIRED for real-time)")
print("Voice: NATF2.pt (Natural Female 2) for MYCA")
print("Identity: MYCA (via text_prompt from PersonaPlex Bridge)")
print("Starting NVIDIA PersonaPlex on RTX 5090...")
print("=" * 60)

# Start server using LOCAL NVIDIA PersonaPlex model files
# --static none = skip UI download (we use PersonaPlex bridge)
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
