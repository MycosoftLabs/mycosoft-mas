"""
Smell Trainer Agent - FastAPI service for MINDEX smell training

This service runs on the lab computer with serial access to MycoBrain devices.
It manages training sessions, records sensor data, and integrates with MINDEX
for blob storage and smell signature management.

Run with: uvicorn smell_trainer_agent.app:app --host 0.0.0.0 --port 8042
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import serial.tools.list_ports
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from smell_trainer_agent.models import (
    BlobUploadResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    LatestReading,
    RecordRequest,
    RecordStatus,
    QAStatus,
    SessionInfo,
    BlobInfo,
    SmellSignatureInfo,
)
from smell_trainer_agent.session_manager import SessionManager

# Try to import smell registry
try:
    from scripts.smell_registry import (
        SmellRegistry,
        BlobStatus,
        initialize_default_registry,
    )
    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False
    SmellRegistry = None
    BlobStatus = None

# Configuration
APP_HOST = os.getenv("SMELL_TRAINER_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("SMELL_TRAINER_PORT", "8042"))
REGISTRY_DIR = os.getenv("SMELL_TRAINER_REGISTRY_DIR", "mindex_smell_data")
TRAINING_DATA_DIR = os.getenv("SMELL_TRAINER_DATA_DIR", "training_data")
TEMPLATES_PATH = os.getenv("SMELL_TRAINER_TEMPLATES", "scripts/specimen_templates.json")

# Minimum requirements for export
MIN_SENSORS_REQUIRED = 2
MIN_SAMPLES_REQUIRED = 50

app = FastAPI(
    title="Mycosoft Smell Trainer Agent",
    description="MINDEX smell training data collection and blob management",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3002",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
sessions = SessionManager(data_root=TRAINING_DATA_DIR)

# Initialize registry if available
registry = None
if REGISTRY_AVAILABLE:
    try:
        registry = initialize_default_registry(REGISTRY_DIR)
    except Exception as e:
        print(f"Warning: Could not initialize smell registry: {e}")


# ============================================================================
# Health & Info Endpoints
# ============================================================================

@app.get("/health")
def health() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "ok": True,
        "service": "Smell Trainer Agent",
        "version": "1.0.0",
        "registry_available": REGISTRY_AVAILABLE and registry is not None,
    }


@app.get("/ports")
def list_ports() -> List[Dict[str, str]]:
    """List available serial ports"""
    ports = []
    for p in serial.tools.list_ports.comports():
        ports.append({
            "device": p.device,
            "description": p.description or "",
            "hwid": p.hwid or "",
            "vid": str(p.vid) if p.vid else "",
            "pid": str(p.pid) if p.pid else "",
        })
    return ports


@app.get("/templates")
def get_templates() -> Dict[str, Any]:
    """Get specimen training templates"""
    path = Path(TEMPLATES_PATH)
    if not path.exists():
        return {"ok": False, "error": f"Templates file not found: {path}"}
    try:
        import json
        return {"ok": True, "templates": json.loads(path.read_text())}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================================
# Session Management Endpoints
# ============================================================================

@app.get("/sessions")
def list_sessions() -> Dict[str, Any]:
    """List all training sessions"""
    return {
        "ok": True,
        "sessions": sessions.list_sessions(),
        "count": len(sessions.list_sessions()),
    }


@app.post("/sessions", response_model=CreateSessionResponse)
def create_session(req: CreateSessionRequest):
    """Create a new training session"""
    try:
        sess = sessions.create(
            port=req.port,
            baud=req.baud,
            created_by=req.created_by,
            device_id=req.device_id,
            notes=req.notes,
        )
        sensor_status = sess.verify_sensors()
        return CreateSessionResponse(
            session_id=sess.session_id,
            data_dir=str(sess.data_dir),
            sensor_status=sensor_status
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/sessions/{session_id}")
def get_session(session_id: str) -> Dict[str, Any]:
    """Get session details"""
    try:
        sess = sessions.get(session_id)
        return {
            "ok": True,
            "session": {
                "session_id": sess.session_id,
                "port": sess.port,
                "created_at": sess.created_at,
                "created_by": sess.created_by,
                "device_id": sess.device_id,
                "notes": sess.notes,
                "specimens": sess.specimens,
                "total_samples": sess.total_samples,
                "status": sess.recording.state,
            }
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown session_id")


@app.get("/sessions/{session_id}/status", response_model=RecordStatus)
def session_status(session_id: str):
    """Get current recording status for a session"""
    try:
        sess = sessions.get(session_id)
        r = sess.recording
        return RecordStatus(
            state=r.state,
            current_label=r.current_label,
            started_at=r.started_at,
            elapsed_sec=r.elapsed_sec,
            sample_count=r.sample_count,
            last_error=r.last_error,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown session_id")


@app.get("/sessions/{session_id}/latest", response_model=LatestReading)
def session_latest(session_id: str):
    """Get the most recent sensor reading from a session"""
    try:
        sess = sessions.get(session_id)
        if not sess.latest_reading:
            # Fetch one reading on demand
            data = sess.get_sensor_data() or {}
            from datetime import datetime
            sess.latest_reading = {"timestamp": datetime.now().isoformat(), "data": data}
        return LatestReading(
            timestamp=sess.latest_reading.get("timestamp", ""),
            data=sess.latest_reading
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown session_id")


@app.post("/sessions/{session_id}/record")
def start_recording(session_id: str, req: RecordRequest):
    """Start recording a specimen"""
    try:
        sess = sessions.get(session_id)
        sess.start_recording(req.label, req.duration_sec, req.interval_sec, req.description)
        return {"ok": True, "message": f"Started recording '{req.label}'"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/sessions/{session_id}/stop")
def stop_recording(session_id: str):
    """Stop the current recording"""
    try:
        sess = sessions.get(session_id)
        sess.stop_recording()
        return {"ok": True, "message": "Recording stopped"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown session_id")


@app.get("/sessions/{session_id}/qa", response_model=QAStatus)
def check_qa(session_id: str):
    """Check quality assurance requirements for a session"""
    try:
        sess = sessions.get(session_id)
        sensor_status = sess.verify_sensors()
        sensors_online = sum(1 for v in sensor_status.values() if v)
        
        issues = []
        if sensors_online < MIN_SENSORS_REQUIRED:
            issues.append(f"Need {MIN_SENSORS_REQUIRED} sensors online, only {sensors_online} detected")
        if sess.total_samples < MIN_SAMPLES_REQUIRED:
            issues.append(f"Need at least {MIN_SAMPLES_REQUIRED} samples, only {sess.total_samples} collected")
        
        can_export = len(issues) == 0
        
        return QAStatus(
            sensors_online=sensors_online >= MIN_SENSORS_REQUIRED,
            sensor_count=sensors_online,
            required_sensor_count=MIN_SENSORS_REQUIRED,
            minimum_samples=MIN_SAMPLES_REQUIRED,
            current_samples=sess.total_samples,
            can_export=can_export,
            issues=issues,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown session_id")


@app.get("/sessions/{session_id}/export.csv")
def export_csv(session_id: str):
    """Export session data as CSV for AI-Studio"""
    try:
        sess = sessions.get(session_id)
        csv_path = sess.export_csv()
        return FileResponse(
            path=str(csv_path),
            filename=f"{session_id}_training_data.csv",
            media_type="text/csv"
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/sessions/{session_id}/export.zip")
def export_zip(session_id: str):
    """Export full session as ZIP archive"""
    try:
        sess = sessions.get(session_id)
        zip_bytes = sess.export_zip_bytes()
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{session_id}_training_session.zip"'
            },
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown session_id")


@app.delete("/sessions/{session_id}")
def close_session(session_id: str):
    """Close and clean up a session"""
    try:
        sessions.close(session_id)
        return {"ok": True, "message": f"Session {session_id} closed"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown session_id")


# ============================================================================
# MINDEX Blob Management Endpoints
# ============================================================================

@app.post("/mindex/blobs", response_model=BlobUploadResponse)
async def upload_blob(
    file: UploadFile = File(...),
    name: str = Form(...),
    version: str = Form("1.0.0"),
    classes: str = Form(...),  # comma-separated
    training_method: str = Form("ai_studio"),
    description: str = Form(""),
    created_by: str = Form(""),
):
    """Upload a BSEC selectivity blob to MINDEX"""
    if not REGISTRY_AVAILABLE or not registry:
        raise HTTPException(status_code=503, detail="Smell registry not available")
    
    class_labels = [c.strip() for c in classes.split(",") if c.strip()]
    if len(class_labels) == 0:
        raise HTTPException(status_code=400, detail="classes must contain at least 1 label")

    # Save to a temp file
    suffix = Path(file.filename or "blob.config").suffix or ".config"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        blob_id = registry.import_blob_from_file(
            file_path=tmp_path,
            name=name,
            version=version,
            class_labels=class_labels,
            description=description,
            training_method=training_method,
            created_by=created_by,
            bsec_version="2.4.0",
            sensor_model="BME688",
        )

        blob = registry.get_blob(blob_id)
        if not blob:
            raise RuntimeError("Blob imported but could not be reloaded")

        # Default to TESTING so staff can validate before promoting
        registry.set_blob_status(blob_id, BlobStatus.TESTING)

        return BlobUploadResponse(
            blob_id=blob_id,
            blob_hash=blob.blob_hash,
            status=BlobStatus.TESTING.value
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@app.get("/mindex/blobs")
def list_blobs() -> Dict[str, Any]:
    """List all BSEC blobs in MINDEX"""
    if not REGISTRY_AVAILABLE or not registry:
        return {"ok": False, "error": "Smell registry not available", "blobs": []}
    
    try:
        blobs = [b.to_dict() for b in registry.list_blobs()]
        return {"ok": True, "blobs": blobs, "count": len(blobs)}
    except Exception as e:
        return {"ok": False, "error": str(e), "blobs": []}


@app.get("/mindex/blobs/{blob_id}")
def get_blob(blob_id: str) -> Dict[str, Any]:
    """Get details of a specific blob"""
    if not REGISTRY_AVAILABLE or not registry:
        raise HTTPException(status_code=503, detail="Smell registry not available")
    
    blob = registry.get_blob(blob_id)
    if not blob:
        raise HTTPException(status_code=404, detail="Blob not found")
    
    return {"ok": True, "blob": blob.to_dict()}


@app.post("/mindex/blobs/{blob_id}/status")
def set_blob_status(blob_id: str, status: str = Form(...)):
    """Update the status of a blob (testing/active/deprecated)"""
    if not REGISTRY_AVAILABLE or not registry:
        raise HTTPException(status_code=503, detail="Smell registry not available")
    
    try:
        st = BlobStatus(status)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}. Must be: testing, active, deprecated")

    ok = registry.set_blob_status(blob_id, st)
    if not ok:
        raise HTTPException(status_code=404, detail="Unknown blob_id")
    return {"ok": True, "blob_id": blob_id, "status": status}


@app.get("/mindex/blobs/{blob_id}/export")
def export_blob(blob_id: str, format: str = "header"):
    """Export a blob as C header or raw binary"""
    if not REGISTRY_AVAILABLE or not registry:
        raise HTTPException(status_code=503, detail="Smell registry not available")
    
    blob = registry.get_blob(blob_id)
    if not blob:
        raise HTTPException(status_code=404, detail="Blob not found")
    
    if format == "header":
        # Export as C header
        try:
            header_content = registry.export_blob_as_header(blob_id)
            return Response(
                content=header_content,
                media_type="text/plain",
                headers={
                    "Content-Disposition": f'attachment; filename="bsec_selectivity_{blob_id[:8]}.h"'
                }
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # Export raw blob
        blob_path = Path(REGISTRY_DIR) / "blobs" / f"{blob_id}.config"
        if not blob_path.exists():
            raise HTTPException(status_code=404, detail="Blob file not found")
        return FileResponse(
            path=str(blob_path),
            filename=f"{blob_id}.config",
            media_type="application/octet-stream"
        )


# ============================================================================
# MINDEX Smell Signatures Endpoints
# ============================================================================

@app.get("/mindex/smells")
def list_signatures() -> Dict[str, Any]:
    """List all smell signatures"""
    if not REGISTRY_AVAILABLE or not registry:
        return {"ok": False, "error": "Smell registry not available", "smells": []}
    
    try:
        signatures = [s.to_dict() for s in registry.list_signatures()]
        return {"ok": True, "smells": signatures, "count": len(signatures)}
    except Exception as e:
        return {"ok": False, "error": str(e), "smells": []}


@app.get("/mindex/smells/{smell_id}")
def get_signature(smell_id: str) -> Dict[str, Any]:
    """Get details of a specific smell signature"""
    if not REGISTRY_AVAILABLE or not registry:
        raise HTTPException(status_code=503, detail="Smell registry not available")
    
    signature = registry.get_signature(smell_id)
    if not signature:
        raise HTTPException(status_code=404, detail="Smell signature not found")
    
    return {"ok": True, "smell": signature.to_dict()}


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print(f"Starting Smell Trainer Agent on {APP_HOST}:{APP_PORT}")
    print(f"Registry directory: {REGISTRY_DIR}")
    print(f"Training data directory: {TRAINING_DATA_DIR}")
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
