# MycoBrain LoRa Gateway Link Test Plan (Mar 13, 2026)

## Date

Mar 13, 2026

## Status

Ready for field execution

## Objective

Validate that a COM7-connected MycoBrain gateway node (serial -> local MycoBrain service -> MAS) can initialize LoRa/mesh and act as the local radio ingress point for a second MycoBrain board in the same yard.

## Scope

- Gateway board connected by serial on local machine and registered to MAS as `device_role: gateway`
- LoRa control path exercised through MAS command proxy
- Optional peer board LoRa send path exercised through MAS command proxy

## Firmware Requirement

- Gateway board firmware must include LoRa command handlers.
- Current implementation target in repo:
  - `firmware/MycoBrain_DeviceManager_BSEC2/MycoBrain_DeviceManager_BSEC2.ino`
  - Version updated to `2.1.0`
  - Added command plane handlers:
    - `lora init`
    - `lora status`
    - `lora send <payload>`
    - `mesh status`

## Prerequisites

- Local MycoBrain service is running and healthy at `http://localhost:8003`
- MAS reachable at `http://192.168.0.188:8001`
- Gateway registration is visible in MAS (`/api/devices`)
- Gateway role/capabilities include `lora`, `wifi`, `bluetooth`, `sim`, `store_and_forward`

## Scripts Added

- `scripts/start-mycobrain-gateway-local.ps1`
  - New `-RunLoraPrep` switch to run gateway LoRa init/status checks immediately after startup.
- `scripts/test-mycobrain-gateway-lora-link.ps1`
  - End-to-end LoRa gateway link test via MAS device command proxy.
  - Auto-resolves online gateway if `-GatewayDeviceId` is not provided.
  - Supports optional downstream peer board test with `-PeerDeviceId`.

## Execution

### 1) Start gateway in deterministic mode (COM7 pin + gateway role)

```powershell
.\scripts\start-mycobrain-gateway-local.ps1 -AllowedPorts COM7 -RunLoraPrep
```

### 2) Gateway-only LoRa readiness test

```powershell
.\scripts\test-mycobrain-gateway-lora-link.ps1
```

### 3) Gateway + peer LoRa link test (when peer board is online)

```powershell
.\scripts\test-mycobrain-gateway-lora-link.ps1 -GatewayDeviceId mycobrain-COM7 -PeerDeviceId <peer-device-id>
```

## Expected Results

- `gateway-status`, `gateway-lora-init`, `gateway-lora-status`, `gateway-mesh-status` return success.
- `gateway-lora-send-beacon` returns success.
- If peer is provided:
  - `peer-status`, `peer-lora-init`, `peer-lora-status`, `peer-lora-send` return success.
  - `gateway-post-peer-status` succeeds and can be inspected for link evidence.

## Notes

- This validates control plane and command routing for LoRa operations through MAS.
- RF quality/channel alignment and final payload verification remain field-dependent.
- If a peer board is not yet online, run gateway-only mode first and then rerun with `-PeerDeviceId` during live field pairing.
