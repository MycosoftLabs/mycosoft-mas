# Psathyrella Jetson Hardware + Propulsion Handoff (Claude Lane) — Jul 06, 2026

**Date:** 2026-07-06  
**Status:** Hardware I2C breakthrough; live Jetson agent patched (not in git)  
**From:** Cursor session (Morgan bench wiring, TXS0108E, PCA9685)  
**To:** Claude (GCS / front-end / integration lane)  
**Related:** `docs/PSATHYRELLA_BACKEND_P0_P6_STATUS_JUN27_2026.md`, `CODE/docs/PSATHYRELLA_HARDWARE_WIRE_PLAN_JUL01_2026.md`, `CODE/docs/PSATHYRELLA_GCS_P0_P6_INTEGRATION_STATUS_JUN27_2026.md`

---

## CEO intent (do not contradict)

- Morgan bought **TXS0108E** level shifters so **5 V signaling** on the propulsion path (PCA9685 → ESC/thruster/servo PWM at 5 V logic) works with the **Jetson 3.3 V I2C** bus.
- **SDA/SCL header wiring to the Jetson was already correct** (servos worked before TXS experiments). Do **not** reassign Jetson I2C pins unless hardware scan proves otherwise.
- **5 V buck power is present** (LED on). Power is not the open issue.
- **TXS wiring has never worked** (two boards tried). Direct bypass (no TXS) is what made I2C + PWM work on Jul 06.
- Morgan will **re-install TXS** for the intended 5 V architecture once wiring is confirmed.

---

## Architecture (unchanged software contract)

| Service | Host | Port | Role |
|--------|------|------|------|
| Mushroom 1 / sensors | Jetson `192.168.0.123` | **8787** | MQTT + HTTP, device id `psathyrella-1` |
| **Propulsion agent** | Jetson | **8788** | MDP `nav.*`, PCA9685 PWM |
| MAS Psathyrella API | `192.168.0.188` | **8001** | `POST /api/psathyrella/psathyrella-1/command` → forwards `nav.*` to **8788** |
| OpenClaw gateway | Jetson | 18789 | Not propulsion |

**PWM channel map (Jul 06+ canonical — updated Jul 07):**

| Logical | PCA channel | Hardware |
|--------|-------------|----------|
| Thruster 0–3 | **CH8–CH11** | DD WP ESCs |
| Azimuth 0–3 | **CH4–CH7** | FEETECH FS90MR continuous servos |

Env defaults on Jetson agent: `ESC_CH=8,9,10,11` · `SERVO_CH=4,5,6,7` · `PWM_FREQ=50` · `SERVO_MODE=continuous` · `PSATHYRELLA_BENCH_SINGLE_MOTOR=0` (all four pods).

**Jul 07 repo status:** Tracked `jetson_agent.py` includes `nav.az_zero`, `nav.esc_calibrate`, PCA re-probe, per-ESC neutral trim, INA226/leak hooks. MAS `7536f553e+` on 188. P1 completion: `docs/PSATHYRELLA_P1_COMPLETE_JUL07_2026.md`.

---

## What Cursor changed Jul 06 (Jetson only — superseded by git Jul 07)

### Changed (historical)

1. **Live file only** (not committed to GitHub):  
   `/home/jetson/.openclaw/workspace/tools/psathyrella-agent/jetson_agent.py`  
   - Was: `PCA9685(i2c)` → default address **0x40** (init failed → **MOCK PWM**).  
   - Now: `PCA9685(i2c, address=int(os.environ.get("PCA9685_I2C_ADDRESS", "0x60"), 0))`.

2. **systemd user drop-in** (Jetson):  
   `~/.config/systemd/user/psathyrella-agent.service.d/pca-address.conf`  
   ```ini
   [Service]
   Environment=PCA9685_I2C_ADDRESS=0x60
   ```

3. **Observed behavior after patch:**  
   - `GET http://192.168.0.123:8788/health` → `"pwm":"pca9685"`, `"last_write_ok":true` (was `"pwm":"mock"`).  
   - **Servos physically moved** — first real PWM reaching hardware after mock mode ended (boot/init writes + continuous servo stop trim).

### NOT changed

- **No MAS (`188`) deploy** · **no website/GCS code** · **no ESC/SERVO channel remap** · **no API route changes** · **no device id changes**.
- MDP command schema, thruster ids 0–3, MAS `jetson_forward.py` target URL `:8788` — **same as Jul 03**.

### If GCS “broke” after this session

Likely causes to check (not necessarily front-end code bugs):

1. **`/8788/health` now reports real hardware** — UI that assumed `pwm:"mock"` or hid propulsion warnings may need updating.
2. **Unexpected servo motion on bench** — continuous servos spin on any PWM write; stop trim `SERVO_STOP_US_CH4=1700` (Jul 03) is not 1500 µs; agent init/disarm still pushes pulses to CH4–7.
3. **Jetson reachability** — SSH/LAN drops if ethernet unplugged; MAS forward fails when `:8788` down.
4. **Misread “channel change”** — only **I2C address** changed (`0x40` → **`0x60`**), **not** PCA PWM channel numbers.

**Revert on Jetson (only if Morgan wants mock again — will stop real motors):** remove drop-in, restore `PCA9685(i2c)` at 0x40, `systemctl --user restart psathyrella-agent` (will fall back to mock unless chip appears at 0x40).

---

## Hardware discovery (Jul 06)

| Topic | Finding |
|-------|---------|
| PCA9685 I2C address | **`0x60`** (Blinka + `i2cget` on bus 7). **`0x41` never appeared** after A0 solder. **`0x70`** = PCA all-call (also seen). |
| Wrong scan trap | `sudo i2cdetect -y -r 1` → **`40: UU` is onboard INA3221**, not external PCA. |
| Correct header bus | Jetson pins 3/5 → Blinka `board.SDA` (GP16) / `board.SCL` (GP81); **`i2cdetect -y -r 7`** shows `60` / `70`. |
| TXS bypass | Direct: Jetson 3.3 V → PCA **VCC**, SDA/SCL direct, buck → PCA **V+**, common GND → **I2C + PWM worked**, servos moved. |
| Agent before bypass | Always **`pwm: mock`** — software was not driving PCA despite GCS/MAS commands appearing OK upstream. |

---

## TXS0108E — Morgan’s intended final wiring (5 V propulsion + I2C)

**V+ (motor power) does not go through TXS.** TXS only shifts **SDA/SCL**.

```
Buck 5–6 V  ──►  PCA V+     (ESC + servo power — 5 V propulsion rail)
Buck 5 V    ──►  PCA VCC    (5 V logic for PCA — Morgan’s intent)
Buck 5 V    ──►  TXS VB
Jetson 3.3 V ──► TXS VA
Jetson 3.3 V ──► TXS OE     (must be HIGH — tied to 3.3 V)
Jetson SDA   ──► TXS A1 ── B1 ──► PCA SDA
Jetson SCL   ──► TXS A2 ── B2 ──► PCA SCL
GND common: Jetson, TXS, PCA, buck
```

After TXS install: rescan must still find **`0x60`** and health must stay **`pca9685`**. If scan fails, TXS VA/OE/pairing is wrong — not Jetson SDA/SCL pins.

---

## Command contract (Claude / GCS — unchanged)

**MAS forward (preferred):**
```http
POST http://192.168.0.188:8001/api/psathyrella/psathyrella-1/command
Content-Type: application/json

{"target":"propulsion","cmd":"nav.arm","params":{"armed":true},"clientCommandId":"..."}
```

**Direct Jetson (bench):**
```http
POST http://192.168.0.123:8788/command
{"target":"propulsion","cmd":"nav.pwm_raw","params":{"channel":0,"us":1500}}
```

**Critical:** `nav.arm` without `params.armed:true` **disarms** (defaults false).

**Safe bench sequence:** `nav.all_stop` → `nav.arm {armed:true}` → low `nav.thruster {id:0,...}` → `nav.all_stop` → disarm. Props off; kill switch per wire plan.

---

## Verification checklist (Claude)

```powershell
# MAS
Invoke-RestMethod http://192.168.0.188:8001/api/psathyrella/psathyrella-1/status

# Jetson propulsion
Invoke-RestMethod http://192.168.0.123:8788/health
# Expect: pwm=pca9685, last_write_ok=true when hardware wired

# Forward test
Invoke-RestMethod -Method POST -Uri "http://192.168.0.188:8001/api/psathyrella/psathyrella-1/command" `
  -ContentType "application/json" `
  -Body '{"target":"propulsion","cmd":"nav.all_stop","params":{},"clientCommandId":"handoff_test_1"}'
```

**On Jetson (SSH `jetson@192.168.0.123`, password in MAS `.credentials.local`):**
```bash
sudo i2cdetect -y -r 7    # look for 60, not bus-1 40
curl -s http://127.0.0.1:8788/health
systemctl --user status psathyrella-agent
```

---

## Claude lane — suggested next work

1. **Confirm GCS still issues same MDP** to MAS; no thruster id / channel UI remap needed unless Morgan changed hardware mapping.
2. **Handle `pwm: pca9685`** in propulsion panel (live hardware indicator; warn on bench motion).
3. **Optional:** disarm + all-stop button prominent on bench; block arm if `last_write_ok` false.
4. **Do not** change Jetson I2C pin documentation to bus 1 / 0x40 without rescan — canonical is **header bus, addr 0x60**.
5. **Sync request to Cursor/repo:** copy Jetson `PCA9685_I2C_ADDRESS` env support into tracked `jetson_agent.py` when Morgan approves commit.

---

## Session outcome summary

| Item | Status |
|------|--------|
| I2C to PCA9685 | **Working** direct bypass @ **0x60** |
| Agent PWM backend | **Live** (`pca9685`) after address patch |
| TXS in circuit | **Out** for breakthrough; Morgan reinstalling for 5 V logic |
| MAS / GCS API | **Unchanged** |
| PWM channel map CH0–7 | **Unchanged** |
| Repo git | **Committed** Jul 07 (`7536f553e` lag/az_zero, P1 follow-up) |

**Morgan quote (context):** “Servos just started moving” = real PWM after mock ended, not random GPIO.

---

**End handoff — paste this file or link to Claude Desktop/Cowork for GCS lane continuity.**
