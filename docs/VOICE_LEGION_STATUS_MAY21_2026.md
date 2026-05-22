# Voice Legion Status — May 21, 2026

## Scope

PersonaPlex-only validation for RTX 4080 local stack and Voice Legion-compatible topology:

- Moshi server: `localhost:8998`
- PersonaPlex Bridge: `localhost:8999`
- Website voice page: `http://localhost:3010/test-voice`

## Current operational truth

- Bridge health is consistently:
  - `status=healthy`
  - `moshi_available=true`
  - `local_stt_mode=false`
- Bridge now forwards `moshi_ready` only after receiving real Moshi `0x00` handshake.
- VAD barge-in in Moshi duplex path is disabled by default via `MYCA_ENABLE_VAD_BARGE_IN=false`.
- Bridge session cleanup now cancels the sibling task when either browser->moshi or moshi->browser loop exits, then actively closes upstream Moshi WS to reduce stale-session reconnect stalls.

## Verification evidence (May 21, 2026 runs)

1. Fresh-stack run confirms handshake chain:
   - `bridge_ready local_stt=false`
   - `moshi handshake 0x00`
   - `moshi_ready`
2. Reconnect behavior improved after session cleanup fix:
   - Bridge logs show proper `Session ended` after browser close instead of hanging gather loops.
3. Explicit text-turn spoken reply path fixed in bridge:
   - `process_with_mas_brain(..., force_spoken_reply=True)` now guarantees spoken output for `user_speech` text turns in Moshi mode.
   - Bridge attempts Moshi `0x02` text injection and also emits local TTS fallback packets for deterministic audibility.
4. Post-fix QA pass (`scripts/qa_voice_user_speech_tts.py`):
   - `bridge_ready local_stt=false`
   - `moshi handshake 0x00`
   - `myca text: Hello! I'm MYCA...`
   - `first audio packet 102 bytes`
   - `audio_packets 173`

## Canonical PersonaPlex gates

Use:

```powershell
cd C:\Users\Owner1\mycosoft-mas
python scripts/verify_personaplex_bridge_e2e.py
python scripts/qa_voice_user_speech_tts.py
```

Gate checks:

- `bridge_ready` reports `local_stt_mode=false`
- Real Moshi `0x00` handshake is received
- Bridge emits outbound audio packet(s) without switching to local STT bypass
- QA text-turn path produces MYCA text and non-zero audio packets

## Required runtime flags

- `MYCA_FORCE_MOSHI=true`
- `MYCA_4080_LOCAL_STT=false`
- `MYCA_ENABLE_VAD_BARGE_IN=false` (unless explicitly testing barge-in)
- `PERSONAPLEX_CPU_OFFLOAD=1`
- `NO_CUDA_GRAPH=1`
- `NO_TORCH_COMPILE=1`

## Known constraints

- First connection warmup on 4080 can still take 30-90s.
- Synthetic audio automation is less reliable than real microphone speech for sustained Moshi responses.
- `asyncpg` is not installed, so voice session DB persistence is degraded; this does not block live duplex transport.
