# Firmware Audit — May 27, 2026

**Date:** 2026-05-29 00:26 UTC
**Status:** Complete (automated probe)
**Canonical Side A target:** `side-a-mdp-2.1.0`

## Version diff (vs canonical)

| Device | Observed firmware | Target | Tier | Action |
|--------|-------------------|--------|------|--------|
| Local serial (COM7 via :8003) | *(no USB connected)* | `side-a-mdp-2.1.0` | unknown | Connect COM7 and re-probe; flash with `mycobrain/scripts/flash-mycobrain-production.ps1` |
| Mushroom 1 (123) | `recovery-operator-bsec2-v0.7` | `side-a-mdp-2.1.0` (env mushroom1) | incompatible | Flash Side A + Side B from Jetson USB; OpenClaw :18789 reachable |
| Hyphae 1 (228) | `recovery-operator-bsec2-v0.7` | `side-a-mdp-2.1.0` (env hyphae1) | incompatible | Same as Mushroom 1 |

**Note:** Field boards run BSEC2 recovery operator firmware, not MDP v1. Console buzzer/LED/I2C widgets require MDP 2.1.0+.

## Summary

- **Local serial (MycoBrain service)** (`local-serial-com7`): tier **unknown**, firmware `unknown`
- **Mushroom 1 Jetson** (`mycobrain-mushroom1-jetson-123`): tier **incompatible**, firmware `recovery-operator-bsec2-v0.7`
- **Hyphae 1 Jetson** (`mycobrain-hyphae1-jetson-228`): tier **incompatible**, firmware `recovery-operator-bsec2-v0.7`

## Probe details

### Local serial (MycoBrain service)
- Agent: `http://127.0.0.1:8003` — reachable=True
- Recommended: Probe agent or connect USB to read firmware_version

```json
{
  "label": "Local serial (MycoBrain service)",
  "device_id": "local-serial-com7",
  "agent_url": "http://127.0.0.1:8003",
  "openclaw_url": null,
  "firmware_version": "",
  "compatibility_tier": "unknown",
  "missing_capabilities": [
    "mdp_v1_commands",
    "buzzer_presets",
    "neopixel_patterns",
    "i2c_peripheral_grid",
    "optical_acoustic_tx",
    "openclaw_agent"
  ],
  "recommended_action": "Probe agent or connect USB to read firmware_version",
  "agent_probe": {
    "reachable": true,
    "status_code": 200,
    "body": {
      "status": "ok",
      "service": "mycobrain",
      "version": "2.2.0",
      "devices_connected": 0,
      "timestamp": "2026-05-28T17:26:48.846339"
    },
    "path": "/health",
    "fw_version": null,
    "serial_connected": null,
    "openclaw": null
  },
  "openclaw_probe": {
    "reachable": false
  }
}
```

### Mushroom 1 Jetson
- Agent: `http://192.168.0.123:8787` — reachable=True
- OpenClaw: `http://192.168.0.123:18789` — reachable=True
- Recommended: Flash MycoBrain_SideA_MDP env mushroom1/hyphae1 → side-a-mdp-2.1.0

```json
{
  "label": "Mushroom 1 Jetson",
  "device_id": "mycobrain-mushroom1-jetson-123",
  "agent_url": "http://192.168.0.123:8787",
  "openclaw_url": "http://192.168.0.123:18789",
  "firmware_version": "recovery-operator-bsec2-v0.7",
  "compatibility_tier": "incompatible",
  "missing_capabilities": [
    "mdp_v1_commands",
    "buzzer_presets",
    "neopixel_patterns",
    "i2c_peripheral_grid",
    "optical_acoustic_tx"
  ],
  "recommended_action": "Flash MycoBrain_SideA_MDP env mushroom1/hyphae1 \u2192 side-a-mdp-2.1.0",
  "agent_probe": {
    "reachable": true,
    "status_code": 200,
    "body": {
      "ok": true,
      "serialPort": "/dev/ttyACM0",
      "serialConnected": true,
      "lastHeartbeat": "2026-05-29T00:26:49.345Z",
      "lastError": "Expected ',' or '}' after property value in JSON at position 128 (line 1 column 129)",
      "lastScan": {
        "addresses": [],
        "count": 0,
        "ts": null
      },
      "lastSensorReading": {
        "type": "telemetry",
        "device_id": "mycobrain-sidea-10b41d",
        "node_id": "mycobrain-sidea-10b41d",
        "role": "side_a",
        "sensor_slot": "amb",
        "address": "0x77",
        "present": true,
        "valid": true,
        "fw_version": "recovery-operator-bsec2-v0.7",
        "config_version": "bsec2-default-lp",
        "bsec_version": "2.6.1.0",
        "location": {
          "lat": null,
          "lon": null,
          "source": "na"
        },
        "ts_ms": 78803257,
        "temperature_c_comp": 33.58,
        "temperature_f_comp": 92.44,
        "humidity_pct_comp": 24.48,
        "gas_resistance_ohm_comp": null,
        "ambient_temperature_c": 33.64,
        "ambient_temperature_f": 92.56,
        "ambient_humidity_pct": 24.39,
        "iaq": 107.35,
        "iaq_static": 75.05,
        "iaq_accuracy": 1,
        "eco2_ppm": 750.52,
        "bvoc_ppm": 0.88,
        "gas_percentage": null,
        "pressure_hpa": 657.39,
        "gas_resistance_ohm": 337842,
        "stabilization_status": 1,
        "run_in_status": 1,
        "output_accuracy": 1,
        "bsec_status_code": 0,
        "bme68x_status_code": 0,
        "gas_estimate_1": null,
        "gas_estimate_2": null,
        "gas_estimate_3": null,
        "gas_estimate_4": null,
        "gas_estimate_accuracy": null,
        "new_data": true,
        "measuring": false,
        "gas_measuring": true,
        "gas_meas_index": 0,
        "sub_meas_index": 0,
        "gas_valid": true,
        "heat_stable": true,
        "chip_id": "0x61",
        "variant_id": "0x01",
        "temp_offset_c": 0,
        "sample_rate_mode": "lp",
        "heater_profile_id": 0,
        "model_type": "selectivity",
        "class_count": 4,
        "uptime_s": 78803,
        "boot_count": 0,
        "ts": "2026-05-29T00:26:50.347Z"
      },
      "lastLines": [
        {
          "ts": "2026-05-29T00:25:38.277Z",
          "line": "{\"type\":\"telemetry\",\"device_id\":\"mycobrain-sidea-10b41d\",\"node_id\":\"mycobrain-sidea-10b41d\",\"role\":\"side_a\",\"sensor_slot\":\"amb\",\"address\":\"0x77\",\"present\":true,\"valid\":true,\"fw_version\":\"recovery-operator-bsec2-v0.7\",\"config_version\":\"bsec2-default-lp\",\"bsec_version\":\"2.6.1.0\",\"location\":{\"lat\":null,\"lon\":null,\"source\":\"na\"},\"ts_ms\":78731187,\"temperature_c_comp\":33.57,\"temperature_f_comp\":92.43,\"humidity_pct_comp\":24.50,\"gas_resistance_ohm_comp\":null,\"ambient_temperature_c\":33.63,\"ambient_temperature_f\":92.54,\"ambient_humidity_pct\":24.42,\"iaq\":106.65,\"iaq_static\":74.75,\"iaq_accuracy\":1,\"eco2_ppm\":747.48,\"bvoc_ppm\":0.88,\"gas_percentage\":null,\"pressure_hpa\":657.38,\"gas_resistance_ohm\":337842,\"stabilization_status\":1,\"run_in_status\":1,\"output_accuracy\":1,\"bsec_status_code\":0,\"bme68x_status_code\":0,\"gas_estimate_1\":null,\"gas_estimate_2\":null,\"gas_estimate_3\":null,\"gas_estimate_4\":null,\"gas_estimate_accuracy\":null,\"new_data\":true,\"measuring\":false,\"gas_measur
```

### Hyphae 1 Jetson
- Agent: `http://192.168.0.228:8787` — reachable=True
- OpenClaw: `http://192.168.0.228:18789` — reachable=False
- Recommended: Flash MycoBrain_SideA_MDP env mushroom1/hyphae1 → side-a-mdp-2.1.0

```json
{
  "label": "Hyphae 1 Jetson",
  "device_id": "mycobrain-hyphae1-jetson-228",
  "agent_url": "http://192.168.0.228:8787",
  "openclaw_url": "http://192.168.0.228:18789",
  "firmware_version": "recovery-operator-bsec2-v0.7",
  "compatibility_tier": "incompatible",
  "missing_capabilities": [
    "mdp_v1_commands",
    "buzzer_presets",
    "neopixel_patterns",
    "i2c_peripheral_grid",
    "optical_acoustic_tx",
    "openclaw_agent"
  ],
  "recommended_action": "Flash MycoBrain_SideA_MDP env mushroom1/hyphae1 \u2192 side-a-mdp-2.1.0",
  "agent_probe": {
    "reachable": true,
    "status_code": 200,
    "body": {
      "ok": true,
      "serialPort": "/dev/ttyACM0",
      "serialConnected": true,
      "lastHeartbeat": "2026-05-29T00:26:50.503Z",
      "lastError": "Expected ',' or '}' after property value in JSON at position 127 (line 1 column 128)",
      "lastScan": {
        "addresses": [],
        "count": 0,
        "ts": null
      },
      "lastSensorReading": {
        "type": "telemetry",
        "device_id": "mycobrain-sidea-10b41d",
        "node_id": "mycobrain-sidea-10b41d",
        "role": "side_a",
        "sensor_slot": "env",
        "address": "0x76",
        "present": true,
        "valid": true,
        "fw_version": "recovery-operator-bsec2-v0.7",
        "config_version": "bsec2-default-lp",
        "bsec_version": "2.6.1.0",
        "location": {
          "lat": null,
          "lon": null,
          "source": "na"
        },
        "ts_ms": 78964499,
        "temperature_c_comp": 25.09,
        "temperature_f_comp": 77.15,
        "humidity_pct_comp": 37.16,
        "gas_resistance_ohm_comp": null,
        "ambient_temperature_c": 25.15,
        "ambient_temperature_f": 77.27,
        "ambient_humidity_pct": 37.02,
        "iaq": 82.34,
        "iaq_static": 67.63,
        "iaq_accuracy": 3,
        "eco2_ppm": 676.35,
        "bvoc_ppm": 0.75,
        "gas_percentage": null,
        "pressure_hpa": 647.21,
        "gas_resistance_ohm": 467153,
        "stabilization_status": 1,
        "run_in_status": 1,
        "output_accuracy": 3,
        "bsec_status_code": 0,
        "bme68x_status_code": 0,
        "gas_estimate_1": null,
        "gas_estimate_2": null,
        "gas_estimate_3": null,
        "gas_estimate_4": null,
        "gas_estimate_accuracy": null,
        "new_data": true,
        "measuring": false,
        "gas_measuring": true,
        "gas_meas_index": 0,
        "sub_meas_index": 0,
        "gas_valid": true,
        "heat_stable": true,
        "chip_id": "0x61",
        "variant_id": "0x01",
        "temp_offset_c": 0,
        "sample_rate_mode": "lp",
        "heater_profile_id": 0,
        "model_type": "selectivity",
        "class_count": 4,
        "uptime_s": 78964,
        "boot_count": 0,
        "ts": "2026-05-29T00:26:52.481Z"
      },
      "lastLines": [
        {
          "ts": "2026-05-29T00:26:07.424Z",
          "line": "{\"type\":\"telemetry\",\"device_id\":\"mycobrain-sidea-10b41d\",\"node_id\":\"mycobrain-sidea-10b41d\",\"role\":\"side_a\",\"sensor_slot\":\"env\",\"address\":\"0x76\",\"present\":true,\"valid\":true,\"fw_version\":\"recovery-operator-bsec2-v0.7\",\"config_version\":\"bsec2-default-lp\",\"bsec_version\":\"2.6.1.0\",\"location\":{\"lat\":null,\"lon\":null,\"source\":\"na\"},\"ts_ms\":78919442,\"temperature_c_comp\":25.09,\"temperature_f_comp\":77.16,\"humidity_pct_comp\":37.14,\"gas_resistance_ohm_comp\":null,\"ambient_temperature_c\":25.15,\"ambient_temperature_f\":77.27,\"ambient_humidity_pct\":36.99,\"iaq\":81.38,\"iaq_static\":67.12,\"iaq_accuracy\":3,\"eco2_ppm\":671.20,\"bvoc_ppm\":0.74,\"gas_percentage\":null,\"pressure_hpa\":647.21,\"gas_resistance_ohm\":469725,\"stabilization_status\":1,\"run_in_status\":1,\"output_accuracy\":3,\"bsec_status_code\":0,\"bme68x_status_code\":0,\"gas_estimate_1\":null,\"gas_estimate_2\":null,\"gas_estimate_3\":null,\"gas_estimate_4\":null,\"gas_estimate_accuracy\":null,\"new_data\":true,\"measuring\":fa
```

## Compatibility matrix

- **mdp_v1_commands** — MDP v1 commands (min: side-a-mdp-2.0.0)
- **buzzer_presets** — Buzzer presets (min: side-a-mdp-2.0.0)
- **neopixel_patterns** — NeoPixel patterns (min: side-a-mdp-2.0.0)
- **i2c_peripheral_grid** — I2C peripheral grid (min: side-a-mdp-2.0.0)
- **optical_acoustic_tx** — Optical/acoustic TX (min: side-a-mdp-2.1.0)
- **openclaw_agent** — OpenClaw / NemoClaw agent (min: None)