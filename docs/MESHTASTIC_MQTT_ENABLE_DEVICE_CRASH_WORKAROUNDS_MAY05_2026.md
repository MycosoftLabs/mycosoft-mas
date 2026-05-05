# Meshtastic — MQTT toggle crashes device (May 05, 2026)

**Symptom:** Turning MQTT **on** in the Meshtastic mobile app causes reboot, freeze, or disconnect on LilyGO / ESP32-class radios.

**Broker target (Mycosoft LAN):** `192.168.0.196:1883` **plaintext** (no TLS), credentials per Mosquitto ACL (e.g. `mycobrain` + `MQTT_BROKER_PASSWORD` in `.credentials.local`).

---

## 1. Why this happens (firmware, not Mycosoft bridge)

Upstream **meshtastic/firmware** has had multiple reports of **ESP32 reboot loops or panics** when **Wi-Fi + MQTT** start together—especially with **TLS**, **auth**, or **tight Wi-Fi event + MQTT connect** ordering (stack size / task timing). Examples: GitHub issues around MQTT bootloops, TLS MQTT reconnect, Wi-Fi hangs with MQTT.

Your LAN setup uses **port 1883 without TLS**, which avoids one common failure mode (TLS + small stack). Crashes can still occur from **app protobuf writes**, **Wi-Fi not ready**, or **firmware regressions** on a given board build.

---

## 2. Recommended order (app)

1. **Network → Wi-Fi:** SSID and password correct; device shows **connected** to LAN (same VLAN as `192.168.0.196`).
2. **MQTT module** — configure **before** flipping the master enable if the UI allows:
   - Address: `192.168.0.196`
   - Port: `1883`
   - **Encryption / TLS: OFF** (matches plaintext broker).
   - Username / password: match Mosquitto (publish allowed to `msh/#`).
3. **Then** enable MQTT / uplink.

If the UI only offers a single toggle first, use **CLI over USB** (section 3) for one board to confirm stability, then mirror settings in the app.

---

## 3. Safer path: Meshtastic CLI over USB (one COM port at a time)

Install Python CLI (`pip install meshtastic`), connect **one** radio via USB, then use `--set` for MQTT fields. Exact keys vary slightly by firmware; always run:

```bash
meshtastic --port COMx --info
meshtastic --port COMx --help
```

Typical pattern (verify names with `--help`):

- Point MQTT at **`192.168.0.196`**, port **`1883`**, **encryption disabled** for LAN plaintext.
- Enable MQTT module **after** address/port match your broker.

If the device **bootloops**, connect USB immediately after power-on and run:

```bash
meshtastic --port COMx --set mqtt.enabled false
```

(as soon as the serial link comes up) to break the loop without a full reflash—same idea as upstream issue discussions.

---

## 4. Firmware / app hygiene

- **Match app** to firmware generation (current Meshtastic mobile app from store).
- **Pinned fleet firmware** (e.g. v2.7.15.x): if **all four** crash on the same build, try **one** board on the **latest stable** release from Meshtastic to see if the crash disappears (regression vs hardware).
- Release notes for recent betas mention **telemetry defaults** and **MQTT when disconnected** fixes—stay on a **single** fleet version when diagnosing.

---

## 5. Broker-side sanity (does not fix MCU crash but avoids reconnect storms)

- From any LAN PC: broker listens on **1883**, accepts your MQTT user, and allows publish/subscribe patterns Meshtastic uses (`msh/#`).
- **Wrong TLS/port** (client thinks TLS, broker is plain) causes rapid reconnect → stress on radio Wi-Fi stack.

---

## 6. Mycosoft ingest

Once radios stay up with MQTT enabled and LAN broker sees **`msh/#`**, **VM 196** `mqtt-meshtastic-bridge` forwards to **MINDEX** / **Redis**; **MAS** `/api/meshtastic/*` reflects packets. No mock path—empty stats until real uplink traffic.
