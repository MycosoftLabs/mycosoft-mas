# MycoBrain → Supabase Telemetry Architecture

**Date:** March 7, 2026  
**Status:** Complete  
**Related:** `DEVICE_PRODUCTS_AND_MYCOFORGE_SYNC_MAR07_2026.md`, `MYCOBRAIN_TO_MAS_FLOW_MAR07_2026.md`, `MYCOBRAIN_SANDBOX_ALWAYS_ON_COMPLETE_MAR07_2026.md`

---

## Overview

MycoBrain IoT telemetry flows through a unified pipeline so **Supabase**, **Device Manager**, **MINDEX**, and the rest of the Mycosoft platform stay in sync. This doc describes the end-to-end architecture, why Supabase over SQLite, and how each system consumes the data.

---

## Why Supabase Over SQLite

| Aspect | SQLite | Supabase (PostgreSQL) |
|--------|--------|------------------------|
| **Scale** | Single-file, locking under high concurrency | Distributed, handles millions of devices |
| **Concurrency** | Write locks block readers | ACID, concurrent reads/writes |
| **Real-time** | Manual polling only | Built-in Realtime (WebSockets) |
| **Time-series** | Not optimized | TimescaleDB extension available |
| **Deployment** | Edge/local only | Managed cloud, auto-scaling |
| **Verdict** | Prototyping, single-device edge buffering | **Production central store** |

For VOC/sensor data from many devices, **Supabase wins**. SQLite remains useful for edge buffering (e.g., LoRa node offline storage) before sync to central Supabase.

---

## End-to-End Telemetry Flow

```
┌─────────────────┐     serial      ┌──────────────────────┐     HTTP POST      ┌─────────────────────┐
│  MycoBrain      │ ──────────────► │  MycoBrain Service   │ ─────────────────► │  Website Ingest API │
│  (ESP32-S3)     │   MDP v1        │  (port 8003)         │  /api/devices/     │  (port 3010/3000)   │
└─────────────────┘                 └──────────────────────┘     ingest         └──────────┬──────────┘
                                                                                           │
        LoRa / ChirpStack ────────────────────────────────────────────────────────────────┤
        Home Assistant ────────────────────────────────────────────────────────────────────┤
                                                                                           ▼
                                                                               ┌─────────────────────┐
                                                                               │  Supabase           │
                                                                               │  devices            │
                                                                               │  telemetry          │
                                                                               └──────────┬──────────┘
                                                                                          │
        ┌─────────────────────────────────────────────────────────────────────────────────┼─────────────────┐
        │                                                                                 │                 │
        ▼                                                                                 ▼                 ▼
┌───────────────┐                                 ┌─────────────────────┐     ┌─────────────────────┐
│  Device       │                                 │  Network Telemetry  │     │  MINDEX / OEI       │
│  Manager UI   │                                 │  Route (fallback)   │     │  (event bus)        │
│  (dashboard)  │                                 │  MAS → Supabase     │     │  (future)           │
└───────────────┘                                 └─────────────────────┘     └─────────────────────┘
```

1. **Device → MycoBrain Service:** Serial (MDP v1) or LoRa/ChirpStack webhook
2. **MycoBrain Service → Ingest API:** HTTP POST when `TELEMETRY_INGEST_URL` is set
3. **Ingest API → Supabase:** Upserts `devices`, inserts `telemetry` (admin client)
4. **Device Manager:** Fetches device list from MAS registry; telemetry from MAS or Supabase fallback
5. **OEI Event Bus:** Ingest API publishes entities/observations for future MINDEX/CREP integration

---

## Components

### 1. Website Ingest API

**Route:** `POST /api/devices/ingest`  
**File:** `WEBSITE/website/app/api/devices/ingest/route.ts`

- **Accepts:** Standard JSON, ChirpStack webhooks, Home Assistant webhooks
- **Payload shape:** `{ deviceId, deviceType?, readings?: [...], temperature?, humidity?, ... }`
- **Actions:**
  - Publishes to OEI event bus (entities + observations)
  - Writes to Supabase: `devices` (upsert by `external_id`), `telemetry` (insert)
- **Auth:** None currently; optional `TELEMETRY_INGEST_API_KEY` for future Bearer auth

### 2. MycoBrain Service → Ingest Bridge

**File:** `MAS/mycosoft-mas/services/mycobrain/mycobrain_service_standalone.py`

- After each `get_telemetry()` (serial read), if `TELEMETRY_INGEST_URL` is set:
  - Builds payload: `{ deviceId, deviceType: "mycobrain", readings: [bme1, bme2] }`
  - Fire-and-forget POST to ingest API (daemon thread)
- **Env vars:**
  - `TELEMETRY_INGEST_URL` — Full ingest endpoint (dev: `http://localhost:3010/api/devices/ingest`, Sandbox: `http://127.0.0.1:3000/api/devices/ingest`)
  - `TELEMETRY_INGEST_API_KEY` — Optional; sent as `Authorization: Bearer ...` if set

### 3. Supabase Schema

**Project:** `hnevnsxnhfibhbsipqvz` (Mycosoft Supabase)

**Tables:**

- `devices`: `id`, `external_id`, `device_name`, `device_type`, `last_seen`, `config`, `updated_at`
- `telemetry`: `device_id` (FK), `timestamp`, `temperature`, `humidity`, `pressure`, `gas_resistance`, `iaq`, `co2`, `voc`, `sensor_type`, `raw_data`

Ingest uses admin client; RLS does not apply to ingest writes.

### 4. Network Telemetry Route (Device Manager)

**Route:** `GET /api/devices/network/[deviceId]/telemetry`  
**File:** `WEBSITE/website/app/api/devices/network/[deviceId]/telemetry/route.ts`

- **Primary:** Fetches from MAS `GET /api/devices/{deviceId}/telemetry` (live from device)
- **Fallback:** On MAS 5xx or fetch error → `getTelemetryFromSupabase(deviceId)`
- **Supabase query:** Latest row per `sensor_type` (`amb` → bme1, `env` → bme2)
- **Response shape:** `{ success, device_id, telemetry: { bme1, bme2 }, timestamp, source: "mas"|"supabase" }`

### 5. Device Manager UI

- Device list: `GET /api/devices/network` → MAS device registry
- Telemetry: `GET /api/devices/network/[deviceId]/telemetry` → MAS or Supabase fallback
- Single response contract; `source` indicates origin

---

## Environment Configuration

### MycoBrain Service (local / Sandbox)

| Variable | Dev | Prod (Sandbox) |
|----------|-----|----------------|
| `TELEMETRY_INGEST_URL` | `http://localhost:3010/api/devices/ingest` | `http://127.0.0.1:3000/api/devices/ingest` |
| `TELEMETRY_INGEST_API_KEY` | (optional) | (optional) |

**Note:** MycoBrain runs on the dev PC (local) or Sandbox VM (187). It must reach the website ingest API. For Sandbox, MycoBrain (host) and website (Docker) both run on 187; use `http://127.0.0.1:3000/api/devices/ingest` so host-to-container traffic works. The Sandbox systemd unit sets this automatically.

### Website

- Supabase: `NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (for admin client)
- MAS: `MAS_API_URL` (default `http://192.168.0.188:8001`)

---

## Hardware Context (MYCOBRAIN_REV_U1)

- **ESP-1:** Communications, LoRa, watchdog, OTA, heartbeat
- **ESP-2:** Sensors, FCI, I2C, analog
- **LoRa:** Primary field radio (SX1262)
- **SIM7600:** Optional gateway add-on only
- **Ingest:** Devices do not connect directly to Supabase; data flows via MycoBrain service or ChirpStack → Ingest API.

---

## MINDEX Integration (Future)

- OEI event bus already receives entities and observations from ingest
- MINDEX can subscribe or poll Supabase `telemetry` for analytics
- TimescaleDB extension (if enabled) would optimize time-series queries and retention

---

## Verification

1. **Ingest:** `curl -X POST http://localhost:3010/api/devices/ingest -H "Content-Type: application/json" -d '{"deviceId":"test-001","temperature":23.5,"humidity":65}'`
2. **Supabase:** Check `devices` and `telemetry` in Supabase dashboard
3. **Fallback:** Stop MAS, request telemetry for a device that has ingested data → should return Supabase fallback with `source: "supabase"`

---

## Related Docs

- `MYCOBRAIN_TO_MAS_FLOW_MAR07_2026.md` — Heartbeat, device registry
- `MYCOBRAIN_JETSON_GATEWAY_BUILD_PLAN_MAR07_2026.md` — Hardware, LoRa-first
- `REQUEST_FLOW_ARCHITECTURE_MAR05_2026.md` — VM layout, request flows
