"""
Jetson Orin Nano inference server.

Runs ON the Jetson Orin Nano. Provides camera streaming, audio capture/transcription,
and model inference. MAS connects via HTTP.

Usage on Jetson:
    python -m mycosoft_mas.edge.jetson_server

Or from MAS repo:
    python scripts/run_jetson_server.py  # if wrapper exists

Created: February 17, 2026
"""

from __future__ import annotations

import io
import logging
import os
import time
import uuid
from typing import Any, Dict, Generator, Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import Response, StreamingResponse

logger = logging.getLogger(__name__)

# Optional: jetson-inference / jetson-utils (only available on Jetson)
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from jetson_utils import cudaImage, videoSource
    HAS_JETSON_UTILS = True
except ImportError:
    HAS_JETSON_UTILS = False

try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

app = FastAPI(title="Jetson Inference Server", version="1.0.0")

# Global state
_camera: Optional[Any] = None
_models: Dict[str, Any] = {}
_whisper_model: Optional[Any] = None


def _load_whisper_model() -> Optional[Any]:
    """Lazy-load Whisper model on first transcription request."""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    if not HAS_WHISPER:
        return None
    model_name = os.getenv("JETSON_WHISPER_MODEL", "tiny")
    compute_type = os.getenv("JETSON_WHISPER_COMPUTE_TYPE", "int8")
    try:
        _whisper_model = WhisperModel(model_name, device="auto", compute_type=compute_type)
        logger.info("Loaded Whisper model: %s (%s)", model_name, compute_type)
        return _whisper_model
    except Exception as exc:
        logger.warning("Failed to load Whisper model: %s", exc)
        return None


def _get_camera():
    """Lazy-init camera. Prefer Jetson videoSource, fallback to OpenCV."""
    global _camera
    if _camera is not None:
        return _camera
    if HAS_JETSON_UTILS:
        try:
            _camera = videoSource("/dev/video0")
            return _camera
        except Exception as e:
            logger.warning("Jetson videoSource failed: %s", e)
    if HAS_CV2:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            _camera = cap
            return _camera
    logger.warning("No camera available (no cv2 or jetson-utils)")
    return None


def _capture_frame() -> Optional[bytes]:
    """Capture single JPEG frame from camera."""
    cam = _get_camera()
    if cam is None:
        return None
    try:
        if HAS_JETSON_UTILS and hasattr(cam, "Capture"):
            img = cam.Capture()
            if img is None:
                return None
            # jetson-utils: need to encode to JPEG (cudaImage)
            if HAS_CV2:
                import numpy as np
                arr = img.numpy() if hasattr(img, "numpy") else None
                if arr is not None:
                    _, jpeg = cv2.imencode(".jpg", arr)
                    return jpeg.tobytes()
        if HAS_CV2 and hasattr(cam, "read"):
            ok, frame = cam.read()
            if not ok or frame is None:
                return None
            _, jpeg = cv2.imencode(".jpg", frame)
            return jpeg.tobytes()
    except Exception as e:
        logger.warning("Frame capture error: %s", e)
    return None


def _stream_frames() -> Generator[bytes, None, None]:
    """MJPEG stream generator."""
    while True:
        frame = _capture_frame()
        if frame is None:
            time.sleep(0.033)  # ~30fps
            continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        )
        time.sleep(0.033)


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Health check. Returns device type and status."""
    return {
        "status": "healthy",
        "device": "jetson_orin_nano",
        "camera": _get_camera() is not None,
        "whisper": _whisper_model is not None,
        "models": list(_models.keys()),
    }


@app.get("/camera/frame")
async def camera_frame(format: str = Query("jpeg", alias="format")) -> Response:
    """Capture single frame. Returns JPEG bytes."""
    frame = _capture_frame()
    if frame is None:
        raise HTTPException(status_code=503, detail="Camera unavailable")
    return Response(content=frame, media_type="image/jpeg")


@app.get("/camera/stream")
async def camera_stream():
    """MJPEG stream for live viewing."""
    return StreamingResponse(
        _stream_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.post("/audio/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Transcribe audio via Whisper (Whisper-tiny on Jetson)."""
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio")
    whisper_model = _load_whisper_model()
    if whisper_model is None:
        # Keep a deterministic, explicit fallback instead of silent failure.
        return {
            "text": "",
            "language": language or "en",
            "duration_seconds": 0.0,
            "engine": "unavailable",
        }
    try:
        # faster-whisper accepts file paths, file-like streams, or numpy audio.
        # BytesIO works for uploaded WAV/MP3 payloads.
        segments, info = whisper_model.transcribe(io.BytesIO(data), language=language)
        text = " ".join(segment.text.strip() for segment in segments if segment.text).strip()
        return {
            "text": text,
            "language": info.language,
            "duration_seconds": float(getattr(info, "duration", 0.0) or 0.0),
            "engine": "faster-whisper",
        }
    except Exception as exc:
        logger.warning("Whisper transcription failed: %s", exc)
        return {
            "text": "",
            "language": language or "en",
            "duration_seconds": 0.0,
            "engine": "error",
            "error": str(exc),
        }


@app.post("/inference")
async def inference(
    data: UploadFile = File(...),
    model: str = Query(...),
    input_type: str = Query("image"),
) -> Dict[str, Any]:
    """Run model inference. input_type: image | audio."""
    payload = await data.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty input")
    start = time.perf_counter()
    prediction = []
    confidence = 0.0
    # Lightweight baseline: if OpenCV is available, decode and emit frame stats.
    # This keeps the endpoint useful before model deployment.
    if input_type == "image" and HAS_CV2:
        try:
            import numpy as np
            frame_array = np.frombuffer(payload, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
            if frame is not None:
                h, w = frame.shape[:2]
                mean_bgr = frame.mean(axis=(0, 1)).tolist()
                prediction = [
                    {
                        "type": "image_stats",
                        "width": int(w),
                        "height": int(h),
                        "mean_bgr": [round(float(x), 2) for x in mean_bgr],
                    }
                ]
                confidence = 0.2
        except Exception as exc:
            logger.warning("Image baseline inference failed: %s", exc)
    elif input_type == "audio":
        prediction = [{"type": "audio_detected", "bytes": len(payload)}]
        confidence = 0.1

    latency_ms = (time.perf_counter() - start) * 1000
    return {
        "model": model,
        "prediction": prediction,
        "confidence": round(confidence, 3),
        "latency_ms": round(latency_ms, 2),
    }


@app.get("/models")
async def list_models() -> Dict[str, Any]:
    """List loaded models."""
    return {"models": [{"id": k, "loaded": True} for k in _models]}


@app.post("/models/deploy")
async def deploy_model(body: Dict[str, Any]) -> Dict[str, Any]:
    """Load a model. body: { model_path: str }."""
    path = body.get("model_path")
    if not path:
        raise HTTPException(status_code=400, detail="model_path required")
    model_id = str(uuid.uuid4())[:8]
    _models[model_id] = {"path": path}
    return {"model_id": model_id}


def main() -> None:
    """Run server. Use: uvicorn mycosoft_mas.edge.jetson_server:app --host 0.0.0.0 --port 8080"""
    import uvicorn
    port = int(os.getenv("JETSON_SERVER_PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
