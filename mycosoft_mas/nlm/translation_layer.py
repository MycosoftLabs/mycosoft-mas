"""
NLM Translation Layer

Translates raw sensor data through:
1. Raw -> Normalized (scaling, calibration)
2. Normalized -> Bio-Tokens (vocabulary mapping)
3. Bio-Tokens -> NMF (frame assembly)

Created: February 25, 2026
"""

import logging
from typing import Any, Dict, List, Optional

from mycosoft_mas.nlm.bio_tokens import get_semantic
from mycosoft_mas.nlm.nmf import NatureMessageFrame
from mycosoft_mas.nlm.telemetry_envelopes import TelemetryEnvelope

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Normalization thresholds (used for Raw -> Normalized)
# ---------------------------------------------------------------------------

TEMP_OPT_LO = 20.0
TEMP_OPT_HI = 28.0
TEMP_STRESS_LO = 15.0
TEMP_STRESS_HI = 35.0

HUM_LOW = 40.0
HUM_HIGH = 80.0

LIGHT_LOW = 100.0
LIGHT_OPT = 500.0
LIGHT_HIGH = 2000.0

CO2_HIGH = 1500.0
CO2_OPT = 800.0

PH_ACID = 6.0
PH_ALK = 8.0

MOISTURE_DRY = 30.0
MOISTURE_SAT = 80.0


def normalize_raw(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 1: Raw -> Normalized.
    Scale and calibrate raw sensor values to standard ranges.
    """
    out: Dict[str, Any] = dict(raw)
    # Temperature (if present)
    t = raw.get("temperature_c") or raw.get("temp_c") or raw.get("temperature")
    if t is not None:
        out["temperature_c"] = float(t)
    # Humidity
    h = raw.get("humidity_pct") or raw.get("humidity") or raw.get("rh")
    if h is not None:
        out["humidity_pct"] = float(h)
    # Light
    lx = raw.get("light_lux") or raw.get("lux") or raw.get("light")
    if lx is not None:
        out["light_lux"] = float(lx)
    # CO2
    co2 = raw.get("co2_ppm") or raw.get("co2")
    if co2 is not None:
        out["co2_ppm"] = float(co2)
    # pH
    ph = raw.get("ph")
    if ph is not None:
        out["ph"] = float(ph)
    # Moisture
    m = raw.get("moisture_pct") or raw.get("moisture")
    if m is not None:
        out["moisture_pct"] = float(m)
    return out


def raw_to_bio_tokens(raw: Dict[str, Any]) -> List[str]:
    """
    Step 2: Raw/Normalized -> Bio-Tokens.
    Map sensor values to bio-token codes using thresholds.
    """
    tokens: List[str] = []
    norm = normalize_raw(raw)

    # Temperature
    t = norm.get("temperature_c")
    if t is not None:
        if TEMP_OPT_LO <= t <= TEMP_OPT_HI:
            tokens.append("TEMP_OPT")
        elif t > TEMP_STRESS_HI:
            tokens.append("TEMP_STRESS_HI")
        elif t < TEMP_STRESS_LO:
            tokens.append("TEMP_STRESS_LO")
        elif t < TEMP_OPT_LO:
            tokens.append("TEMP_COOL")
        else:
            tokens.append("TEMP_WARM")

    # Humidity
    h = norm.get("humidity_pct")
    if h is not None:
        if h > HUM_HIGH:
            tokens.append("HUM_HIGH")
        elif h < HUM_LOW:
            tokens.append("HUM_LOW")
        else:
            tokens.append("HUM_OPT")

    # Light
    lx = norm.get("light_lux")
    if lx is not None:
        if lx < LIGHT_LOW:
            tokens.append("LIGHT_LOW")
        elif lx >= LIGHT_OPT and lx <= LIGHT_HIGH:
            tokens.append("LIGHT_OPT")
        elif lx > LIGHT_HIGH:
            tokens.append("LIGHT_HIGH")

    # CO2
    co2 = norm.get("co2_ppm")
    if co2 is not None:
        if co2 > CO2_HIGH:
            tokens.append("CO2_HIGH")
        else:
            tokens.append("CO2_OPT")

    # pH
    ph = norm.get("ph")
    if ph is not None:
        if ph < PH_ACID:
            tokens.append("PH_ACID")
        elif ph > PH_ALK:
            tokens.append("PH_ALK")
        else:
            tokens.append("PH_NEUTRAL")

    # Moisture
    m = norm.get("moisture_pct")
    if m is not None:
        if m < MOISTURE_DRY:
            tokens.append("MOIST_DRY")
        elif m > MOISTURE_SAT:
            tokens.append("MOIST_SAT")
        else:
            tokens.append("MOIST_OPT")

    # Seismic (if present)
    mag = norm.get("magnitude") or norm.get("mag")
    if mag is not None:
        if float(mag) >= 2.0:
            tokens.append("SEISMIC_ACT")
        else:
            tokens.append("SEISMIC_QUIET")

    # Pattern / FCI (pass-through)
    pattern = norm.get("pattern_name") or norm.get("pattern")
    if pattern:
        if "growth" in str(pattern).lower() or "active" in str(pattern).lower():
            tokens.append("GROWTH_ACT")
        elif "dormant" in str(pattern).lower():
            tokens.append("GROWTH_DORM")
        else:
            tokens.append("STIM_RESP")

    return tokens


def build_nmf(
    raw: Dict[str, Any],
    envelopes: Optional[List[TelemetryEnvelope]] = None,
    source_id: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> NatureMessageFrame:
    """
    Step 3: Build Nature Message Frame from raw data and envelopes.
    """
    tokens = raw_to_bio_tokens(raw)
    norm = normalize_raw(raw)
    structured = {
        "normalized": norm,
        "bio_tokens": [get_semantic(t) for t in tokens],
        "token_codes": tokens,
    }
    return NatureMessageFrame(
        bio_tokens=tokens,
        structured_output=structured,
        envelopes=envelopes or [],
        context=context or {},
        confidence=1.0,
        source_id=source_id,
    )


def translate(
    raw: Dict[str, Any],
    envelopes: Optional[List[TelemetryEnvelope]] = None,
    source_id: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> NatureMessageFrame:
    """
    Full translation: Raw -> Normalized -> Bio-Tokens -> NMF.
    """
    return build_nmf(raw, envelopes=envelopes, source_id=source_id, context=context)
