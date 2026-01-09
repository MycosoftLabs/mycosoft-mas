# Smell Trainer Agent

A FastAPI service for MINDEX smell training data collection and BSEC blob management.

## Overview

The Smell Trainer Agent runs on the lab computer with serial access to MycoBrain devices. It provides:

- **Session Management**: Create and manage smell training sessions
- **Data Collection**: Record BME688 sensor data with labels for AI-Studio training
- **MINDEX Integration**: Upload and manage BSEC selectivity blobs
- **Quality Assurance**: Validate sensor status and sample counts before export

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Service

```bash
# From the mycosoft-mas directory:
python -m smell_trainer_agent.app

# Or with uvicorn directly:
uvicorn smell_trainer_agent.app:app --host 0.0.0.0 --port 8042
```

### 3. Access the API

- Health check: `GET http://localhost:8042/health`
- List ports: `GET http://localhost:8042/ports`
- API docs: `http://localhost:8042/docs`

## API Endpoints

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sessions` | List all training sessions |
| POST | `/sessions` | Create a new training session |
| GET | `/sessions/{id}` | Get session details |
| GET | `/sessions/{id}/status` | Get recording status |
| POST | `/sessions/{id}/record` | Start recording a specimen |
| POST | `/sessions/{id}/stop` | Stop recording |
| GET | `/sessions/{id}/qa` | Check QA requirements |
| GET | `/sessions/{id}/export.csv` | Export as AI-Studio CSV |
| GET | `/sessions/{id}/export.zip` | Export full session ZIP |
| DELETE | `/sessions/{id}` | Close session |

### MINDEX Blobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mindex/blobs` | List all blobs |
| POST | `/mindex/blobs` | Upload a new blob |
| GET | `/mindex/blobs/{id}` | Get blob details |
| POST | `/mindex/blobs/{id}/status` | Set blob status (testing/active/deprecated) |
| GET | `/mindex/blobs/{id}/export` | Export blob as C header or binary |

### Smell Signatures

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mindex/smells` | List all smell signatures |
| GET | `/mindex/smells/{id}` | Get signature details |

## Training Workflow

### 1. Connect to Device

```bash
# List available ports
curl http://localhost:8042/ports

# Create a session
curl -X POST http://localhost:8042/sessions \
  -H "Content-Type: application/json" \
  -d '{"port": "COM7", "created_by": "lab_user"}'
```

### 2. Record Specimens

```bash
# Record clean air baseline (60 seconds)
curl -X POST http://localhost:8042/sessions/{session_id}/record \
  -H "Content-Type: application/json" \
  -d '{"label": "clean_air_baseline", "duration_sec": 60}'

# Record a fungal specimen
curl -X POST http://localhost:8042/sessions/{session_id}/record \
  -H "Content-Type: application/json" \
  -d '{"label": "pleurotus_ostreatus", "duration_sec": 120, "description": "Fresh oyster mushroom"}'
```

### 3. Check Quality

```bash
# Check if session meets QA requirements
curl http://localhost:8042/sessions/{session_id}/qa
```

### 4. Export Data

```bash
# Export CSV for AI-Studio
curl -O http://localhost:8042/sessions/{session_id}/export.csv

# Export full session ZIP
curl -O http://localhost:8042/sessions/{session_id}/export.zip
```

### 5. Upload Trained Blob

After training in Bosch AI-Studio:

```bash
curl -X POST http://localhost:8042/mindex/blobs \
  -F "file=@bsec_selectivity.config" \
  -F "name=Oyster Mushroom Detection" \
  -F "version=1.0.0" \
  -F "classes=clean_air,pleurotus_ostreatus" \
  -F "training_method=ai_studio" \
  -F "created_by=lab_user"
```

### 6. Promote Blob to Active

```bash
# After validation, promote to active
curl -X POST http://localhost:8042/mindex/blobs/{blob_id}/status \
  -F "status=active"
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SMELL_TRAINER_HOST` | `0.0.0.0` | Service bind host |
| `SMELL_TRAINER_PORT` | `8042` | Service port |
| `SMELL_TRAINER_REGISTRY_DIR` | `mindex_smell_data` | MINDEX registry directory |
| `SMELL_TRAINER_DATA_DIR` | `training_data` | Training session data directory |
| `SMELL_TRAINER_TEMPLATES` | `scripts/specimen_templates.json` | Training templates file |

## QA Requirements

Before export is allowed:

- **2 BME688 sensors** must be online (0x77 ambient + 0x76 specimen)
- **Minimum 50 samples** must be collected

## Integration with NatureOS

The Smell Trainer Agent is designed to be called from the NatureOS dashboard at `/natureos/smell-training`. The dashboard provides a visual wizard for:

1. Selecting COM port and verifying sensors
2. Running baseline and specimen recording
3. Monitoring live sensor data
4. Exporting data and uploading blobs
5. Managing blob status (staff only)

## File Structure

```
smell_trainer_agent/
├── app.py              # FastAPI main application
├── session_manager.py  # Training session state management
├── models.py           # Pydantic models
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Related Files

- `scripts/smell_training_collector.py` - Low-level sensor data collection
- `scripts/smell_registry.py` - MINDEX blob and signature storage
- `scripts/specimen_templates.json` - Pre-defined training scenarios
- `mindex_smell_data/` - File-based storage for blobs and signatures
