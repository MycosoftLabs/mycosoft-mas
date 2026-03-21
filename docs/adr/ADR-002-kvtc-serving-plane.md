# ADR-002: KVTC as Serving-Plane KV-Cache Codec

**Date:** 2026-03-21
**Status:** Accepted
**Authors:** MYCA Engineering

## Decision

KVTC (KV Cache Transform Coding) is a **serving-plane KV-cache codec**, not a training-plane checkpoint compressor.

## Context

The ICLR 2026 paper demonstrates 20× compression with negligible quality loss on dense decoder models using:

1. **PCA decorrelation** — per-layer principal component analysis on captured K/V tensors
2. **Dynamic-programming bit allocation** — optimal bit budget across PCA components
3. **Entropy coding** — lossless final compression

Compression happens **after prefill/decode** for storage and transfer. Decode still runs on **decompressed** KV — attention math is unchanged.

This is fundamentally different from:
- Quantization-aware training (modifies weights)
- Pruning (removes parameters)
- Knowledge distillation (changes model architecture)
- GPTQ/AWQ (post-training weight quantization)

## Consequences

1. KVTC artifacts (PCA matrices, bitplans) are stored alongside model builds but **do not modify them**
2. Cache manager hooks sit at **offload/persistence/transfer boundaries**, not inside attention computation
3. The recent window (last 128 tokens) and sink tokens (first 4) remain **uncompressed** — these are accessed too frequently and too cheaply to justify codec overhead
4. For hybrid attention + Mamba models, only the **attention KV path** is compressed — Mamba recurrent state is never touched
5. For MLA (Multi-head Latent Attention) models, compression targets the **latent cache**, not the projected KV
6. Calibration runs once per model build per compression target — results are deterministic given the same dataset
7. Jetson and other edge devices are **consumers** of pre-compressed caches, never calibration or promotion authority

## Alternatives Considered

- **Weight quantization instead of KV compression:** Rejected — orthogonal concern. Weight quantization reduces model size; KV compression reduces serving memory. Both can coexist.
- **Compress everything including recent window:** Rejected — recent tokens are in hot cache, decompression latency would dominate TTFT
- **Apply to Mamba state:** Rejected — Mamba state is recurrent, not key-value. PCA on recurrent state would destroy temporal dynamics.
