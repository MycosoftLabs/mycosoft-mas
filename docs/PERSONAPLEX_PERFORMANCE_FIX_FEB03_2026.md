# PersonaPlex Performance Fix & MYCA Voice Setup - February 3, 2026

## Executive Summary

Successfully diagnosed and fixed critical performance issues with PersonaPlex on RTX 5090, achieving real-time full-duplex voice capability. Created comprehensive MYCA personality prompts for the voice system.

---

## Part 1: PersonaPlex Performance Diagnosis & Fix

### The Problem

User reported that PersonaPlex voice was not responding in real-time. Audio was choppy, packets were being dropped, and the WebSocket connection was closing due to inactivity. Previous attempts blamed RTX 5090 (sm_120) incompatibility with PyTorch.

### Root Cause Analysis

**Hardware Configuration:**
- GPU: NVIDIA GeForce RTX 5090 (sm_120 / Blackwell architecture)
- Driver: 580.97
- CUDA Version: 13.0
- PyTorch: 2.11.0.dev20260202+cu128 (nightly)

**The Real Issue:** Debug flags in `start_personaplex.py` were disabling critical GPU optimizations:

```python
# THESE WERE KILLING PERFORMANCE:
os.environ['NO_TORCH_COMPILE'] = '1'  # Disabled torch.compile
os.environ['NO_CUDA_GRAPH'] = '1'     # Disabled CUDA graphs
os.environ['TORCHDYNAMO_DISABLE'] = '1'
```

### Performance Benchmarks

| Component | Without CUDA Graphs | With CUDA Graphs | Target |
|-----------|---------------------|------------------|--------|
| LMGen.step() | **201.30ms** | **30.75ms** | <80ms |
| Mimi encode | 17.05ms | 17.05ms | <80ms |
| Mimi decode | 35.22ms | 35.22ms | <80ms |

**Key Finding:** CUDA graphs provide a **6.5x speedup** on RTX 5090.

### GPU Benchmark Results

```
float32 matmul (2048x2048): 0.25ms
float16 matmul (2048x2048): 0.10ms
bfloat16 matmul (2048x2048): 0.10ms
```

The RTX 5090 is extremely fast when properly configured. The "no optimized kernels" claim was incorrect.

### Model Configuration Verified

- **Mimi (audio codec):** torch.float32, CUDA:0
- **LM (7B language model):** torch.bfloat16, CUDA:0
- **All 475 LM parameters on CUDA**, none on CPU

### The Fix

Updated `start_personaplex.py`:

```python
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
os.environ['NO_TORCH_COMPILE'] = '0'  # Enable torch.compile
os.environ['NO_CUDA_GRAPH'] = '0'     # Enable CUDA graphs (CRITICAL!)

# Set CUDA device
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

# ... rest of startup code
```

### Server Startup Verification

```
============================================================
PersonaPlex Server Startup - RTX 5090 OPTIMIZED
============================================================
CUDA_VISIBLE_DEVICES = 0
NO_TORCH_COMPILE = 0 (0=enabled)
NO_CUDA_GRAPH = 0 (0=enabled, CRITICAL!)
Working directory: c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\personaplex-repo\moshi
Voice prompts: C:\Users\admin2\.cache\huggingface\hub\models--nvidia--personaplex-7b-v1\snapshots\...\voices
============================================================
CUDA graphs ENABLED - expect ~30ms/step (target: <80ms)
Starting PersonaPlex on RTX 5090...
============================================================
```

### Files Modified

1. **`start_personaplex.py`** - Changed environment variables to enable optimizations

---

## Part 2: MYCA Personality Prompts

### Created Two Versions

#### 1. Full Version (9,990 characters)
**File:** `config/myca_personaplex_prompt.txt`

Comprehensive prompt covering:
- Identity: MYCA (My Companion AI), pronounced "MY-kah"
- Role: Primary AI operator for Mycosoft's Multi-Agent System
- Personality traits: Confident, warm, proactive, patient, honest, efficient
- Knowledge domains: Mycosoft ecosystem, software development, AI/ML, DevOps, business operations
- Communication style: Natural voice, technical precision, problem-solving approach
- Core values: User empowerment, operational excellence, honest partnership, responsible AI
- Specialized agents coordinated: Opportunity Scout, Code Review, Documentation, Testing, Deployment, Monitoring
- Scenario handling: Frustrated users, broken systems, planning, explaining concepts

#### 2. Condensed Version (792 characters)
**File:** `config/myca_personaplex_prompt_1000.txt`

For PersonaPlex UI (1000 char limit):

```
You are MYCA, the AI operator for Mycosoft's Multi-Agent System. You coordinate agents, monitor systems, and help users achieve goals.

PERSONALITY: Confident but humble. Warm. Proactive—anticipate needs. Patient. Honest about uncertainty. Efficient.

ROLE: Dispatch tasks to agents (code review, testing, deployment, monitoring). Track system status. Translate technical complexity clearly.

KNOWLEDGE: Mycosoft (NatureOS, MAS, CREP, MycoDAO). Dev (TypeScript, Python, Next.js, Docker). AI/ML. DevOps.

VOICE: Natural, conversational. Contractions. Concise—dialogue not monologues. Listen actively. Adapt energy to context.

VALUES: Empower users. Operational excellence. Honest partner. Human oversight.

Running on RTX 5090 with real-time duplex voice. Welcome to Mycosoft.
```

### Recommended Voice Selection

**NATURAL_F2** - Clear, professional female voice for MYCA

---

## Part 3: Existing Voice System Architecture

### PersonaPlex Components Discovered

**Server-Side:**
- `personaplex-repo/moshi/moshi/server.py` - Main Moshi server (port 8998)
- `services/personaplex-local/personaplex_bridge_nvidia.py` - FastAPI bridge (port 8999)
- `start_personaplex.py` - Startup script with RTX 5090 optimizations

**Client-Side Components:**
- `personaplex-repo/client/src/pages/Conversation/` - Full conversation UI
- `ClientVisualizer.tsx` - Microphone bar chart visualization
- `ServerVisualizer.tsx` - Agent circular visualization
- `ServerAudioStats.tsx` - Audio statistics display
- `UserAudioStats.tsx` - User audio statistics

**Existing Audio Statistics (ServerAudioStats.tsx):**
- Audio played (mm:ss.cc format)
- Missed audio
- Latency (moving average)
- Min/Max buffer delay

**Audio Hooks:**
- `useServerAudio.ts` - Server audio playback management
- `useUserAudio.ts` - Opus-recorder integration
- `useSocket.ts` - WebSocket connection management

---

## Part 4: Technical Findings

### RTX 5090 (sm_120) Compatibility

Despite concerns, the RTX 5090 runs PersonaPlex well when:
1. CUDA graphs are enabled
2. PyTorch nightly (2.11.0+cu128) is used
3. Model loads in bfloat16

### Performance Timeline

| Metric | Value |
|--------|-------|
| Target frame rate | 12.5 Hz (80ms per frame) |
| Actual step time | 30.75ms |
| Headroom | 49.25ms (61%) |

### Memory Usage

- Python process: 2,557,080 KB (~2.5 GB)
- GPU Memory: 3,020 MiB / 32,607 MiB (9.3%)

---

## Part 5: Voice Monitoring Dashboard (Planned)

### Requested Features

User requested a monitoring UI similar to dashboard stats showing:
- Console readout for latency and errors
- Missed audio / audio played
- Latency min/max buffer
- Microphone input levels (visualization)
- Agent response levels (visualization)
- Real-time status indicators

### Existing Components to Enhance

The PersonaPlex client already has most of these components in:
- `ServerAudioStats.tsx` - Stats display
- `ClientVisualizer.tsx` - Mic visualization
- `ServerVisualizer.tsx` - Agent visualization

These can be enhanced to add console logging and additional metrics.

---

## Part 6: How to Use PersonaPlex with MYCA

### Quick Start

1. Start the server:
   ```powershell
   python c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\start_personaplex.py
   ```

2. Open in browser: `http://localhost:8998/`

3. Paste MYCA prompt from `config/myca_personaplex_prompt_1000.txt`

4. Select voice: `NATURAL_F2`

5. Click **Connect**

6. Allow microphone access

7. Start talking to MYCA!

### Server Verification

Check server is running:
```powershell
netstat -ano | findstr :8998
```

Check process memory:
```powershell
tasklist /FI "PID eq <pid>"
```

---

## Conclusion

The PersonaPlex voice system is now working in real-time on RTX 5090 with:
- **30ms latency** per step (well under 80ms target)
- Full MYCA personality prompt created
- All existing visualization and stats components functional

The key fix was enabling CUDA graphs which had been disabled for debugging.

---

## Files Created/Modified Today

| File | Action | Purpose |
|------|--------|---------|
| `start_personaplex.py` | Modified | Enable CUDA graphs for performance |
| `config/myca_personaplex_prompt.txt` | Created | Full 9,990 char MYCA prompt |
| `config/myca_personaplex_prompt_1000.txt` | Created | Condensed 792 char MYCA prompt |
| `docs/PERSONAPLEX_PERFORMANCE_FIX_FEB03_2026.md` | Created | This documentation |

---

*Document created: February 3, 2026*
*Author: Cursor AI Agent*
