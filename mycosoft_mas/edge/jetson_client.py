"""
Jetson Orin Nano client for MAS.

HTTP client for camera streaming, audio capture, and model inference on Jetson Orin Nano.
Communicates with jetson_server.py running on the edge device.

Created: February 17, 2026
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

JETSON_DEFAULT_HOST = "192.168.0.100"
JETSON_DEFAULT_PORT = 8080
DEFAULT_TIMEOUT = 30.0


class JetsonClient:
    """HTTP client for Jetson Orin Nano inference server."""

    def __init__(
        self,
        host: str = JETSON_DEFAULT_HOST,
        port: int = JETSON_DEFAULT_PORT,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.host = host
        self.port = port
        self._base_url = base_url or f"http://{host}:{port}"
        self._timeout = httpx.Timeout(timeout)
        self._connected = False
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        """Verify Jetson server is reachable."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.get(f"{self._base_url}/health")
                r.raise_for_status()
                data = r.json()
                if data.get("status") != "healthy":
                    logger.warning("Jetson health check returned non-healthy: %s", data)
                    return False
                self._connected = True
                self._client = httpx.AsyncClient(timeout=self._timeout, base_url=self._base_url)
                logger.info("Connected to Jetson at %s:%d", self.host, self.port)
                return True
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning("Jetson connection failed: %s", e)
            self._connected = False
            return False
        except Exception as e:
            logger.exception("Jetson connect error: %s", e)
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    def _client_or_raise(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout, base_url=self._base_url)
        return self._client

    async def get_camera_frame(self, format: str = "jpeg") -> Optional[bytes]:
        """Capture a single frame from the Jetson camera. Returns JPEG bytes."""
        try:
            client = self._client_or_raise()
            r = await client.get("/camera/frame", params={"format": format})
            r.raise_for_status()
            return r.content
        except Exception as e:
            logger.warning("Camera frame capture failed: %s", e)
            return None

    def get_camera_stream_url(self) -> str:
        """Return URL for MJPEG stream from Jetson camera."""
        return f"{self._base_url}/camera/stream"

    async def transcribe_audio(self, audio_bytes: bytes, language: Optional[str] = None) -> str:
        """Send audio to Jetson Whisper, return transcription."""
        try:
            client = self._client_or_raise()
            files = {"audio": ("audio.wav", audio_bytes, "audio/wav")}
            params = {} if language is None else {"language": language}
            r = await client.post("/audio/transcribe", files=files, params=params)
            r.raise_for_status()
            data = r.json()
            return data.get("text", "")
        except Exception as e:
            logger.warning("Audio transcription failed: %s", e)
            return ""

    async def run_inference(
        self,
        model_name: str,
        input_data: bytes,
        input_type: str = "image",
    ) -> Dict[str, Any]:
        """Run model inference on Jetson. input_type: 'image' or 'audio'."""
        try:
            client = self._client_or_raise()
            files = {"data": ("input.bin", input_data, "application/octet-stream")}
            r = await client.post(
                "/inference",
                files=files,
                params={"model": model_name, "input_type": input_type},
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("Inference failed: %s", e)
            return {
                "model": model_name,
                "prediction": [],
                "confidence": 0.0,
                "latency_ms": 0,
                "error": str(e),
            }

    async def run_image_inference(self, model_name: str, image_bytes: bytes) -> Dict[str, Any]:
        """Run image classification/detection on Jetson."""
        return await self.run_inference(model_name, image_bytes, input_type="image")

    async def deploy_model(self, model_path: str) -> str:
        """Request Jetson to load a model. Returns model_id."""
        try:
            client = self._client_or_raise()
            r = await client.post("/models/deploy", json={"model_path": model_path})
            r.raise_for_status()
            data = r.json()
            model_id = data.get("model_id", "")
            logger.info("Deployed model: %s", model_id)
            return model_id
        except Exception as e:
            logger.warning("Model deploy failed: %s", e)
            return ""

    async def list_models(self) -> List[Dict[str, Any]]:
        """List loaded models on Jetson."""
        try:
            client = self._client_or_raise()
            r = await client.get("/models")
            r.raise_for_status()
            data = r.json()
            return data.get("models", [])
        except Exception as e:
            logger.warning("List models failed: %s", e)
            return []

    async def health_check(self) -> Dict[str, Any]:
        """Full health check with device info."""
        try:
            client = self._client_or_raise()
            r = await client.get("/health")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    @property
    def is_connected(self) -> bool:
        return self._connected
