# GPU Server Options for PersonaPlex + Earth2 - February 12, 2026

## Current Situation

| Resource | Status | Notes |
|----------|--------|-------|
| Local Dev Machine | RTX 5090 (24GB) | Single GPU - can't run PersonaPlex + Earth2 + MAS simultaneously |
| Sandbox VM (187) | No GPU | Website Docker only |
| MAS VM (188) | No GPU | Orchestrator only |
| MINDEX VM (189) | No GPU | Database only |
| Proxmox Host | No GPU passed through | VMs don't have GPU access |

## Requirements

PersonaPlex + Earth2 running simultaneously for:
- MYCA voice controlling CREP dashboard
- MYCA voice controlling Earth Simulator
- Low latency (<500ms) voice responses
- Real-time Earth2 predictions

### GPU VRAM Requirements

| Service | Minimum VRAM | Recommended | Notes |
|---------|--------------|-------------|-------|
| PersonaPlex/Moshi | 8GB | 16GB | Full-duplex voice |
| Earth2 FourCastNet | 8GB | 16GB | Weather prediction |
| Earth2 DLWP | 4GB | 8GB | Additional weather model |
| Earth2 Pangu | 8GB | 16GB | High-res forecasting |
| **Total** | **28GB** | **56GB** | For all services simultaneously |

Single RTX 5090 (24GB) **cannot** run everything at once.

---

## Option 1: Add GPU to Proxmox Host (BEST)

**Hardware**: Add a dedicated GPU card to the Proxmox server

### Recommended GPUs

| GPU | VRAM | Price (New) | Price (Used) | Notes |
|-----|------|-------------|--------------|-------|
| NVIDIA RTX 4090 | 24GB | $1,599 | $1,200-1,400 | Best consumer option |
| NVIDIA RTX A6000 | 48GB | $4,500 | $2,500-3,000 | Workstation, ECC memory |
| NVIDIA L40 | 48GB | $7,000 | $4,000-5,000 | Data center, newest |
| NVIDIA A100 (40GB) | 40GB | N/A | $6,000-8,000 | Data center reference |
| NVIDIA A100 (80GB) | 80GB | N/A | $12,000-15,000 | Maximum VRAM |

### Recommended Setup

**For your use case (PersonaPlex + Earth2):**
- **Budget option**: 1x RTX 4090 (24GB) - $1,200-1,600
  - Run PersonaPlex OR Earth2, not both simultaneously
  - Swap models as needed
  
- **Ideal option**: 1x RTX A6000 (48GB) - $2,500-3,000
  - Run PersonaPlex + Earth2 FourCastNet simultaneously
  - Enough headroom for future models

- **Future-proof**: 2x RTX 4090 or 1x L40 (48GB)
  - Run everything simultaneously
  - Room for MAS GPU-accelerated features

### Proxmox GPU Passthrough Steps

1. **Enable IOMMU in BIOS**
   ```
   # Intel: VT-d
   # AMD: AMD-Vi
   ```

2. **Configure Proxmox** (`/etc/default/grub`)
   ```bash
   # Intel
   GRUB_CMDLINE_LINUX_DEFAULT="quiet intel_iommu=on iommu=pt"
   
   # AMD
   GRUB_CMDLINE_LINUX_DEFAULT="quiet amd_iommu=on iommu=pt"
   ```

3. **Blacklist host drivers** (`/etc/modprobe.d/blacklist.conf`)
   ```
   blacklist nouveau
   blacklist nvidia
   ```

4. **Add VFIO** (`/etc/modprobe.d/vfio.conf`)
   ```
   options vfio-pci ids=10de:XXXX  # Your GPU's PCI ID
   ```

5. **Create GPU VM** (MAS VM or new dedicated GPU VM)
   - Assign GPU to VM in Proxmox GUI
   - Install NVIDIA drivers in VM
   - Deploy PersonaPlex + Earth2

---

## Option 2: Cloud GPU (Monthly Cost)

### Dedicated GPU Servers

| Provider | GPU | VRAM | Monthly | Notes |
|----------|-----|------|---------|-------|
| **RunPod** | A100 40GB | 40GB | $1,200/mo | Best for ML |
| **RunPod** | A6000 | 48GB | $800/mo | Good balance |
| **Lambda Labs** | A100 40GB | 40GB | $1,100/mo | ML-focused |
| **Vast.ai** | RTX 4090 | 24GB | $400-600/mo | Variable pricing |
| **Paperspace** | A100 | 40GB | $3,000/mo | Enterprise |

### On-Demand (Per Hour)

| Provider | GPU | $/hour | For 8hrs/day | Notes |
|----------|-----|--------|--------------|-------|
| RunPod | A100 | $1.89 | ~$450/mo | Pay as you go |
| RunPod | RTX 4090 | $0.69 | ~$165/mo | Budget option |
| Lambda | A100 | $1.29 | ~$310/mo | Academic pricing |
| Vast.ai | RTX 4090 | $0.40-0.80 | ~$100-200/mo | Spot pricing |

### Recommendation for Cloud

**If using cloud GPU:**
1. **Start with RunPod Spot** - RTX 4090 at ~$0.50/hr
2. **Test PersonaPlex + Earth2** - Verify they fit in 24GB
3. **Upgrade to A6000/A100** if needed for simultaneous ops
4. **Consider reserved instance** if using >8 hrs/day

---

## Option 3: Hybrid Local + Cloud

Run services on different GPUs:

| Service | Location | GPU | Notes |
|---------|----------|-----|-------|
| PersonaPlex | Local RTX 5090 | 8GB used | Voice always available |
| Earth2 | Cloud A100 | 40GB | On-demand weather |
| MAS (CPU) | VM 188 | None | No GPU needed for orchestration |

**Pros**: 
- Voice always works locally
- Earth2 scales with demand
- Lower monthly cost

**Cons**:
- Latency between local and cloud
- More complex deployment
- Cloud costs accumulate

---

## Option 4: Optimize for Single GPU

If budget is limited, optimize to run on single RTX 5090:

### Model Quantization
- Use INT8 quantized Moshi (~4GB instead of 8GB)
- Use smaller Earth2 models (DLWP instead of FourCastNet)

### Time-Slicing
- Run PersonaPlex in voice-active mode only
- Unload Earth2 when not viewing simulator
- Dynamic model loading/unloading

### Implementation
```python
# GPU memory manager
class GPUMemoryManager:
    def load_personaplex(self):
        self.unload_earth2()  # Free VRAM first
        load_moshi_model()
    
    def load_earth2(self):
        self.unload_personaplex()  # Free VRAM first
        load_fourcastnet_model()
```

**Cons**: 
- Can't use voice + Earth2 simultaneously
- Loading/unloading adds latency (5-10 seconds)

---

## Recommendation

### Short-term (Now)
1. **Use local RTX 5090 for PersonaPlex** - voice works now
2. **Disable Earth2** when using voice
3. **Plan GPU purchase** for Proxmox

### Medium-term (1-2 months)
**Buy one of:**
- RTX 4090 ($1,400) - Add to Proxmox, passthrough to MAS VM
- RTX A6000 ($2,500-3,000 used) - 48GB, run everything

### Long-term (3+ months)
- Add second GPU for redundancy
- Or upgrade to dual-GPU server chassis
- Consider NVIDIA A100 for maximum capability

---

## Cost Summary

| Option | One-Time | Monthly | Notes |
|--------|----------|---------|-------|
| RTX 4090 in Proxmox | $1,400 | $30 (power) | Best value |
| RTX A6000 in Proxmox | $2,800 | $40 (power) | Best capability |
| Cloud A100 dedicated | $0 | $1,200 | No hardware |
| Cloud A100 on-demand | $0 | $300-500 | 8hrs/day |
| Hybrid (local + cloud) | $0 | $150-300 | Mixed |

---

## Next Steps

1. **Decide budget** for GPU hardware vs cloud
2. **If buying hardware**: Check Proxmox server has PCIe slot + power
3. **If cloud**: Test RunPod with PersonaPlex Docker image
4. **Document choice** in `docs/GPU_DEPLOYMENT_DECISION_FEB12_2026.md`

---

**Author**: MYCA Coding Agent
**Date**: February 12, 2026
**Status**: Awaiting decision from user
