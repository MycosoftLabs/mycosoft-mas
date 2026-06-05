"""NLM bridge — RootedFrameBuilder + NLMWorldModel when NLM package is on PYTHONPATH."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from nlm.core.frames import RootedNatureFrame  # noqa: F401
    from nlm.data.rooted_frame_builder import RootedFrameBuilder
    from nlm.model.nlm_model import NLMConfig, NLMWorldModel

    _NLM_AVAILABLE = True
except ImportError:
    RootedNatureFrame = Any  # type: ignore[misc, assignment]
    RootedFrameBuilder = None  # type: ignore[misc, assignment]
    NLMWorldModel = None  # type: ignore[misc, assignment]
    NLMConfig = None  # type: ignore[misc, assignment]
    _NLM_AVAILABLE = False


class NlmInterface:
    """Builds frames and runs world-model predictions; AVANI hook on outputs."""

    def __init__(self, enabled: bool | None = None) -> None:
        self._enabled = enabled if enabled is not None else _NLM_AVAILABLE
        self._builder = RootedFrameBuilder() if _NLM_AVAILABLE and RootedFrameBuilder else None
        self._model = None
        if _NLM_AVAILABLE and NLMWorldModel and NLMConfig:
            try:
                self._model = NLMWorldModel(NLMConfig(d_model=256))
            except Exception as e:
                logger.warning("NLMWorldModel init skipped: %s", e)

    async def build_frame_async(
        self,
        raw_data: dict[str, Any],
        lat: float,
        lon: float,
        alt: float,
        *,
        classify_library: bool = False,
    ) -> Any:
        """Async frame build with optional MINDEX library_blob_id resolution."""
        library_blob_id = raw_data.get("library_blob_id")
        waveform_refs = None
        library_extras: dict[str, Any] = {}

        if library_blob_id:
            try:
                from mycosoft_mas.nlm.library_frames import (
                    build_library_frame_extras,
                    waveform_refs_to_nlm,
                )

                library_extras = await build_library_frame_extras(
                    str(library_blob_id),
                    classify=classify_library,
                )
                waveform_refs = waveform_refs_to_nlm(library_extras.get("waveform_refs") or [])
            except Exception as e:
                logger.warning("library_blob_id resolution failed: %s", e)

        frame = self.build_frame(
            raw_data,
            lat,
            lon,
            alt,
            waveform_refs=waveform_refs,
        )
        if library_extras and isinstance(frame, dict):
            frame.update(library_extras)
        return frame

    def build_frame(
        self,
        raw_data: dict[str, Any],
        lat: float,
        lon: float,
        alt: float,
        waveform_refs: Any = None,
    ) -> Any:
        """Return RootedNatureFrame when NLM installed; else a geo-tagged envelope stub."""
        if self._builder is None:
            out: dict[str, Any] = {
                "stub": True,
                "geo": {"lat": lat, "lon": lon, "alt": alt},
                "raw_data": raw_data,
                "note": "Install NLM package and set HARNESS_NLM_ENABLED=1",
            }
            if raw_data.get("library_blob_id"):
                out["library_blob_id"] = raw_data["library_blob_id"]
            if waveform_refs:
                out["waveform_refs"] = waveform_refs
            return out
        try:
            from nlm.core.protocols import DeviceEnvelope

            envelope = DeviceEnvelope.model_validate(
                {
                    **raw_data,
                    "latitude": lat,
                    "longitude": lon,
                    "altitude_m": alt,
                }
            )
            if waveform_refs is not None:
                try:
                    return self._builder.build(envelope, waveform_refs=waveform_refs)
                except TypeError:
                    pass
            return self._builder.build(envelope)
        except Exception as e:
            logger.warning("build_frame fallback stub: %s", e)
            return {
                "stub": True,
                "geo": {"lat": lat, "lon": lon, "alt": alt},
                "raw_data": raw_data,
            }

    def predict(self, frame: Any) -> dict[str, Any]:
        out: dict[str, Any] = {
            "next_state": {},
            "anomaly_score": 0.0,
            "grounding_confidence": 1.0,
        }
        if self._model is None:
            return out
        try:
            # Actual forward pass is model-specific; placeholder contract for harness
            out["anomaly_score"] = 0.1
            out["grounding_confidence"] = 0.95
        except Exception as e:
            logger.warning("NLM predict failed: %s", e)
        if not self.guardian_veto(out):
            out["guardian"] = "allow"
        else:
            out["guardian"] = "veto"
        return out

    def guardian_veto(self, prediction: dict[str, Any]) -> bool:
        """AVANI can extend this path; default threshold-only guard."""
        try:
            from nlm.guardian.avani import AVANIGuardian  # noqa: F401

            _ = AVANIGuardian  # wired when full tensor evaluation is enabled
        except ImportError:
            pass
        return float(prediction.get("anomaly_score", 0)) > 0.99
