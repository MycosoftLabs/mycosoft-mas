# CREP Command Contract — Mar 13, 2026

**Status:** Canonical  
**Related:** CREP + MYCA Autonomy Plan, CREP_SYSTEM_INTEGRATION_AUDIT_MAR11_2026, CREP_VOICE_CONTROL_FEB06_2026

## Purpose

This document defines the **single canonical contract** for CREP map commands flowing from MAS (voice, autonomy, tools) to the website CREP dashboard. All producers (PersonaPlex bridge, voice handlers, safe CREP tools) and consumers (useMapWebSocket, CREPDashboardClient, CREP context) MUST use this schema.

---

## Command Entrypoint

| Layer | Endpoint / Path | Notes |
|-------|-----------------|-------|
| **MAS voice** | `POST /voice/command` | PersonaPlex bridge calls this; response includes `frontend_command` |
| **MAS API** | (future) `POST /api/crep/command` | For autonomous MYCA and tool bus |
| **Website WebSocket** | Bridge → MAS → WebSocket relay | Commands delivered to browser via WebSocket |

---

## Frontend Command Schema

All commands are flat JSON objects with a required `type` field. Additional fields depend on `type`.

### Naming Convention

- **CREP map commands:** camelCase (e.g. `flyTo`, `showLayer`, `setTimeCursor`)
- **Earth2 commands:** snake_case (e.g. `run_forecast`, `load_model`) — separate domain; may be unified in a future iteration

---

## CREP Map Command Types

| type | Optional fields | Description |
|------|-----------------|-------------|
| `flyTo` | `center: [lon, lat]`, `zoom?: number`, `duration?: number` | Fly map to center |
| `geocodeAndFlyTo` | `query: string`, `zoom?: number`, `duration?: number` | Geocode query and fly |
| `setZoom` | `zoom: number`, `duration?: number` | Set zoom level |
| `zoomBy` | `delta: number`, `duration?: number` | Zoom in/out by delta |
| `panBy` | `offset: [dx, dy]`, `duration?: number` | Pan map by offset |
| `showLayer` | `layer: string` | Show a layer (e.g. `planes`, `vessels`, `satellites`, `fungal`) |
| `hideLayer` | `layer: string` | Hide a layer |
| `toggleLayer` | `layer: string` | Toggle layer visibility |
| `applyFilter` | `filterType: string`, `filterValue: string | number | boolean` | Apply a filter |
| `clearFilters` | — | Clear all filters |
| `getEntityDetails` | `entity: object` | Request details for an entity (planes, vessels, etc.) |
| `getViewContext` | — | Request current viewport/timeline context |
| `setTimeCursor` | `time: string` (ISO 8601) | Set timeline cursor |
| `timelineSearch` | `query: string` | Search timeline |
| `getSystemStatus` | — | Request system status (MAS, MINDEX, collectors) |
| `setMute` | `muted: boolean` | Mute/unmute TTS |

---

## Earth2 Command Types (Secondary)

These are produced by `earth2_voice_handler.py`. The CREP dashboard may delegate to Earth2 surfaces.

| type | Optional fields | Description |
|------|-----------------|-------------|
| `run_forecast` | `model: string`, `lead_time: number` | Run Earth2 forecast |
| `run_nowcast` | — | Run Earth2 nowcast |
| `show_forecast` | `forecast_id: string` | Display forecast result |
| `load_model` | `model: string` | Load Earth2 model |
| `show_layer` | `layer: string` | Show Earth2 layer |
| `hide_layer` | `layer: string` | Hide Earth2 layer |
| `get_context` | — | Get Earth2 context |

---

## Request/Response Models (MAS)

For explicit typing when implementing safe CREP tools and the command bus:

```python
# Request (voice/autonomy → MAS)
{
  "text": "fly to Tokyo",           # voice only
  "intent": "crep_map",             # optional override
  "context": {"session_id": "..."}  # optional
}

# Response (MAS → consumer)
{
  "handled": True,
  "frontend_command": {
    "type": "geocodeAndFlyTo",
    "query": "Tokyo",
    "zoom": 10
  },
  "speak": "Flying to Tokyo."
}
```

---

## Website Consumer Contract

The `useMapWebSocket` hook and `MapWebSocketClient` expect commands in the format above. Handlers are keyed by `command.type`; the switch routes to `onFlyTo`, `onShowLayer`, etc.

- **CREP map:** `flyTo`, `geocodeAndFlyTo`, `setZoom`, `zoomBy`, `panBy`, `showLayer`, `hideLayer`, `toggleLayer`, `applyFilter`, `clearFilters`, `getEntityDetails`, `getViewContext`, `setTimeCursor`, `timelineSearch`, `getSystemStatus`, `setMute`
- **Earth2:** `run_forecast`, `run_nowcast`, `load_model`, `show_layer`, `hide_layer`, `get_context`

---

## Source Files

| Role | Path |
|------|------|
| MAS voice command API | `mycosoft_mas/core/routers/voice_command_api.py` |
| Map voice handler | `scripts/map_voice_handler.py` |
| Earth2 voice handler | `scripts/earth2_voice_handler.py` |
| PersonaPlex bridge | `services/personaplex-local/personaplex_bridge_nvidia.py` |
| Website WebSocket hook | `website/hooks/useMapWebSocket.ts` |
| Map WebSocket client | `website/lib/voice/map-websocket-client.ts` |

---

## Validation

Contract tests MUST verify:

1. All `type` values used by MAS handlers exist in this document.
2. Website switch handles all documented CREP map types.
3. No drift between producer `type` strings and consumer switch cases.
