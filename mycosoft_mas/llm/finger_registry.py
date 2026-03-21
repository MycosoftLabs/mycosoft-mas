"""
Finger Registry for MYCA Opposable Thumb architecture.

Maps external AI "fingers" to domains, capabilities, and trust/cost metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class FingerProfile:
    """Metadata for a single external AI finger."""

    finger_id: str
    display_name: str
    domain: str
    providers: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    data_boundary: List[str] = field(default_factory=list)
    cost_tier: str = "medium"
    trust_weight: float = 0.7
    health_score: float = 1.0


class FingerRegistry:
    """
    Registry of known AI fingers and their operating constraints.

    This is intentionally a policy/config layer (not hardcoded model behavior).
    """

    def __init__(self) -> None:
        self._fingers: Dict[str, FingerProfile] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        self.register(
            FingerProfile(
                finger_id="amazon_commerce",
                display_name="Amazon Commerce Finger",
                domain="commerce",
                providers=["amazon", "aws", "bedrock"],
                capabilities=["catalog_reasoning", "fulfillment_planning", "pricing_assist"],
                data_boundary=["aggregated_context", "non_pii", "derived_signals_only"],
                cost_tier="medium",
                trust_weight=0.75,
            )
        )
        self.register(
            FingerProfile(
                finger_id="web_cognition",
                display_name="Web Cognition Finger",
                domain="web",
                providers=["google", "openai", "anthropic"],
                capabilities=["reasoning", "search_summarization", "code_assist"],
                data_boundary=["redacted_prompt", "derived_context", "no_raw_sensor_stream"],
                cost_tier="medium",
                trust_weight=0.8,
            )
        )
        self.register(
            FingerProfile(
                finger_id="mobility_infra",
                display_name="Mobility/Infrastructure Finger",
                domain="mobility",
                providers=["tesla", "xai"],
                capabilities=["spatiotemporal_reasoning", "infrastructure_forecast"],
                data_boundary=["aggregate_telemetry_only", "no_device_identifiers"],
                cost_tier="high",
                trust_weight=0.65,
            )
        )
        self.register(
            FingerProfile(
                finger_id="device_experience",
                display_name="Device Experience Finger",
                domain="device",
                providers=["apple"],
                capabilities=["device_assistance", "private_inference_handoff"],
                data_boundary=["privacy_preserving_summary", "no_raw_sensor_payload"],
                cost_tier="medium",
                trust_weight=0.7,
            )
        )

    def register(self, profile: FingerProfile) -> None:
        self._fingers[profile.finger_id] = profile

    def get(self, finger_id: str) -> Optional[FingerProfile]:
        return self._fingers.get(finger_id)

    def list_all(self) -> List[FingerProfile]:
        return list(self._fingers.values())

    def list_by_domain(self, domain: str) -> List[FingerProfile]:
        domain_l = domain.lower()
        return [f for f in self._fingers.values() if f.domain.lower() == domain_l]
