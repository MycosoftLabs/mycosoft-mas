# MYCA Worldview Integration Test Plan

**Created:** Feb 17, 2026

Verifies that NLM, EarthLIVE, and consciousness integration work across MYCA page, Search, Voice, and Chat.

## Prerequisites

- Website dev server: `npm run dev:next-only` (port 3010)
- MAS running on 192.168.0.188:8001 (must have consciousness_api with nlm/earthlive/presence in world response)
- MINDEX on 192.168.0.189:8000 (optional for Search)

## Test Matrix

| Surface | API Used | Expected Behavior |
|---------|----------|-------------------|
| MYCA page → World tab | `/api/myca/consciousness/world` | Returns `nlm`, `earthlive`, `presence` when WorldModel has data |
| MYCA page → Chat | `/api/myca/consciousness/chat` | Chat uses world context (nlm, earthlive, presence) in consciousness pipeline |
| Search AI | `/api/search/ai` → `queryMYCAConsciousness` | Uses MAS `/api/myca/chat` with full consciousness |
| Voice orchestrator | `/api/mas/voice/orchestrator` | Uses MAS `/api/myca/chat` for chat fallback |
| MYCAChatWidget | `/api/myca/consciousness/chat` | Same as MYCA page Chat |

## Manual Test Steps

### 1. MAS World Endpoint (direct)

```powershell
$r = Invoke-RestMethod "http://192.168.0.188:8001/api/myca/world" -TimeoutSec 10
$r | ConvertTo-Json -Depth 3
# Expect: nlm, earthlive, presence keys (may be null/empty if sensors not populated)
```

### 2. Website World Proxy

```powershell
$r = Invoke-RestMethod "http://localhost:3010/api/myca/consciousness/world" -TimeoutSec 15
$r | ConvertTo-Json -Depth 3
# Expect: same keys as MAS, plus available: true
```

### 3. MYCA Page (browser)

1. Open http://localhost:3010/myca
2. Click "World" tab in LiveDemo
3. Verify JSON includes `nlm`, `earthlive`, `presence` (or that existing keys render)

### 4. MYCA Chat (browser)

1. On MYCA page, type a message in Chat tab
2. Send; verify response (consciousness chat uses world context internally)

### 5. Search with MYCA

1. Use search with AI enabled
2. queryMYCAConsciousness is tried first; responses should reflect MYCA's world-aware context

### 6. Voice (if PersonaPlex/Moshi running)

1. Use voice input; orchestrator calls MAS `/api/myca/chat` when appropriate
2. Verify voice→chat path works

## Code Changes (Feb 17, 2026)

- **consciousness_api.py**: `WorldStateResponse` now includes `nlm`, `earthlive`, `presence`
- **LiveDemo.tsx**: `WorldState` interface updated with `nlm`, `earthlive`, `presence`, `mycobrain`
- **WorldModel** (already had): `nlm_insights`, `earthlive_packet`, `presence_data` in state and `get_context_for_chat()`

## Deployment Requirement

MAS on VM 188 must be rebuilt and restarted for the new world response fields to appear. Run:

```bash
# On MAS VM after git pull
docker build -t mycosoft/mas-agent:latest --no-cache .
docker stop myca-orchestrator-new && docker rm myca-orchestrator-new
docker run -d --name myca-orchestrator-new --restart unless-stopped -p 8001:8000 mycosoft/mas-agent:latest
```

## Automated Script

See `scripts/test_myca_worldview_integration.ps1` for a PowerShell script that runs the API checks.
