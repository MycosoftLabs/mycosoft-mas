"""NatureOS Signal Processor - February 3, 2026"""
import asyncio
import logging
import numpy as np
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from collections import deque
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class SignalType(str, Enum):
    BIOELECTRIC = "bioelectric"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    PRESSURE = "pressure"
    GAS_RESISTANCE = "gas_resistance"
    VOC = "voc"
    SPORE_COUNT = "spore_count"
    ACOUSTIC = "acoustic"
    OPTICAL = "optical"
    CHEMICAL = "chemical"

class PatternClass(str, Enum):
    NORMAL = "normal"
    SPIKE = "spike"
    OSCILLATION = "oscillation"
    BURST = "burst"
    STRESS_RESPONSE = "stress_response"
    NUTRIENT_RESPONSE = "nutrient_response"
    COMMUNICATION = "communication"
    ENVIRONMENTAL_ALERT = "environmental_alert"
    UNKNOWN = "unknown"

class ProcessedSignal(BaseModel):
    signal_id: UUID
    device_id: UUID
    signal_type: str
    pattern_class: str
    confidence: float
    features: Dict[str, float]
    anomaly_score: float
    processed_at: datetime
    metadata: Dict[str, Any] = {}

class SignalProcessor:
    def __init__(self, config: Any):
        self.config = config
        self.num_workers = getattr(config, "signal_processing_workers", 4)
        self._running = False
        self._signal_buffers: Dict[UUID, deque] = {}
        self._pattern_cache: Dict[str, Dict[str, Any]] = {}
        self._processing_queue: asyncio.Queue = asyncio.Queue()
        self.window_size = 256
        self.overlap = 0.5
        logger.info("Signal Processor initialized")
    
    async def start(self) -> None:
        self._running = True
        for i in range(self.num_workers):
            asyncio.create_task(self._processing_worker(i))
        logger.info(f"Signal Processor started with {self.num_workers} workers")
    
    async def shutdown(self) -> None:
        self._running = False
        logger.info("Signal Processor shutdown")
    
    async def health_check(self) -> bool:
        return self._running
    
    async def process(self, device_id: UUID, signal_data: bytes, signal_type: str) -> Dict[str, Any]:
        try:
            samples = np.frombuffer(signal_data, dtype=np.float32)
            normalized = self._normalize_signal(samples)
            features = self._extract_features(normalized)
            pattern_class, confidence = self._classify_pattern_internal(normalized, features)
            anomaly_score = self._calculate_anomaly_score(features, signal_type)
            result = ProcessedSignal(
                signal_id=uuid4(), device_id=device_id, signal_type=signal_type,
                pattern_class=pattern_class.value, confidence=confidence,
                features=features, anomaly_score=anomaly_score,
                processed_at=datetime.now(timezone.utc),
                metadata={"sample_count": len(samples), "processing_version": "1.0"}
            )
            self._cache_pattern(device_id, result)
            return result.dict()
        except Exception as e:
            logger.error(f"Error processing signal from {device_id}: {e}")
            raise
    
    async def classify_pattern(self, signal_data: bytes) -> Dict[str, Any]:
        samples = np.frombuffer(signal_data, dtype=np.float32)
        normalized = self._normalize_signal(samples)
        features = self._extract_features(normalized)
        pattern_class, confidence = self._classify_pattern_internal(normalized, features)
        return {"pattern_class": pattern_class.value, "confidence": confidence, "features": features}
    
    def _normalize_signal(self, samples: np.ndarray) -> np.ndarray:
        if len(samples) == 0: return samples
        mean, std = np.mean(samples), np.std(samples)
        return (samples - mean) / std if std > 0 else samples - mean
    
    def _extract_features(self, samples: np.ndarray) -> Dict[str, float]:
        if len(samples) == 0: return {}
        features = {
            "mean": float(np.mean(samples)), "std": float(np.std(samples)),
            "min": float(np.min(samples)), "max": float(np.max(samples)),
            "range": float(np.max(samples) - np.min(samples)),
            "rms": float(np.sqrt(np.mean(samples**2))),
            "zero_crossings": float(np.sum(np.diff(np.sign(samples)) != 0))
        }
        peaks = self._find_peaks(samples)
        features["num_peaks"] = float(len(peaks))
        if len(peaks) > 1:
            peak_intervals = np.diff(peaks)
            features["mean_peak_interval"] = float(np.mean(peak_intervals))
            features["peak_interval_std"] = float(np.std(peak_intervals))
        else:
            features["mean_peak_interval"] = 0.0
            features["peak_interval_std"] = 0.0
        if len(samples) >= 4:
            fft_result = np.fft.fft(samples)
            fft_magnitude = np.abs(fft_result[:len(samples)//2])
            features["spectral_energy"] = float(np.sum(fft_magnitude**2))
            features["dominant_freq_idx"] = float(np.argmax(fft_magnitude))
            features["spectral_centroid"] = float(np.sum(np.arange(len(fft_magnitude)) * fft_magnitude) / (np.sum(fft_magnitude) + 1e-10))
        return features
    
    def _find_peaks(self, samples: np.ndarray, threshold: float = 0.5) -> List[int]:
        peaks = []
        for i in range(1, len(samples) - 1):
            if samples[i] > samples[i-1] and samples[i] > samples[i+1] and samples[i] > threshold:
                peaks.append(i)
        return peaks
    
    def _classify_pattern_internal(self, samples: np.ndarray, features: Dict[str, float]) -> Tuple[PatternClass, float]:
        if features.get("num_peaks", 0) > 10 and features.get("range", 0) > 2.0:
            if features.get("mean_peak_interval", 0) < 10: return PatternClass.BURST, 0.85
            return PatternClass.SPIKE, 0.80
        if features.get("zero_crossings", 0) > len(samples) * 0.3:
            if 5 < features.get("spectral_centroid", 0) < 50: return PatternClass.OSCILLATION, 0.75
        if features.get("std", 0) > 1.5 and features.get("kurtosis", 0) > 3:
            return PatternClass.STRESS_RESPONSE, 0.70
        if features.get("std", 0) < 0.5 and features.get("range", 0) < 1.0:
            return PatternClass.NORMAL, 0.85
        return PatternClass.UNKNOWN, 0.40
    
    def _calculate_anomaly_score(self, features: Dict[str, float], signal_type: str) -> float:
        ranges = {"bioelectric": {"std": (0.1, 2.0), "range": (0.5, 5.0)}}
        r = ranges.get(signal_type, {"std": (0.1, 2.0), "range": (0.5, 5.0)})
        score = 0.0
        std = features.get("std", 0)
        if std < r["std"][0]: score += 0.3 * (r["std"][0] - std) / r["std"][0]
        elif std > r["std"][1]: score += 0.3 * (std - r["std"][1]) / r["std"][1]
        return min(1.0, score)
    
    def _cache_pattern(self, device_id: UUID, result: ProcessedSignal) -> None:
        self._pattern_cache[str(device_id)] = {
            "pattern_class": result.pattern_class, "confidence": result.confidence,
            "timestamp": result.processed_at.isoformat(), "features": result.features
        }
    
    async def _processing_worker(self, worker_id: int) -> None:
        while self._running:
            try:
                job = await asyncio.wait_for(self._processing_queue.get(), timeout=1.0)
                await self.process(**job)
            except asyncio.TimeoutError: continue
            except asyncio.CancelledError: break
            except Exception as e: logger.error(f"Worker {worker_id} error: {e}")
