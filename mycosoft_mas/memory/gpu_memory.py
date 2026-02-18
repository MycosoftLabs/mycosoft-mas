"""
GPU State Memory System - February 5, 2026

Provides memory management for GPU resources:
- Model load/unload history tracking
- VRAM usage patterns and optimization
- Inference latency metrics
- Predictive model preloading based on usage patterns
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

logger = logging.getLogger("GPUMemory")


class GPUModelType(str, Enum):
    """Types of GPU models tracked."""
    MOSHI = "moshi"
    PERSONAPLEX = "personaplex"
    EARTH2_FCN = "earth2_fcn"
    EARTH2_PANGU = "earth2_pangu"
    EARTH2_GRAPHCAST = "earth2_graphcast"
    EARTH2_SFNO = "earth2_sfno"
    EARTH2_CORRDIFF = "earth2_corrdiff"
    EARTH2_STORMSCOPE = "earth2_stormscope"
    WHISPER = "whisper"
    STABLE_DIFFUSION = "stable_diffusion"
    CUSTOM = "custom"


class LoadState(str, Enum):
    """Model load state."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"


@dataclass
class ModelLoadEvent:
    """Record of a model load/unload event."""
    id: UUID = field(default_factory=uuid4)
    model_type: GPUModelType = GPUModelType.CUSTOM
    model_name: str = ""
    event_type: str = "load"  # 'load', 'unload', 'error'
    vram_mb: int = 0
    load_time_ms: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    error_message: Optional[str] = None
    triggered_by: str = "api"  # 'api', 'voice', 'scheduled', 'preload'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "model_type": self.model_type.value,
            "model_name": self.model_name,
            "event_type": self.event_type,
            "vram_mb": self.vram_mb,
            "load_time_ms": self.load_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error_message": self.error_message,
            "triggered_by": self.triggered_by
        }


@dataclass
class VRAMSnapshot:
    """Snapshot of VRAM state at a point in time."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_vram_mb: int = 32768  # Default 32GB
    used_vram_mb: int = 0
    free_vram_mb: int = 32768
    loaded_models: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_vram_mb": self.total_vram_mb,
            "used_vram_mb": self.used_vram_mb,
            "free_vram_mb": self.free_vram_mb,
            "loaded_models": self.loaded_models,
            "utilization_percent": round(self.used_vram_mb / self.total_vram_mb * 100, 1) if self.total_vram_mb > 0 else 0
        }


@dataclass
class ModelUsagePattern:
    """Usage pattern for a model for preload optimization."""
    model_type: GPUModelType
    model_name: str
    total_loads: int = 0
    total_inference_calls: int = 0
    avg_load_time_ms: float = 0.0
    avg_inference_time_ms: float = 0.0
    hourly_usage: Dict[int, int] = field(default_factory=dict)  # hour -> count
    daily_usage: Dict[str, int] = field(default_factory=dict)  # day_of_week -> count
    vram_mb: int = 0
    last_used: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_type": self.model_type.value,
            "model_name": self.model_name,
            "total_loads": self.total_loads,
            "total_inference_calls": self.total_inference_calls,
            "avg_load_time_ms": self.avg_load_time_ms,
            "avg_inference_time_ms": self.avg_inference_time_ms,
            "hourly_usage": self.hourly_usage,
            "daily_usage": self.daily_usage,
            "vram_mb": self.vram_mb,
            "last_used": self.last_used.isoformat() if self.last_used else None
        }
    
    def get_peak_hours(self, top_n: int = 3) -> List[int]:
        """Get the peak usage hours."""
        if not self.hourly_usage:
            return []
        sorted_hours = sorted(self.hourly_usage.items(), key=lambda x: x[1], reverse=True)
        return [h for h, _ in sorted_hours[:top_n]]


@dataclass
class InferenceMetric:
    """Single inference metric record."""
    model_name: str
    inference_time_ms: int
    input_size: Optional[int] = None
    output_size: Optional[int] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True


class GPUMemory:
    """
    Memory manager for GPU state and model loading.
    
    Provides:
    - Model load/unload history
    - VRAM usage tracking
    - Inference latency metrics
    - Predictive preloading recommendations
    """
    
    MAX_HISTORY_SIZE = 1000  # Max events to keep in memory
    VRAM_SNAPSHOT_INTERVAL = 60  # Seconds between snapshots
    
    def __init__(self, database_url: Optional[str] = None, total_vram_mb: int = 32768):
        self._database_url = database_url or os.getenv(
        if not self._database_url:
            raise ValueError(
                "MINDEX_DATABASE_URL environment variable is required. "
                "Please set it to your PostgreSQL connection string."
            )
            "MINDEX_DATABASE_URL",
            os.getenv("MINDEX_DATABASE_URL")
        )
        self._pool = None
        self._initialized = False
        self._total_vram_mb = total_vram_mb
        
        # Current state
        self._loaded_models: Dict[str, Dict[str, Any]] = {}  # model_name -> info
        self._current_vram_used_mb: int = 0
        
        # History
        self._load_history: List[ModelLoadEvent] = []
        self._vram_snapshots: List[VRAMSnapshot] = []
        self._inference_metrics: List[InferenceMetric] = []
        
        # Usage patterns
        self._usage_patterns: Dict[str, ModelUsagePattern] = {}
    
    async def initialize(self) -> None:
        """Initialize the GPU memory system."""
        if self._initialized:
            return
        
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=1,
                max_size=3
            )
            logger.info("GPU memory connected to database")
        except Exception as e:
            logger.warning(f"Database connection failed, using in-memory only: {e}")
        
        # Take initial VRAM snapshot
        await self._take_vram_snapshot()
        
        self._initialized = True
        logger.info("GPU memory manager initialized")
    
    async def record_model_load(
        self,
        model_name: str,
        model_type: str = "custom",
        vram_mb: int = 0,
        load_time_ms: int = 0,
        triggered_by: str = "api",
        success: bool = True,
        error_message: Optional[str] = None
    ) -> ModelLoadEvent:
        """
        Record a model load event.
        
        Args:
            model_name: Name of the model
            model_type: Type of model (moshi, earth2_fcn, etc.)
            vram_mb: VRAM used by the model
            load_time_ms: Time to load in milliseconds
            triggered_by: What triggered the load
            success: Whether load was successful
            error_message: Error message if failed
        
        Returns:
            Created ModelLoadEvent
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            model_type_enum = GPUModelType(model_type.lower())
        except ValueError:
            model_type_enum = GPUModelType.CUSTOM
        
        event = ModelLoadEvent(
            model_type=model_type_enum,
            model_name=model_name,
            event_type="load",
            vram_mb=vram_mb,
            load_time_ms=load_time_ms,
            success=success,
            error_message=error_message,
            triggered_by=triggered_by
        )
        
        # Update current state
        if success:
            self._loaded_models[model_name] = {
                "model_type": model_type,
                "vram_mb": vram_mb,
                "loaded_at": datetime.now(timezone.utc).isoformat()
            }
            self._current_vram_used_mb += vram_mb
        
        # Record event
        self._load_history.append(event)
        if len(self._load_history) > self.MAX_HISTORY_SIZE:
            self._load_history = self._load_history[-self.MAX_HISTORY_SIZE:]
        
        # Update usage pattern
        await self._update_usage_pattern(model_name, model_type_enum, vram_mb, load_time_ms)
        
        # Take VRAM snapshot
        await self._take_vram_snapshot()
        
        # Persist to database
        await self._persist_load_event(event)
        
        logger.debug(f"Recorded model load: {model_name} ({vram_mb}MB)")
        return event
    
    async def record_model_unload(
        self,
        model_name: str,
        triggered_by: str = "api"
    ) -> Optional[ModelLoadEvent]:
        """Record a model unload event."""
        if not self._initialized:
            await self.initialize()
        
        if model_name not in self._loaded_models:
            return None
        
        model_info = self._loaded_models.pop(model_name)
        vram_mb = model_info.get("vram_mb", 0)
        self._current_vram_used_mb -= vram_mb
        
        try:
            model_type_enum = GPUModelType(model_info.get("model_type", "custom").lower())
        except ValueError:
            model_type_enum = GPUModelType.CUSTOM
        
        event = ModelLoadEvent(
            model_type=model_type_enum,
            model_name=model_name,
            event_type="unload",
            vram_mb=vram_mb,
            triggered_by=triggered_by
        )
        
        self._load_history.append(event)
        await self._take_vram_snapshot()
        await self._persist_load_event(event)
        
        logger.debug(f"Recorded model unload: {model_name}")
        return event
    
    async def record_inference(
        self,
        model_name: str,
        inference_time_ms: int,
        input_size: Optional[int] = None,
        output_size: Optional[int] = None,
        success: bool = True
    ) -> None:
        """Record an inference execution."""
        if not self._initialized:
            await self.initialize()
        
        metric = InferenceMetric(
            model_name=model_name,
            inference_time_ms=inference_time_ms,
            input_size=input_size,
            output_size=output_size,
            success=success
        )
        
        self._inference_metrics.append(metric)
        if len(self._inference_metrics) > self.MAX_HISTORY_SIZE:
            self._inference_metrics = self._inference_metrics[-self.MAX_HISTORY_SIZE:]
        
        # Update usage pattern
        if model_name in self._usage_patterns:
            pattern = self._usage_patterns[model_name]
            pattern.total_inference_calls += 1
            total_time = pattern.avg_inference_time_ms * (pattern.total_inference_calls - 1) + inference_time_ms
            pattern.avg_inference_time_ms = total_time / pattern.total_inference_calls
            pattern.last_used = datetime.now(timezone.utc)
            
            # Update hourly usage
            hour = datetime.now(timezone.utc).hour
            pattern.hourly_usage[hour] = pattern.hourly_usage.get(hour, 0) + 1
            
            # Update daily usage
            day = datetime.now(timezone.utc).strftime("%A")
            pattern.daily_usage[day] = pattern.daily_usage.get(day, 0) + 1
    
    async def get_current_state(self) -> Dict[str, Any]:
        """Get current GPU memory state."""
        return {
            "total_vram_mb": self._total_vram_mb,
            "used_vram_mb": self._current_vram_used_mb,
            "free_vram_mb": self._total_vram_mb - self._current_vram_used_mb,
            "utilization_percent": round(self._current_vram_used_mb / self._total_vram_mb * 100, 1),
            "loaded_models": self._loaded_models,
            "model_count": len(self._loaded_models)
        }
    
    async def get_load_history(
        self,
        limit: int = 50,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get model load/unload history."""
        history = self._load_history
        if event_type:
            history = [e for e in history if e.event_type == event_type]
        
        return [e.to_dict() for e in history[-limit:]]
    
    async def get_vram_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get VRAM usage history."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [
            s.to_dict() for s in self._vram_snapshots
            if s.timestamp > cutoff
        ]
    
    async def get_usage_patterns(self) -> Dict[str, Any]:
        """Get all model usage patterns."""
        return {
            name: pattern.to_dict()
            for name, pattern in self._usage_patterns.items()
        }
    
    async def get_preload_recommendations(
        self,
        available_vram_mb: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get model preload recommendations based on usage patterns.
        
        Returns models likely to be used soon, prioritized by usage frequency
        and fitting within available VRAM.
        """
        if available_vram_mb is None:
            available_vram_mb = self._total_vram_mb - self._current_vram_used_mb
        
        current_hour = datetime.now(timezone.utc).hour
        current_day = datetime.now(timezone.utc).strftime("%A")
        
        recommendations = []
        
        for name, pattern in self._usage_patterns.items():
            # Skip already loaded models
            if name in self._loaded_models:
                continue
            
            # Skip models too large
            if pattern.vram_mb > available_vram_mb:
                continue
            
            # Calculate score based on usage patterns
            hourly_score = pattern.hourly_usage.get(current_hour, 0)
            daily_score = pattern.daily_usage.get(current_day, 0)
            recency_score = 0
            if pattern.last_used:
                hours_since_use = (datetime.now(timezone.utc) - pattern.last_used).total_seconds() / 3600
                recency_score = max(0, 24 - hours_since_use) / 24 * 10
            
            total_score = hourly_score * 2 + daily_score + recency_score + pattern.total_inference_calls / 100
            
            if total_score > 0:
                recommendations.append({
                    "model_name": name,
                    "model_type": pattern.model_type.value,
                    "vram_mb": pattern.vram_mb,
                    "score": round(total_score, 2),
                    "peak_hours": pattern.get_peak_hours(),
                    "avg_load_time_ms": round(pattern.avg_load_time_ms, 0)
                })
        
        # Sort by score
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        return recommendations[:5]
    
    async def can_load_model(self, vram_mb: int) -> Tuple[bool, str]:
        """Check if a model can be loaded given current VRAM."""
        available = self._total_vram_mb - self._current_vram_used_mb
        
        if vram_mb <= available:
            return True, f"Sufficient VRAM: {available}MB available, {vram_mb}MB needed"
        
        # Check if we can unload models to make room
        unloadable_vram = sum(
            info.get("vram_mb", 0)
            for info in self._loaded_models.values()
        )
        
        if vram_mb <= available + unloadable_vram:
            return True, f"VRAM available after unloading models: {unloadable_vram}MB can be freed"
        
        return False, f"Insufficient VRAM: {available}MB available, {vram_mb}MB needed, only {unloadable_vram}MB can be freed"
    
    async def suggest_models_to_unload(self, required_vram_mb: int) -> List[str]:
        """Suggest models to unload to free up VRAM."""
        available = self._total_vram_mb - self._current_vram_used_mb
        needed = required_vram_mb - available
        
        if needed <= 0:
            return []
        
        # Sort loaded models by usage (least recently used first)
        models_by_usage = []
        for name, info in self._loaded_models.items():
            pattern = self._usage_patterns.get(name)
            score = 0
            if pattern and pattern.last_used:
                score = (datetime.now(timezone.utc) - pattern.last_used).total_seconds()
            models_by_usage.append((name, info.get("vram_mb", 0), score))
        
        models_by_usage.sort(key=lambda x: x[2], reverse=True)  # LRU first
        
        to_unload = []
        freed = 0
        for name, vram, _ in models_by_usage:
            if freed >= needed:
                break
            to_unload.append(name)
            freed += vram
        
        return to_unload
    
    async def get_context_for_llm(self) -> Dict[str, Any]:
        """Get GPU context for LLM prompt injection."""
        state = await self.get_current_state()
        
        model_list = [
            f"{name} ({info.get('vram_mb', 0)}MB)"
            for name, info in self._loaded_models.items()
        ]
        
        return {
            "vram_total_mb": self._total_vram_mb,
            "vram_used_mb": self._current_vram_used_mb,
            "vram_free_mb": state["free_vram_mb"],
            "utilization_percent": state["utilization_percent"],
            "loaded_models": model_list,
            "model_count": len(self._loaded_models)
        }
    
    async def _update_usage_pattern(
        self,
        model_name: str,
        model_type: GPUModelType,
        vram_mb: int,
        load_time_ms: int
    ) -> None:
        """Update usage pattern for a model."""
        if model_name not in self._usage_patterns:
            self._usage_patterns[model_name] = ModelUsagePattern(
                model_type=model_type,
                model_name=model_name,
                vram_mb=vram_mb
            )
        
        pattern = self._usage_patterns[model_name]
        pattern.total_loads += 1
        
        # Update average load time
        total_time = pattern.avg_load_time_ms * (pattern.total_loads - 1) + load_time_ms
        pattern.avg_load_time_ms = total_time / pattern.total_loads
        
        pattern.last_used = datetime.now(timezone.utc)
        
        # Update hourly usage
        hour = datetime.now(timezone.utc).hour
        pattern.hourly_usage[hour] = pattern.hourly_usage.get(hour, 0) + 1
        
        # Update daily usage
        day = datetime.now(timezone.utc).strftime("%A")
        pattern.daily_usage[day] = pattern.daily_usage.get(day, 0) + 1
    
    async def _take_vram_snapshot(self) -> None:
        """Take a VRAM usage snapshot."""
        snapshot = VRAMSnapshot(
            total_vram_mb=self._total_vram_mb,
            used_vram_mb=self._current_vram_used_mb,
            free_vram_mb=self._total_vram_mb - self._current_vram_used_mb,
            loaded_models=list(self._loaded_models.keys())
        )
        
        self._vram_snapshots.append(snapshot)
        
        # Keep last 24 hours of snapshots (assuming 1 per minute = 1440)
        if len(self._vram_snapshots) > 1440:
            self._vram_snapshots = self._vram_snapshots[-1440:]
    
    async def _persist_load_event(self, event: ModelLoadEvent) -> bool:
        """Persist a load event to the database."""
        if not self._pool:
            return False
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO mindex.gpu_model_events
                        (id, model_type, model_name, event_type, vram_mb, load_time_ms,
                         timestamp, success, error_message, triggered_by)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """, str(event.id), event.model_type.value, event.model_name,
                    event.event_type, event.vram_mb, event.load_time_ms,
                    event.timestamp, event.success, event.error_message, event.triggered_by)
            return True
        except Exception as e:
            logger.error(f"Failed to persist load event: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get GPU memory statistics."""
        state = await self.get_current_state()
        return {
            "initialized": self._initialized,
            "database_connected": self._pool is not None,
            **state,
            "total_load_events": len(self._load_history),
            "total_snapshots": len(self._vram_snapshots),
            "total_inference_metrics": len(self._inference_metrics),
            "tracked_models": len(self._usage_patterns)
        }
    
    async def shutdown(self) -> None:
        """Shutdown the GPU memory manager."""
        if self._pool:
            await self._pool.close()
        logger.info("GPU memory manager shutdown")


# Singleton instance
_gpu_memory: Optional[GPUMemory] = None


async def get_gpu_memory() -> GPUMemory:
    """Get or create the singleton GPU memory instance."""
    global _gpu_memory
    if _gpu_memory is None:
        _gpu_memory = GPUMemory()
        await _gpu_memory.initialize()
    return _gpu_memory