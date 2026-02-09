"""
VRAM Manager for Earth2 + PersonaPlex - February 5, 2026

Smart VRAM management for running both PersonaPlex (voice AI) and
Earth2Studio (weather AI) on a single RTX 5090 (32GB VRAM).

Memory Budget:
- PersonaPlex/Moshi: ~23GB (fixed, always loaded)
- Earth2 models: ~6-8GB available
- System overhead: ~1GB

This manager:
1. Monitors GPU memory usage in real-time
2. Implements smart model loading with memory budgets
3. Unloads models when memory pressure is high
4. Prioritizes voice AI over weather models
5. Implements a model queue for sequential loading
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


class ModelPriority(Enum):
    """Model priority levels for VRAM allocation."""
    CRITICAL = 0    # Voice AI - never unload
    HIGH = 1        # Active weather model
    MEDIUM = 2      # Recently used models
    LOW = 3         # Idle models


@dataclass
class ModelInfo:
    """Information about a loaded model."""
    name: str
    vram_gb: float
    priority: ModelPriority
    loaded_at: datetime = field(default_factory=datetime.utcnow)
    last_used: datetime = field(default_factory=datetime.utcnow)
    load_time_seconds: float = 0.0
    inference_count: int = 0


@dataclass
class VRAMBudget:
    """VRAM budget configuration."""
    total_gb: float = 32.0
    personaplex_reserved_gb: float = 24.0  # Fixed reservation for voice
    system_overhead_gb: float = 1.0
    max_earth2_gb: float = 6.0  # Max for Earth2 models
    safety_margin_gb: float = 1.0


# Estimated VRAM usage for Earth2 models (GB)
EARTH2_MODEL_VRAM = {
    "fcn": 2.0,
    "pangu": 3.5,
    "graphcast": 2.5,
    "sfno": 1.5,
    "aurora": 3.0,
    "fuxi": 3.0,
    "dlwp": 1.5,
    "precipitation_afno": 1.0,
    "wind_afno": 1.0,
}


class VRAMManager:
    """
    Manages VRAM allocation for Earth2 and PersonaPlex.
    
    Ensures both services can run on a single RTX 5090 by:
    - Monitoring memory usage
    - Smart model loading/unloading
    - Priority-based allocation
    """
    
    def __init__(self, budget: Optional[VRAMBudget] = None):
        self.budget = budget or VRAMBudget()
        self.loaded_models: Dict[str, ModelInfo] = {}
        self.loading_lock = asyncio.Lock()
        self._monitoring_task: Optional[asyncio.Task] = None
        self._stop_monitoring = False
        self._memory_pressure = False
        self._callbacks: List[Callable[[Dict[str, Any]], Awaitable[None]]] = []
        
        # Initialize with actual GPU info
        self._init_gpu_info()
    
    def _init_gpu_info(self) -> None:
        """Initialize with actual GPU information."""
        try:
            import torch
            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                self.budget.total_gb = props.total_memory / (1024**3)
                logger.info(f"GPU detected: {props.name} ({self.budget.total_gb:.1f} GB)")
        except Exception as e:
            logger.warning(f"Could not detect GPU: {e}")
    
    def get_memory_status(self) -> Dict[str, Any]:
        """Get current GPU memory status."""
        try:
            import torch
            if torch.cuda.is_available():
                total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                allocated = torch.cuda.memory_allocated() / (1024**3)
                reserved = torch.cuda.memory_reserved() / (1024**3)
                free = total - reserved
                
                # Calculate available for Earth2
                earth2_available = max(0, free - self.budget.safety_margin_gb)
                
                return {
                    "total_gb": round(total, 2),
                    "allocated_gb": round(allocated, 2),
                    "reserved_gb": round(reserved, 2),
                    "free_gb": round(free, 2),
                    "earth2_available_gb": round(earth2_available, 2),
                    "earth2_budget_gb": self.budget.max_earth2_gb,
                    "personaplex_reserved_gb": self.budget.personaplex_reserved_gb,
                    "memory_pressure": allocated > (total * 0.9),
                    "timestamp": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            logger.error(f"Memory status error: {e}")
        
        return {
            "total_gb": self.budget.total_gb,
            "allocated_gb": 0,
            "free_gb": self.budget.total_gb,
            "earth2_available_gb": self.budget.max_earth2_gb,
            "error": "Could not read GPU memory",
        }
    
    def can_load_model(self, model_name: str) -> Dict[str, Any]:
        """
        Check if a model can be loaded within the budget.
        
        Returns dict with:
        - can_load: bool
        - reason: str
        - suggested_action: str (if can't load)
        """
        model_vram = EARTH2_MODEL_VRAM.get(model_name.lower(), 3.0)
        status = self.get_memory_status()
        available = status.get("earth2_available_gb", 0)
        
        # Check if already loaded
        if model_name.lower() in self.loaded_models:
            return {
                "can_load": True,
                "reason": "Model already loaded",
                "model": model_name,
                "vram_required_gb": 0,
            }
        
        # Check memory budget
        if model_vram <= available:
            return {
                "can_load": True,
                "reason": "Sufficient VRAM available",
                "model": model_name,
                "vram_required_gb": model_vram,
                "available_gb": available,
            }
        
        # Calculate what needs to be freed
        to_free = model_vram - available
        unloadable = self._get_unloadable_models(exclude=[model_name])
        unloadable_vram = sum(m.vram_gb for m in unloadable)
        
        if unloadable_vram >= to_free:
            # Can free enough by unloading other models
            to_unload = []
            freed = 0
            for m in unloadable:
                to_unload.append(m.name)
                freed += m.vram_gb
                if freed >= to_free:
                    break
            
            return {
                "can_load": True,
                "reason": "Will unload other models to make room",
                "model": model_name,
                "vram_required_gb": model_vram,
                "will_unload": to_unload,
            }
        
        return {
            "can_load": False,
            "reason": "Insufficient VRAM even after unloading other models",
            "model": model_name,
            "vram_required_gb": model_vram,
            "available_gb": available,
            "suggested_action": "PersonaPlex is using most VRAM. Consider using a smaller model.",
        }
    
    def _get_unloadable_models(self, exclude: List[str] = None) -> List[ModelInfo]:
        """Get list of models that can be unloaded, sorted by priority."""
        exclude = exclude or []
        unloadable = []
        
        for name, info in self.loaded_models.items():
            if name in exclude:
                continue
            if info.priority == ModelPriority.CRITICAL:
                continue
            unloadable.append(info)
        
        # Sort by priority (lowest first) then by last used (oldest first)
        unloadable.sort(key=lambda m: (m.priority.value, -m.last_used.timestamp()))
        return unloadable
    
    async def request_load(
        self,
        model_name: str,
        loader_func: Callable[[], Awaitable[Any]],
        priority: ModelPriority = ModelPriority.HIGH,
    ) -> Dict[str, Any]:
        """
        Request to load a model, managing VRAM as needed.
        
        Args:
            model_name: Name of the model to load
            loader_func: Async function that actually loads the model
            priority: Priority level for the model
        
        Returns:
            Result dict with success status and any errors
        """
        async with self.loading_lock:
            # Check if already loaded
            if model_name.lower() in self.loaded_models:
                self.loaded_models[model_name.lower()].last_used = datetime.utcnow()
                return {
                    "success": True,
                    "model": model_name,
                    "action": "already_loaded",
                }
            
            # Check if we can load
            check = self.can_load_model(model_name)
            
            if not check["can_load"]:
                return {
                    "success": False,
                    "model": model_name,
                    "error": check["reason"],
                    "suggestion": check.get("suggested_action"),
                }
            
            # Unload models if needed
            if "will_unload" in check:
                for model_to_unload in check["will_unload"]:
                    await self._unload_model(model_to_unload)
            
            # Load the model
            try:
                start_time = time.time()
                await loader_func()
                load_time = time.time() - start_time
                
                # Track the loaded model
                model_vram = EARTH2_MODEL_VRAM.get(model_name.lower(), 3.0)
                self.loaded_models[model_name.lower()] = ModelInfo(
                    name=model_name,
                    vram_gb=model_vram,
                    priority=priority,
                    load_time_seconds=load_time,
                )
                
                logger.info(f"Loaded model {model_name} ({model_vram:.1f} GB) in {load_time:.1f}s")
                
                return {
                    "success": True,
                    "model": model_name,
                    "action": "loaded",
                    "vram_gb": model_vram,
                    "load_time_seconds": load_time,
                }
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}")
                return {
                    "success": False,
                    "model": model_name,
                    "error": str(e),
                }
    
    async def _unload_model(self, model_name: str) -> bool:
        """Unload a model from GPU memory."""
        model_name = model_name.lower()
        
        if model_name not in self.loaded_models:
            return True
        
        info = self.loaded_models[model_name]
        
        if info.priority == ModelPriority.CRITICAL:
            logger.warning(f"Cannot unload critical model: {model_name}")
            return False
        
        try:
            # Trigger garbage collection to free VRAM
            import torch
            import gc
            
            del self.loaded_models[model_name]
            gc.collect()
            torch.cuda.empty_cache()
            
            logger.info(f"Unloaded model {model_name} ({info.vram_gb:.1f} GB freed)")
            return True
        except Exception as e:
            logger.error(f"Failed to unload model {model_name}: {e}")
            return False
    
    def mark_model_used(self, model_name: str) -> None:
        """Mark a model as recently used."""
        model_name = model_name.lower()
        if model_name in self.loaded_models:
            self.loaded_models[model_name].last_used = datetime.utcnow()
            self.loaded_models[model_name].inference_count += 1
    
    def get_loaded_models(self) -> List[Dict[str, Any]]:
        """Get list of currently loaded models."""
        return [
            {
                "name": info.name,
                "vram_gb": info.vram_gb,
                "priority": info.priority.name,
                "loaded_at": info.loaded_at.isoformat(),
                "last_used": info.last_used.isoformat(),
                "inference_count": info.inference_count,
            }
            for info in self.loaded_models.values()
        ]
    
    async def start_monitoring(self, interval_seconds: float = 5.0):
        """Start background VRAM monitoring."""
        self._stop_monitoring = False
        
        async def monitor_loop():
            while not self._stop_monitoring:
                try:
                    status = self.get_memory_status()
                    
                    # Check for memory pressure
                    was_pressure = self._memory_pressure
                    self._memory_pressure = status.get("memory_pressure", False)
                    
                    # Alert on memory pressure change
                    if self._memory_pressure and not was_pressure:
                        logger.warning("GPU memory pressure detected!")
                        await self._handle_memory_pressure()
                    
                    # Notify callbacks
                    for callback in self._callbacks:
                        try:
                            await callback(status)
                        except Exception as e:
                            logger.error(f"Monitor callback error: {e}")
                    
                except Exception as e:
                    logger.error(f"Monitor loop error: {e}")
                
                await asyncio.sleep(interval_seconds)
        
        self._monitoring_task = asyncio.create_task(monitor_loop())
        logger.info(f"VRAM monitoring started (interval: {interval_seconds}s)")
    
    async def stop_monitoring(self):
        """Stop background monitoring."""
        self._stop_monitoring = True
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("VRAM monitoring stopped")
    
    async def _handle_memory_pressure(self):
        """Handle memory pressure by unloading low-priority models."""
        unloadable = self._get_unloadable_models()
        
        if unloadable:
            # Unload lowest priority model
            model = unloadable[0]
            logger.warning(f"Memory pressure: unloading {model.name}")
            await self._unload_model(model.name)
    
    def register_callback(self, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Register a callback for memory status updates."""
        self._callbacks.append(callback)
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of VRAM manager status."""
        memory = self.get_memory_status()
        return {
            "memory": memory,
            "loaded_models": self.get_loaded_models(),
            "model_count": len(self.loaded_models),
            "memory_pressure": self._memory_pressure,
            "monitoring_active": self._monitoring_task is not None and not self._monitoring_task.done(),
        }


# Singleton instance
_manager: Optional[VRAMManager] = None


def get_vram_manager() -> VRAMManager:
    """Get or create the VRAM manager singleton."""
    global _manager
    if _manager is None:
        _manager = VRAMManager()
    return _manager


# Convenience functions
def get_memory_status() -> Dict[str, Any]:
    """Get current GPU memory status."""
    return get_vram_manager().get_memory_status()


def can_load_model(model_name: str) -> bool:
    """Check if a model can be loaded."""
    result = get_vram_manager().can_load_model(model_name)
    return result.get("can_load", False)


def get_loaded_models() -> List[Dict[str, Any]]:
    """Get list of loaded models."""
    return get_vram_manager().get_loaded_models()
