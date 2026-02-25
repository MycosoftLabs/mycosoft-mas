"""
NLM Bio-Token Vocabulary - Micro-Speak for Nature Signals

Bio-tokens are the semantic vocabulary for translating raw sensor data
into nature-oriented "micro-speak" tokens consumed by NLM and World Model.

Created: February 25, 2026
"""

from typing import Dict, List, Set

# ---------------------------------------------------------------------------
# Bio-Token Vocabulary - Micro-speak for nature signals
# ---------------------------------------------------------------------------

BIO_TOKEN_VOCABULARY: Dict[str, str] = {
    # Temperature
    "TEMP_OPT": "temperature_optimal",  # 20-28°C
    "TEMP_STRESS_HI": "temperature_stress_high",  # >35°C
    "TEMP_STRESS_LO": "temperature_stress_low",  # <15°C
    "TEMP_COOL": "temperature_cool",
    "TEMP_WARM": "temperature_warm",
    # Humidity
    "HUM_HIGH": "humidity_high",  # >80%
    "HUM_LOW": "humidity_low",  # <40%
    "HUM_OPT": "humidity_optimal",
    # Light
    "LIGHT_LOW": "light_low",
    "LIGHT_OPT": "light_optimal",
    "LIGHT_HIGH": "light_high",
    "LIGHT_DAWN": "light_dawn",
    "LIGHT_DUSK": "light_dusk",
    # Biological / FCI
    "GROWTH_ACT": "growth_active",
    "GROWTH_DORM": "growth_dormant",
    "GROWTH_SPIKE": "growth_spike",
    "STIM_RESP": "stimulus_response",
    "BIO_QUIESC": "bioelectric_quiescent",
    "BIO_ACTIVE": "bioelectric_active",
    # Seismic
    "SEISMIC_PRE": "seismic_precursor",
    "SEISMIC_ACT": "seismic_active",
    "SEISMIC_QUIET": "seismic_quiet",
    "ULF_DETECT": "ulf_detected",
    # Atmospheric
    "CO2_HIGH": "co2_high",
    "CO2_OPT": "co2_optimal",
    "VOC_ELEV": "voc_elevated",
    "PRESS_DROP": "pressure_dropping",
    "PRESS_STABLE": "pressure_stable",
    # Substrate / Resource
    "MOIST_OPT": "moisture_optimal",
    "MOIST_DRY": "moisture_dry",
    "MOIST_SAT": "moisture_saturated",
    "PH_ACID": "ph_acidic",
    "PH_NEUTRAL": "ph_neutral",
    "PH_ALK": "ph_alkaline",
    "NUTRIENT_FLOW": "nutrient_flow_detected",
    "SUBSTRATE_STABLE": "substrate_stable",
    # Early warning / Prediction
    "FRUITING_LIKELY": "fruiting_likely",
    "FRUITING_IMM": "fruiting_imminent",
    "STRESS_ALERT": "stress_alert",
    "ANOMALY": "anomaly_detected",
}


# Reverse mapping: human-readable -> token code
BIO_TOKEN_REVERSE: Dict[str, str] = {v: k for k, v in BIO_TOKEN_VOCABULARY.items()}


def get_token_code(semantic: str) -> str:
    """Get token code (e.g. TEMP_OPT) from semantic label (e.g. temperature_optimal)."""
    return BIO_TOKEN_REVERSE.get(semantic, semantic)


def get_semantic(token_code: str) -> str:
    """Get semantic label from token code."""
    return BIO_TOKEN_VOCABULARY.get(token_code, token_code)


def all_tokens() -> List[str]:
    """Return list of all token codes."""
    return list(BIO_TOKEN_VOCABULARY.keys())


def all_semantics() -> Set[str]:
    """Return set of all semantic labels."""
    return set(BIO_TOKEN_VOCABULARY.values())
