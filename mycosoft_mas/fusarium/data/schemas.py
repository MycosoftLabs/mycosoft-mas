from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class GeoPoint(BaseModel):
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    depth_m: Optional[float] = None


class Assessment(BaseModel):
    assessment_id: UUID = Field(default_factory=uuid4)
    domain: str
    classification: str
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    recommendation: Optional[str] = None
    entities: List[UUID] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    observed_at: datetime = Field(default_factory=datetime.utcnow)
    merkle_hash: Optional[str] = None


class Prediction(BaseModel):
    prediction_id: UUID = Field(default_factory=uuid4)
    domain: str
    prediction_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    result: Dict[str, Any] = Field(default_factory=dict)
    valid_until: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntelligenceProduct(BaseModel):
    product_id: UUID = Field(default_factory=uuid4)
    title: str
    body: str
    domain: str = "multi-domain"
    classification: str = "CUI"
    confidence: float = Field(ge=0.0, le=1.0)
    sources: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list)
    stix_bundle: Optional[Dict[str, Any]] = None
