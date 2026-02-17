# Remote 5090 Inference Split Plan (Feb 13, 2026)

## Goal

Run heavy voice inference on the 5090 machine, while keeping PersonaPlex logic/interface on the Ubuntu 1080 Ti machine.

- **Inference host (this machine)**: RTX 5090, serves Moshi on `:8998`
- **Logic host (gpu01 Ubuntu)**: PersonaPlex Bridge on `:8999`, website/test harness
- **MAS host**: `192.168.0.188:8001`

This keeps full PersonaPlex architecture and removes heavy model pressure from the 1080 Ti.

## Network Topology

- 5090 host LAN IP: `192.168.0.172` (current)
- 1080 Ti logic host: `192.168.0.190`
- Both are on the same switch (direct link optional, not required)

Bridge on 1080 should connect to Moshi on 5090:

- `MOSHI_HOST=192.168.0.172`
- `MOSHI_PORT=8998`

## Inference Host (5090) Steps

From MAS repo root on 5090 host:

```powershell
.\scripts\run-moshi-docker-local.ps1 -Device cuda
```

Expected endpoint:

- `ws://192.168.0.172:8998`

## Logic Host (1080 Ubuntu) Steps

Set bridge environment on 1080 host:

```bash
export MOSHI_HOST=192.168.0.172
export MOSHI_PORT=8998
export MAS_ORCHESTRATOR_URL=http://192.168.0.188:8001
python services/personaplex-local/personaplex_bridge_nvidia.py
```

Bridge endpoint:

- `ws://192.168.0.190:8999`

## No-Admin Fallback (Verified): SSH Reverse Tunnel

If `gpu01` cannot reach `192.168.0.172:8998` directly due Windows firewall, use a reverse tunnel from 5090 host:

On 5090 host (keep running):

```powershell
ssh -o ExitOnForwardFailure=yes -N -R 19198:127.0.0.1:8998 mycosoft@192.168.0.190
```

(If port 19198 is already in use on gpu01, use another port e.g. 19298 and set `MOSHI_PORT` accordingly.)

Then on gpu01 set:

```bash
export MOSHI_HOST=127.0.0.1
export MOSHI_PORT=19198
```

This path is verified from gpu01 with:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:19198/
```

Expected: `200`

**gpu01 bridge run (after tunnel is up):** From MAS repo copied to gpu01 at `~/mycosoft-mas`:

```bash
cd ~/mycosoft-mas && source .venv/bin/activate
export MOSHI_HOST=127.0.0.1 MOSHI_PORT=19198 MAS_ORCHESTRATOR_URL=http://192.168.0.188:8001
python services/personaplex-local/personaplex_bridge_nvidia.py
```

## Test Flow

1. Start Moshi on 5090 host (`:8998`).
2. Start PersonaPlex Bridge on 1080 host (`:8999`) pointing at `192.168.0.172:8998`.
3. Open `http://localhost:3010/test-voice` on logic/dev side.
4. Verify:
   - Bridge health says Moshi available.
   - Voice STT/TTS roundtrip works.
   - MAS events and memory panels populate.

## Health Checks

On 5090 host:

```powershell
docker ps --filter "name=moshi-voice"
docker logs moshi-voice --tail 100
```

On 1080 host:

```bash
curl -s http://localhost:8999/health
```

Should report:

- `moshi_url` pointing to `http://192.168.0.172:8998`
- `moshi_available: true`

## Notes

- Full PersonaPlex policy remains: Moshi-only STT/TTS, no edge fallback.
- The `gpu_node` integration now supports configurable host/IP via env:
  - `GPU_NODE_SSH_HOST`
  - `GPU_NODE_HOSTNAME`
  - `GPU_NODE_IP`
  - `GPU_NODE_USER`
