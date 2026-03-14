# Jetson and Firmware Implementation Guide

**Date:** March 7, 2026  
**Status:** Active  
**Related:** `MYCOBRAIN_FIRMWARE_ROADMAP_MAR07_2026.md`, `DEVICE_JETSON16_CORTEX_ARCHITECTURE_MAR07_2026.md`, `GATEWAY_JETSON4_LILYGO_ARCHITECTURE_MAR07_2026.md`

---

## What Was Implemented

### Firmware (new MDP-first targets)

- `firmware/MycoBrain_SideA_MDP/`
  - MDP framing (COBS + CRC16)
  - Side A command family (`read_sensors`, `stream_sensors`, `output_control`, `estop`, `clear_estop`, `health`)
  - HELLO + capability/sensor advertisement
- `firmware/MycoBrain_SideB_MDP/`
  - MDP dual-UART relay topology (Jetson16 ↔ SideB ↔ SideA)
  - Transport directives (`lora_send`, `ble_advertise`, `wifi_connect`, `sim_send`, `transport_status`)
  - Link-status events and ACK/NACK handling

### On-device Jetson (16GB)

- `mycosoft_mas/edge/ondevice_operator.py`
  - Side A and Side B command arbitration
  - Audit logging (`data/edge/ondevice_audit.jsonl`)
  - Proposal/approval/apply flow for firmware/code/config mutation
  - OpenClaw task integration endpoint
- `mycosoft_mas/edge/mdp_protocol.py` and `mycosoft_mas/edge/mdp_serial_bridge.py`
  - Shared MDP Python implementation and serial bridge
- Launcher: `scripts/run_ondevice_operator.py`

### Gateway Jetson (4GB + LilyGO)

- `mycosoft_mas/edge/gateway_router.py`
  - Ingest + store-and-forward queue
  - Upstream publish to MAS heartbeat, Mycorrhizae, MINDEX, website ingest
  - Gateway self-registration
  - OpenClaw task integration endpoint (gateway profile)
  - Audit log (`data/edge/gateway_audit.jsonl`)
- Launcher: `scripts/run_gateway_router.py`

### Deployment and Execution Tooling

- Systemd units:
  - `deploy/jetson/mycobrain-ondevice-operator.service`
  - `deploy/jetson/mycobrain-gateway-router.service`
- Env templates:
  - `deploy/jetson/ondevice-operator.env.example`
  - `deploy/jetson/gateway-router.env.example`
- Service installer:
  - `deploy/jetson/install_jetson_services.sh`
- Firmware flash helper:
  - `scripts/flash_mycobrain_mdp.ps1`
- Coordinated bring-up helper:
  - `scripts/bringup_mycobrain_jetsons.ps1`
- Runtime smoke check:
  - `scripts/jetson_execute_next_steps.py`

---

## Side A Firmware Build and Flash

1. Connect Side A ESP32-S3 to USB.
2. Build:

```powershell
cd "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\firmware\MycoBrain_SideA_MDP"
pio run
```

3. Upload (replace COM port):

```powershell
pio run -t upload --upload-port COM7
```

4. Verify serial output:

```powershell
pio device monitor -b 115200 --port COM7
```

Expected: HELLO frame emission and periodic telemetry.

---

## Side B Firmware Build and Flash

1. Connect Side B ESP32-S3 to USB.
2. Build:

```powershell
cd "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\firmware\MycoBrain_SideB_MDP"
pio run
```

3. Upload:

```powershell
pio run -t upload --upload-port COM8
```

4. Verify:

```powershell
pio device monitor -b 115200 --port COM8
```

Expected: HELLO frame and status LED tied to Jetson heartbeat activity.

---

## On-device Jetson (16GB) Setup

### Environment

Set on the 16GB Jetson:

```bash
export ONDEVICE_SIDE_A_PORT=/dev/ttyTHS1
export ONDEVICE_SIDE_B_PORT=/dev/ttyTHS2
export ONDEVICE_MDP_BAUD=115200
export ONDEVICE_AUDIT_LOG=/opt/mycosoft/logs/ondevice_audit.jsonl
export OPENCLAW_BASE_URL=http://127.0.0.1:8000
export OPENCLAW_API_KEY=<your_openclaw_key_if_required>
```

### Run service

```bash
cd /opt/mycosoft/mas
python scripts/run_ondevice_operator.py --host 0.0.0.0 --port 8110
```

### Health check

```bash
curl -s http://127.0.0.1:8110/health
```

### Install as systemd service

```bash
cd /opt/mycosoft/mas
sudo bash deploy/jetson/install_jetson_services.sh ondevice
sudo cp deploy/jetson/ondevice-operator.env.example /etc/mycosoft/ondevice-operator.env
sudo nano /etc/mycosoft/ondevice-operator.env
sudo systemctl restart mycobrain-ondevice-operator
sudo systemctl status mycobrain-ondevice-operator --no-pager
```

---

## Gateway Jetson (4GB + LilyGO) Setup

### Environment

Set on the 4GB gateway Jetson:

```bash
export GATEWAY_ID=site-gateway-01
export GATEWAY_HOST=192.168.0.123
export GATEWAY_PORT=8120
export GATEWAY_LOCATION=server-room
export MAS_API_URL=http://192.168.0.188:8001
export MYCORRHIZAE_API_URL=http://192.168.0.187:8002
export MINDEX_API_URL=http://192.168.0.189:8000
export TELEMETRY_INGEST_URL=http://192.168.0.187:3000
export GATEWAY_OPENCLAW_BASE_URL=http://127.0.0.1:8000
export GATEWAY_OPENCLAW_API_KEY=<your_openclaw_key_if_required>
```

### Run service

```bash
cd /opt/mycosoft/mas
python scripts/run_gateway_router.py --host 0.0.0.0 --port 8120
```

### Register gateway and verify

```bash
curl -s -X POST http://127.0.0.1:8120/gateway/register
curl -s http://127.0.0.1:8120/health
curl -s http://127.0.0.1:8120/queue
```

### Install as systemd service

```bash
cd /opt/mycosoft/mas
sudo bash deploy/jetson/install_jetson_services.sh gateway
sudo cp deploy/jetson/gateway-router.env.example /etc/mycosoft/gateway-router.env
sudo nano /etc/mycosoft/gateway-router.env
sudo systemctl restart mycobrain-gateway-router
sudo systemctl status mycobrain-gateway-router --no-pager
```

---

## End-to-End Command Checks

### Side A via on-device operator

```bash
curl -s -X POST http://127.0.0.1:8110/side-a/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"read_sensors","params":{},"ack_requested":true}'
```

### Side B transport status via on-device operator

```bash
curl -s -X POST http://127.0.0.1:8110/side-b/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"transport_status","params":{},"ack_requested":true}'
```

### Queue message on gateway

```bash
curl -s -X POST http://127.0.0.1:8120/ingest \
  -H 'Content-Type: application/json' \
  -d '{"device_id":"mushroom1-alpha","transport":"lora","payload":{"readings":[{"sensor":"bme688_a","temperature":24.1}]}}'
```

### Automated smoke check

```bash
python scripts/jetson_execute_next_steps.py \
  --ondevice-url http://127.0.0.1:8110 \
  --gateway-url http://127.0.0.1:8120
```

### Firmware flash helper (Windows)

```powershell
# Side A only
.\scripts\flash_mycobrain_mdp.ps1 -Target sidea -SideAPort COM7

# Side B only
.\scripts\flash_mycobrain_mdp.ps1 -Target sideb -SideBPort COM8

# Both
.\scripts\flash_mycobrain_mdp.ps1 -Target both -SideAPort COM7 -SideBPort COM8
```

### Coordinated next-step bring-up (Windows)

```powershell
.\scripts\bringup_mycobrain_jetsons.ps1 `
  -OnDeviceHost 192.168.0.210 `
  -GatewayHost 192.168.0.211 `
  -SshUser mycosoft `
  -FlashFirmware `
  -SideAPort COM7 `
  -SideBPort COM8
```

---

## Safety and Approval Flow

On-device operator mutation flow:

1. `POST /mutations/propose`
2. `POST /mutations/{proposal_id}/decision`
3. `POST /mutations/{proposal_id}/apply`

All events are audit logged; mutation apply is blocked unless approved.

---

## Notes

- Side B transport directives are implemented as control surfaces; integrate hardware-specific LoRa/SIM drivers for physical radio transmission on your LilyGO stack.
- Identity invariants remain enforced at architecture level: canonical device identity remains Side A/MycoBrain identity.
