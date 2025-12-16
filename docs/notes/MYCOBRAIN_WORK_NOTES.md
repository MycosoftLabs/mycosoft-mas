## MycoBrain → MAS integration work notes

### What exists now
- **Protocol layer**: `mycosoft_mas/protocols/mdp_v1.py` implements MDP v1 framing (COBS + CRC16) and JSON payload parsing.
- **Device connectivity**: `mycosoft_mas/agents/mycobrain/device_agent.py` handles UART transport today; Gateway/LoRa is scaffolded for the firmware-side API.
- **Ingestion**: `mycosoft_mas/agents/mycobrain/ingestion_agent.py` batches telemetry, dedupes via `(device_id, sequence)`, and pushes to MINDEX.
- **Mycorrhizae Protocol**: `mycosoft_mas/agents/clusters/protocol_management/mycobrain_protocol_extension.py` lets protocols subscribe to MycoBrain telemetry and use it for step checks.

### Assumptions baked into the code
- **MDP payloads are JSON** (UTF-8) inside the framed payload. If MycoBrain firmware uses binary payloads for telemetry, the decoder/mapper will need a schema update.
- **MINDEX endpoints** assumed by client:
  - `POST /telemetry/mycobrain/ingest`
  - `GET /telemetry/mycobrain`
  - `POST /devices/mycobrain/register`
  - (and generic `GET /devices` filtered by device_type)

### Security notes
- `env.local` and machine-specific diagnostics are **ignored** and should never be committed.
- Device ingestion supports an optional per-device API key header (`X-Device-API-Key`).

### Next integration steps (firmware/ops)
- **Gateway transport**: finalize Gateway API (HTTP/WebSocket/serial bridge) so `ConnectionType.GATEWAY` can send/receive MDP frames.
- **MINDEX schema**: add/confirm tables or REST endpoints for MycoBrain telemetry + device registry.
- **NatureOS UI**: build a MycoBrain widget and command UI (MOSFET toggle, scan, telemetry interval).

### Where to read the full docs
- `docs/integrations/MYCOBRAIN_INTEGRATION.md`
- `docs/protocols/MDP_V1_SPEC.md`
- `docs/notion/MYCOBRAIN_KNOWLEDGE_BASE.md`
- `MYCOBRAIN_INTEGRATION_SUMMARY.md`
