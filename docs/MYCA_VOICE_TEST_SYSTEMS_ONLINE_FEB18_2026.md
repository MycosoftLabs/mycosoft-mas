# MYCA Voice Test – Systems Online Checklist (Feb 18, 2026)

## What Was Fixed

1. **Diagnostics** (`WEBSITE/website/app/api/test-voice/diagnostics/route.ts`)
   - Moshi status is **derived from PersonaPlex Bridge health** (`moshi_available`).
   - No direct check to `localhost:8998`; when using the GPU node, Moshi runs on the node (e.g. 192.168.0.190 internal) and the bridge reports availability.
   - All four services (Moshi via Bridge, Bridge, MAS Consciousness, Memory Bridge) are checked in one server-side request.

2. **Test-voice UI** (`WEBSITE/website/app/test-voice/page.tsx`)
   - First service label updated from "Moshi Server (8998)" to **"Moshi (via Bridge)"** to match GPU node architecture.

## Requirements for All Systems to Show Online

| Service | Where It Runs | Env (website `.env.local`) | Notes |
|--------|----------------|-----------------------------|--------|
| Moshi | GPU node (e.g. 192.168.0.190), internal port | — | Status comes from bridge health `moshi_available`. |
| PersonaPlex Bridge | GPU node 192.168.0.190:8999 | `PERSONAPLEX_BRIDGE_URL=http://192.168.0.190:8999` | Must be reachable from the machine running Next.js. |
| MAS Consciousness | MAS VM 192.168.0.188:8001 | `MAS_API_URL=http://192.168.0.188:8001` | `/api/myca/status` and `/api/memory/health`. |
| Memory Bridge | Same as MAS | Same | Part of MAS. |

- **WebSocket (browser):** `NEXT_PUBLIC_PERSONAPLEX_BRIDGE_WS_URL=ws://192.168.0.190:8999` so the test-voice page connects to the bridge on the GPU node.

## How to Verify

1. Ensure **Bridge + Moshi** are running on the GPU node (190) and **MAS** is up on 188.
2. In the **website** repo set `.env.local`:
   - `PERSONAPLEX_BRIDGE_URL=http://192.168.0.190:8999`
   - `NEXT_PUBLIC_PERSONAPLEX_BRIDGE_WS_URL=ws://192.168.0.190:8999`
   - `MAS_API_URL=http://192.168.0.188:8001`
3. Start dev: `npm run dev:next-only` (port 3010).
4. Open **http://localhost:3010/test-voice** and run diagnostics.
5. All four services should show **online** when 190 and 188 are reachable from the dev machine.
6. Click **Start MYCA Voice** and test voice with the GPU node.

## If Diagnostics Time Out

- Diagnostics run **server-side** from the Next.js server. The dev machine must have **network access** to:
  - `192.168.0.190:8999` (PersonaPlex Bridge)
  - `192.168.0.188:8001` (MAS)
- If the dev PC is on a different VLAN or cannot reach those IPs, diagnostics will show services offline or time out. Run the website from a host that can reach both (e.g. same LAN as the VMs and GPU node).
