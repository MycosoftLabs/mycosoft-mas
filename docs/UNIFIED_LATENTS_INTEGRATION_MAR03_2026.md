# Unified Latents (UL) Integration

**Date:** March 3, 2026
**Paper:** Heek, Hoogeboom, Mensink, Salimans (2026) "Unified Latents: How to train your latents" (arXiv 2602.17270)
**Category:** Simulation / Scientific / GPU Inference

---

## Overview

Unified Latents (UL) is a framework for training latent representations that jointly regularises them with a **diffusion prior** and decodes them with a **diffusion model**. The key innovation links the VAE encoder's output noise to the diffusion prior's minimum noise level, producing a training objective that upper-bounds latent bitrate.

### Benchmark Results

| Dataset | Metric | Score |
|---------|--------|-------|
| ImageNet-512 | FID | **1.4** |
| ImageNet-512 | PSNR | High reconstruction quality |
| Kinetics-600 | FVD | **1.3** (SOTA) |

UL achieves these results with **fewer training FLOPs** than Stable Diffusion-based approaches.

---

## Architecture

The UL framework has three components:

1. **Encoder** -- Maps high-dimensional data (images/video) to latent representations
2. **Diffusion Prior** -- Models the distribution of learned latents
3. **Diffusion Decoder** -- Reconstructs data from latents via iterative denoising

The encoder noise schedule is **synchronized** with the diffusion prior's forward process, enabling end-to-end gradient flow and joint optimisation of all components.

### Training Objective

The unified objective combines:
- Reconstruction error from the encoder-decoder pair
- KL divergence regularisation
- Diffusion prior matching loss

This provides an upper bound on latent bitrate while balancing the rate-distortion tradeoff.

---

## MAS Integration

### Agent

**UnifiedLatentsAgent** (`mycosoft_mas/agents/v2/simulation_agents.py`)

A v2 scientific simulation agent that manages UL model training and inference. Registered in the `SIMULATION_AGENTS` registry as `"unified_latents"`.

**Task types:**

| Task | Description |
|------|-------------|
| `encode_to_latent` | Encode image/video data into the unified latent space |
| `decode_from_latent` | Decode a latent representation back to pixel space |
| `generate_image` | Sample new images via diffusion prior + decoder |
| `generate_video` | Sample new video clips via diffusion prior + decoder |
| `train_model` | Launch / resume a UL training run on the GPU node |
| `get_model_status` | Query status of a running or completed training run |
| `evaluate_model` | Compute FID / FVD / PSNR metrics for a checkpoint |

### API Router

**`/api/unified-latents/`** (`mycosoft_mas/core/routers/unified_latents_api.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/unified-latents/health` | Health check |
| GET | `/api/unified-latents/info` | Framework metadata and benchmarks |
| POST | `/api/unified-latents/generate/image` | Generate images from text prompt |
| POST | `/api/unified-latents/generate/video` | Generate video from text prompt |
| POST | `/api/unified-latents/encode` | Encode input to latent space |
| POST | `/api/unified-latents/decode` | Decode latent back to pixels |
| POST | `/api/unified-latents/train` | Launch training run |
| GET | `/api/unified-latents/train/{run_id}` | Get training run status |
| POST | `/api/unified-latents/evaluate` | Evaluate a model checkpoint |

### GPU Memory Tracking

`UNIFIED_LATENTS` has been added to the `GPUModelType` enum in `mycosoft_mas/memory/gpu_memory.py` for VRAM usage tracking and predictive model preloading.

### GPU Node

All heavy inference runs on the GPU node at **192.168.0.190** (mycosoft-gpu01).

---

## Files Modified / Created

| File | Action |
|------|--------|
| `mycosoft_mas/agents/v2/simulation_agents.py` | Added `UnifiedLatentsAgent` class |
| `mycosoft_mas/core/routers/unified_latents_api.py` | **New** -- API router |
| `mycosoft_mas/core/myca_main.py` | Registered UL router |
| `mycosoft_mas/memory/gpu_memory.py` | Added `UNIFIED_LATENTS` enum value |
| `tests/test_unified_latents.py` | **New** -- Agent + API tests |
| `docs/UNIFIED_LATENTS_INTEGRATION_MAR03_2026.md` | **New** -- This document |

---

## Usage Examples

### Generate an Image

```bash
curl -X POST http://192.168.0.188:8001/api/unified-latents/generate/image \
  -H "Content-Type: application/json" \
  -d '{"prompt": "macro photo of Pleurotus ostreatus fruiting body", "resolution": 512}'
```

### Generate a Video

```bash
curl -X POST http://192.168.0.188:8001/api/unified-latents/generate/video \
  -H "Content-Type: application/json" \
  -d '{"prompt": "timelapse of mycelium colonizing agar plate", "num_frames": 32, "fps": 16}'
```

### Launch Training

```bash
curl -X POST http://192.168.0.188:8001/api/unified-latents/train \
  -H "Content-Type: application/json" \
  -d '{"dataset": "imagenet-512", "batch_size": 64, "max_steps": 500000}'
```

### Evaluate a Checkpoint

```bash
curl -X POST http://192.168.0.188:8001/api/unified-latents/evaluate \
  -H "Content-Type: application/json" \
  -d '{"checkpoint": "v1-500k", "metrics": ["fid", "psnr", "fvd"]}'
```
