# Side B Transport-Only and Backhaul Strategy

**Date:** March 7, 2026  
**Status:** Current  
**Related:** MycoBrain Rail Unification, MycoBrain firmware

## Side B Role: Transport Only

**Side B** is the transport/backhaul half of the dual-ESP32 MycoBrain:

- **Serial/UART** — UART-2 (USB-C) for PC/gateway connection
- **LoRa** — SX1262 for long-range backhaul
- **WiFi** — Optional WiFi for local gateway
- **Modem** — Future cellular modem for field deployment

Side B does **not** run sensing logic. Sensing (BME688, FCI, etc.) is on **Side A**. Side B forwards data from Side A to the gateway/MAS.

## Modem and Gateway Strategy

| Scenario | Transport | Gateway | Heartbeat Source |
|----------|-----------|---------|------------------|
| Lab (USB) | Serial | PC MycoBrain service | PC (device_id from Side A) |
| Field (LoRa) | LoRa | Jetson Nano / Gateway | Gateway (device_id from Side A via LoRa) |
| Field (Cellular) | Modem | Cloud / MAS | Modem gateway (device_id from Side A) |

**Device identity** is always derived from Side A (MAC, role). Side B is transparent transport.

## Refactor Notes

- Side B firmware: focus on UART relay, LoRa TX/RX, modem AT commands.
- No application logic on Side B beyond transport.
- Heartbeat and telemetry format unchanged; gateway assembles and sends to MAS.
