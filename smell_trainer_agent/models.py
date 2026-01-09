"""Pydantic models for Smell Trainer Agent API"""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from enum import Enum


class BlobStatus(str, Enum):
    """Status of a BSEC selectivity blob"""
    TESTING = "testing"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class CreateSessionRequest(BaseModel):
    """Request to create a new training session"""
    port: str = Field(..., description="Serial port, e.g. COM7 or /dev/ttyACM0")
    baud: int = Field(115200, description="Serial baud rate")
    created_by: Optional[str] = Field(None, description="User email/handle")
    device_id: Optional[str] = Field(None, description="MycoBrain device ID (if available)")
    notes: Optional[str] = None


class CreateSessionResponse(BaseModel):
    """Response after creating a training session"""
    session_id: str
    data_dir: str
    sensor_status: Dict[str, bool]


class RecordRequest(BaseModel):
    """Request to start recording a specimen"""
    label: str = Field(..., description="Class label, e.g. clean_air_baseline, pleurotus_ostreatus")
    duration_sec: int = Field(60, ge=5, le=3600)
    interval_sec: float = Field(1.0, ge=0.2, le=10.0)
    description: Optional[str] = None


class RecordStatus(BaseModel):
    """Current recording status"""
    state: str  # idle|recording|completed|error
    current_label: Optional[str] = None
    started_at: Optional[str] = None
    elapsed_sec: float = 0.0
    sample_count: int = 0
    last_error: Optional[str] = None


class LatestReading(BaseModel):
    """Most recent sensor reading"""
    timestamp: str
    data: Dict[str, Any]


class BlobUploadResponse(BaseModel):
    """Response after uploading a BSEC blob"""
    blob_id: str
    blob_hash: str
    status: str


class SessionInfo(BaseModel):
    """Information about a training session"""
    session_id: str
    port: str
    created_at: str
    created_by: Optional[str] = None
    device_id: Optional[str] = None
    notes: Optional[str] = None
    specimens: List[Dict[str, Any]] = []
    total_samples: int = 0
    status: str = "active"


class SmellSignatureInfo(BaseModel):
    """Information about a smell signature"""
    id: str
    name: str
    category: str
    subcategory: str
    description: str
    bsec_class_id: int
    training_samples: int = 0
    confidence_threshold: float = 0.75
    current_blob_id: Optional[str] = None


class BlobInfo(BaseModel):
    """Information about a BSEC blob"""
    id: str
    name: str
    blob_hash: str
    status: str
    class_labels: List[str]
    training_method: str
    created_at: str
    created_by: Optional[str] = None
    bsec_version: str
    sensor_model: str


class QAStatus(BaseModel):
    """Quality assurance check status"""
    sensors_online: bool
    sensor_count: int
    required_sensor_count: int = 2
    minimum_samples: int = 50
    current_samples: int = 0
    can_export: bool = False
    issues: List[str] = []
