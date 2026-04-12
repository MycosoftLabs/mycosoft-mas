# TAC-O CURSOR IMPLEMENTATION PLAN
## Mycosoft Systems Integration for NUWC Tactical Oceanography
### Feed this entire file into Cursor as the master plan

---

## MISSION CONTEXT

Mycosoft is subcontracting under Zeetachec LLC for the NUWC TAC-O CSO (N66604-26-9-A00X).
We provide AI/ML signal classification, data fusion, decision support, and NIST 800-171 compliance.
Zeetachec provides underwater acoustic/magnetic sensors (Zeeta Fuze, Buoy, RF Receiver).

**Goal**: Adapt FUSARIUM, NLM, MINDEX, MYCA, MycoBrain, CREP, and Worldview for maritime tactical oceanography.

---

## REPO MAP

| Repo | Path | Role in TAC-O |
|---|---|---|
| `mycosoft-mas` | MycosoftLabs/mycosoft-mas | MAS orchestrator, agents, FUSARIUM API, CREP streaming, voice, decision support |
| `NLM` | MycosoftLabs/NLM | Foundation model: acoustic classification, anomaly detection, prediction heads |
| `mindex` | MycosoftLabs/mindex | Data platform: maritime schemas, ETL pipelines, vector search, Worldview API |
| `mycobrain` | MycosoftLabs/mycobrain | Edge firmware: signal processing, acoustic modem, Jetson integration |
| `website` | MycosoftLabs/website | CREP dashboard, FUSARIUM dashboard, defense pages, compliance UI |

---

## EXECUTION LANES

There are 7 parallel execution lanes. Each lane targets specific repos and files.
Agents should work lane-by-lane. Lanes 1-4 can run in parallel. Lanes 5-7 depend on 1-4.

---

## LANE 1: NLM — ACOUSTIC DOMAIN ADAPTATION
**Repo**: `MycosoftLabs/NLM`
**Agent**: Use `backend-dev` or custom AI/ML agent
**Priority**: CRITICAL — this is the core AI value proposition

### Task 1.1: Add Maritime Fingerprint Types
**File**: `nlm/core/fingerprints.py`
**Action**: Add new fingerprint dataclasses alongside existing ones

```python
# ADD these new types to fingerprints.py

@dataclass
class HydroacousticFingerprint:
    """Underwater acoustic signature for maritime classification."""
    frequency_bands: List[Tuple[float, float]]      # Hz ranges
    spectral_energy: List[float]                      # energy per band
    harmonics: List[float]                            # harmonic frequencies
    modulation_rate: Optional[float]                  # blade/propeller rate
    cavitation_index: Optional[float]                 # cavitation noise indicator
    broadband_level: float                            # dB re 1μPa
    narrowband_peaks: List[Tuple[float, float]]       # (freq_Hz, level_dB)
    waveform_digest: bytes                            # compressed waveform hash
    source_depth_estimate: Optional[float]            # meters
    ambient_noise_level: float                        # dB re 1μPa

@dataclass
class MagneticAnomalyFingerprint:
    """Magnetic field anomaly for ferrous object detection."""
    Bx: float                   # nT, magnetic field x-component
    By: float                   # nT, magnetic field y-component
    Bz: float                   # nT, magnetic field z-component
    total_field: float          # nT, magnitude
    inclination: float          # degrees
    declination: float          # degrees
    anomaly_magnitude: float    # nT, deviation from baseline
    gradient_x: float           # nT/m
    gradient_y: float           # nT/m
    dipole_moment_estimate: Optional[float]  # A·m²

@dataclass
class OceanEnvironmentFingerprint:
    """Environmental state for sonar performance prediction."""
    sound_speed_profile: List[Tuple[float, float]]  # (depth_m, speed_m/s)
    thermocline_depth: Optional[float]               # meters
    sea_surface_temp: float                          # °C
    salinity: float                                  # PSU
    sea_state: int                                   # 0-9 Beaufort
    current_speed: float                             # m/s
    current_direction: float                         # degrees
    bottom_depth: float                              # meters
    bottom_type: str                                 # sand/mud/rock/coral
    ambient_noise_spectrum: List[Tuple[float, float]] # (freq_Hz, level_dB)
```

### Task 1.2: Extend Spectral Sensory Encoder for Maritime
**File**: `nlm/model/encoders.py`
**Action**: Add `hydroacoustic_enc` and `magnetic_anomaly_enc` sub-encoders to `SpectralSensoryEncoder`

Find the existing `acoustic_enc` in `SpectralSensoryEncoder.__init__` and add parallel encoders:

```python
# In SpectralSensoryEncoder.__init__, after acoustic_enc:
self.hydroacoustic_enc = nn.Sequential(
    nn.Linear(hydroacoustic_dim, d_model),
    nn.GELU(),
    nn.Linear(d_model, d_model),
    nn.LayerNorm(d_model)
)
self.magnetic_anomaly_enc = nn.Sequential(
    nn.Linear(magnetic_anomaly_dim, d_model),
    nn.GELU(),
    nn.Linear(d_model, d_model),
    nn.LayerNorm(d_model)
)
self.ocean_environment_enc = nn.Sequential(
    nn.Linear(ocean_env_dim, d_model),
    nn.GELU(),
    nn.Linear(d_model, d_model),
    nn.LayerNorm(d_model)
)
```

### Task 1.3: Add Maritime Prediction Heads
**File**: `nlm/model/heads.py`
**Action**: Add 4 new heads after existing `AnomalyDetectionHead`

```python
class UnderwaterTargetClassificationHead(nn.Module):
    """Classify acoustic contacts into target categories."""
    CATEGORIES = [
        'submarine', 'surface_vessel', 'torpedo', 'uuv',
        'mine', 'marine_mammal', 'fish_school', 'seismic',
        'weather_noise', 'shipping_noise', 'ambient', 'unknown'
    ]
    def __init__(self, d_model: int, num_classes: int = 12):
        super().__init__()
        self.classifier = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(d_model // 2, num_classes)
        )
        self.confidence = nn.Linear(d_model, 1)

    def forward(self, fused_state):
        logits = self.classifier(fused_state)
        conf = torch.sigmoid(self.confidence(fused_state))
        return {'logits': logits, 'confidence': conf}


class SonarPerformancePredictionHead(nn.Module):
    """Predict sonar detection ranges given environmental state."""
    def __init__(self, d_model: int):
        super().__init__()
        self.predictor = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Linear(d_model // 2, 4)  # [min_range, max_range, optimal_depth, figure_of_merit]
        )

    def forward(self, fused_state):
        return self.predictor(fused_state)


class TacticalRecommendationHead(nn.Module):
    """Generate tactical recommendation embeddings for operator decision support."""
    ACTIONS = [
        'reposition_sensors', 'increase_gain', 'decrease_gain',
        'deploy_deep', 'deploy_shallow', 'activate_magnetic',
        'classify_contact', 'alert_operator', 'log_and_continue',
        'request_verification'
    ]
    def __init__(self, d_model: int, num_actions: int = 10):
        super().__init__()
        self.action_head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Linear(d_model // 2, num_actions)
        )
        self.urgency = nn.Linear(d_model, 1)

    def forward(self, fused_state):
        action_logits = self.action_head(fused_state)
        urgency = torch.sigmoid(self.urgency(fused_state))
        return {'actions': action_logits, 'urgency': urgency}


class MarineMammalFilterHead(nn.Module):
    """AVANI ecological safety: identify marine wildlife to prevent false positives."""
    def __init__(self, d_model: int):
        super().__init__()
        self.filter = nn.Sequential(
            nn.Linear(d_model, d_model // 4),
            nn.GELU(),
            nn.Linear(d_model // 4, 1)
        )

    def forward(self, fused_state):
        # Score > 0.5 = likely marine mammal, gate threat classification
        return torch.sigmoid(self.filter(fused_state))
```

### Task 1.4: Register Maritime Heads in NLM Model
**File**: `nlm/model/nlm_model.py`
**Action**: Add maritime heads to `NLMFungaTransformer` alongside existing heads

In `__init__`:
```python
self.underwater_target_head = UnderwaterTargetClassificationHead(config.d_model)
self.sonar_performance_head = SonarPerformancePredictionHead(config.d_model)
self.tactical_recommendation_head = TacticalRecommendationHead(config.d_model)
self.marine_mammal_filter = MarineMammalFilterHead(config.d_model)
```

In `forward`, after existing head outputs:
```python
outputs['underwater_target'] = self.underwater_target_head(fused)
outputs['sonar_performance'] = self.sonar_performance_head(fused)
outputs['tactical_recommendation'] = self.tactical_recommendation_head(fused)
outputs['marine_mammal_score'] = self.marine_mammal_filter(fused)
```

### Task 1.5: Add Hydroacoustic Preconditioner
**File**: `nlm/data/preconditioner.py`
**Action**: Add deterministic physics transforms for underwater acoustics

```python
class HydroacousticPreconditioner:
    """Deterministic physics transforms for underwater sound propagation."""

    @staticmethod
    def compute_sound_speed(temp_c: float, salinity_psu: float, depth_m: float) -> float:
        """Mackenzie equation for sound speed in seawater."""
        c = (1448.96 + 4.591 * temp_c - 0.05304 * temp_c**2
             + 2.374e-4 * temp_c**3 + 1.340 * (salinity_psu - 35)
             + 1.630e-2 * depth_m + 1.675e-7 * depth_m**2
             - 1.025e-2 * temp_c * (salinity_psu - 35)
             - 7.139e-13 * temp_c * depth_m**3)
        return c

    @staticmethod
    def transmission_loss(range_m: float, frequency_hz: float, depth_m: float) -> float:
        """Spherical spreading + absorption loss in dB."""
        spreading = 20 * math.log10(max(range_m, 1))
        # Thorp absorption coefficient (dB/km)
        f_khz = frequency_hz / 1000
        alpha = (0.11 * f_khz**2 / (1 + f_khz**2)
                + 44 * f_khz**2 / (4100 + f_khz**2)
                + 2.75e-4 * f_khz**2 + 0.003)
        absorption = alpha * range_m / 1000
        return spreading + absorption

    @staticmethod
    def ray_trace_simple(ssp: List[Tuple[float, float]], source_depth: float,
                         initial_angle: float, max_range: float) -> List[Tuple[float, float]]:
        """Simple ray tracing through sound speed profile.
        Returns list of (range_m, depth_m) points."""
        # Snell's law: cos(theta)/c = constant
        path = [(0.0, source_depth)]
        # ... implement layer-by-layer ray trace using Snell's law
        return path

    @staticmethod
    def calibrate_magnetometer(raw_bx: float, raw_by: float, raw_bz: float,
                                hard_iron: Tuple[float, float, float],
                                soft_iron: np.ndarray) -> Tuple[float, float, float]:
        """Hard/soft iron calibration for magnetic sensor data."""
        raw = np.array([raw_bx - hard_iron[0],
                        raw_by - hard_iron[1],
                        raw_bz - hard_iron[2]])
        calibrated = soft_iron @ raw
        return tuple(calibrated)
```

### Task 1.6: Extend AVANI Guardian for Marine Ecology
**File**: `nlm/guardian/avani.py`
**Action**: Add marine ecological safety checks

```python
class MarineEcologicalGuard:
    """AVANI sub-module: prevents misclassification of marine wildlife as threats."""

    PROTECTED_SPECIES_FREQ_RANGES = {
        'blue_whale': (10, 100),        # Hz
        'humpback_whale': (20, 4000),   # Hz
        'sperm_whale': (2000, 30000),   # Hz (clicks)
        'bottlenose_dolphin': (200, 150000),  # Hz
        'harbor_porpoise': (110000, 150000),  # Hz
    }

    def evaluate(self, classification_output: dict, acoustic_fingerprint: dict) -> dict:
        """Gate threat classifications through ecological safety check."""
        marine_mammal_score = classification_output.get('marine_mammal_score', 0)
        if marine_mammal_score > 0.5:
            return {
                'action': 'gate_for_human_review',
                'reason': f'Possible marine mammal (score={marine_mammal_score:.2f})',
                'ecological_impact': 'HIGH',
                'override_threat': True,
                'original_classification': classification_output
            }
        return {
            'action': 'pass',
            'ecological_impact': 'NONE',
            'override_threat': False
        }
```

### Task 1.7: Add Maritime Training Data Loader
**File**: `nlm/training/dataset.py` (extend existing)
**Action**: Add `MaritimeAcousticDataset` class that loads from MINDEX maritime schemas

### Task 1.8: Add Maritime Losses
**File**: `nlm/training/losses.py` (extend existing)
**Action**: Add classification loss for underwater targets, sonar performance MSE loss, and marine mammal filter BCE loss

### Task 1.9: Tests
**File**: `tests/test_maritime.py` (new file)
**Action**: Test all new fingerprints, encoders, heads, preconditioner, and AVANI guard

---

## LANE 2: MINDEX — MARITIME DATA PLATFORM
**Repo**: `MycosoftLabs/mindex`
**Agent**: Use `database-engineer` or `data-pipeline`
**Priority**: CRITICAL — data infrastructure for all other lanes

### Task 2.1: Add Maritime Database Schemas
**File**: `migrations/0030_maritime_acoustic_schemas.sql` (new)
**Action**: Create new schemas for maritime data

```sql
-- Maritime acoustic signatures catalog
CREATE TABLE IF NOT EXISTS acoustic_signatures (
    id SERIAL PRIMARY KEY,
    signature_id UUID DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT NOT NULL,  -- submarine, surface_vessel, torpedo, uuv, mine, marine_mammal, ambient
    subcategory TEXT,
    frequency_range_low FLOAT,   -- Hz
    frequency_range_high FLOAT,  -- Hz
    spectral_energy JSONB,       -- frequency-energy distribution
    narrowband_peaks JSONB,      -- [(freq, level), ...]
    broadband_level FLOAT,       -- dB re 1μPa
    modulation_rate FLOAT,       -- blade rate Hz
    waveform_hash BYTEA,
    source TEXT,                  -- training data source
    confidence FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_acoustic_sig_category ON acoustic_signatures(category);
CREATE INDEX idx_acoustic_sig_freq ON acoustic_signatures(frequency_range_low, frequency_range_high);

-- Ocean environment observations
CREATE TABLE IF NOT EXISTS ocean_environments (
    id SERIAL PRIMARY KEY,
    observation_id UUID DEFAULT gen_random_uuid(),
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    depth_m FLOAT,
    sound_speed FLOAT,               -- m/s at depth
    temperature_c FLOAT,
    salinity_psu FLOAT,
    sea_state INT,
    current_speed FLOAT,             -- m/s
    current_direction FLOAT,         -- degrees
    bottom_depth FLOAT,
    bottom_type TEXT,
    sound_speed_profile JSONB,       -- [(depth, speed), ...]
    ambient_noise_spectrum JSONB,    -- [(freq, level), ...]
    observed_at TIMESTAMPTZ NOT NULL,
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_ocean_env_location ON ocean_environments USING GIST(location);
CREATE INDEX idx_ocean_env_time ON ocean_environments(observed_at);

-- Magnetic field baselines and anomalies
CREATE TABLE IF NOT EXISTS magnetic_baselines (
    id SERIAL PRIMARY KEY,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    bx FLOAT, by FLOAT, bz FLOAT,   -- nT
    total_field FLOAT,               -- nT
    inclination FLOAT,               -- degrees
    declination FLOAT,               -- degrees
    survey_date TIMESTAMPTZ,
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_mag_baseline_location ON magnetic_baselines USING GIST(location);

-- TAC-O sensor observations (fused from Zeetachec sensors)
CREATE TABLE IF NOT EXISTS taco_observations (
    id SERIAL PRIMARY KEY,
    observation_id UUID DEFAULT gen_random_uuid(),
    sensor_id TEXT NOT NULL,          -- Zeeta Fuze/Buoy ID
    sensor_type TEXT NOT NULL,        -- acoustic, magnetic, environmental
    location GEOGRAPHY(POINT, 4326),
    depth_m FLOAT,
    raw_data JSONB,
    processed_fingerprint JSONB,
    nlm_classification JSONB,         -- NLM output
    anomaly_score FLOAT,
    confidence FLOAT,
    avani_review TEXT,                -- pass, gate_for_human_review
    observed_at TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    merkle_hash TEXT                   -- provenance hash
);
CREATE INDEX idx_taco_obs_sensor ON taco_observations(sensor_id);
CREATE INDEX idx_taco_obs_time ON taco_observations(observed_at);
CREATE INDEX idx_taco_obs_location ON taco_observations USING GIST(location);

-- AI-generated tactical assessments
CREATE TABLE IF NOT EXISTS taco_assessments (
    id SERIAL PRIMARY KEY,
    assessment_id UUID DEFAULT gen_random_uuid(),
    observation_ids UUID[],           -- linked observations
    assessment_type TEXT NOT NULL,     -- threat, environmental, recommendation
    classification JSONB,
    recommendation JSONB,
    sonar_performance JSONB,
    urgency FLOAT,
    avani_ecological_check JSONB,
    operator_action_taken TEXT,
    assessed_at TIMESTAMPTZ DEFAULT NOW(),
    merkle_hash TEXT
);
```

### Task 2.2: Add Maritime ETL Sources
**New files in**: `mindex_etl/sources/`

#### `mindex_etl/sources/noaa_ocean.py` (new)
Ingest NOAA ocean buoy data (NDBC), sound speed profiles, bathymetry.
Pattern after existing `mindex_etl/sources/noaa.py`.

#### `mindex_etl/sources/navy_oceanographic.py` (new)
Ingest NCOM (Navy Coastal Ocean Model), GOFS (Global Ocean Forecast System) outputs.
Public data from HYCOM: https://www.hycom.org/data/glby0pt08

#### `mindex_etl/sources/noaa_hydrophone.py` (new)
Ingest NOAA Pacific Marine Environmental Laboratory hydrophone network data.
Historical underwater acoustic datasets for NLM training.

#### `mindex_etl/sources/zeetachec_ingest.py` (new)
Ingest sensor data from Zeetachec Zeeta Fuze/Buoy network via the MycoBrain MDP bridge.
```python
"""Zeetachec sensor data ingestion via MycoBrain MDP protocol."""

class ZeetachecIngestor:
    """Ingest acoustic and magnetic sensor data from Zeeta Fuze sensors
    relayed through Zeeta Buoy → MycoBrain → MINDEX pipeline."""

    async def ingest_acoustic(self, mdp_payload: dict) -> str:
        """Process acoustic data from Zeeta Fuze acoustic sensor."""
        # 1. Parse MDP envelope
        # 2. Apply hydroacoustic preconditioner
        # 3. Extract HydroacousticFingerprint
        # 4. Store in taco_observations
        # 5. Compute merkle hash
        # 6. Return observation_id

    async def ingest_magnetic(self, mdp_payload: dict) -> str:
        """Process magnetic data from Zeeta Fuze magnetic sensor."""
        # 1. Parse MDP envelope
        # 2. Apply magnetometer calibration
        # 3. Extract MagneticAnomalyFingerprint
        # 4. Compare against magnetic_baselines
        # 5. Store in taco_observations
        # 6. Return observation_id
```

### Task 2.3: Add Maritime ETL Jobs
**New file**: `mindex_etl/jobs/sync_maritime_data.py`
Scheduled job to sync NOAA, HYCOM, hydrophone data on regular cadence.

### Task 2.4: Configure Qdrant Vector Collections
**File**: `mindex_api/config.py` or Qdrant setup script
**Action**: Add vector collections for acoustic signature similarity search

```python
MARITIME_VECTOR_COLLECTIONS = {
    'acoustic_signatures': {
        'size': 512,          # NLM embedding dimension
        'distance': 'Cosine',
        'description': 'Acoustic signature embeddings for similarity search'
    },
    'magnetic_anomalies': {
        'size': 256,
        'distance': 'Cosine',
        'description': 'Magnetic anomaly embeddings'
    }
}
```

### Task 2.5: Add Maritime API Routers
**New file**: `mindex_api/routers/maritime.py`
REST endpoints for maritime data CRUD and query.

**New file**: `mindex_api/routers/taco.py`
TAC-O specific endpoints: observation ingestion, assessment retrieval, sensor status.

### Task 2.6: Extend Worldview Maritime Endpoints
**Existing dir**: `mindex_api/routers/worldview/`
**New file**: `mindex_api/routers/worldview/maritime.py`

```python
"""Maritime-specific Worldview API endpoints for TAC-O."""

@router.get("/worldview/maritime/acoustic-environment")
async def get_acoustic_environment(lat: float, lon: float, radius_nm: float):
    """Sound speed profiles, ambient noise, environmental conditions."""

@router.get("/worldview/maritime/threat-assessment")
async def get_threat_assessment(sector: str = None):
    """Current FUSARIUM Maritime threat assessments."""

@router.get("/worldview/maritime/sensor-health")
async def get_sensor_health():
    """Zeeta sensor network status and health metrics."""

@router.get("/worldview/maritime/decision-aid")
async def get_decision_aid():
    """MYCA tactical recommendations for current operational picture."""
```

### Task 2.7: Extend NLM Router for Acoustic Inference
**Existing file**: `mindex_api/routers/nlm_router.py`
**Action**: Add acoustic classification and maritime prediction endpoints

```python
@router.post("/nlm/classify/acoustic")
async def classify_acoustic(payload: AcousticClassificationRequest):
    """Run NLM acoustic classification on sensor data."""

@router.post("/nlm/predict/sonar-performance")
async def predict_sonar(payload: SonarPredictionRequest):
    """Predict sonar detection ranges for current environment."""

@router.post("/nlm/assess/tactical")
async def tactical_assessment(payload: TacticalAssessmentRequest):
    """Generate tactical recommendation from fused sensor state."""
```

---

## LANE 3: MYCOSOFT-MAS — AGENTS + FUSARIUM MARITIME
**Repo**: `MycosoftLabs/mycosoft-mas`
**Agent**: Use `backend-dev`, `crep-agent`, or `integration-hub`
**Priority**: HIGH — operator-facing system

### Task 3.1: Create TAC-O Agent Cluster
**New directory**: `mycosoft_mas/agents/clusters/taco/`
**New files**:

#### `mycosoft_mas/agents/clusters/taco/__init__.py`

#### `mycosoft_mas/agents/clusters/taco/signal_classifier_agent.py`
```python
"""Signal Classifier Agent — runs NLM acoustic/magnetic classification."""
from mycosoft_mas.agents.base_agent import BaseAgent

class SignalClassifierAgent(BaseAgent):
    """Ingests sensor data from Zeeta Fuze via MycoBrain MDP.
    Runs NLM classification heads.
    Outputs to FUSARIUM Maritime threat panel."""

    AGENT_ID = "taco-signal-classifier"
    CLUSTER = "taco"

    async def process(self, sensor_data: dict):
        # 1. Receive MDP payload from MycoBrain
        # 2. Extract fingerprint (acoustic or magnetic)
        # 3. Call NLM /nlm/classify/acoustic endpoint
        # 4. Check AVANI marine mammal filter
        # 5. If mammal_score > 0.5: gate for human review
        # 6. Else: publish classification to FUSARIUM
        # 7. Store in MINDEX taco_observations
        pass
```

#### `mycosoft_mas/agents/clusters/taco/anomaly_investigator_agent.py`
```python
"""Anomaly Investigator Agent — monitors feeds for baseline deviations."""
class AnomalyInvestigatorAgent(BaseAgent):
    AGENT_ID = "taco-anomaly-investigator"
    CLUSTER = "taco"
    # Uses NLM AnomalyDetectionHead
    # Correlates with AIS (via mindex_etl/sources/ais_marine.py) and environment
    # Triggers investigation workflows when anomaly_score > threshold
```

#### `mycosoft_mas/agents/clusters/taco/ocean_predictor_agent.py`
```python
"""Ocean Predictor Agent — forecasts environmental conditions."""
class OceanPredictorAgent(BaseAgent):
    AGENT_ID = "taco-ocean-predictor"
    CLUSTER = "taco"
    # Uses NLM NextStatePredictionHead + SonarPerformancePredictionHead
    # Ingests NOAA/NCEP data via Worldview maritime endpoints
    # Feeds sonar performance predictions to operators
```

#### `mycosoft_mas/agents/clusters/taco/policy_compliance_agent.py`
```python
"""Policy Compliance Agent — real-time NIST 800-171 monitoring."""
class PolicyComplianceAgent(BaseAgent):
    AGENT_ID = "taco-policy-compliance"
    CLUSTER = "taco"
    # Monitors encryption status on all data channels
    # Validates CUI markings on stored data
    # Checks access logs for unauthorized access
    # Auto-flags NIST 800-171 control violations
    # Reports to security_audit_api.py
```

#### `mycosoft_mas/agents/clusters/taco/data_curator_agent.py`
```python
"""Data Curator Agent — manages training data lifecycle."""
class DataCuratorAgent(BaseAgent):
    AGENT_ID = "taco-data-curator"
    CLUSTER = "taco"
    # Manages MINDEX acoustic/magnetic training datasets
    # Handles ingestion, labeling, QA, versioning, provenance
    # Coordinates with Zeetachec for new field data
    # Tracks dataset lineage via merkle hashes
```

### Task 3.2: Register TAC-O Agents in Agent Manager
**File**: `mycosoft_mas/agents/agent_manager.py`
**Action**: Import and register all 5 TAC-O agents in the agent registry

### Task 3.3: Register TAC-O Cluster
**File**: `mycosoft_mas/agents/cluster_manager.py`
**Action**: Add `taco` cluster definition with all 5 agents

### Task 3.4: Extend FUSARIUM API for Maritime
**Existing file**: `mycosoft_mas/core/routers/fusarium_api.py`
**Action**: Add maritime-specific endpoints

```python
@router.get("/fusarium/maritime/threat-panel")
async def maritime_threat_panel():
    """Real-time maritime threat classifications from TAC-O sensors."""

@router.get("/fusarium/maritime/sensor-network")
async def sensor_network_status():
    """Zeeta sensor network health and connectivity status."""

@router.post("/fusarium/maritime/assess")
async def maritime_assessment(request: MaritimeAssessmentRequest):
    """Trigger full maritime assessment: acoustic + magnetic + environmental fusion."""

@router.get("/fusarium/maritime/decision-aid")
async def maritime_decision_aid():
    """Current tactical recommendations from MYCA TAC-O agents."""

@router.ws("/fusarium/maritime/stream")
async def maritime_stream(websocket):
    """Real-time WebSocket stream of TAC-O detections and alerts."""
```

### Task 3.5: Extend CREP for Zeeta Sensor Feeds
**Existing file**: `mycosoft_mas/core/routers/crep_stream.py`
**Action**: Add Zeetachec sensor data source to CREP unified stream

```python
# Add to CREP data sources:
ZEETA_SENSOR_SOURCE = {
    'name': 'zeetachec_sensors',
    'type': 'maritime_sensor_network',
    'protocol': 'mdp_websocket',
    'categories': ['acoustic_detection', 'magnetic_anomaly', 'environmental'],
    'refresh_interval': 1  # seconds — real-time
}
```

### Task 3.6: Extend CREP Command API for Maritime
**Existing file**: `mycosoft_mas/core/routers/crep_command_api.py`
**Action**: Add commands for maritime sensor control

```python
@router.post("/crep/command/sensor/deploy")
@router.post("/crep/command/sensor/reconfigure")
@router.post("/crep/command/sensor/interrogate")
```

### Task 3.7: Add Zeetachec Integration Client
**New file**: `mycosoft_mas/integrations/zeetachec_client.py`
```python
"""Integration client for Zeetachec sensor network.
Communicates via MycoBrain MDP protocol bridge."""

class ZeetachecClient:
    """Manages bidirectional communication with Zeeta sensor network.

    Inbound: Zeeta Fuze → Zeeta Buoy → LoRa/RF → MycoBrain → MDP → this client
    Outbound: this client → MDP → MycoBrain → Zeeta Buoy → Zeeta Fuze (reconfigure)
    """

    async def subscribe_sensor_feed(self, sensor_ids: List[str]):
        """Subscribe to real-time sensor data from Zeeta Fuze units."""

    async def reconfigure_sensor(self, sensor_id: str, config: dict):
        """Send configuration update to a Zeeta Fuze sensor."""

    async def get_sensor_status(self) -> List[dict]:
        """Query health status of all Zeeta sensors in the network."""

    async def get_buoy_network_topology(self) -> dict:
        """Get the current buoy relay network topology."""
```

### Task 3.8: Extend Defense Client for TAC-O
**Existing file**: `mycosoft_mas/integrations/defense_client.py`
**Action**: Add NUWC-specific methods, SAM.gov contract tracking

### Task 3.9: Extend AVANI Router for Ecological Safety
**Existing file**: `mycosoft_mas/core/routers/avani_router.py`
**Action**: Add marine ecological safety endpoints

```python
@router.post("/avani/ecological-review")
async def ecological_review(classification: dict):
    """AVANI reviews classification for marine wildlife false positives."""

@router.get("/avani/ecological-audit-log")
async def ecological_audit_log(since: datetime = None):
    """Retrieve AVANI ecological governance audit trail."""
```

### Task 3.10: Voice Commands for Maritime Operations
**Existing file**: `mycosoft_mas/core/routers/voice_command_api.py`
**Action**: Add TAC-O voice command intents

```python
TACO_VOICE_INTENTS = {
    'classify_contact': 'Run classification on bearing {bearing} range {range}',
    'sonar_prediction': 'What is current sonar performance prediction',
    'sensor_status': 'Report sensor network status',
    'threat_summary': 'Give me current threat summary',
    'deploy_sensor': 'Deploy sensor at depth {depth}',
    'environmental_report': 'Report current ocean environment',
}
```

---

## LANE 4: MYCOBRAIN — EDGE FIRMWARE + ACOUSTIC INTEROP
**Repo**: `MycosoftLabs/mycobrain`
**Agent**: Use `device-firmware` or `mycobrain-ops`
**Priority**: HIGH — edge processing and Zeetachec hardware bridge

### Task 4.1: Extend FCI Signal Processing for Maritime
**Existing file**: `firmware/MycoBrain_FCI/src/fci_signal.cpp`
**Action**: Add underwater acoustic signal processing modes

```cpp
// Add to fci_signal.cpp:
// Maritime acoustic processing mode
void fci_process_hydroacoustic(float* samples, size_t num_samples, float sample_rate) {
    // 1. Apply bandpass filter for maritime bands (10 Hz - 100 kHz)
    // 2. STFT with Blackman-Harris window (existing)
    // 3. Extract narrowband peaks (blade rates, machinery tones)
    // 4. Compute broadband level (dB re 1μPa)
    // 5. Detect modulation patterns (propeller blade rate)
    // 6. Package as MDP telemetry frame
}

// Magnetic anomaly processing mode
void fci_process_magnetic_anomaly(float bx, float by, float bz,
                                   float* hard_iron, float soft_iron[3][3]) {
    // 1. Apply hard/soft iron calibration
    // 2. Compute total field magnitude
    // 3. Compare against stored baseline
    // 4. Compute anomaly magnitude and gradient
    // 5. Package as MDP telemetry frame
}
```

### Task 4.2: Extend FCI Config for Maritime
**Existing file**: `firmware/MycoBrain_FCI/include/fci_config.h`
**Action**: Add maritime configuration constants

```c
// Maritime acoustic processing config
#define FCI_MARITIME_SAMPLE_RATE    48000    // Hz (hydrophone standard)
#define FCI_MARITIME_FFT_SIZE       4096
#define FCI_MARITIME_FREQ_LOW       10       // Hz
#define FCI_MARITIME_FREQ_HIGH      100000   // Hz
#define FCI_MARITIME_WINDOW         BLACKMAN_HARRIS
#define FCI_MARITIME_OVERLAP        0.75

// Magnetic anomaly config
#define FCI_MAG_BASELINE_UPDATE_S   3600     // seconds between baseline updates
#define FCI_MAG_ANOMALY_THRESHOLD   50       // nT deviation to trigger alert
```

### Task 4.3: Extend Acoustic Modem for Zeeta Interop
**Existing file**: `firmware/MycoBrain_ScienceComms/src/modem_audio.cpp`
**Existing file**: `firmware/MycoBrain_ScienceComms/include/modem_audio.h`
**Action**: Add protocol bridge for Zeetachec acoustic modem compatibility

```cpp
// Add to modem_audio.h:
// Zeetachec acoustic modem interop
typedef struct {
    uint16_t zeeta_sensor_id;
    uint8_t  data_type;       // 0x01=acoustic, 0x02=magnetic, 0x03=env
    uint16_t payload_len;
    uint8_t  payload[];
} zeeta_acoustic_frame_t;

bool modem_rx_zeeta_frame(zeeta_acoustic_frame_t* frame);
bool modem_tx_zeeta_command(uint16_t sensor_id, uint8_t cmd, uint8_t* data, uint16_t len);
```

### Task 4.4: Jetson Inference Pipeline for Maritime NLM
**Existing dir**: `deploy/jetson/`
**New file**: `deploy/jetson/taco_inference.py`

```python
"""Jetson edge inference pipeline for TAC-O NLM models.
Loads ONNX/TorchScript models exported from NLM repo.
Runs real-time classification on sensor data from MycoBrain."""

class TACOJetsonInference:
    def __init__(self, model_path: str):
        # Load ONNX model via onnxruntime or TorchScript
        self.session = ort.InferenceSession(model_path)

    async def classify_acoustic(self, fingerprint: dict) -> dict:
        """Run acoustic classification at edge."""

    async def detect_anomaly(self, sensor_state: dict) -> float:
        """Run anomaly detection at edge."""

    async def filter_marine_mammal(self, fingerprint: dict) -> float:
        """Run AVANI marine mammal filter at edge."""
```

### Task 4.5: MDP Protocol Extension for Maritime Data
**Reference**: `docs/MDP_PROTOCOL_CONTRACTS_MAR07_2026.md`
**Action**: Add maritime telemetry types to MDP protocol

```python
# New MDP message types for maritime:
MDP_TYPE_ACOUSTIC_RAW = 0x30
MDP_TYPE_ACOUSTIC_FINGERPRINT = 0x31
MDP_TYPE_MAGNETIC_RAW = 0x32
MDP_TYPE_MAGNETIC_ANOMALY = 0x33
MDP_TYPE_OCEAN_ENVIRONMENT = 0x34
MDP_TYPE_TACO_CLASSIFICATION = 0x35
MDP_TYPE_TACO_ALERT = 0x36
MDP_TYPE_ZEETA_BRIDGE = 0x37      # Zeetachec interop frame
```

---

## LANE 5: WEBSITE — FUSARIUM MARITIME DASHBOARD
**Repo**: `MycosoftLabs/website`
**Agent**: Use `website-dev` or `neuromorphic-ui`
**Priority**: MEDIUM — depends on Lanes 2-3 for API data
**Depends on**: Lane 2 (MINDEX maritime endpoints), Lane 3 (FUSARIUM maritime API)

### Task 5.1: FUSARIUM Maritime Dashboard Page
**New file**: `app/dashboard/fusarium-maritime/page.tsx`
**Pattern after**: `app/dashboard/crep/page.tsx`

Features:
- Maritime map (Mapbox/Leaflet) with sensor positions, detection overlays
- Real-time acoustic classification feed (WebSocket from FUSARIUM maritime stream)
- Magnetic anomaly heatmap overlay
- Sonar performance prediction layer
- Environmental conditions panel (SSP, thermocline, ambient noise)
- Threat classification timeline
- AVANI ecological review panel
- Sensor network health status

### Task 5.2: Extend CREP Dashboard for Maritime
**Existing file**: `app/dashboard/crep/CREPDashboardClient.tsx`
**Action**: Add Zeeta sensor layer to CREP globe

```typescript
// Add maritime sensor layer to CREP
const MARITIME_LAYERS = {
  zeetaSensors: {
    name: 'Zeeta Sensor Network',
    icon: 'sonar',
    source: '/api/crep/maritime/sensors',
    refresh: 1000,  // 1 second
    categories: ['acoustic', 'magnetic', 'environmental']
  },
  acousticDetections: {
    name: 'Acoustic Detections',
    icon: 'waveform',
    source: '/api/crep/maritime/detections',
    refresh: 1000
  },
  magneticAnomalies: {
    name: 'Magnetic Anomalies',
    icon: 'magnet',
    source: '/api/crep/maritime/anomalies',
    refresh: 5000
  }
};
```

### Task 5.3: Maritime CREP API Routes
**New file**: `app/api/crep/maritime/sensors/route.ts`
**New file**: `app/api/crep/maritime/detections/route.ts`
**New file**: `app/api/crep/maritime/anomalies/route.ts`

### Task 5.4: FUSARIUM Maritime API Routes
**New file**: `app/api/fusarium/maritime/route.ts`
**New file**: `app/api/fusarium/maritime/threats/route.ts`
**New file**: `app/api/fusarium/maritime/assessment/route.ts`

### Task 5.5: Defense Compliance Dashboard Extension
**Existing routes**: `app/api/security/`
**Action**: Add TAC-O NIST 800-171 compliance status panel
**New file**: `app/api/security/taco-compliance/route.ts`

---

## LANE 6: COMPLIANCE — NIST 800-171 PACKAGE
**Repo**: `MycosoftLabs/website` (security APIs) + `MycosoftLabs/mycosoft-mas` (compliance agent)
**Agent**: Use `security-auditor`
**Priority**: HIGH — required for submission
**Depends on**: Lane 3 (Policy Compliance Agent)

### Task 6.1: Generate TAC-O System Security Plan
**Reference**: `.claude/skills/defense-security-compliance/SKILL.md`
**Action**: Use existing SSP generator to produce TAC-O-scoped SSP

The system boundary for TAC-O SSP includes:
- MycoBrain edge nodes (processing CUI sensor data)
- MINDEX database (storing CUI observations)
- MAS/MYCA orchestrator (processing CUI classifications)
- FUSARIUM Maritime dashboard (displaying CUI assessments)
- Network links (MDP, HTTPS, WebSocket)
- Zeetachec sensor interfaces (data ingestion points)

### Task 6.2: Map NIST 800-171 Controls
**New file**: `docs/TACO_NIST_800_171_MAPPING.md`
Map all 110 controls to specific system components:
- Access Control (3.1.x) → MINDEX API keys, RBAC, MFA
- Audit (3.3.x) → Merkle ledger, MINDEX event logging
- Configuration (3.4.x) → Docker configs, firmware versions
- Identification (3.5.x) → MAS authentication, API key auth
- Incident Response (3.6.x) → Alert API, security stream
- Maintenance (3.7.x) → CI/CD pipelines, firmware OTA
- Media Protection (3.8.x) → AES-256-GCM encryption at rest
- Personnel Security (3.9.x) → Team access controls
- Physical Protection (3.10.x) → Server/VM security
- Risk Assessment (3.11.x) → Security audit API
- Security Assessment (3.12.x) → Automated compliance checks
- System/Comms (3.13.x) → TLS 1.3, encrypted MDP
- System/Info Integrity (3.14.x) → Merkle roots, provenance

### Task 6.3: SPRS Score Calculator
**New file**: `mycosoft_mas/agents/compliance/sprs_calculator.py`
**Action**: Automated SPRS self-assessment score computation

### Task 6.4: CUI Handling Procedures
**New file**: `docs/TACO_CUI_HANDLING.md`
Document CUI marking, storage, transmission, and destruction procedures for sensor data.

---

## LANE 7: CURSOR AGENT DEFINITIONS + RULES
**Repo**: `MycosoftLabs/mycosoft-mas` (primary)
**Priority**: MEDIUM — accelerates all other lanes

### Task 7.1: TAC-O Cursor Agent
**New file**: `.cursor/agents/taco-integration.md`

```markdown
# TAC-O Integration Agent

## Identity
You are the TAC-O Integration Agent for the Mycosoft × Zeetachec NUWC Tactical Oceanography project.

## Context
- Mycosoft is subcontracting under Zeetachec for NUWC TAC-O CSO (N66604-26-9-A00X)
- We provide AI/ML signal classification, data fusion, decision support, NIST 800-171 compliance
- Zeetachec provides underwater acoustic/magnetic sensors (Zeeta Fuze, Buoy, RF Receiver)

## Your Scope
- All files in mycosoft_mas/agents/clusters/taco/
- All files in mycosoft_mas/core/routers/ related to fusarium, crep, avani, maritime
- Integration with mindex_api/routers/maritime.py and nlm/ maritime heads
- mycosoft_mas/integrations/zeetachec_client.py

## Rules
1. All sensor data is CUI — apply NIST 800-171 controls
2. All classifications must pass through AVANI ecological safety check before alerting
3. Use Merkle hashing for data provenance on all stored observations
4. MDP protocol is the transport layer between MycoBrain and MAS
5. Export inference models as ONNX for Jetson edge deployment
6. Log all agent decisions to MINDEX taco_assessments table
```

### Task 7.2: Maritime NLM Agent
**New file**: `.cursor/agents/maritime-nlm.md` (in NLM repo)

```markdown
# Maritime NLM Agent

## Identity
You are the Maritime NLM specialist for adapting the Nature Learning Model to underwater acoustic/magnetic domains.

## Your Scope
- nlm/core/fingerprints.py — maritime fingerprint types
- nlm/model/encoders.py — hydroacoustic and magnetic encoders
- nlm/model/heads.py — maritime prediction heads
- nlm/data/preconditioner.py — hydroacoustic physics transforms
- nlm/guardian/avani.py — marine ecological safety
- nlm/training/ — maritime training data and losses

## Rules
1. Preserve all existing NLM functionality — add, don't replace
2. Maritime heads are additive to existing heads
3. All new code must have tests in tests/test_maritime.py
4. Use deterministic physics transforms before neural encoding (Snell's law, Thorp absorption)
5. AVANI marine mammal filter gates ALL threat classifications
```

### Task 7.3: TAC-O Cursor Rules
**New file**: `.cursor/rules/taco-integration.mdc` (in mycosoft-mas repo)

```markdown
---
description: Rules for TAC-O maritime integration work
globs: ["**/taco/**", "**/maritime/**", "**/fusarium/**maritime**"]
---

# TAC-O Integration Rules

## Data Handling
- All sensor data from Zeetachec is CUI — encrypt at rest (AES-256-GCM) and in transit (TLS 1.3)
- Apply Merkle hashing to every stored observation
- Never log raw CUI data to stdout/console in production

## Architecture
- Zeeta sensors → MycoBrain (edge processing) → MDP → MAS (classification) → MINDEX (storage)
- NLM inference runs at TWO tiers: Jetson edge (fast, lightweight) and server (full model)
- AVANI ecological safety check is MANDATORY before any threat alert reaches operator

## API Patterns
- Maritime endpoints follow existing patterns in fusarium_api.py and crep_stream.py
- Use WebSocket for real-time feeds, REST for queries
- All maritime routes are under /fusarium/maritime/ or /crep/maritime/

## Agent Patterns
- TAC-O agents live in mycosoft_mas/agents/clusters/taco/
- All agents extend BaseAgent from mycosoft_mas/agents/base_agent.py
- Register agents in agent_manager.py and cluster_manager.py

## Testing
- Every new module requires tests
- Test acoustic classification with synthetic waveforms
- Test AVANI filter with known marine mammal frequency profiles
- Test MDP protocol with mock Zeeta sensor frames
```

### Task 7.4: Add TAC-O to Existing Cursor Rules
**Existing file**: `.cursor/rules/mycosoft-full-codebase-map.mdc`
**Action**: Add TAC-O repos/files to the codebase map

**Existing file**: `.cursor/rules/crep-context.mdc`
**Action**: Add maritime sensor layers to CREP context

**Existing file**: `.cursor/rules/fci-vision-alignment.mdc`
**Action**: Add maritime FCI processing modes

---

## EXECUTION ORDER

```
Week 1 (April 8-14): Foundation
├── LANE 1: Tasks 1.1-1.6 (NLM fingerprints, encoders, heads, preconditioner, AVANI)
├── LANE 2: Tasks 2.1-2.3 (MINDEX schemas, ETL sources, ETL jobs)
├── LANE 4: Tasks 4.1-4.2 (MycoBrain FCI maritime extensions)
└── LANE 7: Tasks 7.1-7.4 (Cursor agents and rules — enables all other work)

Week 2 (April 14-20): Integration
├── LANE 1: Tasks 1.7-1.9 (NLM training, losses, tests)
├── LANE 2: Tasks 2.4-2.7 (Qdrant vectors, API routers, Worldview, NLM router)
├── LANE 3: Tasks 3.1-3.5 (TAC-O agents, FUSARIUM maritime, CREP extension)
├── LANE 4: Tasks 4.3-4.5 (Acoustic interop, Jetson inference, MDP extension)
└── LANE 6: Tasks 6.1-6.2 (SSP generation, NIST mapping)

Week 3 (April 20-27): Dashboard + Compliance
├── LANE 3: Tasks 3.6-3.10 (Voice commands, Zeetachec client, AVANI router)
├── LANE 5: Tasks 5.1-5.5 (FUSARIUM Maritime dashboard, CREP maritime layers)
└── LANE 6: Tasks 6.3-6.4 (SPRS calculator, CUI procedures)

Week 4+ (Post-submission): Training + Testing
├── Train NLM on initial acoustic datasets (NOAA hydrophone, synthetic)
├── End-to-end integration testing (MycoBrain → MINDEX → NLM → FUSARIUM → Dashboard)
├── Export ONNX models for Jetson edge deployment
└── Prepare for prototype demonstration
```

---

## VERIFICATION CHECKLIST

After each lane, verify:

- [ ] All new files have imports and are registered in their parent module's `__init__.py`
- [ ] All new agents are registered in `agent_manager.py` and `cluster_manager.py`
- [ ] All new API routers are included in the FastAPI app
- [ ] All new database tables have proper indexes
- [ ] All new ETL sources are registered in the scheduler
- [ ] All new MDP message types are documented
- [ ] All new Cursor agents/rules are properly scoped with globs
- [ ] Tests pass for all new code
- [ ] No secrets or CUI data in any committed files
- [ ] Merkle hashing is applied to all stored observations

---

## FILE INDEX (Quick Reference)

### New Files to Create
```
NLM/
├── nlm/core/fingerprints.py          ← EXTEND (add maritime types)
├── nlm/model/encoders.py             ← EXTEND (add maritime encoders)
├── nlm/model/heads.py                ← EXTEND (add 4 maritime heads)
├── nlm/model/nlm_model.py            ← EXTEND (register maritime heads)
├── nlm/data/preconditioner.py        ← EXTEND (add hydroacoustic transforms)
├── nlm/guardian/avani.py             ← EXTEND (add marine ecological guard)
├── nlm/training/dataset.py           ← EXTEND (add maritime dataset)
├── nlm/training/losses.py            ← EXTEND (add maritime losses)
└── tests/test_maritime.py            ← NEW

mindex/
├── migrations/0030_maritime_acoustic_schemas.sql  ← NEW
├── mindex_etl/sources/noaa_ocean.py               ← NEW
├── mindex_etl/sources/navy_oceanographic.py       ← NEW
├── mindex_etl/sources/noaa_hydrophone.py          ← NEW
├── mindex_etl/sources/zeetachec_ingest.py         ← NEW
├── mindex_etl/jobs/sync_maritime_data.py          ← NEW
├── mindex_api/routers/maritime.py                 ← NEW
├── mindex_api/routers/taco.py                     ← NEW
├── mindex_api/routers/worldview/maritime.py       ← NEW
└── mindex_api/routers/nlm_router.py               ← EXTEND

mycosoft-mas/
├── mycosoft_mas/agents/clusters/taco/__init__.py                ← NEW
├── mycosoft_mas/agents/clusters/taco/signal_classifier_agent.py ← NEW
├── mycosoft_mas/agents/clusters/taco/anomaly_investigator_agent.py ← NEW
├── mycosoft_mas/agents/clusters/taco/ocean_predictor_agent.py   ← NEW
├── mycosoft_mas/agents/clusters/taco/policy_compliance_agent.py ← NEW
├── mycosoft_mas/agents/clusters/taco/data_curator_agent.py      ← NEW
├── mycosoft_mas/agents/agent_manager.py                         ← EXTEND
├── mycosoft_mas/agents/cluster_manager.py                       ← EXTEND
├── mycosoft_mas/core/routers/fusarium_api.py                    ← EXTEND
├── mycosoft_mas/core/routers/crep_stream.py                     ← EXTEND
├── mycosoft_mas/core/routers/crep_command_api.py                ← EXTEND
├── mycosoft_mas/core/routers/avani_router.py                    ← EXTEND
├── mycosoft_mas/core/routers/voice_command_api.py               ← EXTEND
├── mycosoft_mas/integrations/zeetachec_client.py                ← NEW
├── mycosoft_mas/integrations/defense_client.py                  ← EXTEND
├── .cursor/agents/taco-integration.md                           ← NEW
├── .cursor/rules/taco-integration.mdc                           ← NEW
├── .cursor/rules/mycosoft-full-codebase-map.mdc                 ← EXTEND
├── .cursor/rules/crep-context.mdc                               ← EXTEND
└── .cursor/rules/fci-vision-alignment.mdc                       ← EXTEND

mycobrain/
├── firmware/MycoBrain_FCI/src/fci_signal.cpp                    ← EXTEND
├── firmware/MycoBrain_FCI/include/fci_config.h                  ← EXTEND
├── firmware/MycoBrain_ScienceComms/src/modem_audio.cpp          ← EXTEND
├── firmware/MycoBrain_ScienceComms/include/modem_audio.h        ← EXTEND
└── deploy/jetson/taco_inference.py                              ← NEW

website/
├── app/dashboard/fusarium-maritime/page.tsx                     ← NEW
├── app/dashboard/crep/CREPDashboardClient.tsx                   ← EXTEND
├── app/api/crep/maritime/sensors/route.ts                       ← NEW
├── app/api/crep/maritime/detections/route.ts                    ← NEW
├── app/api/crep/maritime/anomalies/route.ts                     ← NEW
├── app/api/fusarium/maritime/route.ts                           ← NEW
├── app/api/fusarium/maritime/threats/route.ts                   ← NEW
├── app/api/fusarium/maritime/assessment/route.ts                ← NEW
└── app/api/security/taco-compliance/route.ts                    ← NEW

Compliance docs (in mycosoft-mas or separate docs repo):
├── docs/TACO_NIST_800_171_MAPPING.md                            ← NEW
├── docs/TACO_CUI_HANDLING.md                                    ← NEW
└── mycosoft_mas/agents/compliance/sprs_calculator.py            ← NEW
```
