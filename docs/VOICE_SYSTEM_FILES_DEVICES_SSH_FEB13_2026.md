# Voice System: Files, Devices, SSH Routes (Feb 13, 2026)

Single reference for bringing the voice GPU node and test-voice system up.

## Devices and ports

| Role        | Host / IP          | Port  | Service / Notes                          |
|------------|--------------------|-------|------------------------------------------|
| Inference  | 5090 dev PC        | 8998  | Moshi (STT/TTS); Docker or native         |
| Tunnel     | 5090 → gpu01       | 19198 | SSH reverse: gpu01:19198 → 5090:8998     |
| Bridge     | gpu01 192.168.0.190 | 8999  | PersonaPlex Bridge (WebSocket, MAS)      |
| MAS        | 192.168.0.188      | 8001  | Orchestrator, consciousness, voice APIs  |
| Website dev| localhost          | 3010  | Next.js; test page /test-voice           |

## Key files

### MAS repo (mycosoft-mas)

- **Bridge:** `services/personaplex-local/personaplex_bridge_nvidia.py`
- **Bridge env (tunnel):** `services/personaplex-local/.env.gpu01-tunnel.example`
- **Verify script:** `scripts/voice-system-verify-and-start.ps1`
- **Moshi Docker:** `scripts/run-moshi-docker-local.ps1` (5090)
- **Remote plan:** `docs/REMOTE_5090_INFERENCE_SPLIT_PLAN_FEB13_2026.md`

### Website repo (website)

- **Test page:** `app/test-voice/page.tsx`
- **Diagnostics API:** `app/api/test-voice/diagnostics/route.ts`
- **Bridge proxy:** `app/api/test-voice/bridge/health/route.ts`, `bridge/session/route.ts`
- **MAS proxies:** `app/api/test-voice/mas/*`

### gpu01 (after SCP/sync)

- **Path:** `~/mycosoft-mas` (contains `services/personaplex-local`, `config`, venv)
- **Venv:** `~/mycosoft-mas/.venv`
- **Bridge log:** e.g. `~/personaplex_bridge.log` if run with nohup

## SSH routes

| From  | To    | Command / purpose |
|-------|-------|--------------------|
| 5090  | gpu01 | `ssh -o ExitOnForwardFailure=yes -N -R 19198:127.0.0.1:8998 mycosoft@192.168.0.190` — reverse tunnel so gpu01 sees Moshi at 127.0.0.1:19198 |
| Dev PC| gpu01 | `ssh mycosoft@192.168.0.190` — start bridge, check logs |
| Dev PC| MAS   | Not required for voice; website and bridge use HTTP to 192.168.0.188:8001 |

## Startup order (split architecture)

1. **5090:** Start Moshi on 8998 (e.g. `.\scripts\run-moshi-docker-local.ps1 -Device cuda`).
2. **5090:** Start SSH tunnel (see table above); leave session open.
3. **gpu01:** Start bridge with tunnel port:
   ```bash
   cd ~/mycosoft-mas && source .venv/bin/activate
   export MOSHI_HOST=127.0.0.1 MOSHI_PORT=19198 MAS_ORCHESTRATOR_URL=http://192.168.0.188:8001
   python services/personaplex-local/personaplex_bridge_nvidia.py
   ```
4. **Dev PC:** In website repo run `npm run dev:next-only`, open http://localhost:3010/test-voice.

## Verification

- **From dev PC:**  
  `.\scripts\voice-system-verify-and-start.ps1` (MAS repo)  
  Optional: `.\scripts\voice-system-verify-and-start.ps1 -PrintCommands` to print start commands.
- **Bridge health:** `curl -s http://192.168.0.190:8999/health` → `moshi_available: true` when Moshi + tunnel are up.
- **Website diagnostics:** http://localhost:3010/api/test-voice/diagnostics (all four services OK when stack is up).

## Env (website .env.local for test-voice)

- `PERSONAPLEX_BRIDGE_URL=http://192.168.0.190:8999`
- `NEXT_PUBLIC_PERSONAPLEX_BRIDGE_URL=http://192.168.0.190:8999`
- `NEXT_PUBLIC_PERSONAPLEX_BRIDGE_WS_URL=ws://192.168.0.190:8999`

Browser connects to `ws://192.168.0.190:8999/ws/<session_id>`; bridge talks to Moshi at `http://127.0.0.1:19198` on gpu01 (via tunnel).

## GPU Node API (MAS)

MAS exposes a **GPU node API** for gpu01 (192.168.0.190): status, containers, deploy services. See **`docs/GPU_NODE_INTEGRATION_FEB13_2026.md`**.

- **Base URL:** `http://192.168.0.188:8001/api/gpu-node/`
- **Health:** `GET /api/gpu-node/health`
- **Status:** `GET /api/gpu-node/status`
- **Deploy service:** `POST /api/gpu-node/deploy/service` with `{"service_name": "moshi-voice"}` or `"personaplex-bridge"`

Requires MAS to be restarted on 188 after the GPU node router is deployed.
