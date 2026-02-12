# Real-time Streaming Endpoints - Quick Reference

Created 4 WebSocket/SSE endpoint pairs using Redis pub/sub (February 12, 2026)

## Endpoint Map

| Dashboard | MAS WebSocket | Website SSE | Redis Channel |
|-----------|---------------|-------------|---------------|
| **Scientific** | `ws://192.168.0.188:8001/api/stream/scientific/live` | `GET /api/stream/scientific` | `experiments:data` |
| **MAS Topology** | `ws://192.168.0.188:8001/ws/topology` | `GET /api/stream/agents` | `agents:status` |
| **CREP/OEI** | `ws://192.168.0.188:8001/api/crep/stream` | `GET /api/stream/crep` | `crep:live` |
| **Device Telemetry** | `ws://192.168.0.188:8001/ws/devices/{id}` | `GET /api/stream/devices/[id]` | `devices:telemetry` |

## Files Created

### MAS Backend (Python)
- `mycosoft_mas/core/routers/scientific_stream.py`
- `mycosoft_mas/core/routers/topology_stream.py`
- `mycosoft_mas/core/routers/crep_stream.py`
- `mycosoft_mas/core/routers/devices_stream.py`

### Website Frontend (TypeScript)
- `app/api/stream/scientific/route.ts`
- `app/api/stream/agents/route.ts`
- `app/api/stream/crep/route.ts`
- `app/api/stream/devices/[id]/route.ts`

### Documentation
- `docs/REALTIME_STREAMING_ENDPOINTS_FEB12_2026.md` (full documentation)

## Files Modified

- `mycosoft_mas/core/myca_main.py` (added router imports and registrations)

## Quick Test

```bash
# Test MAS WebSocket
wscat -c ws://192.168.0.188:8001/api/stream/scientific/live

# Test Website SSE
curl -N http://localhost:3010/api/stream/scientific
```

## Status
✅ All 4 endpoint pairs created  
✅ Redis pub/sub integration  
✅ NO MOCK DATA  
✅ No linter errors  
✅ Fully documented
