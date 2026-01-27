# PersonaPlex Setup Guide - January 27, 2026

## Prerequisites

### 1. Accept HuggingFace License

1. Go to https://huggingface.co/nvidia/personaplex-7b-v1
2. Log in with your HuggingFace account
3. Accept the NVIDIA Open Model License terms
4. Generate an access token at https://huggingface.co/settings/tokens

### 2. Set Environment Variable

Add to your `.env.local`:

```bash
HF_TOKEN=hf_your_token_here
```

### 3. Hardware Requirements

**With GPU (Recommended):**
- NVIDIA GPU with 16GB+ VRAM (A100, H100, RTX 4090)
- CUDA 12.0+ and nvidia-docker

**CPU Offload Mode:**
- 32GB+ System RAM
- Slower latency (~1-2 seconds)
- Use `--cpu-offload` flag

## Voices

Available female voices for MYCA:
- `NATF0.pt` - Natural Female 0
- `NATF1.pt` - Natural Female 1
- `NATF2.pt` - Natural Female 2 (DEFAULT - most conversational)
- `NATF3.pt` - Natural Female 3
