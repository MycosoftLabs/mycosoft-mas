"""
FCI (Fungal Computer Interface) API Router

Provides endpoints for:
- FCI device management
- Signal processing and pattern detection
- HPL program execution
- Bi-directional stimulation commands
- GFST pattern library access

This router acts as the orchestration layer between FCI firmware,
the Mycorrhizae Protocol, and MINDEX storage.

(c) 2026 Mycosoft Labs
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

# Try to import Mycorrhizae Protocol components
try:
    from mycorrhizae.protocol import (
        MycorrhizaeEnvelope,
        EnvelopeFactory,
        SemanticTranslator,
        translate_pattern,
    )
    from mycorrhizae.fci import (
        FCISignalProcessor,
        BiologicalPattern,
        ProcessedSignal,
    )
    HAS_MYCORRHIZAE = True
except ImportError:
    HAS_MYCORRHIZAE = False

router = APIRouter(prefix="/api/fci", tags=["FCI - Fungal Computer Interface"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class FCIDeviceStatus(BaseModel):
    device_id: str
    name: str
    probe_type: str
    status: str
    last_seen: Optional[datetime] = None
    firmware_version: Optional[str] = None
    channels: int = 2


class FCISignalData(BaseModel):
    device_id: str
    timestamp: datetime
    channels: List[Dict[str, Any]]
    environment: Optional[Dict[str, float]] = None


class FCIPatternResult(BaseModel):
    pattern_name: str
    category: str
    confidence: float
    semantic_meaning: Optional[str] = None
    implications: Optional[List[str]] = None
    recommended_actions: Optional[List[str]] = None


class FCIStimulusCommand(BaseModel):
    device_id: str
    waveform: str = "sine"  # sine, square, triangle, pulse
    frequency_hz: float = Field(ge=0.1, le=100.0)
    amplitude_mv: float = Field(ge=0.0, le=50.0)
    duration_ms: int = Field(ge=10, le=60000)
    channel: int = Field(ge=0, le=1, default=0)


class HPLProgramRequest(BaseModel):
    program: str
    device_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class GFSTPatternResponse(BaseModel):
    pattern_name: str
    category: str
    description: str
    frequency_min: float
    frequency_max: float
    amplitude_min: float
    amplitude_max: float
    physics_basis: str
    biology_basis: str


# ============================================================================
# IN-MEMORY STATE (would be replaced by proper storage in production)
# ============================================================================

_connected_devices: Dict[str, FCIDeviceStatus] = {}
_pending_commands: Dict[str, List[FCIStimulusCommand]] = {}


# ============================================================================
# GFST PATTERN LIBRARY
# ============================================================================

GFST_PATTERNS: List[GFSTPatternResponse] = [
    GFSTPatternResponse(
        pattern_name="baseline",
        category="metabolic",
        description="Normal resting state with minimal external stimulation",
        frequency_min=0.1,
        frequency_max=0.5,
        amplitude_min=0.1,
        amplitude_max=0.5,
        physics_basis="Low K+ channel activity, stable membrane potential ~-70mV",
        biology_basis="Maintenance metabolism, no active growth or stress",
    ),
    GFSTPatternResponse(
        pattern_name="active_growth",
        category="metabolic",
        description="Nutrient uptake and hyphal extension phase",
        frequency_min=0.5,
        frequency_max=2.0,
        amplitude_min=0.5,
        amplitude_max=2.0,
        physics_basis="Increased Ca2+ influx driving tip growth, H+ ATPase activity",
        biology_basis="Active colonization of substrate, carbon allocation to tips",
    ),
    GFSTPatternResponse(
        pattern_name="nutrient_seeking",
        category="metabolic",
        description="Increased frequency during active foraging",
        frequency_min=1.0,
        frequency_max=5.0,
        amplitude_min=1.0,
        amplitude_max=3.0,
        physics_basis="Oscillating Ca2+ waves guiding directional growth",
        biology_basis="Chemotropism toward nutrient gradients",
    ),
    GFSTPatternResponse(
        pattern_name="temperature_stress",
        category="environmental",
        description="Response to thermal changes outside optimal range",
        frequency_min=0.2,
        frequency_max=1.0,
        amplitude_min=1.0,
        amplitude_max=5.0,
        physics_basis="Membrane fluidity changes affecting ion channel kinetics",
        biology_basis="Heat shock protein expression, metabolic adjustment",
    ),
    GFSTPatternResponse(
        pattern_name="chemical_stress",
        category="environmental",
        description="Toxin, pollutant, or pH imbalance detection",
        frequency_min=2.0,
        frequency_max=10.0,
        amplitude_min=2.0,
        amplitude_max=8.0,
        physics_basis="Rapid membrane depolarization from toxin binding",
        biology_basis="Detoxification enzyme activation, efflux pump upregulation",
    ),
    GFSTPatternResponse(
        pattern_name="network_communication",
        category="communication",
        description="Long-range signaling between mycelial colonies",
        frequency_min=0.1,
        frequency_max=1.0,
        amplitude_min=0.5,
        amplitude_max=2.0,
        physics_basis="Propagating Ca2+ waves along hyphae at 0.5-50 mm/min",
        biology_basis="Resource allocation signals, warning transmission to connected plants",
    ),
    GFSTPatternResponse(
        pattern_name="action_potential",
        category="communication",
        description="Rapid spike signals, fast propagation",
        frequency_min=5.0,
        frequency_max=20.0,
        amplitude_min=5.0,
        amplitude_max=20.0,
        physics_basis="All-or-nothing depolarization via voltage-gated channels",
        biology_basis="Rapid response coordination, possibly learning/memory",
    ),
    GFSTPatternResponse(
        pattern_name="seismic_precursor",
        category="predictive",
        description="Ultra-low frequency preceding geological events",
        frequency_min=0.01,
        frequency_max=0.1,
        amplitude_min=0.2,
        amplitude_max=1.0,
        physics_basis="Piezoelectric response to subsurface pressure waves",
        biology_basis="Unknown sensitivity mechanism, possibly electrochemical gradient detection",
    ),
    GFSTPatternResponse(
        pattern_name="defense_activation",
        category="defensive",
        description="Pathogen or predator detection response",
        frequency_min=2.0,
        frequency_max=8.0,
        amplitude_min=2.0,
        amplitude_max=6.0,
        physics_basis="Oxidative burst generating ion flux",
        biology_basis="Secondary metabolite production, cell wall reinforcement",
    ),
    GFSTPatternResponse(
        pattern_name="sporulation_initiation",
        category="reproductive",
        description="Pre-reproductive signaling cascade",
        frequency_min=0.5,
        frequency_max=2.0,
        amplitude_min=1.0,
        amplitude_max=3.0,
        physics_basis="Ca2+ signaling cascade activating sporulation genes",
        biology_basis="Light, nutrient, or density-triggered reproduction",
    ),
]


# ============================================================================
# DEVICE MANAGEMENT ENDPOINTS
# ============================================================================


@router.get("/devices", response_model=List[FCIDeviceStatus])
async def list_fci_devices(
    status: Optional[str] = None,
    probe_type: Optional[str] = None,
):
    """List all connected FCI devices."""
    devices = list(_connected_devices.values())
    
    if status:
        devices = [d for d in devices if d.status == status]
    if probe_type:
        devices = [d for d in devices if d.probe_type == probe_type]
    
    return devices


@router.post("/devices/register", response_model=FCIDeviceStatus)
async def register_fci_device(
    device_id: str,
    name: str,
    probe_type: str = "copper_steel_agar",
    firmware_version: str = "1.0.0",
    channels: int = 2,
):
    """Register a new FCI device."""
    device = FCIDeviceStatus(
        device_id=device_id,
        name=name,
        probe_type=probe_type,
        status="online",
        last_seen=datetime.now(timezone.utc),
        firmware_version=firmware_version,
        channels=channels,
    )
    _connected_devices[device_id] = device
    return device


@router.post("/devices/{device_id}/heartbeat")
async def device_heartbeat(device_id: str):
    """Update device last-seen timestamp."""
    if device_id not in _connected_devices:
        raise HTTPException(status_code=404, detail="Device not registered")
    
    _connected_devices[device_id].last_seen = datetime.now(timezone.utc)
    _connected_devices[device_id].status = "online"
    
    # Return any pending commands
    commands = _pending_commands.pop(device_id, [])
    return {"status": "ok", "pending_commands": [c.dict() for c in commands]}


# ============================================================================
# SIGNAL PROCESSING ENDPOINTS
# ============================================================================


@router.post("/signals/process", response_model=FCIPatternResult)
async def process_signal(data: FCISignalData, background_tasks: BackgroundTasks):
    """
    Process incoming bioelectric signal data and detect patterns.
    
    This endpoint:
    1. Receives raw signal features from FCI firmware
    2. Applies GFST pattern matching
    3. Returns semantic interpretation
    4. Optionally stores to MINDEX in background
    """
    # Extract channel data
    if not data.channels:
        raise HTTPException(status_code=400, detail="No channel data provided")
    
    # Use first channel for primary analysis
    channel = data.channels[0]
    
    # Match against GFST patterns
    detected_pattern = "baseline"
    confidence = 0.5
    
    dominant_freq = channel.get("dominant_frequency", 0.3)
    amplitude_mv = channel.get("amplitude_mv", 0.5)
    
    # Simple pattern matching based on frequency and amplitude
    for pattern in GFST_PATTERNS:
        if (pattern.frequency_min <= dominant_freq <= pattern.frequency_max and
            pattern.amplitude_min <= amplitude_mv <= pattern.amplitude_max):
            detected_pattern = pattern.pattern_name
            # Calculate confidence based on how well it matches
            freq_match = 1 - abs(
                (dominant_freq - (pattern.frequency_min + pattern.frequency_max) / 2) /
                ((pattern.frequency_max - pattern.frequency_min) / 2 + 0.01)
            )
            amp_match = 1 - abs(
                (amplitude_mv - (pattern.amplitude_min + pattern.amplitude_max) / 2) /
                ((pattern.amplitude_max - pattern.amplitude_min) / 2 + 0.01)
            )
            confidence = max(0.4, min(0.95, (freq_match + amp_match) / 2))
            break
    
    # Generate semantic interpretation
    semantic_mapping = {
        "baseline": ("Normal metabolic activity", ["Mycelium is stable"], ["Continue monitoring"]),
        "active_growth": ("Active nutrient uptake detected", ["Healthy growth phase", "Good substrate colonization"], ["Maintain optimal conditions"]),
        "nutrient_seeking": ("Foraging behavior active", ["May need substrate enrichment"], ["Consider adding nutrients"]),
        "temperature_stress": ("Thermal stress detected", ["Temperature outside optimal range"], ["Check heating/cooling", "Adjust environmental controls"]),
        "chemical_stress": ("Chemical stressor detected", ["Possible toxin or pH issue"], ["Check substrate chemistry", "Monitor air quality"]),
        "network_communication": ("Inter-colony signaling", ["Mycorrhizal network active"], ["Monitor connected organisms"]),
        "action_potential": ("Rapid spike detected", ["Strong signal event"], ["Investigate trigger"]),
        "seismic_precursor": ("Ultra-low frequency detected", ["Possible geological precursor"], ["Cross-reference with seismic data", "Alert monitoring systems"]),
        "defense_activation": ("Defense response active", ["Pathogen or predator detected"], ["Inspect for contamination"]),
        "sporulation_initiation": ("Reproductive signaling", ["Sporulation may begin"], ["Prepare for spore collection if desired"]),
    }
    
    meaning, implications, actions = semantic_mapping.get(
        detected_pattern, 
        ("Unknown pattern", ["Requires analysis"], ["Log for review"])
    )
    
    result = FCIPatternResult(
        pattern_name=detected_pattern,
        category=next(
            (p.category for p in GFST_PATTERNS if p.pattern_name == detected_pattern),
            "unknown"
        ),
        confidence=confidence,
        semantic_meaning=meaning,
        implications=implications,
        recommended_actions=actions,
    )
    
    # Background task: store to MINDEX (would be implemented)
    # background_tasks.add_task(store_pattern_to_mindex, data.device_id, result)
    
    return result


# ============================================================================
# STIMULATION ENDPOINTS
# ============================================================================


@router.post("/stimulate", status_code=202)
async def send_stimulus(command: FCIStimulusCommand):
    """
    Send a stimulation command to an FCI device.
    
    The command is queued and delivered on the device's next heartbeat.
    """
    device_id = command.device_id
    
    if device_id not in _connected_devices:
        raise HTTPException(status_code=404, detail="Device not registered")
    
    # Validate safety limits
    if command.amplitude_mv > 20.0:
        raise HTTPException(
            status_code=400, 
            detail="Amplitude exceeds safety limit of 20mV"
        )
    
    if command.duration_ms > 10000:
        raise HTTPException(
            status_code=400,
            detail="Duration exceeds safety limit of 10 seconds"
        )
    
    # Queue the command
    if device_id not in _pending_commands:
        _pending_commands[device_id] = []
    _pending_commands[device_id].append(command)
    
    return {
        "status": "queued",
        "command_id": str(uuid4()),
        "message": f"Stimulus command queued for device {device_id}",
    }


# ============================================================================
# GFST PATTERN LIBRARY ENDPOINTS
# ============================================================================


@router.get("/gfst/patterns", response_model=List[GFSTPatternResponse])
async def list_gfst_patterns(category: Optional[str] = None):
    """Get the GFST pattern library."""
    patterns = GFST_PATTERNS
    
    if category:
        patterns = [p for p in patterns if p.category == category]
    
    return patterns


@router.get("/gfst/patterns/{pattern_name}", response_model=GFSTPatternResponse)
async def get_gfst_pattern(pattern_name: str):
    """Get a specific GFST pattern by name."""
    for pattern in GFST_PATTERNS:
        if pattern.pattern_name == pattern_name:
            return pattern
    
    raise HTTPException(status_code=404, detail=f"Pattern '{pattern_name}' not found")


# ============================================================================
# HPL EXECUTION ENDPOINTS
# ============================================================================


@router.post("/hpl/execute")
async def execute_hpl_program(request: HPLProgramRequest):
    """
    Execute an HPL (Hypha Programming Language) program.
    
    This endpoint parses and executes HPL code for interacting with FCI devices.
    """
    if not HAS_MYCORRHIZAE:
        raise HTTPException(
            status_code=503,
            detail="Mycorrhizae Protocol not installed"
        )
    
    # For now, return a stub response
    # Full implementation would use the HPL interpreter
    return {
        "status": "executed",
        "program_hash": str(uuid4())[:8],
        "result": {
            "message": "HPL execution not yet fully implemented",
            "program_preview": request.program[:100] + "..." if len(request.program) > 100 else request.program,
        },
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================


@router.get("/health")
async def health_check():
    """Check FCI subsystem health."""
    return {
        "status": "healthy",
        "connected_devices": len(_connected_devices),
        "pending_commands": sum(len(cmds) for cmds in _pending_commands.values()),
        "gfst_patterns_loaded": len(GFST_PATTERNS),
        "mycorrhizae_available": HAS_MYCORRHIZAE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
