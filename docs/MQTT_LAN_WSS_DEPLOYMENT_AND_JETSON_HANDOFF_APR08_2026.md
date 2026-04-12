# MQTT LAN + Public WSS Deployment And Jetson Handoff APR08 2026

**Date:** 2026-04-08  
**Status:** Complete (deployed + tunnel applied)  
**Scope:** Make MQTT fast on LAN, secure/public over Internet, and provide Beto-to-Jetson handoff instructions.

## Current Endpoints

- LAN (fastest): `mqtt://192.168.0.196:1883`
- Public remote (TLS via Cloudflare): `wss://mqtt.mycosoft.com:443` with WebSocket path `/`

## One-Command Jetson Bootstrap (New)

Script: `scripts/bootstrap_jetson_mqtt_env.py`

### Generate + apply LAN profile to Jetson

```powershell
python scripts/bootstrap_jetson_mqtt_env.py --mode lan --apply
```

### Generate + apply remote/public profile to Jetson

```powershell
python scripts/bootstrap_jetson_mqtt_env.py --mode remote --apply
```

### Generate only (no SSH apply)

```powershell
python scripts/bootstrap_jetson_mqtt_env.py --mode lan --output .\_jetson_mqtt.env
```

The script reads credentials from `.credentials.local` / env and writes:
- `MYCOBRAIN_MQTT_URL`
- `MYCOBRAIN_MQTT_USERNAME`
- `MYCOBRAIN_MQTT_PASSWORD`
- `MYCOBRAIN_MQTT_TRANSPORT`
- `MYCOBRAIN_MQTT_WS_PATH`

Defaults:
- Jetson host: `192.168.0.123`
- Jetson user: `jetson`
- Remote env path: `~/.mycosoft/mycobrain_mqtt.env`

## Beto -> Jetson Copy/Paste Handoff

```text
JETSON MQTT SETTINGS

1) If Jetson is on same LAN (fastest)
- URL: mqtt://192.168.0.196:1883
- Username: mycobrain
- Password: <MQTT_BROKER_PASSWORD from secure store>

2) If Jetson is remote/off-LAN (secure public)
- URL: wss://mqtt.mycosoft.com:443
- WebSocket path: /
- Username: mycobrain
- Password: <MQTT_BROKER_PASSWORD from secure store>

IMPORTANT
- Do NOT use mqtt://mqtt.mycosoft.com:1883 over public Internet.
- Public hostname is WSS-only path.
```

## Verification Notes

- Broker running on VM `192.168.0.196` with listeners on `1883` and `9001`.
- Tunnel rule applied: `mqtt.mycosoft.com -> http://192.168.0.196:9001`.
