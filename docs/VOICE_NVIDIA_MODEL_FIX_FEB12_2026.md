# Voice System Fix: NVIDIA PersonaPlex Model - February 12, 2026

## Problem

User reported:
1. **Male voice** instead of female NATF2 voice
2. **"Moshi" identity** - AI identifies as "Moshi" not "MYCA"
3. **Laggy responses**

## Root Cause

The system was using the **Kyutai moshiko-pytorch-bf16** model which:
- Has a **hardcoded male "Moshi" voice** that cannot be changed
- Has a **built-in "Moshi" identity** that resists text prompt overrides
- Voice embedding files (NATF2.pt) are **incompatible** with Kyutai model architecture

## Solution

Switched to the **NVIDIA PersonaPlex 7B v1** model which:
- **Supports custom voice embeddings** (.pt files like NATF2.pt = Natural Female 2)
- **Supports persona text prompts** (MYCA identity from persona file)
- **Is designed for persona customization** (hence "PersonaPlex")

## Changes Made

### `start_personaplex.py`

Changed from:
```python
# OLD - Kyutai model (wrong!)
hf_repo = "kyutai/moshiko-pytorch-bf16"
sys.argv = [
    '--hf-repo', hf_repo,
    '--voice-prompt-dir', voice_prompt_dir,
]
```

To:
```python
# NEW - NVIDIA PersonaPlex model (correct!)
model_dir = r"C:\...\models\personaplex-7b-v1"
moshi_weight = os.path.join(model_dir, "model.safetensors")
mimi_weight = os.path.join(model_dir, "tokenizer-e351c8d8-checkpoint125.safetensors")
tokenizer = os.path.join(model_dir, "tokenizer_spm_32k_3.model")
voice_prompt_dir = os.path.join(model_dir, "voices")

sys.argv = [
    '--moshi-weight', moshi_weight,
    '--mimi-weight', mimi_weight,
    '--tokenizer', tokenizer,
    '--voice-prompt-dir', voice_prompt_dir,
]
```

## NVIDIA PersonaPlex Model Files

Located at: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\models\personaplex-7b-v1\`

| File | Size | Purpose |
|------|------|---------|
| `model.safetensors` | 16 GB | Main Moshi model weights |
| `tokenizer-e351c8d8-checkpoint125.safetensors` | 367 MB | Mimi audio codec |
| `tokenizer_spm_32k_3.model` | 0.5 MB | Text tokenizer |
| `voices/NATF2.pt` | 0.4 MB | Natural Female 2 voice embeddings |
| `voices/` | 5.8 MB | All voice options (NATF0-3, NATM0-3, VARF0-4, VARM0-4) |

## Voice Options

| Voice | File | Description |
|-------|------|-------------|
| **NATF2** | NATF2.pt | Natural Female 2 (MYCA default) |
| NATF0-3 | NATF0-3.pt | Natural Female voices 0-3 |
| NATM0-3 | NATM0-3.pt | Natural Male voices 0-3 |
| VARF0-4 | VARF0-4.pt | Variable Female voices 0-4 |
| VARM0-4 | VARM0-4.pt | Variable Male voices 0-4 |

## GPU Memory

- NVIDIA PersonaPlex uses ~18 GB VRAM on RTX 5090
- CUDA graphs enabled for 30ms/step performance

## CRITICAL RULE

**NEVER use the Kyutai model** (`kyutai/moshiko-pytorch-bf16`)
- It has hardcoded "Moshi" identity
- It has built-in male voice that cannot be changed
- Voice embeddings are incompatible

**ALWAYS use the NVIDIA PersonaPlex model** (local files or `nvidia/personaplex-7b-v1`)
- Supports custom voice embeddings
- Supports persona text prompts
- Designed for persona customization

## Test

Test at: http://localhost:3010/test-voice

Expected behavior:
- Female voice (NATF2)
- Identifies as "MYCA" 
- Works for Mycosoft (not Microsoft)
- Knows Morgan is the creator
