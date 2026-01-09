"""Session management for smell training sessions"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from scripts.smell_training_collector import SmellTrainingCollector, convert_to_csv
except ImportError:
    # Fallback if script not found
    SmellTrainingCollector = None
    convert_to_csv = None


def _now_iso() -> str:
    return datetime.now().isoformat()


def _safe_filename(s: str) -> str:
    keep = []
    for ch in s.strip().lower():
        if ch.isalnum() or ch in ("-", "_", "."):
            keep.append(ch)
        elif ch.isspace():
            keep.append("_")
    out = "".join(keep)
    return out[:80] if out else "sample"


@dataclass
class RecordingState:
    """Current state of a recording operation"""
    state: str = "idle"  # idle|recording|completed|error
    current_label: Optional[str] = None
    started_at: Optional[str] = None
    elapsed_sec: float = 0.0
    sample_count: int = 0
    last_error: Optional[str] = None


@dataclass
class Session:
    """A smell training session"""
    session_id: str
    port: str
    baud: int
    data_dir: Path
    created_by: Optional[str] = None
    device_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: str = field(default_factory=_now_iso)
    
    # Serial connection (managed externally or via collector)
    _serial: Any = field(default=None, repr=False)
    _collector: Any = field(default=None, repr=False)
    
    lock: threading.Lock = field(default_factory=threading.Lock)
    recording: RecordingState = field(default_factory=RecordingState)
    stop_event: threading.Event = field(default_factory=threading.Event)
    latest_reading: Optional[Dict[str, Any]] = None
    
    # Session data
    metadata: Dict[str, Any] = field(default_factory=dict)
    specimens: List[Dict[str, Any]] = field(default_factory=list)
    total_samples: int = 0
    
    def __post_init__(self):
        self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.metadata = {
            "session_id": self.session_id,
            "port": self.port,
            "baud": self.baud,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "device_id": self.device_id,
            "notes": self.notes,
            "specimens": [],
            "total_samples": 0,
        }
        self._save_metadata()
    
    def _save_metadata(self) -> None:
        """Save session metadata to disk"""
        meta_path = self.data_dir / "session_metadata.json"
        with self.lock:
            payload = {
                **self.metadata,
                "updated_at": _now_iso(),
                "recording": {
                    "state": self.recording.state,
                    "current_label": self.recording.current_label,
                    "started_at": self.recording.started_at,
                    "elapsed_sec": self.recording.elapsed_sec,
                    "sample_count": self.recording.sample_count,
                    "last_error": self.recording.last_error,
                },
            }
        meta_path.write_text(json.dumps(payload, indent=2))
    
    def get_sensor_data(self) -> Optional[Dict[str, Any]]:
        """Get current sensor data from device"""
        if self._collector:
            return self._collector.get_sensor_data()
        
        # Fallback: direct serial read
        if self._serial and self._serial.is_open:
            try:
                import serial
                self._serial.reset_input_buffer()
                self._serial.write(b'sensors\n')
                time.sleep(1.0)
                
                lines = []
                while self._serial.in_waiting:
                    line = self._serial.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        lines.append(line)
                
                # Parse JSON response
                for line in lines:
                    if line.startswith("{"):
                        try:
                            return json.loads(line)
                        except json.JSONDecodeError:
                            pass
                
                return {"raw": "\n".join(lines)}
            except Exception as e:
                return {"error": str(e)}
        
        return None
    
    def verify_sensors(self) -> Dict[str, bool]:
        """Verify both BME688 sensors are online"""
        data = self.get_sensor_data()
        if not data:
            return {"bme688_0x77": False, "bme688_0x76": False}
        
        bme1_ok = False
        bme2_ok = False
        
        if "bme1" in data:
            bme1 = data.get("bme1", {})
            bme1_ok = isinstance(bme1.get("temp_c"), (int, float))
        
        if "bme2" in data:
            bme2 = data.get("bme2", {})
            bme2_ok = isinstance(bme2.get("temp_c"), (int, float))
        
        return {
            "bme688_0x77": bme1_ok,
            "bme688_0x76": bme2_ok,
        }
    
    def _record_loop(self, label: str, duration_sec: int, interval_sec: float, description: str | None) -> None:
        """Background recording loop"""
        samples = []
        start = time.time()

        with self.lock:
            self.recording = RecordingState(
                state="recording",
                current_label=label,
                started_at=_now_iso(),
                elapsed_sec=0.0,
                sample_count=0,
                last_error=None,
            )
        self._save_metadata()

        try:
            while (time.time() - start) < duration_sec and not self.stop_event.is_set():
                data = self.get_sensor_data()
                if data is not None:
                    sample = {
                        "timestamp": _now_iso(),
                        "label": label,
                        "bme1": data.get("bme1", {}),
                        "bme2": data.get("bme2", {}),
                        "raw": data,
                    }
                    samples.append(sample)

                    with self.lock:
                        self.latest_reading = sample
                        self.recording.sample_count = len(samples)
                        self.recording.elapsed_sec = time.time() - start

                time.sleep(interval_sec)

            # Save specimen data
            out = {
                "label": label,
                "description": description or "",
                "duration_sec": duration_sec,
                "interval_sec": interval_sec,
                "sample_count": len(samples),
                "collected_at": _now_iso(),
                "samples": samples,
            }
            out_path = self.data_dir / f"{_safe_filename(label)}_{len(samples)}_samples.json"
            out_path.write_text(json.dumps(out, indent=2))

            # Update metadata
            with self.lock:
                specimen_info = {
                    "label": label,
                    "description": description or "",
                    "duration_sec": duration_sec,
                    "interval_sec": interval_sec,
                    "sample_count": len(samples),
                    "file": str(out_path),
                }
                self.specimens.append(specimen_info)
                self.metadata["specimens"].append(specimen_info)
                self.total_samples += len(samples)
                self.metadata["total_samples"] = self.total_samples
                self.recording.state = "completed"

            self._save_metadata()

        except Exception as e:
            with self.lock:
                self.recording.state = "error"
                self.recording.last_error = str(e)
            self._save_metadata()

        finally:
            self.stop_event.clear()

    def start_recording(self, label: str, duration_sec: int, interval_sec: float, description: str | None) -> None:
        """Start recording a specimen in the background"""
        with self.lock:
            if self.recording.state == "recording":
                raise RuntimeError("Already recording")
        self.stop_event.clear()
        t = threading.Thread(
            target=self._record_loop,
            args=(label, duration_sec, interval_sec, description),
            daemon=True
        )
        t.start()

    def stop_recording(self) -> None:
        """Stop the current recording"""
        self.stop_event.set()

    def export_csv(self) -> Path:
        """Export all specimen data to CSV for AI-Studio"""
        out_path = self.data_dir / "training_data.csv"
        
        # Collect all samples from all specimen files
        all_samples = []
        for specimen_file in self.data_dir.glob("*_samples.json"):
            try:
                data = json.loads(specimen_file.read_text())
                for sample in data.get("samples", []):
                    row = {
                        "timestamp": sample.get("timestamp", ""),
                        "label": sample.get("label", ""),
                    }
                    # BME1 data
                    bme1 = sample.get("bme1", {})
                    row["bme1_temp_c"] = bme1.get("temp_c", "")
                    row["bme1_rh_pct"] = bme1.get("rh_pct", "")
                    row["bme1_press_hpa"] = bme1.get("press_hpa", "")
                    row["bme1_gas_ohm"] = bme1.get("gas_ohm", "")
                    row["bme1_iaq"] = bme1.get("iaq", "")
                    row["bme1_co2eq"] = bme1.get("co2_equivalent", "")
                    row["bme1_voc"] = bme1.get("voc_equivalent", "")
                    
                    # BME2 data
                    bme2 = sample.get("bme2", {})
                    row["bme2_temp_c"] = bme2.get("temp_c", "")
                    row["bme2_rh_pct"] = bme2.get("rh_pct", "")
                    row["bme2_press_hpa"] = bme2.get("press_hpa", "")
                    row["bme2_gas_ohm"] = bme2.get("gas_ohm", "")
                    row["bme2_iaq"] = bme2.get("iaq", "")
                    row["bme2_co2eq"] = bme2.get("co2_equivalent", "")
                    row["bme2_voc"] = bme2.get("voc_equivalent", "")
                    
                    all_samples.append(row)
            except Exception:
                continue
        
        # Write CSV
        if all_samples:
            import csv
            with open(out_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(all_samples[0].keys()))
                writer.writeheader()
                writer.writerows(all_samples)
        else:
            out_path.write_text("timestamp,label,bme1_temp_c,bme1_rh_pct,bme1_press_hpa,bme1_gas_ohm,bme1_iaq,bme1_co2eq,bme1_voc,bme2_temp_c,bme2_rh_pct,bme2_press_hpa,bme2_gas_ohm,bme2_iaq,bme2_co2eq,bme2_voc\n")
        
        return out_path

    def export_zip_bytes(self) -> bytes:
        """Export entire session as a ZIP file"""
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for p in self.data_dir.rglob("*"):
                if p.is_file():
                    z.write(p, arcname=str(p.relative_to(self.data_dir)))
        return buf.getvalue()

    def disconnect(self) -> None:
        """Close serial connection"""
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        if self._collector:
            try:
                self._collector.disconnect()
            except Exception:
                pass
            self._collector = None


class SessionManager:
    """Manages training sessions"""
    
    def __init__(self, data_root: str = "training_data"):
        self._sessions: Dict[str, Session] = {}
        self._data_root = Path(data_root)
        self._data_root.mkdir(parents=True, exist_ok=True)
    
    def create(
        self,
        port: str,
        baud: int,
        created_by: str | None,
        device_id: str | None,
        notes: str | None
    ) -> Session:
        """Create a new training session"""
        import serial
        
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        data_dir = self._data_root / session_id
        
        # Open serial connection
        try:
            ser = serial.Serial(port, baud, timeout=2)
        except Exception as e:
            raise RuntimeError(f"Failed to connect to port {port}: {e}")
        
        sess = Session(
            session_id=session_id,
            port=port,
            baud=baud,
            data_dir=data_dir,
            created_by=created_by,
            device_id=device_id,
            notes=notes,
        )
        sess._serial = ser
        
        # Verify sensors
        sensor_status = sess.verify_sensors()
        if not sensor_status.get("bme688_0x77") and not sensor_status.get("bme688_0x76"):
            sess.disconnect()
            raise RuntimeError("No BME688 sensors detected")
        
        self._sessions[session_id] = sess
        return sess
    
    def get(self, session_id: str) -> Session:
        """Get a session by ID"""
        sess = self._sessions.get(session_id)
        if not sess:
            raise KeyError(f"Session not found: {session_id}")
        return sess
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions"""
        sessions = []
        for session_id, sess in self._sessions.items():
            sessions.append({
                "session_id": session_id,
                "port": sess.port,
                "created_at": sess.created_at,
                "created_by": sess.created_by,
                "specimens": len(sess.specimens),
                "total_samples": sess.total_samples,
                "status": sess.recording.state,
            })
        return sessions
    
    def close(self, session_id: str) -> None:
        """Close and remove a session"""
        sess = self.get(session_id)
        sess.disconnect()
        sess._save_metadata()
        self._sessions.pop(session_id, None)
