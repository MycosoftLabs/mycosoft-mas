# Voice Topology Locked — May 19, 2026

## Active mode (dev machine)

**Mode B — Local GPU** is the locked default for Morgan's Windows dev host when `NEXT_PUBLIC_USE_LOCAL_GPU=true` in website `.env.local`.

| Component | URL | Notes |
|-----------|-----|-------|
| PersonaPlex Bridge | `http://localhost:8999` | Started via `python scripts/start_voice_system.py` |
| Moshi STT/TTS | `http://localhost:8998` | Same script; CUDA required |
| MAS Brain | `http://192.168.0.188:8001` | `/voice/brain/chat` canonical path |
| MINDEX | `http://192.168.0.189:8000` | Memory/search backing |
| Website test page | `http://localhost:3010/test-voice` | BFF proxies under `/api/test-voice/*` |

## Fallback mode (LAN Voice Legion)

When local GPU is unavailable, use **Voice Legion `192.168.0.241`**:

```env
# website .env.local — disable local GPU, point at Legion
NEXT_PUBLIC_USE_LOCAL_GPU=false
PERSONAPLEX_BRIDGE_URL=http://192.168.0.241:8999
NEXT_PUBLIC_PERSONAPLEX_BRIDGE_WS_URL=ws://192.168.0.241:8999
GPU_VOICE_IP=192.168.0.241
```

Verified May 19, 2026: TCP + HTTP health OK on 241:8998/8999 from dev host.

## Deprecated IPs (do not use)

| IP | Was used for | Replaced by |
|----|--------------|-------------|
| `192.168.0.172` | Moshi (recovery plan stale) | `192.168.0.241` or localhost |
| `192.168.0.190` | Legacy GPU node | `192.168.0.241` Voice Legion |

## Service token

`MYCA_INTERNAL_SERVICE_TOKEN` and `MAS_INTERNAL_SERVICE_TOKEN` must match across:

- MAS VM 188 `.env`
- PersonaPlex bridge process env
- Website `.env.local` (BFF proxies)

## Verification commands

```powershell
python scripts/verify_voice_stack.py
python scripts/test_personaplex_mas.py
Invoke-RestMethod http://localhost:3010/api/test-voice/diagnostics
```

## Canonical voice path

Browser → Bridge WS → Moshi → MAS `/voice/brain/chat` → edge-tts TTS fallback.

See [CANONICAL_MYCA_VOICE_PATH_MAR14_2026.md](CANONICAL_MYCA_VOICE_PATH_MAR14_2026.md).
