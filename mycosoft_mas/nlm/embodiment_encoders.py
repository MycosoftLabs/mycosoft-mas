from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List


def _norm(value: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    clipped = min(max(value, lo), hi)
    return (clipped - lo) / (hi - lo)


@dataclass
class NatureEmbeddingResult:
    vector: List[float]
    anomaly_score: float


class NatureEmbeddingEncoder:
    """
    Lightweight multi-sensor encoder used before full transformer training.
    """

    VECTOR_SIZE = 16

    def encode(self, packet: Dict[str, Any]) -> NatureEmbeddingResult:
        bme = packet.get("bme688") or {}
        fci = packet.get("fci") or {}
        audio_level = packet.get("audio_level_db")

        temp = float(bme.get("temperature_c") or 0.0)
        humidity = float(bme.get("humidity_percent") or 0.0)
        pressure = float(bme.get("pressure_hpa") or 0.0)
        gas = float(bme.get("gas_resistance_ohms") or 0.0)
        iaq = float(bme.get("iaq_index") or 0.0)
        fungal_strength = 0.0
        if isinstance(fci.get("signals"), list) and fci.get("signals"):
            values = [float(x) for x in fci["signals"][-32:] if isinstance(x, (int, float))]
            fungal_strength = sum(abs(v) for v in values) / max(len(values), 1)

        vec = [0.0] * self.VECTOR_SIZE
        vec[0] = _norm(temp, -10, 50)
        vec[1] = _norm(humidity, 0, 100)
        vec[2] = _norm(pressure, 850, 1150)
        vec[3] = _norm(gas, 1000, 1000000)
        vec[4] = _norm(iaq, 0, 500)
        vec[5] = _norm(fungal_strength, 0, 2000)
        vec[6] = _norm(float(audio_level or 0.0), -90, 0)
        vec[7] = 1.0 if packet.get("has_frame") else 0.0
        vec[8] = 1.0 if fci else 0.0
        vec[9] = math.sin(temp * 0.1) * 0.5 + 0.5
        vec[10] = math.cos(humidity * 0.05) * 0.5 + 0.5
        vec[11] = (vec[0] + vec[1]) / 2
        vec[12] = abs(vec[0] - vec[1])
        vec[13] = abs(vec[3] - vec[4])
        vec[14] = vec[5] * vec[1]
        vec[15] = 1.0

        anomaly_score = self._anomaly_score(temp=temp, humidity=humidity, iaq=iaq, fungal_strength=fungal_strength)
        return NatureEmbeddingResult(vector=vec, anomaly_score=anomaly_score)

    def _anomaly_score(self, temp: float, humidity: float, iaq: float, fungal_strength: float) -> float:
        score = 0.0
        if temp < -5 or temp > 45:
            score += 0.35
        if humidity < 10 or humidity > 95:
            score += 0.2
        if iaq > 200:
            score += 0.3
        if fungal_strength > 1200:
            score += 0.25
        return min(score, 1.0)

