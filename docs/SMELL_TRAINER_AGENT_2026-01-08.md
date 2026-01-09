# Smell Trainer Agent - January 8, 2026

## Overview

Created a new FastAPI service for MINDEX smell training data collection and BSEC blob management. The Smell Trainer Agent runs on the lab computer with serial access to MycoBrain devices and provides endpoints for session management, data recording, and blob storage.

## Architecture

```
smell_trainer_agent/
├── app.py              # FastAPI main application
├── session_manager.py  # Training session state management
├── models.py           # Pydantic models
├── requirements.txt    # Python dependencies
├── __init__.py        # Package init
└── README.md          # Usage documentation
```

## Features

### Session Management
- Create training sessions with COM port selection
- Automatic sensor verification (require 2x BME688)
- Background recording with configurable duration and interval
- Live sensor data streaming
- Quality assurance checks before export

### Data Export
- CSV export compatible with Bosch AI-Studio
- ZIP archive export with all session data and metadata
- Session history tracking

### MINDEX Blob Management
- Upload trained BSEC selectivity blobs
- Status workflow: testing → active → deprecated
- Export blobs as C headers for firmware
- List and manage all blobs

### Smell Signatures
- Query smell signatures from MINDEX
- Match gas class to signature database

## API Endpoints

### Health & Info
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/ports` | List available COM ports |
| GET | `/templates` | Get specimen training templates |

### Sessions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sessions` | List all training sessions |
| POST | `/sessions` | Create a new training session |
| GET | `/sessions/{id}` | Get session details |
| GET | `/sessions/{id}/status` | Get recording status |
| GET | `/sessions/{id}/latest` | Get latest sensor reading |
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
| POST | `/mindex/blobs/{id}/status` | Set blob status |
| GET | `/mindex/blobs/{id}/export` | Export blob as C header |

### Smell Signatures
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mindex/smells` | List all smell signatures |
| GET | `/mindex/smells/{id}` | Get signature details |

## Configuration

Environment variables:
| Variable | Default | Description |
|----------|---------|-------------|
| `SMELL_TRAINER_HOST` | `0.0.0.0` | Service bind host |
| `SMELL_TRAINER_PORT` | `8042` | Service port |
| `SMELL_TRAINER_REGISTRY_DIR` | `mindex_smell_data` | MINDEX registry directory |
| `SMELL_TRAINER_DATA_DIR` | `training_data` | Training session data directory |

## QA Requirements

Before export is allowed:
- **2 BME688 sensors** must be online (0x77 ambient + 0x76 specimen)
- **Minimum 50 samples** must be collected

## Usage

### Start the Service

```bash
# From the mycosoft-mas directory:
python -m smell_trainer_agent.app

# Or with uvicorn directly:
uvicorn smell_trainer_agent.app:app --host 0.0.0.0 --port 8042
```

### Training Workflow

1. **Connect to Device**
```bash
curl -X POST http://localhost:8042/sessions \
  -H "Content-Type: application/json" \
  -d '{"port": "COM7", "created_by": "lab_user"}'
```

2. **Record Specimens**
```bash
curl -X POST http://localhost:8042/sessions/{session_id}/record \
  -H "Content-Type: application/json" \
  -d '{"label": "pleurotus_ostreatus", "duration_sec": 120}'
```

3. **Export Data**
```bash
curl -O http://localhost:8042/sessions/{session_id}/export.csv
```

4. **Upload Trained Blob**
```bash
curl -X POST http://localhost:8042/mindex/blobs \
  -F "file=@bsec_selectivity.config" \
  -F "name=Oyster Mushroom Detection" \
  -F "classes=clean_air,pleurotus_ostreatus"
```

## Integration

The Smell Trainer Agent integrates with:
- **NatureOS Dashboard**: `/natureos/smell-training` page
- **MINDEX Registry**: File-based storage in `mindex_smell_data/`
- **MycoBrain Service**: Serial communication via port 8003
- **Bosch AI-Studio**: CSV export compatible with training workflow

## Files Created

| File | Description |
|------|-------------|
| `smell_trainer_agent/app.py` | FastAPI main application |
| `smell_trainer_agent/session_manager.py` | Session state management |
| `smell_trainer_agent/models.py` | Pydantic models |
| `smell_trainer_agent/requirements.txt` | Dependencies |
| `smell_trainer_agent/README.md` | Documentation |
