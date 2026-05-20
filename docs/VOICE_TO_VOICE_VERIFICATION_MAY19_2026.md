# Voice-to-Voice Verification — May 19, 2026

Gate results for `/test-voice` voice stack (local dev, Mode B — Local GPU).

## Infrastructure

| Check | Result |
|-------|--------|
| MAS 188:8001 TCP | OK |
| MINDEX 189:8000 TCP | OK |
| Bridge localhost:8999 | OK |
| Moshi localhost:8998 | OK |
| Voice Legion 241:8998/8999 | OK (fallback) |

## Script gates

| Script | Result |
|--------|--------|
| `verify_voice_stack.py` | PASS — orchestrator chat 200, bridge session OK |
| `test_personaplex_mas.py` | PASS — 7/7 (token loader reads `.env` files) |

## Website BFF diagnostics (services 0–5)

All **ONLINE** after forwarding `X-MYCA-Service-Token` on memory/brain health checks.

| Service | ok |
|---------|-----|
| Moshi (via Bridge) | true |
| PersonaPlex Bridge | true |
| MAS Orchestrator (live) | true |
| Memory Bridge | true |
| MYCA Brain | true |
| MINDEX API | true |

## Code fixes applied

- `app/api/test-voice/diagnostics/route.ts` — service token on MAS protected health routes
- `app/test-voice/page.tsx` — diagnostics client timeout 35s (MINDEX latency)
- `components/myca/MYCALiveActivityChordDiagram.tsx` — d3 ribbon TS fix
- `scripts/test_personaplex_mas.py` — load service token from `.env` files
- `docs/VOICE_TOPOLOGY_LOCKED_MAY19_2026.md` — Mode B local GPU locked

## TTS dependencies

- `edge-tts`, `opuslib` installed via pip
- `ffmpeg` installed via winget (restart shell for PATH)

## Browser smoke

- `/test-voice` loads; BFF session create returns `session_id`
- **Manual:** click Start MYCA Voice, grant mic, speak — requires Morgan (automation cannot capture mic/audio)

## Sandbox deploy

Pending: commit voice-focused changes, VM Docker rebuild, Cloudflare purge.
