#!/usr/bin/env python3
"""
Psathyrella Jetson propulsion agent — DEFAULT PORT :8788 (split-port Option B).

Port note (procurement briefing Jul 01): Jetson :8787 intentionally hosts the Mushroom 1 unified
agent (HTTP operator + MQTT, device id `psathyrella-1`) — do NOT evict it. This propulsion agent
runs on :8788; point MAS at it with PSATHYRELLA_JETSON_AGENT_URL=http://192.168.0.123:8788.
(Option A — extending the :8787 agent with these handlers — is equally valid; this file is the
standalone Option B service.)

Speaks the exact contract `mycosoft_mas/devices/psathyrella/jetson_forward.py` expects:

  POST /command   { "target":"side_b", "cmd":"nav.thruster", "params":{...}, "ack_requested":true }
  -> 200          { "ok":true, "cmd":"nav.thruster", "armed":true,
                    "propulsion": { "thrusters": [ {"id":0,"throttle_pct":35,"azimuth_deg":90,
                                                    "current_a":null,"rpm":null,"faulted":false}, ... ] } }

HARDWARE (per PSATHYRELLA_PROCUREMENT_BRIEFING_JUL01_2026 / HARDWARE_WIRE_PLAN):
  - TD1.2 thrusters + Diamond Dynamics WP ESCs — 50 Hz PWM, 1000–2000 µs, NO BEC.
    DD arming: power the ESC with the signal held at 1500 µs (4 beeps) → ready. This agent holds
    1500 µs neutral on boot and whenever disarmed, so the DD arming condition is met by default.
  - FEETECH FS90MR azimuth servos — 360° CONTINUOUS rotation (speed control, ~1500 µs = stop).
    SERVO_MODE=continuous (default): `azimuth` setpoints are dead-reckoned — the agent spins the
    pod at a calibratable rate (SERVO_DEG_PER_S) for the right duration, then stops. Open-loop:
    add an AS5600 encoder or IMU later for closed-loop azimuth. `nav.thruster_azimuth` also
    accepts {id, rate} (-100..100) for direct spin-rate control.
    SERVO_MODE=positional: classic 500–2500 µs = 0–360° mapping (MG90S/positional servos).
  - PCA9685 @ I2C addr **0x60** (Jetson header bus 7; direct SDA/SCL — **no TXS** in series) — ESC ch **8–11**, azimuth ch 4–7. Neutral/stop **1600µs** at 5V VCC. MOCK=1 runs without hardware.

SAFETY:
  - Arm gate: ESCs held at 1500 µs neutral unless armed (`nav.arm {armed:true}`).
  - Kill switch GPIO (active-low) forces disarm + all-stop.
  - Deadman watchdog: DEADMAN_S>0 → if armed and no command arrives for that many seconds,
    auto disarm + all-stop (set DEADMAN_S=15 for pool; default 0/off for bench jogging).
  - PSATHYRELLA_BENCH_SINGLE_MOTOR=1 → only thruster id 0 accepted (Tier A bench).

Run:
  pip install fastapi uvicorn pydantic     # + adafruit-circuitpython-pca9685 adafruit-blinka Jetson.GPIO on HW
  MOCK=1 python3 jetson_agent.py           # bench/no-hardware
Env: JETSON_AGENT_PORT|PORT(8788) MOCK(0) PWM_FREQ(50) ESC_CH(8,9,10,11) SERVO_CH(4,5,6,7)
     PCA9685_I2C_ADDRESS(0x60) ESC_NEUTRAL_US(1600) SERVO_STOP_US_BY_CHANNEL(4:1600,...)
     SERVO_MODE(continuous|positional) SERVO_DEG_PER_S(120) SERVO_RATE_SPAN_US(300)
     KILL_GPIO(18) THRUSTERS(4) DEADMAN_S(0) PSATHYRELLA_BENCH_SINGLE_MOTOR(0)
     ESC_NEUTRAL_US_BY_CHANNEL(8:1600,9:1600,...) ESC_CAL_HOLD_S(2)
     PCA_REPROBE_S(5) INA226_ENABLED(0) LEAK_GPIO(0)
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import logging
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from fastapi import FastAPI, Request
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s jetson-agent: %(message)s")
log = logging.getLogger("jetson-agent")

# ── config ───────────────────────────────────────────────────────────────────
N_THRUSTERS = int(os.getenv("THRUSTERS", "4"))
PWM_FREQ = int(os.getenv("PWM_FREQ", "50"))                 # Hz (DD ESC + servos = 50 Hz / 20 ms)
ESC_CH = [int(x) for x in os.getenv("ESC_CH", "8,9,10,11").split(",")]
SERVO_CH = [int(x) for x in os.getenv("SERVO_CH", "4,5,6,7").split(",")]
KILL_GPIO = int(os.getenv("KILL_GPIO", "18"))               # kill switch input (active-low)
ESC_NEUTRAL_US, ESC_SPAN_US = int(os.getenv("ESC_NEUTRAL_US", "1600")), 500
SERVO_MODE = os.getenv("SERVO_MODE", "continuous").lower()  # FS90MR = continuous (default)
SERVO_MIN_US, SERVO_MAX_US = 500, 2500                      # positional mode mapping 0–360°
SERVO_STOP_US = int(os.getenv("SERVO_STOP_US", "1500"))      # continuous mode: default stop pulse
SERVO_RATE_SPAN_US = int(os.getenv("SERVO_RATE_SPAN_US", "300"))  # ±µs at full spin rate
SERVO_DEG_PER_S = float(os.getenv("SERVO_DEG_PER_S", "120"))      # dead-reckon rate — CALIBRATE on bench
DEADMAN_S = float(os.getenv("DEADMAN_S", "0"))              # 0 = off; set 15 for pool
BENCH_SINGLE = (os.getenv("PSATHYRELLA_BENCH_SINGLE_MOTOR") or os.getenv("BENCH_SINGLE_MOTOR") or "0") == "1"
MOCK = os.getenv("MOCK", "0") == "1"
PCA_REPROBE_S = float(os.getenv("PCA_REPROBE_S", "5"))
ESC_CAL_HOLD_S = float(os.getenv("ESC_CAL_HOLD_S", "2"))
INA226_ENABLED = os.getenv("INA226_ENABLED", "0") == "1"
LEAK_GPIO = int(os.getenv("LEAK_GPIO", "0") or "0")  # 0 = disabled; active-high = leak when HIGH


def _parse_channel_pulse_overrides(raw: str, channels: List[int], default_us: int, env_prefix: str) -> Dict[int, int]:
    overrides: Dict[int, int] = {}
    for entry in raw.split(","):
        token = entry.strip()
        if not token or ":" not in token:
            continue
        channel_raw, pulse_raw = token.split(":", 1)
        try:
            channel = int(channel_raw.strip())
            pulse_us = int(float(pulse_raw.strip()))
        except ValueError:
            continue
        overrides[channel] = int(clamp(pulse_us, 1000, 2000))
    for channel in channels:
        env_value = os.getenv(f"{env_prefix}{channel}")
        if not env_value:
            continue
        try:
            overrides[channel] = int(clamp(float(env_value), 1000, 2000))
        except ValueError:
            continue
    return overrides


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _parse_servo_stop_overrides(raw: str) -> Dict[int, int]:
    return _parse_channel_pulse_overrides(raw, SERVO_CH, SERVO_STOP_US, "SERVO_STOP_US_CH")


SERVO_STOP_US_BY_CHANNEL = _parse_servo_stop_overrides(
    os.getenv("SERVO_STOP_US_BY_CHANNEL", "4:1600,5:1600,6:1600,7:1600")
)

ESC_NEUTRAL_US_BY_CHANNEL = _parse_channel_pulse_overrides(
    os.getenv("ESC_NEUTRAL_US_BY_CHANNEL", ""),
    ESC_CH,
    ESC_NEUTRAL_US,
    "ESC_NEUTRAL_US_CH",
)


def servo_stop_us_for_channel(channel: int) -> float:
    return float(SERVO_STOP_US_BY_CHANNEL.get(channel, SERVO_STOP_US))


def servo_stop_us_for_thruster(tid: int) -> float:
    if 0 <= tid < len(SERVO_CH):
        return servo_stop_us_for_channel(SERVO_CH[tid])
    return float(SERVO_STOP_US)


def esc_neutral_us_for_channel(channel: int) -> float:
    return float(ESC_NEUTRAL_US_BY_CHANNEL.get(channel, ESC_NEUTRAL_US))


def esc_neutral_us_for_thruster(tid: int) -> float:
    if 0 <= tid < len(ESC_CH):
        return esc_neutral_us_for_channel(ESC_CH[tid])
    return float(ESC_NEUTRAL_US)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_kill_switch_engaged() -> Optional[bool]:
    if MOCK:
        return None
    try:
        import Jetson.GPIO as GPIO  # type: ignore

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(KILL_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        return GPIO.input(KILL_GPIO) == 0
    except Exception:  # noqa: BLE001
        return None


# ── PWM backend (PCA9685 or mock) ────────────────────────────────────────────
class PwmBackend:
    """Sets a channel to a pulse width in microseconds at PWM_FREQ."""

    def __init__(self) -> None:
        self.real = False
        self._pca = None
        self.channels_us: Dict[int, float] = {}
        self.last_write_at: Optional[str] = None
        self.last_write_ok: Optional[bool] = None
        self.write_count = 0
        self.recent_errors: deque[Dict[str, Any]] = deque(maxlen=20)
        self._init_lock = threading.Lock()
        self.last_probe_at: Optional[str] = None
        self.probe_attempts = 0
        self.on_online: Optional[Callable[[], None]] = None
        if not MOCK:
            self._try_init_hardware()
            if not self.real and PCA_REPROBE_S > 0:
                threading.Thread(target=self._reprobe_loop, daemon=True, name="pca-reprobe").start()
        if not self.real:
            log.info("MOCK PWM backend (no hardware output)")

    def _try_init_hardware(self) -> bool:
        if MOCK:
            return False
        with self._init_lock:
            if self.real and self._pca is not None:
                return True
            self.probe_attempts += 1
            self.last_probe_at = now_iso()
            try:
                import board  # type: ignore
                import busio  # type: ignore
                from adafruit_pca9685 import PCA9685  # type: ignore

                i2c = busio.I2C(board.SCL, board.SDA)
                pca_addr = int(os.getenv("PCA9685_I2C_ADDRESS", "0x60"), 0)
                pca = PCA9685(i2c, address=pca_addr)
                pca.frequency = PWM_FREQ
                self._pca = pca
                self.real = True
                log.info("PCA9685 PWM backend up @ %d Hz (addr 0x%x)", PWM_FREQ, pca_addr)
                if self.on_online:
                    try:
                        self.on_online()
                    except Exception as exc:  # noqa: BLE001
                        log.warning("on_online callback failed: %s", exc)
                return True
            except Exception as exc:  # noqa: BLE001
                log.warning("PCA9685 unavailable (%s)", exc)
                return False

    def _reprobe_loop(self) -> None:
        log.info("PCA background re-probe every %.1fs until chip online", PCA_REPROBE_S)
        while not self.real:
            time.sleep(max(1.0, PCA_REPROBE_S))
            if self._try_init_hardware():
                log.info("PCA9685 online after background re-probe (attempt %d)", self.probe_attempts)
                return

    def set_us(self, channel: int, pulse_us: float) -> None:
        period_us = 1_000_000 / PWM_FREQ
        duty = int(clamp(pulse_us / period_us, 0.0, 1.0) * 0xFFFF)
        self.channels_us[channel] = round(float(pulse_us), 2)
        self.last_write_at = now_iso()
        self.write_count += 1
        if self.real and self._pca is not None:
            try:
                self._pca.channels[channel].duty_cycle = duty
                self.last_write_ok = True
            except Exception as exc:  # noqa: BLE001
                self.last_write_ok = False
                self.recent_errors.append(
                    {
                        "at": now_iso(),
                        "channel": channel,
                        "pulse_us": round(float(pulse_us), 2),
                        "error": str(exc),
                    }
                )
                log.error("PWM ch%d set failed: %s", channel, exc)
        else:
            self.last_write_ok = None
            log.info("PWM ch%-2d -> %4.0f us (duty %d)", channel, pulse_us, duty)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "driver": "pca9685" if self.real else "mock",
            "frequency_hz": PWM_FREQ,
            "last_write_at": self.last_write_at,
            "last_write_ok": self.last_write_ok,
            "write_count": self.write_count,
            "last_probe_at": self.last_probe_at,
            "probe_attempts": self.probe_attempts,
            "reprobe_interval_s": PCA_REPROBE_S if not MOCK else None,
            "channels_us": {str(ch): us for ch, us in sorted(self.channels_us.items())},
            "recent_errors": list(self.recent_errors),
        }


class PowerTelemetry:
    """Optional INA226 per-ESC current + leak GPIO — null when hardware absent."""

    def __init__(self) -> None:
        self.enabled = INA226_ENABLED and not MOCK
        self._sensors: List[Any] = []
        self._addresses = [
            int(token.strip(), 0)
            for token in (os.getenv("INA226_ADDRESSES") or "").split(",")
            if token.strip()
        ]
        if self.enabled:
            self._init_sensors()

    def _init_sensors(self) -> None:
        try:
            import board  # type: ignore
            import busio  # type: ignore
            from adafruit_ina226 import INA226  # type: ignore

            i2c = busio.I2C(board.SCL, board.SDA)
            addresses = self._addresses or [0x40, 0x41, 0x44, 0x45]
            for addr in addresses[: len(ESC_CH)]:
                try:
                    self._sensors.append(INA226(i2c, address=addr))
                except Exception as exc:  # noqa: BLE001
                    log.warning("INA226 0x%x unavailable: %s", addr, exc)
            if self._sensors:
                log.info("INA226 telemetry: %d sensor(s)", len(self._sensors))
            else:
                self.enabled = False
        except Exception as exc:  # noqa: BLE001
            log.warning("INA226 init failed (%s)", exc)
            self.enabled = False

    def read_thruster_currents(self) -> Dict[int, Optional[float]]:
        currents: Dict[int, Optional[float]] = {i: None for i in range(N_THRUSTERS)}
        if not self.enabled or not self._sensors:
            return currents
        for idx, sensor in enumerate(self._sensors):
            if idx >= N_THRUSTERS:
                break
            try:
                currents[idx] = round(float(sensor.current), 3)
            except Exception:  # noqa: BLE001
                currents[idx] = None
        return currents

    def snapshot(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "addresses": [hex(a) for a in self._addresses] if self._addresses else None,
            "sensor_count": len(self._sensors),
        }


def read_leak_detected() -> Optional[bool]:
    if MOCK or LEAK_GPIO <= 0:
        return None
    try:
        import Jetson.GPIO as GPIO  # type: ignore

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(LEAK_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        return GPIO.input(LEAK_GPIO) == GPIO.HIGH
    except Exception:  # noqa: BLE001
        return None


# ── thruster state + control ─────────────────────────────────────────────────
class Thruster:
    def __init__(self, tid: int) -> None:
        self.id = tid
        self.throttle_pct = 0.0
        self.azimuth_deg = 0.0            # commanded azimuth (echoed to MAS immediately)
        self.az_actual = 0.0              # dead-reckoned physical estimate (continuous mode)
        self.az_cancel = threading.Event()  # cancels an in-flight rotation worker
        self.current_a: Optional[float] = None  # null until ESC telemetry / INA226 wired
        self.rpm: Optional[float] = None
        self.faulted = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "throttle_pct": self.throttle_pct, "azimuth_deg": self.azimuth_deg,
            "az_actual_deg": round(self.az_actual, 2), "current_a": self.current_a, "rpm": self.rpm, "faulted": self.faulted,
        }


class Propulsion:
    def __init__(self) -> None:
        self.pwm = PwmBackend()
        self.pwm.on_online = self.neutral_all
        self.power = PowerTelemetry()
        self.thrusters: List[Thruster] = [Thruster(i) for i in range(N_THRUSTERS)]
        self.armed = False
        self.mode = "MANUAL"
        self.fight_current = False
        self._lock = threading.Lock()
        self.last_cmd_ts = time.monotonic()
        self.last_command: Optional[Dict[str, Any]] = None
        self._refresh_power_telemetry()
        # Boot: ESC signal held at neutral -> DD ESC arming beeps complete on power-up.
        self.neutral_all()

    def _refresh_power_telemetry(self) -> None:
        currents = self.power.read_thruster_currents()
        for tid, amps in currents.items():
            if 0 <= tid < len(self.thrusters):
                self.thrusters[tid].current_a = amps

    # -- low-level pulse helpers --
    def _esc_us(self, throttle_pct: float, *, tid: Optional[int] = None) -> float:
        neutral = esc_neutral_us_for_thruster(tid) if tid is not None else float(ESC_NEUTRAL_US)
        return neutral + (clamp(throttle_pct, -100, 100) / 100.0) * ESC_SPAN_US

    def _servo_positional_us(self, azimuth_deg: float) -> float:
        return SERVO_MIN_US + (clamp(azimuth_deg, 0, 360) / 360.0) * (SERVO_MAX_US - SERVO_MIN_US)

    def _servo_rate_us(self, rate_pct: float, *, center_us: Optional[float] = None) -> float:
        center = float(SERVO_STOP_US if center_us is None else center_us)
        return center + (clamp(rate_pct, -100, 100) / 100.0) * SERVO_RATE_SPAN_US

    def _apply_esc(self, t: Thruster) -> None:
        eff = t.throttle_pct if self.armed and not t.faulted else 0.0
        if t.id < len(ESC_CH):
            self.pwm.set_us(ESC_CH[t.id], self._esc_us(eff, tid=t.id))

    def _servo_stop(self, t: Thruster) -> None:
        if t.id < len(SERVO_CH):
            stop_us = servo_stop_us_for_thruster(t.id)
            self.pwm.set_us(SERVO_CH[t.id], stop_us if SERVO_MODE == "continuous" else self._servo_positional_us(t.azimuth_deg))

    def neutral_all(self) -> None:
        for t in self.thrusters:
            self._apply_esc(t)
            if SERVO_MODE == "continuous":
                if t.id < len(SERVO_CH):
                    self.pwm.set_us(SERVO_CH[t.id], servo_stop_us_for_thruster(t.id))
            else:
                self._servo_stop(t)

    # -- azimuth (continuous FS90MR: dead-reckoned timed rotation; positional: direct) --
    def _rotate_worker(self, t: Thruster, target: float, cancel: threading.Event) -> None:
        delta = ((target - t.az_actual + 540) % 360) - 180  # shortest path, -180..180
        if abs(delta) < 2:
            self._servo_stop(t)
            t.az_actual = target
            return
        direction = 1.0 if delta > 0 else -1.0
        duration = abs(delta) / max(1.0, SERVO_DEG_PER_S)
        if t.id < len(SERVO_CH):
            self.pwm.set_us(
                SERVO_CH[t.id],
                self._servo_rate_us(direction * 60, center_us=servo_stop_us_for_thruster(t.id)),
            )  # 60% rate spin
        start = time.monotonic()
        while time.monotonic() - start < duration:
            if cancel.is_set():
                break
            time.sleep(0.02)
        if t.id < len(SERVO_CH):
            self.pwm.set_us(SERVO_CH[t.id], servo_stop_us_for_thruster(t.id))
        elapsed = time.monotonic() - start
        t.az_actual = (t.az_actual + direction * min(1.0, elapsed / duration) * abs(delta)) % 360

    def set_azimuth(self, t: Thruster, azimuth: float) -> None:
        t.azimuth_deg = clamp(float(azimuth), 0, 360)
        if SERVO_MODE == "continuous":
            t.az_cancel.set()
            t.az_cancel = threading.Event()
            threading.Thread(target=self._rotate_worker, args=(t, t.azimuth_deg, t.az_cancel), daemon=True).start()
        else:
            self._servo_stop(t)  # positional: direct pulse

    def set_azimuth_rate(self, t: Thruster, rate_pct: float) -> None:
        """Direct spin-rate control (continuous servos only) — rate -100..100, 0 = stop."""
        t.az_cancel.set()
        if t.id < len(SERVO_CH):
            self.pwm.set_us(
                SERVO_CH[t.id],
                self._servo_rate_us(rate_pct, center_us=servo_stop_us_for_thruster(t.id))
                if SERVO_MODE == "continuous"
                else self._servo_positional_us(t.azimuth_deg),
            )

    def az_zero_home(self, tid: Optional[int] = None) -> str:
        """Declare the pod's current physical orientation as 0° home — no rotation."""
        with self._lock:
            ids = [int(tid)] if tid is not None else list(range(len(self.thrusters)))
            touched: List[int] = []
            for i in ids:
                if not (0 <= i < len(self.thrusters)):
                    continue
                note = self._bench_gate(i)
                if note:
                    continue
                t = self.thrusters[i]
                t.az_cancel.set()
                t.azimuth_deg = 0.0
                t.az_actual = 0.0
                if t.id < len(SERVO_CH) and SERVO_MODE == "continuous":
                    self.pwm.set_us(SERVO_CH[t.id], servo_stop_us_for_thruster(t.id))
                touched.append(i)
            return f"azimuth home set for {touched}"

    # -- command surface --
    def _bench_gate(self, tid: int) -> Optional[str]:
        if BENCH_SINGLE and tid != 0:
            return f"bench_single_motor: id {tid} ignored (only id 0 active)"
        return None

    def set_thruster(self, tid: int, throttle: Optional[float], azimuth: Optional[float]) -> Optional[str]:
        with self._lock:
            if not (0 <= tid < len(self.thrusters)):
                return f"bad thruster id {tid}"
            note = self._bench_gate(tid)
            if note:
                return note
            t = self.thrusters[tid]
            if throttle is not None:
                t.throttle_pct = clamp(float(throttle), -100, 100)
                self._apply_esc(t)
            if azimuth is not None:
                self.set_azimuth(t, float(azimuth))
            return None

    def thrust_vector(self, heading: float, magnitude: float, yaw_rate: float) -> None:
        with self._lock:
            for t in self.thrusters:
                if BENCH_SINGLE and t.id != 0:
                    continue
                bias = (1 if t.id in (1, 3) else -1) * clamp(yaw_rate, -100, 100) * 0.3
                t.throttle_pct = clamp(magnitude + bias, -100, 100)
                self._apply_esc(t)
                self.set_azimuth(t, heading % 360)

    def all_stop(self) -> None:
        with self._lock:
            for t in self.thrusters:
                t.throttle_pct = 0.0
                t.az_cancel.set()          # halt any in-flight rotation
                self._apply_esc(t)
                if t.id < len(SERVO_CH) and SERVO_MODE == "continuous":
                    self.pwm.set_us(SERVO_CH[t.id], servo_stop_us_for_thruster(t.id))

    def set_armed(self, armed: bool) -> None:
        with self._lock:
            self.armed = bool(armed)
            # Always arm into neutral so DD ESCs see a clean 1500 us interlock.
            # A fresh throttle command must arrive after arming before any ESC moves.
            for t in self.thrusters:
                t.throttle_pct = 0.0
                t.az_cancel.set()
            self.neutral_all()
            log.info("ARMED=%s", self.armed)

    def note_command(self, cmd: str, params: Dict[str, Any], detail: str) -> None:
        self.last_command = {
            "at": now_iso(),
            "cmd": cmd,
            "params": params,
            "detail": detail,
        }

    def esc_calibrate(
        self,
        *,
        dry_run: bool,
        thruster_ids: Optional[List[int]] = None,
        hold_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        DD WP ESC throttle-range teach: full forward -> full reverse -> neutral per ESC.
        Disarmed only; props off; kill switch accessible.
        """
        hold = max(0.5, float(hold_s if hold_s is not None else ESC_CAL_HOLD_S))
        ids = thruster_ids if thruster_ids is not None else list(range(len(self.thrusters)))
        if self.armed:
            return {"ok": False, "error": "disarm_before_esc_calibrate"}
        actions: List[Dict[str, Any]] = []
        with self._lock:
            for tid in ids:
                if not (0 <= tid < len(self.thrusters)):
                    continue
                note = self._bench_gate(tid)
                if note:
                    actions.append({"thruster_id": tid, "skipped": note})
                    continue
                if tid >= len(ESC_CH):
                    continue
                ch = ESC_CH[tid]
                neutral = esc_neutral_us_for_thruster(tid)
                fwd = self._esc_us(100.0, tid=tid)
                rev = self._esc_us(-100.0, tid=tid)
                steps = [
                    ("full_forward", fwd),
                    ("full_reverse", rev),
                    ("neutral", neutral),
                ]
                for phase, pulse in steps:
                    actions.append({"thruster_id": tid, "channel": ch, "phase": phase, "pulse_us": round(pulse, 1)})
                    if not dry_run:
                        self.pwm.set_us(ch, pulse)
                        if phase != "neutral":
                            time.sleep(hold)
                if not dry_run and tid < len(self.thrusters):
                    self.thrusters[tid].throttle_pct = 0.0
            if not dry_run:
                self.neutral_all()
        return {
            "ok": True,
            "dry_run": dry_run,
            "hold_s": hold,
            "detail": "esc_range_calibration",
            "actions": actions,
        }

    def deadman_seconds_remaining(self) -> Optional[float]:
        if not self.armed or DEADMAN_S <= 0:
            return None
        remaining = DEADMAN_S - (time.monotonic() - self.last_cmd_ts)
        return round(max(0.0, remaining), 3)

    def snapshot(self) -> Dict[str, Any]:
        self._refresh_power_telemetry()
        leak = read_leak_detected()
        kill = read_kill_switch_engaged()
        return {
            "status": "ok",
            "service": "psathyrella-jetson-agent",
            "armed": self.armed,
            "armedToActuate": self.armed,
            "mode": self.mode,
            "fightCurrent": self.fight_current,
            "bench_single_motor": BENCH_SINGLE,
            "deadman_s": DEADMAN_S,
            "deadman_seconds_remaining": self.deadman_seconds_remaining(),
            "safety": {
                "kill_switch_engaged": kill,
                "killSwitchEngaged": kill,
                "leak_detected": leak,
                "leakDetected": leak,
                "deadman_seconds_remaining": self.deadman_seconds_remaining(),
            },
            "kill_switch_engaged": kill,
            "leak_detected": leak,
            "servo_mode": SERVO_MODE,
            "servo_stop_us_default": SERVO_STOP_US,
            "esc_neutral_us": ESC_NEUTRAL_US,
            "esc_neutral_us_by_channel": {str(ch): pulse for ch, pulse in sorted(ESC_NEUTRAL_US_BY_CHANNEL.items())},
            "servo_stop_us_by_channel": {str(ch): pulse for ch, pulse in sorted(SERVO_STOP_US_BY_CHANNEL.items())},
            "channels": {
                "esc": ESC_CH,
                "servo": SERVO_CH,
            },
            "power_telemetry": self.power.snapshot(),
            "last_command": self.last_command,
            "last_command_age_s": round(max(0.0, time.monotonic() - self.last_cmd_ts), 3),
            "pwm": self.pwm.snapshot(),
            "propulsion": {"thrusters": [t.as_dict() for t in self.thrusters]},
        }

    def run_selftest(self, *, dry_run: bool, thruster_id: int, apply_neutral: bool) -> Dict[str, Any]:
        if not (0 <= thruster_id < len(self.thrusters)):
            return {"ok": False, "error": f"bad thruster id {thruster_id}"}

        thruster = self.thrusters[thruster_id]
        esc_channel = ESC_CH[thruster_id] if thruster_id < len(ESC_CH) else None
        servo_channel = SERVO_CH[thruster_id] if thruster_id < len(SERVO_CH) else None
        actions: List[Dict[str, Any]] = []

        if apply_neutral:
            if esc_channel is not None:
                neutral = esc_neutral_us_for_thruster(thruster_id)
                actions.append({"kind": "esc_neutral", "channel": esc_channel, "pulse_us": neutral})
                if not dry_run:
                    self.pwm.set_us(esc_channel, neutral)
            if servo_channel is not None:
                servo_pulse = servo_stop_us_for_channel(servo_channel) if SERVO_MODE == "continuous" else self._servo_positional_us(thruster.azimuth_deg)
                actions.append({"kind": "servo_safe", "channel": servo_channel, "pulse_us": round(float(servo_pulse), 2)})
                if not dry_run:
                    self.pwm.set_us(servo_channel, servo_pulse)

        return {
            "ok": True,
            "safe": True,
            "dryRun": dry_run,
            "detail": "neutral_only_selftest",
            "thruster_id": thruster_id,
            "actions": actions,
            "state": self.snapshot(),
        }


PROP = Propulsion()


# ── watchdogs ────────────────────────────────────────────────────────────────
def kill_switch_watch() -> None:
    if MOCK:
        return
    try:
        import Jetson.GPIO as GPIO  # type: ignore

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(KILL_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        log.info("kill-switch watch on GPIO%d (active-low)", KILL_GPIO)
        while True:
            if GPIO.input(KILL_GPIO) == 0 and PROP.armed:
                log.warning("KILL SWITCH — forcing disarm + all-stop")
                PROP.set_armed(False)
            time.sleep(0.05)
    except Exception as exc:  # noqa: BLE001
        log.warning("kill-switch watch disabled (%s)", exc)


def deadman_watch() -> None:
    """Comms-loss failsafe: armed + silence for DEADMAN_S seconds -> disarm + all-stop."""
    if DEADMAN_S <= 0:
        log.info("deadman watchdog OFF (DEADMAN_S=0) — set DEADMAN_S=15 for pool ops")
        return
    log.info("deadman watchdog ON: disarm after %.0fs of command silence while armed", DEADMAN_S)
    while True:
        time.sleep(0.5)
        if PROP.armed and (time.monotonic() - PROP.last_cmd_ts) > DEADMAN_S:
            log.warning("DEADMAN (%.0fs silent) — disarm + all-stop", DEADMAN_S)
            PROP.set_armed(False)


# ── HTTP API ─────────────────────────────────────────────────────────────────
app = FastAPI(title="Psathyrella Jetson Propulsion Agent", version="1.1.0")


class MdpCommand(BaseModel):
    target: Optional[str] = None
    cmd: str
    params: Optional[Dict[str, Any]] = None
    ack_requested: Optional[bool] = True
    timeout_ms: Optional[int] = None


class SelfTestRequest(BaseModel):
    dry_run: bool = True
    thruster_id: int = 0
    apply_neutral: bool = True


def _feedback(cmd: str, ok: bool = True, detail: str = "applied") -> Dict[str, Any]:
    return {
        "ok": ok, "cmd": cmd, "armed": PROP.armed, "armedToActuate": PROP.armed,
        "mode": PROP.mode, "fightCurrent": PROP.fight_current, "detail": detail,
        "propulsion": {"thrusters": [t.as_dict() for t in PROP.thrusters]},
    }


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "psathyrella-jetson-agent", "armed": PROP.armed,
            "armedToActuate": PROP.armed, "mode": PROP.mode,
            "pwm": "pca9685" if PROP.pwm.real else "mock", "thrusters": N_THRUSTERS,
            "servo_mode": SERVO_MODE, "bench_single_motor": BENCH_SINGLE,
            "deadman_s": DEADMAN_S, "last_write_ok": PROP.pwm.last_write_ok,
            "recent_error_count": len(PROP.pwm.recent_errors)}


@app.get("/state")
def state() -> Dict[str, Any]:
    return PROP.snapshot()


@app.post("/selftest")
def selftest(body: SelfTestRequest) -> Dict[str, Any]:
    return PROP.run_selftest(
        dry_run=body.dry_run,
        thruster_id=body.thruster_id,
        apply_neutral=body.apply_neutral,
    )


@app.post("/command")
async def command(body: MdpCommand, request: Request) -> Dict[str, Any]:  # noqa: ARG001
    cmd = (body.cmd or "").strip()
    p = body.params or {}
    PROP.last_cmd_ts = time.monotonic()
    try:
        if cmd == "nav.arm":
            PROP.set_armed(bool(p.get("armed", False)))
            PROP.note_command(cmd, p, "applied")
            return _feedback(cmd)
        if cmd == "nav.all_stop":
            PROP.all_stop()
            PROP.note_command(cmd, p, "applied")
            return _feedback(cmd)
        if cmd == "nav.thruster":
            note = PROP.set_thruster(int(p.get("id", 0)), p.get("throttle"), p.get("azimuth"))
            PROP.note_command(cmd, p, note or "applied")
            return _feedback(cmd, detail=note or "applied")
        if cmd == "nav.az_zero":
            tid_raw = p.get("id")
            detail = PROP.az_zero_home(int(tid_raw) if tid_raw is not None else None)
            PROP.note_command(cmd, p, detail)
            return _feedback(cmd, detail=detail)
        if cmd == "nav.esc_calibrate":
            tid_raw = p.get("id")
            ids = [int(tid_raw)] if tid_raw is not None else None
            result = PROP.esc_calibrate(
                dry_run=bool(p.get("dry_run", False)),
                thruster_ids=ids,
                hold_s=p.get("hold_s"),
            )
            detail = result.get("detail") or result.get("error") or "esc_calibrate"
            PROP.note_command(cmd, p, detail)
            if not result.get("ok"):
                return _feedback(cmd, ok=False, detail=str(result.get("error") or detail))
            return {**_feedback(cmd, detail=detail), "calibration": result}
        if cmd == "nav.thruster_azimuth":
            tid = int(p.get("id", 0))
            if not (0 <= tid < len(PROP.thrusters)):
                return _feedback(cmd, ok=False, detail=f"bad thruster id {tid}")
            t = PROP.thrusters[tid]
            if p.get("rate") is not None:
                PROP.set_azimuth_rate(t, float(p.get("rate", 0)))
                PROP.note_command(cmd, p, f"rate {p.get('rate')}")
                return _feedback(cmd, detail=f"rate {p.get('rate')}")
            note = PROP.set_thruster(tid, None, p.get("azimuth"))
            PROP.note_command(cmd, p, note or "applied")
            return _feedback(cmd, detail=note or "applied")
        if cmd == "nav.pwm_raw":
            # Bench diagnostic: drive ANY PCA9685 channel (0-15) to a raw pulse, bypassing the
            # thruster map AND the arm gate. For finding which channel a servo/ESC is on and
            # trimming a continuous servo's true stop. Clamped to [1000,2000] µs. Kill switch in hand.
            try:
                ch = int(p.get("channel"))
                default_us = servo_stop_us_for_channel(ch) if ch in SERVO_CH else float(SERVO_STOP_US)
                us = float(p.get("us", default_us))
            except (TypeError, ValueError):
                return _feedback(cmd, ok=False, detail="channel (0-15) and us required")
            if not (0 <= ch <= 15):
                return _feedback(cmd, ok=False, detail=f"bad channel {ch} (must be 0-15)")
            us = clamp(us, 1000.0, 2000.0)
            PROP.pwm.set_us(ch, us)
            PROP.note_command(cmd, p, f"ch{ch}={us:.0f}us")
            return _feedback(cmd, detail=f"ch{ch}={us:.0f}us")
        if cmd == "nav.thrust_vector":
            PROP.thrust_vector(float(p.get("heading", 0)), float(p.get("magnitude", 0)), float(p.get("yaw_rate", 0)))
            PROP.note_command(cmd, p, "applied")
            return _feedback(cmd)
        if cmd == "nav.set_mode":
            PROP.mode = str(p.get("mode") or PROP.mode or "MANUAL").strip().upper() or "MANUAL"
            PROP.note_command(cmd, p, f"accepted:{cmd}")
            return _feedback(cmd, detail=f"accepted:{cmd}")
        if cmd == "nav.station_keep":
            PROP.mode = "STATION_KEEP"
            PROP.note_command(cmd, p, f"accepted:{cmd}")
            return _feedback(cmd, detail=f"accepted:{cmd}")
        if cmd == "nav.fight_current":
            PROP.fight_current = bool(p.get("enabled", True))
            PROP.note_command(cmd, p, f"accepted:{cmd}")
            return _feedback(cmd, detail=f"accepted:{cmd}")
        return {"ok": False, "cmd": cmd, "error": f"unknown command: {cmd}",
                "propulsion": {"thrusters": [t.as_dict() for t in PROP.thrusters]}}
    except Exception as exc:  # noqa: BLE001
        log.error("command %s failed: %s", cmd, exc)
        return {"ok": False, "cmd": cmd, "error": str(exc)}


def main() -> None:
    import uvicorn

    threading.Thread(target=kill_switch_watch, daemon=True).start()
    threading.Thread(target=deadman_watch, daemon=True).start()
    port = int(os.getenv("JETSON_AGENT_PORT") or os.getenv("PORT") or "8788")
    log.info("Psathyrella propulsion agent on :%d (mock=%s, servo=%s, thrusters=%d, bench_single=%s)",
             port, MOCK, SERVO_MODE, N_THRUSTERS, BENCH_SINGLE)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info", access_log=False)


if __name__ == "__main__":
    main()
