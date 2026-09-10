"""Observation and forecast envelopes from the FormSpace–NLM handoff (Section 11)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def _parse_dt(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class ObservationEnvelope(BaseModel):
    schema_version: str = "formspace.observation/v1"
    observation_id: str = Field(default_factory=lambda: f"obs-{uuid4()}")
    subject_id: str
    source_id: str
    root_evidence_id: str
    event_time: datetime
    received_at: datetime
    available_at: datetime
    recorded_at: Optional[datetime] = None
    chart_id: str
    chart_version: str
    values: Dict[str, Any]
    units: Dict[str, str] = Field(default_factory=dict)
    observed_mask: Dict[str, bool] = Field(default_factory=dict)
    quality: Dict[str, Any] = Field(default_factory=dict)
    origin: str = "SYNTHETIC"
    provenance: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_times(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        for key in ("event_time", "received_at", "available_at", "recorded_at"):
            if data.get(key):
                data[key] = _parse_dt(data[key])
        return data


class ForecastEnvelope(BaseModel):
    schema_version: str = "formspace.forecast/v1"
    forecast_id: str = Field(default_factory=lambda: f"fcst-{uuid4()}")
    run_id: str = Field(default_factory=lambda: f"run-{uuid4()}")
    subject_id: str
    episode_id: str
    issued_at: datetime
    input_cutoff_at: datetime
    task_id: str = "task12"
    event_definition_id: str
    horizon_seconds: List[int] = Field(default_factory=list)
    hazard_probabilities: Optional[List[Optional[float]]] = None
    cumulative_probabilities: Optional[List[Optional[float]]] = None
    support_status: str = "UNSUPPORTED"
    reasons: List[str] = Field(default_factory=list)
    uncertainty: Dict[str, Any] = Field(default_factory=dict)
    input_observation_ids: List[str] = Field(default_factory=list)
    root_evidence_ids: List[str] = Field(default_factory=list)
    upstream_prediction_ids: List[str] = Field(default_factory=list)
    model_id: str = "nlm-forecast"
    model_hash: Optional[str] = None
    encoder_version: Optional[str] = None
    chart_id: str
    chart_version: str
    filter_version: Optional[str] = None
    calibration_id: Optional[str] = None
    criteria_hash: Optional[str] = None
    origin: str = "DERIVED"
    runtime_identity: str = "mas-formspace-stage-b"
    input_hash: Optional[str] = None
    artifact_hashes: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_times(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        for key in ("issued_at", "input_cutoff_at"):
            if data.get(key):
                data[key] = _parse_dt(data[key])
        return data

    @model_validator(mode="after")
    def _cutoff_before_issue(self) -> "ForecastEnvelope":
        if self.input_cutoff_at > self.issued_at:
            raise ValueError("input_cutoff_at must be <= issued_at")
        if self.support_status != "SUPPORTED":
            self.hazard_probabilities = None
            self.cumulative_probabilities = None
        return self
