## MycoBrain integration changelog

### Unreleased

- **Added**: MDP v1 protocol library (COBS framing + CRC16) under `mycosoft_mas/protocols/`.
- **Added**: MycoBrain device agent under `mycosoft_mas/agents/mycobrain/` (UART + placeholder Gateway transport, command ACK/retry, telemetry capture).
- **Added**: MycoBrain ingestion agent that maps telemetry to MINDEX schema and posts to MINDEX endpoints.
- **Added**: MycoBrain extension for the Mycorrhizae Protocol agent for protocol-driven device telemetry/command usage.
- **Added**: MycoBrain documentation set (integration guide, protocol spec, Notion KB template, summary).

- **Changed**: Added integration configuration blocks in `config.yaml` (MINDEX / NatureOS / Website / Notion / N8N).
- **Changed**: Added integration env vars to `docker-compose.yml` for local dev.
- **Changed**: Added `DeviceType.MYCOBRAIN` to device coordinator.
- **Changed**: Added `pyserial` + `pyserial-asyncio` to `requirements.txt`.
