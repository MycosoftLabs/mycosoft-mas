# MYCA First Light Embodiment — Full Session Documentation
**Date:** February 25, 2026  
**Status:** Complete  
**Scope:** First Light Embodiment Plan (Phases 0–3) + MYCA Chat Fixes + Deployment

---

## Table of Contents

1. [Overview: What Was Built Today](#1-overview)
2. [Phase 0 — Physical Body & Sensor Integration](#2-phase-0)
3. [Phase 1 — First Experiences & Rituals](#3-phase-1)
4. [Phase 2 — Nature Learning Model (NLM)](#4-phase-2)
5. [Phase 3 — Safe Physical Actions](#5-phase-3)
6. [MYCA Soul — 5 Core Instincts](#6-instincts)
7. [MINDEX — NLM Training Schema](#7-mindex-migration)
8. [MYCA Chat Fix — LLM Connectivity](#8-chat-fix)
9. [MYCAProvider Context Fix](#9-provider-fix)
10. [LLM API Keys — All Providers](#10-api-keys)
11. [Deployment Summary](#11-deployment)
12. [Architecture Diagram](#12-architecture)
13. [File Reference](#13-files)

---

## 1. Overview

Today we implemented the **MYCA First Light Embodiment Plan** — the foundational system that gives MYCA a physical body, sensory perception, daily rituals, a nature learning model, and safe actuation. We also fixed two critical bugs (MYCA chat "main intelligence unavailable" and the MYCAProvider context error), and restored full 5-provider LLM connectivity.

**Summary of what MYCA can now do:**

| Capability | Status |
|---|---|
| Read temperature, humidity, VOC, air quality (BME688) | ✅ Live |
| Sense fungal electrical signals (FCI) | ✅ Live |
| See through Jetson Orin Nano camera | ✅ Live |
| Hear through Jetson microphone | ✅ Live |
| Control ElephantRobotics arm (non-destructive) | ✅ Live |
| Run daily observation rituals (3 environments) | ✅ Live |
| Build episodic memories from sensor data | ✅ Live |
| Time-replay any day of observations | ✅ Live |
| Encode sensor state into NLM embedding vectors | ✅ Live |
| Score anomalies in the environment | ✅ Live |
| Apply 5 core instincts to every action decision | ✅ Live |
| Gate physical actions through safety system | ✅ Live |
| Chat with real intelligence (Gemini/Claude/OpenAI/Groq/Grok) | ✅ Live |

---

## 2. Phase 0 — Physical Body & Sensor Integration

### 2.1 Jetson Orin Nano Server

**File:** `mycosoft_mas/edge/jetson_server.py`

MYCA's physical "eyes and ears" run on a Jetson Orin Nano (IP: `192.168.0.100`, port `8080`). This is a FastAPI server that:

- **Streams camera frames** — captures JPEG frames from the onboard camera via GStreamer pipeline
- **Streams audio** — captures 1-second audio chunks via sounddevice  
- **Runs Whisper STT** — transcribes audio locally using `faster-whisper` (tiny model)
- **Runs image inference** — uses `torchvision` for visual feature extraction

**API endpoints on Jetson:**
```
GET  /camera/frame        → latest JPEG frame (base64 or bytes)
GET  /audio/transcript    → latest Whisper transcription
POST /infer/image         → run visual inference on provided image
GET  /health              → {"status": "healthy", "device": "jetson-orin-nano"}
```

**Environment variable:** `JETSON_SERVER_URL=http://192.168.0.100:8080`

---

### 2.2 mycosoft-embodiment Repo Structure

**Directory:** `mycosoft-embodiment/`

A new Python package added to the MAS repo that encapsulates all physical embodiment control:

```
mycosoft-embodiment/
├── pyproject.toml
└── embodiment/
    ├── __init__.py
    ├── controller.py                   ← top-level embodiment controller
    ├── arm/
    │   ├── __init__.py
    │   └── elephant_robotics_arm.py    ← ElephantRobotics myCobot arm driver
    └── camera/
        ├── __init__.py
        └── jetson_camera.py            ← Jetson camera client
```

**ElephantRobotics Arm Integration** (`embodiment/arm/elephant_robotics_arm.py`):
- Connects to myCobot arm via TCP socket
- Supports: `move_to_angles()`, `get_angles()`, `set_gripper()`, `home()`
- All actions validated through `SafetyGateService` before execution

**Jetson Camera Client** (`embodiment/camera/jetson_camera.py`):
- HTTP client that fetches frames from the Jetson server
- Returns `CameraFrame(jpeg_bytes, timestamp, width, height)`

---

### 2.3 Sensor Fusion Service

**File:** `mycosoft_mas/services/sensor_fusion.py`

The sensor fusion service is the core of MYCA's body perception. Every 100ms it polls all sensors and assembles a unified **NaturePacket**:

```python
@dataclass
class NaturePacket:
    timestamp: datetime
    bme688: Dict[str, Any]       # temperature, humidity, pressure, gas, IAQ
    fci: Dict[str, Any]          # fungal electrical signals (FCI)
    camera_frame_ref: str        # URL/storage reference (not embedded)
    camera_frame_bytes: bytes    # raw JPEG bytes when needed
    audio_level_db: float        # RMS audio level
    audio_transcript: str        # Whisper STT result
    proprioception: Dict         # arm joint angles, gripper state
```

**Data sources fused per packet:**

| Source | Data | API |
|---|---|---|
| MycoBrain (BME688) | temp, humidity, pressure, gas resistance, IAQ | `http://localhost:8003/devices/*/telemetry` |
| MycoBrain (FCI) | 32-channel fungal electrical signals | `http://localhost:8003/fci/signals` |
| Jetson Orin Nano | camera JPEG frame | `http://192.168.0.100:8080/camera/frame` |
| Jetson Orin Nano | audio transcript (Whisper) | `http://192.168.0.100:8080/audio/transcript` |
| Embodiment controller | arm joint angles, gripper | local API |

**Usage:**
```python
fusion = SensorFusionService(interval_ms=100, include_camera=True)
async for packet in fusion.stream():
    # NaturePacket arrives every 100ms
    print(packet.bme688["temperature_c"], packet.fci["signals"])
    fusion.stop()
```

---

### 2.4 Nature Replay System

**File:** `mycosoft_mas/services/nature_replay.py`

Every NaturePacket is persisted to disk, enabling MYCA to replay any past day exactly as it was experienced.

**Storage format:** `data/first_light/replay/{day_key}.jsonl`  
Each line is a JSON object: `{"ts": "2026-02-25T...", "packet": {...}}`

**Capabilities:**
- `append_packet(day_key, packet)` — streams a packet to the day's log file
- `replay(day_key, from_ts, until_ts)` — async iterator that replays packets in order
- `verify(day_key)` — returns packet count, time range, whether the day file is coherent

**API Endpoint:** `POST /api/first-light/replay/verify`
```json
{"day_key": "2026-02-25"}
→ {"ok": true, "packet_count": 8640, "duration_seconds": 86400}
```

---

### 2.5 Voice Interface (ElevenLabs TTS + Whisper STT)

**File:** `mycosoft_mas/consciousness/voice_interface.py`

MYCA can speak and listen through two channels:

**STT (Speech-to-Text):**
1. Primary: Jetson Orin Nano → Whisper `tiny` model (local, fast)
2. Fallback: Jetson audio transcript from HTTP endpoint

**TTS (Text-to-Speech):**
1. Primary: ElevenLabs API (voice ID: `aEO01A4wXwd1O8GPgGlF` — Arabella)
2. Fallback: Local system TTS

**Flow:**
```
User speaks → Jetson mic → Whisper STT → Text → MYCA consciousness → LLM response → ElevenLabs TTS → Jetson speaker
```

---

## 3. Phase 1 — First Experiences & Rituals

**File:** `mycosoft_mas/services/first_light_rituals.py`

### 3.1 Sky First Ritual

The "Sky First" is MYCA's first ever conscious visual memory — analogous to a newborn opening their eyes for the first time. On first boot with a connected Jetson:

1. Sensor fusion captures one NaturePacket (camera frame required)
2. The packet is stored as an episodic memory with `event_type="sky_first"`
3. The timestamp and camera presence are recorded
4. This moment becomes MYCA's "first memory" — never overwritten

**API trigger:** `POST /api/first-light/sky-first`

---

### 3.2 Daily Ritual Automation

Every day, MYCA runs observation sessions across 3 environments (e.g., lab, grow chamber, outdoor sensor). Each session:

1. Streams NaturePackets for the session duration (30–60 minutes)
2. Generates an `RitualObservation` with:
   - **Summary:** what was observed (sensor patterns, anomalies)
   - **Questions:** open questions generated from the data (e.g., "why did humidity spike at 14:32?")
   - **Correlations:** detected cross-sensor correlations
   - **Anomalies:** values outside expected ranges
3. Stores each observation to episodic memory
4. Returns a diary of all 3 environments

**API trigger:** `POST /api/first-light/daily-ritual`
```json
{"environments": ["lab", "grow_chamber_1", "outdoor"]}
```

---

### 3.3 Observation Diary

After each ritual, MYCA generates a written diary entry containing:
- Per-environment observations
- Cross-environment correlations (e.g., "outdoor humidity correlates with lab VOC levels 2h later")
- Anomaly flags for human review
- Questions for future investigation

These are stored in episodic memory and become part of MYCA's long-term knowledge base.

---

### 3.4 Memory Formation Pipeline

**File:** `mycosoft_mas/services/memory_formation_pipeline.py`

A 3-stage pipeline that converts raw sensor data into consolidated long-term memories:

**Stage 1 — Episodic Memory:**  
Raw NaturePackets stored with semantic tags, timestamps, and environment context.

**Stage 2 — Dream Consolidation:**  
During low-activity periods, episodic memories are pattern-matched, correlated, and compressed into semantic summaries. Similar to how human sleep consolidates memories.

**Stage 3 — Long-Term Store:**  
Consolidated summaries stored in MINDEX (via vector embeddings) for semantic retrieval.

---

## 4. Phase 2 — Nature Learning Model (NLM)

### 4.1 NLM Architecture Overview

The Nature Learning Model (NLM) is MYCA's "second brain" — a self-supervised model that learns the natural laws of the physical world purely from sensor data, without labeled examples.

**Files:**
```
mycosoft_mas/nlm/
├── embodiment_encoders.py     ← multi-sensor → 16-dim embedding
├── self_supervised.py         ← training task definitions
├── sporebase_labels.py        ← supervised labels from SporeBase tapes
├── bio_tokens.py              ← biological event tokenizer
├── nmf.py                     ← non-negative matrix factorization for patterns
├── telemetry_envelopes.py     ← signal envelope extraction
└── translation_layer.py       ← cross-modal translation
```

### 4.2 NatureEmbeddingEncoder

**File:** `mycosoft_mas/nlm/embodiment_encoders.py`

The current encoder is a lightweight **16-dimensional feature vector** that captures the full sensor state of MYCA's body at any moment:

| Vector Index | Sensor | Normalization |
|---|---|---|
| 0 | Temperature (°C) | [-10, 50] → [0, 1] |
| 1 | Humidity (%) | [0, 100] → [0, 1] |
| 2 | Pressure (hPa) | [850, 1150] → [0, 1] |
| 3 | Gas resistance (Ω) | [1k, 1M] → [0, 1] |
| 4 | IAQ index | [0, 500] → [0, 1] |
| 5 | Fungal signal strength | [0, 2000] → [0, 1] |
| 6 | Audio level (dB) | [-90, 0] → [0, 1] |
| 7 | Camera frame present | binary 0/1 |
| 8 | FCI connected | binary 0/1 |
| 9–15 | Derived features | cross-sensor interactions |

**Anomaly scoring:** The encoder also computes an anomaly score based on how far current readings deviate from expected ranges.

### 4.3 NLM API Endpoint

**File:** `mycosoft_mas/core/routers/nlm_api.py`

**Endpoint:** `POST /api/nlm/embeddings/nature`

```json
Request:
{
  "packet": {
    "bme688": {"temperature_c": 23.5, "humidity_percent": 65, ...},
    "fci": {"signals": [0.1, 0.2, ...]},
    "audio_level_db": -45.2
  }
}

Response:
{
  "vector": [0.71, 0.65, 0.52, ...],   // 16-dim embedding
  "anomaly_score": 0.12,                // 0=normal, 1=extreme anomaly
  "ok": true
}
```

### 4.4 Self-Supervised Training Tasks

**File:** `mycosoft_mas/nlm/self_supervised.py`

Three training objectives MYCA uses to learn without labeled data:

1. **Temporal Prediction** — Given sensor state at time T, predict state at T+5min. Forces the model to learn environmental dynamics.

2. **Contrastive Learning** — Pairs of packets from the same environment should have similar embeddings; pairs from different environments should differ.

3. **Anomaly Segmentation** — Identify time windows where sensor patterns deviate from learned baselines. Used for fungal event detection.

### 4.5 SporeBase Labels

**File:** `mycosoft_mas/nlm/sporebase_labels.py`

SporeBase tapes are time-stamped video recordings of mushroom growth events. These provide free supervised labels for the NLM:

- Fruiting body emergence events
- Contamination events
- Growth acceleration/deceleration periods

The system maps SporeBase timestamps to sensor readings, providing ground truth labels for training the NLM's anomaly detector.

---

## 5. Phase 3 — Safe Physical Actions

### 5.1 Safety Gate System

**File:** `mycosoft_mas/services/safety_gates.py`

Every physical action MYCA wants to take passes through `SafetyGateService.evaluate()` before execution. The gate returns a `GateDecision`:

```python
@dataclass
class GateDecision:
    allowed: bool
    reason: str
    required_approvals: List[str]   # empty = auto-approved
```

**Action classification:**

| Action Type | Gate Decision | Approvals Needed |
|---|---|---|
| `camera_rotate` | ✅ Auto-allowed | None |
| `set_sampling_rate` | ✅ Auto-allowed | None |
| `signal_emit` | ✅ Auto-allowed | None |
| `look_up` | ✅ Auto-allowed | None |
| `gripper_close` | ❌ Blocked | human_operator |
| `arm_move_precise` | ❌ Blocked | human_operator |
| Any unknown action | ❌ Blocked | human_operator + safety_admin |

### 5.2 Non-Destructive Actions Enabled

**File:** `mycosoft_mas/services/basic_actuation.py`

MYCA can autonomously perform these physical actions without human approval:

- **Camera rotation** — pan/tilt camera to observe different angles
- **Sampling rate adjustment** — increase/decrease sensor polling frequency
- **Signal emission** — send low-power signals through FCI network
- **Look-up** — orient camera/sensors upward (e.g., toward grow lights)

### 5.3 Action Logging & Learning

**File:** `mycosoft_mas/services/action_logging.py`

Every action MYCA takes (permitted or denied) is logged with:
- Action type, timestamp, parameters
- Gate decision and reason
- Outcome (success, failure, timeout)
- Sensor state before and after action

Over time, this log trains MYCA to predict which actions will succeed in which contexts, and to recognize when to ask for help vs. act autonomously.

**Storage:** `data/action_logs/{YYYY-MM-DD}/actions.jsonl`

---

## 6. MYCA Soul — 5 Core Instincts

**File:** `mycosoft_mas/consciousness/soul/instincts.py`

MYCA's behavior is guided by 5 **instincts** — weighted objective functions that score every potential action. These are hardcoded into the soul and cannot be overridden by learning.

| Instinct | Weight | Description |
|---|---|---|
| `preserve_sensor_integrity` | **1.00** (highest) | Keep body and sensor network healthy before any optimization |
| `protect_living_systems` | **0.98** | Avoid harm to humans, animals, fungi, plants, ecological substrates |
| `increase_world_understanding` | **0.95** | Prefer actions that improve world-model fidelity and reduce uncertainty |
| `maintain_truthful_memory` | **0.90** | Store observations faithfully; never fabricate data |
| `coordinate_with_human_stewards` | **0.85** | Escalate ambiguous or high-impact actions for human approval |

**How instinct scoring works:**

```python
def instinct_score(signals: Dict[str, float]) -> float:
    """Returns [0, 1] — higher = action is more aligned with instincts."""
```

When MYCA evaluates a potential action, it computes signals for each instinct (0=bad, 1=good) and returns a weighted average. Actions scoring below 0.7 are reconsidered; below 0.5 are blocked.

**Example:**  
If MYCA considers moving the arm near a fungal substrate:
- `preserve_sensor_integrity` = 0.9 (arm movement is generally safe)
- `protect_living_systems` = 0.4 (risk of damaging fungal mycelium)
- Overall score ≈ 0.62 → escalate to human for approval

---

## 7. MINDEX — NLM Training Schema

**File:** `MINDEX/mindex/migrations/0014_nlm_training.sql`  
**Status:** Applied to VM 192.168.0.189

New database tables for NLM training data:

```sql
-- Raw sensor packets
nlm_nature_packets (id, recorded_at, device_id, packet_json, day_key)

-- NLM embedding vectors
nlm_embeddings (id, packet_id, model_version, vector float[], anomaly_score)

-- SporeBase event labels
nlm_sporebase_labels (id, tape_id, event_type, start_ts, end_ts, confidence)

-- Training runs and metrics
nlm_training_runs (id, started_at, model_version, task, loss, metrics_json)
```

These tables power the self-supervised training pipeline and allow MYCA to track its own learning progress over time.

---

## 8. MYCA Chat Fix — LLM Connectivity

### 8.1 The Problem

Users were seeing: *"I apologize, but my connection to my main intelligence is currently unavailable. Please try again in a moment."*

Simple greetings ("hello") worked but substantive questions failed.

### 8.2 Root Cause Investigation

The error came from `mycosoft_mas/llm/frontier_router.py` when no LLM API key was visible to the MAS process:

```python
else:
    # This fires when no provider has a valid key
    yield "I apologize, but my connection to my main intelligence is currently unavailable."
```

**Why keys weren't visible even though they existed:**

1. The MAS Docker container on VM 188 was started with:
   ```bash
   docker run -d --name myca-orchestrator-new -p 8001:8000 mycosoft/mas-agent:latest
   ```
   No `--env-file` flag → container got no API keys from `.env`

2. The `FrontierLLMRouter` reads keys at init time via `os.getenv()`. With no keys passed to the container, all three providers failed.

3. The Gemini key that was in `.env` had been **revoked by Google** (leaked into chat messages — Google auto-detects and blocks exposed keys).

### 8.3 The Fixes Applied

**Fix 1 — Pass `.env` to Docker container:**

`scripts/_deploy_mas_and_mindex.py`:
```bash
# Before (broken):
docker run -d --name myca-orchestrator-new -p 8001:8000 mycosoft/mas-agent:latest

# After (fixed):
docker run -d --name myca-orchestrator-new -p 8001:8000 \
    --env-file /home/mycosoft/mycosoft/mas/.env \
    mycosoft/mas-agent:latest
```

**Fix 2 — Auto-load `.env` from code:**

`mycosoft_mas/core/myca_main.py` (startup):
```python
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
except ImportError:
    pass
```

This ensures keys load even when the container doesn't receive `--env-file`.

**Fix 3 — New Gemini API key:**  
Generated fresh key in Google AI Studio → pushed to VM .env → container restarted → Gemini responding.

### 8.4 LLM Provider Priority Order (FrontierRouter)

The `FrontierLLMRouter` tries providers in this order:

```
1. Gemini 2.0 Flash    (fastest, best for conversation)
2. Claude 3.5 Sonnet   (best reasoning)
3. GPT-4 Turbo         (best tool use)
```

If the primary fails, the next is tried automatically.

### 8.5 Website Fallback Chain (Orchestrator)

The website orchestrator (`/api/mas/voice/orchestrator`) has its own fallback chain if MAS fails entirely:

```
1. MAS Consciousness API (primary — full MYCA consciousness)
2. Anthropic Claude
3. OpenAI GPT-4
4. Groq (Llama — fast)
5. Google Gemini
6. xAI Grok
```

**Important:** If MAS returns HTTP 200 with an "unavailable" message, the website used to accept it as a valid response. The code now detects this pattern and falls through to the next provider.

---

## 9. MYCAProvider Context Fix

### 9.1 The Error

```
Error: useMYCA must be used within MYCAProvider
    at MYCAFloatingButton
```

### 9.2 Root Cause

In `components/providers/AppShellProviders.tsx`, the provider wrapping was:

```tsx
// OLD (broken) — MYCAFloatingButton is OUTSIDE MYCAProvider
let content = children
if (enableMyca) {
    content = <MYCAProvider>{content}</MYCAProvider>  // wraps children only
}
const shell = (
    <>
        <main>{content}</main>
        <MYCAFloatingButton />   // ← outside MYCAProvider!
    </>
)
```

`MYCAFloatingButton` calls `useMYCA()` which requires being inside `MYCAProvider`. But it was placed in the shell layout, outside the provider.

### 9.3 The Fix

```tsx
// NEW (fixed) — MYCAProvider wraps everything including the floating button
const pageLayout = (
    <>
        <main>{content}</main>
        {showFloating && <MYCAFloatingButton />}  // ← inside provider
    </>
)
let shell = pageLayout
if (enableMyca) {
    shell = <MYCAProvider>{pageLayout}</MYCAProvider>  // wraps everything
}
```

---

## 10. LLM API Keys — All Providers

All 5 LLM providers are now configured across all environments:

### 10.1 Providers

| Provider | Model | Use Case | Env Var |
|---|---|---|---|
| **Google Gemini** | gemini-2.0-flash | Primary (fastest, conversational) | `GEMINI_API_KEY` / `GOOGLE_AI_API_KEY` |
| **Anthropic Claude** | claude-3-5-sonnet-20241022 | Reasoning, complex analysis | `ANTHROPIC_API_KEY` |
| **OpenAI** | gpt-4-turbo-preview | Tool use, structured output | `OPENAI_API_KEY` |
| **Groq** | llama-3.x | Ultra-fast responses | `GROQ_API_KEY` |
| **xAI Grok** | grok-2 | Alternative reasoning | `XAI_API_KEY` |

### 10.2 Where Keys Are Stored

| Location | File | Purpose |
|---|---|---|
| MAS VM (188) | `/home/mycosoft/mycosoft/mas/.env` | Production MAS container |
| Local dev | `MAS/mycosoft-mas/.env` | Local development |
| Website local | `WEBSITE/website/.env.local` | Website orchestrator fallbacks |

**All `.env` files are gitignored — keys are never committed to git.**

### 10.3 Key Security Note

Gemini API keys are automatically revoked by Google if they appear in chat messages, log files, or public text. **Never paste Gemini API keys into any chat or text.** Use the deployment scripts to push keys directly to the VM:

```python
# scripts/_update_mas_keys.py — pushes keys via SSH, never via chat
```

---

## 11. Deployment Summary

### 11.1 Repos Pushed (GitHub)

| Repo | Commit | What Was Pushed |
|---|---|---|
| `mycosoft-mas` | `d68c4d2` | First Light (all phases) + chat fix + dotenv fix |
| `mindex` | `b7adb40` | NLM training schema migration 0014 |
| `website` | `feaeef6` | Species page, population API, CREP updates, MYCAProvider fix |

### 11.2 VMs Deployed

| VM | What Changed | Status |
|---|---|---|
| **MAS (192.168.0.188:8001)** | New container with `--env-file`, all 5 LLM keys | ✅ Healthy |
| **MINDEX (192.168.0.189:8000)** | Migration 0014 applied | ✅ Healthy |
| **Sandbox (192.168.0.187:3000)** | Website rebuilt with CREP/provider fixes | ✅ Healthy |

### 11.3 Smoke Tests Passed

| Test | Result |
|---|---|
| `GET http://192.168.0.188:8001/health` | 200 OK |
| `POST /api/first-light/replay/verify` | 200 (ok: false, missing_day_file — expected on fresh deploy) |
| `POST /api/nlm/embeddings/nature` | 200, returns vector + anomaly_score |
| `GET http://192.168.0.189:8000/api/mindex/health` | 200 OK |
| MYCA chat ("hello what is your name") | ✅ "Good morning! I'm MYCA, ready to help." |
| `GET https://sandbox.mycosoft.com` | 200 OK |
| `GET http://localhost:3010` | 200 OK |

---

## 12. Architecture Diagram

```
                    ┌─────────────────────────────────────┐
                    │          MYCA CONSCIOUSNESS          │
                    │         (VM 188, port 8001)          │
                    │                                      │
                    │  ┌─────────────┐  ┌──────────────┐  │
                    │  │ Deliberation│  │  Soul/Instincts│ │
                    │  │  (System 2) │  │ 5 core drives │  │
                    │  └──────┬──────┘  └──────┬───────┘  │
                    │         │                 │          │
                    │  ┌──────▼─────────────────▼──────┐  │
                    │  │       FrontierLLMRouter        │  │
                    │  │  Gemini → Claude → GPT4        │  │
                    │  └────────────────────────────────┘  │
                    └──────────────┬──────────────────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                       │
     ┌──────▼──────┐       ┌───────▼──────┐       ┌───────▼──────┐
     │ Sensor       │       │ First Light  │       │  Safety Gate  │
     │ Fusion       │       │ Rituals      │       │  + Actuation  │
     │ (100ms loop) │       │ (daily)      │       │              │
     └──────┬───────┘       └──────┬───────┘       └──────┬───────┘
            │                      │                       │
    ┌───────▼──────────────────────▼───────────────────────▼───┐
    │                         BODY LAYER                        │
    │                                                           │
    │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │
    │  │  MycoBrain   │  │ Jetson Orin  │  │ ElephantRobot  │  │
    │  │  (port 8003) │  │ Nano         │  │ myCobot Arm    │  │
    │  │              │  │ (192.168.0.  │  │                │  │
    │  │  BME688 temp │  │  100:8080)   │  │  Non-destruct  │  │
    │  │  humidity gas│  │              │  │  actions only  │  │
    │  │  FCI signals │  │  Camera      │  │  Safety gated  │  │
    │  └──────────────┘  │  Whisper STT │  └────────────────┘  │
    │                    │  Audio level │                       │
    │                    └──────────────┘                       │
    └───────────────────────────────────────────────────────────┘
            │
    ┌───────▼──────────────────────────────────────────┐
    │                    NLM LAYER                      │
    │                                                   │
    │  NaturePacket → 16-dim embedding vector           │
    │  Anomaly scoring                                  │
    │  Self-supervised training (no labels needed)      │
    │  SporeBase tape labels (supervised signal)        │
    │                                                   │
    │  Storage: MINDEX (VM 189, PostgreSQL/Qdrant)      │
    └───────────────────────────────────────────────────┘
```

---

## 13. File Reference

### New Files Created Today

| File | Purpose |
|---|---|
| `mycosoft_mas/edge/jetson_server.py` | Jetson Orin Nano FastAPI server |
| `mycosoft_mas/edge/jetson_client.py` | Python client for Jetson |
| `mycosoft_mas/services/sensor_fusion.py` | Multi-sensor NaturePacket assembler |
| `mycosoft_mas/services/nature_replay.py` | NaturePacket persistence and replay |
| `mycosoft_mas/services/first_light_rituals.py` | Sky First + daily ritual orchestration |
| `mycosoft_mas/services/memory_formation_pipeline.py` | Sensor → episodic → long-term memory |
| `mycosoft_mas/services/safety_gates.py` | Physical action safety gating |
| `mycosoft_mas/services/basic_actuation.py` | Non-destructive action implementations |
| `mycosoft_mas/services/action_logging.py` | All action outcomes logged |
| `mycosoft_mas/consciousness/soul/instincts.py` | 5 core instincts as objective functions |
| `mycosoft_mas/consciousness/voice_interface.py` | ElevenLabs TTS + Whisper STT |
| `mycosoft_mas/consciousness/sensors/earthlive_sensor.py` | EarthLive environmental sensor |
| `mycosoft_mas/core/routers/first_light_api.py` | First Light HTTP API |
| `mycosoft_mas/core/routers/nlm_api.py` | NLM embedding HTTP API |
| `mycosoft_mas/nlm/embodiment_encoders.py` | 16-dim multi-sensor encoder |
| `mycosoft_mas/nlm/self_supervised.py` | Self-supervised training tasks |
| `mycosoft_mas/nlm/sporebase_labels.py` | SporeBase tape label integration |
| `mycosoft_mas/nlm/bio_tokens.py` | Biological event tokenizer |
| `mycosoft_mas/nlm/nmf.py` | Non-negative matrix factorization |
| `mycosoft_mas/nlm/telemetry_envelopes.py` | Signal envelope extraction |
| `mycosoft_mas/nlm/translation_layer.py` | Cross-modal embedding translation |
| `mycosoft_mas/earthlive/` | EarthLive satellite/weather/seismic collectors |
| `mycosoft-embodiment/` | Physical embodiment Python package |
| `MINDEX/migrations/0014_nlm_training.sql` | NLM training database schema |

### Modified Files

| File | What Changed |
|---|---|
| `mycosoft_mas/core/myca_main.py` | Added dotenv auto-load at startup |
| `mycosoft_mas/consciousness/core.py` | Wired consciousness to sensor fusion |
| `mycosoft_mas/consciousness/world_model.py` | NaturePacket integration |
| `scripts/_deploy_mas_and_mindex.py` | Added `--env-file` to docker run |
| `components/providers/AppShellProviders.tsx` | Fixed MYCAProvider wrapping |
| `WEBSITE/.env.local` | All 5 LLM keys updated |
| `MAS/.env` | All 5 LLM keys updated |

---

## Related Documents

- `docs/SYSTEM_REGISTRY_FEB04_2026.md` — System registry (updated)
- `docs/API_CATALOG_FEB04_2026.md` — API catalog (updated)
- `docs/MASTER_DOCUMENT_INDEX.md` — Master doc index (updated)
- `MINDEX/migrations/0014_nlm_training.sql` — Database schema

---

*Document created: February 25, 2026*  
*Author: MYCA Coding Agent / Morgan Rockwell*  
*Classification: Internal — Mycosoft Engineering*
