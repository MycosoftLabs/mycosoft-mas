"""
Quality Scorer - February 6, 2026

Calculates data quality scores for incoming events.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


@dataclass
class QualityFactors:
    """Factors affecting quality score."""
    recency: float = 1.0        # How recent is the data
    completeness: float = 1.0   # Are all required fields present
    source_trust: float = 1.0   # Trustworthiness of source
    consistency: float = 1.0    # Consistency with prior data
    precision: float = 1.0      # Precision of measurements


SOURCE_TRUST_SCORES: Dict[str, float] = {
    # Official sources
    "opensky": 0.95,
    "norad": 0.99,
    "usgs": 0.98,
    "noaa": 0.97,
    "gbif": 0.90,
    "inaturalist": 0.85,
    
    # Commercial sources
    "marinetraffic": 0.92,
    "flightaware": 0.93,
    "ais": 0.90,
    
    # Model outputs
    "earth2": 0.88,
    "prediction": 0.75,
    
    # User/crowd sources
    "user_report": 0.70,
    "crowd_source": 0.65,
    
    # Default
    "unknown": 0.50,
}

REQUIRED_FIELDS_BY_TYPE: Dict[str, list] = {
    "aircraft": ["lat", "lng", "callsign", "altitude"],
    "vessel": ["lat", "lng", "mmsi", "ship_type"],
    "satellite": ["lat", "lng", "norad_id", "altitude"],
    "earthquake": ["lat", "lng", "magnitude", "depth"],
    "wildlife": ["lat", "lng", "species"],
    "weather": ["lat", "lng", "temperature"],
}


def calculate_recency_score(
    timestamp: datetime,
    max_age_hours: float = 24.0
) -> float:
    """
    Calculate recency score (1.0 = fresh, 0.0 = stale).
    """
    age = datetime.utcnow() - timestamp
    age_hours = age.total_seconds() / 3600
    
    if age_hours <= 0:
        return 1.0
    if age_hours >= max_age_hours:
        return 0.1  # Minimum score for old data
    
    # Exponential decay
    return 0.9 * (0.5 ** (age_hours / (max_age_hours / 4))) + 0.1


def calculate_completeness_score(
    data: Dict[str, Any],
    entity_type: str
) -> float:
    """
    Calculate completeness score based on required fields.
    """
    required = REQUIRED_FIELDS_BY_TYPE.get(entity_type, ["lat", "lng"])
    
    if not required:
        return 1.0
    
    present = sum(1 for f in required if f in data and data[f] is not None)
    return present / len(required)


def get_source_trust(source: str) -> float:
    """
    Get trust score for data source.
    """
    return SOURCE_TRUST_SCORES.get(source.lower(), SOURCE_TRUST_SCORES["unknown"])


def calculate_precision_score(
    lat: Optional[float],
    lng: Optional[float],
    entity_type: str
) -> float:
    """
    Estimate precision based on coordinate format.
    """
    if lat is None or lng is None:
        return 0.5
    
    # Check decimal places
    lat_str = str(lat)
    lng_str = str(lng)
    
    lat_decimals = len(lat_str.split('.')[-1]) if '.' in lat_str else 0
    lng_decimals = len(lng_str.split('.')[-1]) if '.' in lng_str else 0
    
    avg_decimals = (lat_decimals + lng_decimals) / 2
    
    # More decimals = higher precision
    if avg_decimals >= 6:
        return 1.0
    elif avg_decimals >= 4:
        return 0.9
    elif avg_decimals >= 2:
        return 0.7
    else:
        return 0.5


def calculate_quality_score(
    data: Dict[str, Any],
    entity_type: str,
    source: str,
    timestamp: Optional[datetime] = None
) -> float:
    """
    Calculate overall quality score for an event.
    
    Returns:
        Float between 0.0 and 1.0
    """
    timestamp = timestamp or datetime.utcnow()
    
    factors = QualityFactors(
        recency=calculate_recency_score(timestamp),
        completeness=calculate_completeness_score(data, entity_type),
        source_trust=get_source_trust(source),
        precision=calculate_precision_score(
            data.get("lat"), data.get("lng"), entity_type
        ),
        consistency=1.0,  # Would need historical data to calculate
    )
    
    # Weighted average
    weights = {
        "recency": 0.20,
        "completeness": 0.25,
        "source_trust": 0.25,
        "precision": 0.15,
        "consistency": 0.15,
    }
    
    score = (
        factors.recency * weights["recency"] +
        factors.completeness * weights["completeness"] +
        factors.source_trust * weights["source_trust"] +
        factors.precision * weights["precision"] +
        factors.consistency * weights["consistency"]
    )
    
    return round(score, 3)