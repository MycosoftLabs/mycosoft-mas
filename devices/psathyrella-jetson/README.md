# Psathyrella Jetson propulsion agent

**Live path on Jetson:** `/home/jetson/.openclaw/workspace/tools/psathyrella-agent/jetson_agent.py`  
**Tracked mirror:** this directory (Jul 06, 2026 — propulsion live on bench).

## Hardware (Jul 06 ground truth)

| Item | Value |
|------|--------|
| PCA9685 I2C | **0x60**, Jetson header bus (`i2cdetect` **bus 7**) |
| I2C wiring | Direct pin3→SDA, pin5→SCL — **no TXS0108E** (Orin carrier already level-shifts; TXS in series breaks scan) |
| PCA VCC | **5V** from buck (before agent start — chip unpowered at boot → MOCK until restart) |
| ESC channels | **CH8–11** (CH0/1 drivers dead on board) |
| Servo channels | **CH4–7** |
| Neutral / stop | **1600 µs** (5V VCC clock; revert to 1700 if VCC returns to 3.3V) |

## systemd user drop-ins

Copy `systemd/psathyrella-agent.service.d/*.conf` to:

`~/.config/systemd/user/psathyrella-agent.service.d/`

Then:

```bash
systemctl --user daemon-reload
systemctl --user restart psathyrella-agent
curl -s http://127.0.0.1:8788/health
```

## Run locally (mock)

```bash
MOCK=1 python3 jetson_agent.py
```

Port **8788**. MAS forwards `nav.*` via `PSATHYRELLA_PROPULSION_AGENT_URL` (default `http://192.168.0.123:8788`).
