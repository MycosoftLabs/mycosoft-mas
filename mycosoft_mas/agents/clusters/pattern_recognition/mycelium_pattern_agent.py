"""
Mycelium Pattern Agent for Mycology BioAgent System

This agent analyzes mycelium growth patterns, detects signal patterns,
coordinates with simulation data, and updates pattern databases.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
import json
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus, TaskType, TaskStatus, TaskPriority

class PatternType(Enum):
    """Types of mycelium growth patterns"""
    BRANCHING = auto()
    RHIZOMORPHIC = auto()
    TOMENTOSE = auto()
    SECTORING = auto()
    AERIAL = auto()
    STROMA = auto()
    CUSTOM = auto()

class SignalType(Enum):
    """Types of mycelial signals"""
    ELECTRICAL = auto()
    CHEMICAL = auto()
    METABOLIC = auto()
    MECHANICAL = auto()
    OPTICAL = auto()
    CUSTOM = auto()

@dataclass
class GrowthPattern:
    """Growth pattern information"""
    pattern_id: str
    pattern_type: PatternType
    species_id: str
    morphology: Dict[str, Any]  # Morphological characteristics
    metrics: Dict[str, float]  # Quantitative measurements
    images: List[str]  # Image references
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class SignalPattern:
    """Signal pattern information"""
    signal_id: str
    signal_type: SignalType
    species_id: str
    frequency: float  # Hz
    amplitude: float  # Normalized amplitude
    duration: float  # seconds
    waveform: List[float]  # Signal waveform data
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class PatternAnalysisResult:
    """Results of pattern analysis"""
    analysis_id: str
    species_id: str
    growth_patterns: List[GrowthPattern]
    signal_patterns: List[SignalPattern]
    correlations: Dict[str, float]  # Pattern correlations
    anomalies: List[Dict[str, Any]]  # Detected anomalies
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

class MyceliumPatternAgent(BaseAgent):
    """Agent for analyzing mycelium growth patterns"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.growth_patterns: Dict[str, GrowthPattern] = {}
        self.signal_patterns: Dict[str, SignalPattern] = {}
        self.analysis_results: Dict[str, PatternAnalysisResult] = {}
        self.analysis_queue: asyncio.Queue = asyncio.Queue()
        
        # Create necessary directories
        self.data_dir = Path("data/mycelium_patterns")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metrics
        self.metrics.update({
            "patterns_detected": 0,
            "signals_analyzed": 0,
            "analyses_completed": 0,
            "anomalies_detected": 0,
            "analysis_errors": 0
        })
    
    async def initialize(self) -> None:
        """Initialize the agent"""
        await super().initialize()
        await self._load_patterns()
        self.status = AgentStatus.READY
        self.logger.info("Mycelium Pattern Agent initialized")
    
    async def stop(self) -> None:
        """Stop the agent"""
        self.status = AgentStatus.STOPPING
        self.logger.info("Stopping Mycelium Pattern Agent")
        await self._save_patterns()
        await super().stop()
    
    async def register_growth_pattern(
        self,
        pattern_type: PatternType,
        species_id: str,
        morphology: Dict[str, Any],
        metrics: Dict[str, float],
        images: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register a new growth pattern"""
        pattern_id = f"pattern_{len(self.growth_patterns)}"
        
        pattern = GrowthPattern(
            pattern_id=pattern_id,
            pattern_type=pattern_type,
            species_id=species_id,
            morphology=morphology,
            metrics=metrics,
            images=images,
            metadata=metadata or {}
        )
        
        self.growth_patterns[pattern_id] = pattern
        await self._save_patterns()
        
        self.metrics["patterns_detected"] += 1
        return pattern_id
    
    async def register_signal_pattern(
        self,
        signal_type: SignalType,
        species_id: str,
        frequency: float,
        amplitude: float,
        duration: float,
        waveform: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register a new signal pattern"""
        signal_id = f"signal_{len(self.signal_patterns)}"
        
        signal = SignalPattern(
            signal_id=signal_id,
            signal_type=signal_type,
            species_id=species_id,
            frequency=frequency,
            amplitude=amplitude,
            duration=duration,
            waveform=waveform,
            metadata=metadata or {}
        )
        
        self.signal_patterns[signal_id] = signal
        await self._save_patterns()
        
        self.metrics["signals_analyzed"] += 1
        return signal_id
    
    async def analyze_patterns(
        self,
        species_id: str,
        growth_data: Dict[str, Any],
        signal_data: Dict[str, Any]
    ) -> str:
        """Analyze patterns for a species"""
        analysis_id = f"analysis_{len(self.analysis_results)}"
        
        # Create initial analysis result
        result = PatternAnalysisResult(
            analysis_id=analysis_id,
            species_id=species_id,
            growth_patterns=[],
            signal_patterns=[],
            correlations={},
            anomalies=[],
            metadata={}
        )
        
        self.analysis_results[analysis_id] = result
        await self.analysis_queue.put({
            "analysis_id": analysis_id,
            "growth_data": growth_data,
            "signal_data": signal_data
        })
        
        return analysis_id
    
    async def get_analysis_result(self, analysis_id: str) -> Optional[PatternAnalysisResult]:
        """Get the results of pattern analysis"""
        return self.analysis_results.get(analysis_id)
    
    async def _load_patterns(self) -> None:
        """Load patterns from disk"""
        # Load growth patterns
        growth_file = self.data_dir / "growth_patterns.json"
        if growth_file.exists():
            with open(growth_file, "r") as f:
                patterns_data = json.load(f)
                
                for pattern_data in patterns_data:
                    pattern = GrowthPattern(
                        pattern_id=pattern_data["pattern_id"],
                        pattern_type=PatternType[pattern_data["pattern_type"]],
                        species_id=pattern_data["species_id"],
                        morphology=pattern_data["morphology"],
                        metrics=pattern_data["metrics"],
                        images=pattern_data["images"],
                        metadata=pattern_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(pattern_data["created_at"]),
                        updated_at=datetime.fromisoformat(pattern_data["updated_at"])
                    )
                    
                    self.growth_patterns[pattern.pattern_id] = pattern
        
        # Load signal patterns
        signal_file = self.data_dir / "signal_patterns.json"
        if signal_file.exists():
            with open(signal_file, "r") as f:
                signals_data = json.load(f)
                
                for signal_data in signals_data:
                    signal = SignalPattern(
                        signal_id=signal_data["signal_id"],
                        signal_type=SignalType[signal_data["signal_type"]],
                        species_id=signal_data["species_id"],
                        frequency=signal_data["frequency"],
                        amplitude=signal_data["amplitude"],
                        duration=signal_data["duration"],
                        waveform=signal_data["waveform"],
                        metadata=signal_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(signal_data["created_at"]),
                        updated_at=datetime.fromisoformat(signal_data["updated_at"])
                    )
                    
                    self.signal_patterns[signal.signal_id] = signal
    
    async def _save_patterns(self) -> None:
        """Save patterns to disk"""
        # Save growth patterns
        growth_file = self.data_dir / "growth_patterns.json"
        patterns_data = []
        
        for pattern in self.growth_patterns.values():
            pattern_data = {
                "pattern_id": pattern.pattern_id,
                "pattern_type": pattern.pattern_type.name,
                "species_id": pattern.species_id,
                "morphology": pattern.morphology,
                "metrics": pattern.metrics,
                "images": pattern.images,
                "metadata": pattern.metadata,
                "created_at": pattern.created_at.isoformat(),
                "updated_at": pattern.updated_at.isoformat()
            }
            patterns_data.append(pattern_data)
        
        with open(growth_file, "w") as f:
            json.dump(patterns_data, f, indent=2)
        
        # Save signal patterns
        signal_file = self.data_dir / "signal_patterns.json"
        signals_data = []
        
        for signal in self.signal_patterns.values():
            signal_data = {
                "signal_id": signal.signal_id,
                "signal_type": signal.signal_type.name,
                "species_id": signal.species_id,
                "frequency": signal.frequency,
                "amplitude": signal.amplitude,
                "duration": signal.duration,
                "waveform": signal.waveform,
                "metadata": signal.metadata,
                "created_at": signal.created_at.isoformat(),
                "updated_at": signal.updated_at.isoformat()
            }
            signals_data.append(signal_data)
        
        with open(signal_file, "w") as f:
            json.dump(signals_data, f, indent=2)
    
    async def _process_analysis_queue(self) -> None:
        """Process the analysis queue"""
        while self.status == AgentStatus.RUNNING:
            try:
                # Get next analysis task
                task = await self.analysis_queue.get()
                
                # Perform analysis
                await self._perform_analysis(
                    task["analysis_id"],
                    task["growth_data"],
                    task["signal_data"]
                )
                
                # Update metrics
                self.metrics["analyses_completed"] += 1
                
                # Mark task as complete
                self.analysis_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing analysis: {str(e)}")
                self.metrics["analysis_errors"] += 1
                continue
    
    async def _perform_analysis(
        self,
        analysis_id: str,
        growth_data: Dict[str, Any],
        signal_data: Dict[str, Any]
    ) -> None:
        """Perform pattern analysis"""
        try:
            result = self.analysis_results[analysis_id]
            
            # Analyze growth patterns
            growth_patterns = await self._analyze_growth_patterns(growth_data)
            result.growth_patterns.extend(growth_patterns)
            
            # Analyze signal patterns
            signal_patterns = await self._analyze_signal_patterns(signal_data)
            result.signal_patterns.extend(signal_patterns)
            
            # Calculate correlations
            result.correlations = await self._calculate_correlations(
                growth_patterns,
                signal_patterns
            )
            
            # Detect anomalies
            result.anomalies = await self._detect_anomalies(
                growth_patterns,
                signal_patterns
            )
            
            result.updated_at = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(f"Error performing analysis {analysis_id}: {str(e)}")
            self.metrics["analysis_errors"] += 1
    
    async def _analyze_growth_patterns(
        self,
        growth_data: Dict[str, Any]
    ) -> List[GrowthPattern]:
        """Analyze growth patterns from data"""
        # Implementation for growth pattern analysis
        return []
    
    async def _analyze_signal_patterns(
        self,
        signal_data: Dict[str, Any]
    ) -> List[SignalPattern]:
        """Analyze signal patterns from data"""
        # Implementation for signal pattern analysis
        return []
    
    async def _calculate_correlations(
        self,
        growth_patterns: List[GrowthPattern],
        signal_patterns: List[SignalPattern]
    ) -> Dict[str, float]:
        """Calculate correlations between patterns"""
        # Implementation for correlation calculation
        return {}
    
    async def _detect_anomalies(
        self,
        growth_patterns: List[GrowthPattern],
        signal_patterns: List[SignalPattern]
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in patterns"""
        # Implementation for anomaly detection
        return [] 