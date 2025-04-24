"""
Environmental Pattern Agent for Mycology BioAgent System

This agent analyzes environmental patterns affecting mycelial growth,
detects environmental triggers, and correlates conditions with growth outcomes.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from datetime import datetime
import json
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus, TaskType, TaskStatus, TaskPriority

class EnvironmentalFactorType(Enum):
    """Types of environmental factors"""
    TEMPERATURE = auto()
    HUMIDITY = auto()
    CO2_LEVEL = auto()
    LIGHT_INTENSITY = auto()
    AIR_FLOW = auto()
    SUBSTRATE_MOISTURE = auto()
    PH_LEVEL = auto()
    NUTRIENT_LEVEL = auto()
    CONTAMINATION = auto()
    CUSTOM = auto()

class PatternFrequency(Enum):
    """Frequency of environmental patterns"""
    HOURLY = auto()
    DAILY = auto()
    WEEKLY = auto()
    MONTHLY = auto()
    SEASONAL = auto()
    CUSTOM = auto()

@dataclass
class EnvironmentalMeasurement:
    """Single environmental measurement"""
    measurement_id: str
    factor_type: EnvironmentalFactorType
    value: float
    unit: str
    timestamp: datetime
    location: Optional[Dict[str, float]] = None  # Optional spatial coordinates
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EnvironmentalPattern:
    """Environmental pattern information"""
    pattern_id: str
    factor_type: EnvironmentalFactorType
    frequency: PatternFrequency
    measurements: List[EnvironmentalMeasurement]
    trend: Dict[str, float]  # Statistical trends
    seasonality: Dict[str, float]  # Seasonal components
    thresholds: Dict[str, float]  # Critical thresholds
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class PatternAnalysisResult:
    """Results of environmental pattern analysis"""
    analysis_id: str
    patterns: List[EnvironmentalPattern]
    correlations: Dict[str, float]  # Inter-factor correlations
    anomalies: List[Dict[str, Any]]  # Detected anomalies
    recommendations: List[Dict[str, Any]]  # Optimization recommendations
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

class EnvironmentalPatternAgent(BaseAgent):
    """Agent for analyzing environmental patterns"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.measurements: Dict[str, EnvironmentalMeasurement] = {}
        self.patterns: Dict[str, EnvironmentalPattern] = {}
        self.analysis_results: Dict[str, PatternAnalysisResult] = {}
        self.analysis_queue: asyncio.Queue = asyncio.Queue()
        
        # Create necessary directories
        self.data_dir = Path("data/environmental_patterns")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metrics
        self.metrics.update({
            "measurements_recorded": 0,
            "patterns_detected": 0,
            "analyses_completed": 0,
            "anomalies_detected": 0,
            "analysis_errors": 0
        })
    
    async def initialize(self) -> None:
        """Initialize the agent"""
        await super().initialize()
        await self._load_patterns()
        self.status = AgentStatus.READY
        self.logger.info("Environmental Pattern Agent initialized")
    
    async def stop(self) -> None:
        """Stop the agent"""
        self.status = AgentStatus.STOPPING
        self.logger.info("Stopping Environmental Pattern Agent")
        await self._save_patterns()
        await super().stop()
    
    async def record_measurement(
        self,
        factor_type: EnvironmentalFactorType,
        value: float,
        unit: str,
        location: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Record a new environmental measurement"""
        measurement_id = f"measurement_{len(self.measurements)}"
        
        measurement = EnvironmentalMeasurement(
            measurement_id=measurement_id,
            factor_type=factor_type,
            value=value,
            unit=unit,
            timestamp=datetime.utcnow(),
            location=location,
            metadata=metadata or {}
        )
        
        self.measurements[measurement_id] = measurement
        self.metrics["measurements_recorded"] += 1
        
        # Trigger pattern detection if enough measurements
        if len(self.measurements) >= 10:  # Arbitrary threshold
            await self._detect_patterns([measurement])
        
        return measurement_id
    
    async def register_pattern(
        self,
        factor_type: EnvironmentalFactorType,
        frequency: PatternFrequency,
        measurements: List[EnvironmentalMeasurement],
        trend: Dict[str, float],
        seasonality: Dict[str, float],
        thresholds: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register a new environmental pattern"""
        pattern_id = f"pattern_{len(self.patterns)}"
        
        pattern = EnvironmentalPattern(
            pattern_id=pattern_id,
            factor_type=factor_type,
            frequency=frequency,
            measurements=measurements,
            trend=trend,
            seasonality=seasonality,
            thresholds=thresholds,
            metadata=metadata or {}
        )
        
        self.patterns[pattern_id] = pattern
        await self._save_patterns()
        
        self.metrics["patterns_detected"] += 1
        return pattern_id
    
    async def analyze_patterns(
        self,
        factor_types: Optional[List[EnvironmentalFactorType]] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> str:
        """Analyze environmental patterns"""
        analysis_id = f"analysis_{len(self.analysis_results)}"
        
        # Create initial analysis result
        result = PatternAnalysisResult(
            analysis_id=analysis_id,
            patterns=[],
            correlations={},
            anomalies=[],
            recommendations=[],
            metadata={}
        )
        
        self.analysis_results[analysis_id] = result
        await self.analysis_queue.put({
            "analysis_id": analysis_id,
            "factor_types": factor_types,
            "time_range": time_range
        })
        
        return analysis_id
    
    async def get_analysis_result(self, analysis_id: str) -> Optional[PatternAnalysisResult]:
        """Get the results of pattern analysis"""
        return self.analysis_results.get(analysis_id)
    
    async def _load_patterns(self) -> None:
        """Load patterns from disk"""
        patterns_file = self.data_dir / "environmental_patterns.json"
        if patterns_file.exists():
            with open(patterns_file, "r") as f:
                patterns_data = json.load(f)
                
                for pattern_data in patterns_data:
                    # Convert measurements data
                    measurements = []
                    for m_data in pattern_data["measurements"]:
                        measurement = EnvironmentalMeasurement(
                            measurement_id=m_data["measurement_id"],
                            factor_type=EnvironmentalFactorType[m_data["factor_type"]],
                            value=m_data["value"],
                            unit=m_data["unit"],
                            timestamp=datetime.fromisoformat(m_data["timestamp"]),
                            location=m_data.get("location"),
                            metadata=m_data.get("metadata", {})
                        )
                        measurements.append(measurement)
                    
                    pattern = EnvironmentalPattern(
                        pattern_id=pattern_data["pattern_id"],
                        factor_type=EnvironmentalFactorType[pattern_data["factor_type"]],
                        frequency=PatternFrequency[pattern_data["frequency"]],
                        measurements=measurements,
                        trend=pattern_data["trend"],
                        seasonality=pattern_data["seasonality"],
                        thresholds=pattern_data["thresholds"],
                        metadata=pattern_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(pattern_data["created_at"]),
                        updated_at=datetime.fromisoformat(pattern_data["updated_at"])
                    )
                    
                    self.patterns[pattern.pattern_id] = pattern
    
    async def _save_patterns(self) -> None:
        """Save patterns to disk"""
        patterns_file = self.data_dir / "environmental_patterns.json"
        patterns_data = []
        
        for pattern in self.patterns.values():
            # Convert measurements to serializable format
            measurements_data = []
            for measurement in pattern.measurements:
                m_data = {
                    "measurement_id": measurement.measurement_id,
                    "factor_type": measurement.factor_type.name,
                    "value": measurement.value,
                    "unit": measurement.unit,
                    "timestamp": measurement.timestamp.isoformat(),
                    "location": measurement.location,
                    "metadata": measurement.metadata
                }
                measurements_data.append(m_data)
            
            pattern_data = {
                "pattern_id": pattern.pattern_id,
                "factor_type": pattern.factor_type.name,
                "frequency": pattern.frequency.name,
                "measurements": measurements_data,
                "trend": pattern.trend,
                "seasonality": pattern.seasonality,
                "thresholds": pattern.thresholds,
                "metadata": pattern.metadata,
                "created_at": pattern.created_at.isoformat(),
                "updated_at": pattern.updated_at.isoformat()
            }
            patterns_data.append(pattern_data)
        
        with open(patterns_file, "w") as f:
            json.dump(patterns_data, f, indent=2)
    
    async def _detect_patterns(
        self,
        new_measurements: List[EnvironmentalMeasurement]
    ) -> None:
        """Detect patterns in environmental measurements"""
        for measurement in new_measurements:
            factor_type = measurement.factor_type
            
            # Get historical measurements for this factor
            factor_measurements = [
                m for m in self.measurements.values()
                if m.factor_type == factor_type
            ]
            
            if len(factor_measurements) < 10:  # Need more data
                continue
            
            # Calculate basic statistics
            values = [m.value for m in factor_measurements]
            timestamps = [m.timestamp for m in factor_measurements]
            
            trend = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values))
            }
            
            # Simple seasonality detection
            seasonality = self._detect_seasonality(values, timestamps)
            
            # Calculate thresholds
            thresholds = {
                "lower": float(np.percentile(values, 10)),
                "upper": float(np.percentile(values, 90)),
                "critical_low": float(np.percentile(values, 1)),
                "critical_high": float(np.percentile(values, 99))
            }
            
            # Determine pattern frequency
            frequency = self._determine_frequency(timestamps)
            
            # Register new pattern
            await self.register_pattern(
                factor_type=factor_type,
                frequency=frequency,
                measurements=factor_measurements,
                trend=trend,
                seasonality=seasonality,
                thresholds=thresholds
            )
    
    def _detect_seasonality(
        self,
        values: List[float],
        timestamps: List[datetime]
    ) -> Dict[str, float]:
        """Detect seasonal patterns in values"""
        # Simple seasonality detection (placeholder)
        return {
            "daily_amplitude": 0.0,
            "weekly_amplitude": 0.0,
            "monthly_amplitude": 0.0
        }
    
    def _determine_frequency(
        self,
        timestamps: List[datetime]
    ) -> PatternFrequency:
        """Determine the frequency of measurements"""
        if len(timestamps) < 2:
            return PatternFrequency.CUSTOM
        
        # Calculate average time delta
        deltas = [(t2 - t1).total_seconds() for t1, t2 in zip(timestamps[:-1], timestamps[1:])]
        avg_delta = np.mean(deltas)
        
        # Determine frequency based on average delta
        if avg_delta < 3600 * 2:  # 2 hours
            return PatternFrequency.HOURLY
        elif avg_delta < 3600 * 24 * 2:  # 2 days
            return PatternFrequency.DAILY
        elif avg_delta < 3600 * 24 * 7 * 2:  # 2 weeks
            return PatternFrequency.WEEKLY
        elif avg_delta < 3600 * 24 * 30 * 2:  # 2 months
            return PatternFrequency.MONTHLY
        else:
            return PatternFrequency.SEASONAL
    
    async def _process_analysis_queue(self) -> None:
        """Process the analysis queue"""
        while self.status == AgentStatus.RUNNING:
            try:
                # Get next analysis task
                task = await self.analysis_queue.get()
                
                # Perform analysis
                await self._perform_analysis(
                    task["analysis_id"],
                    task["factor_types"],
                    task["time_range"]
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
        factor_types: Optional[List[EnvironmentalFactorType]],
        time_range: Optional[Tuple[datetime, datetime]]
    ) -> None:
        """Perform pattern analysis"""
        try:
            result = self.analysis_results[analysis_id]
            
            # Filter patterns by factor types and time range
            filtered_patterns = self._filter_patterns(factor_types, time_range)
            result.patterns.extend(filtered_patterns)
            
            # Calculate correlations between factors
            result.correlations = await self._calculate_correlations(filtered_patterns)
            
            # Detect anomalies
            result.anomalies = await self._detect_anomalies(filtered_patterns)
            
            # Generate recommendations
            result.recommendations = await self._generate_recommendations(
                filtered_patterns,
                result.anomalies
            )
            
            result.updated_at = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(f"Error performing analysis {analysis_id}: {str(e)}")
            self.metrics["analysis_errors"] += 1
    
    def _filter_patterns(
        self,
        factor_types: Optional[List[EnvironmentalFactorType]],
        time_range: Optional[Tuple[datetime, datetime]]
    ) -> List[EnvironmentalPattern]:
        """Filter patterns by factor types and time range"""
        filtered = list(self.patterns.values())
        
        if factor_types:
            filtered = [p for p in filtered if p.factor_type in factor_types]
        
        if time_range:
            start_time, end_time = time_range
            filtered = [
                p for p in filtered
                if any(start_time <= m.timestamp <= end_time for m in p.measurements)
            ]
        
        return filtered
    
    async def _calculate_correlations(
        self,
        patterns: List[EnvironmentalPattern]
    ) -> Dict[str, float]:
        """Calculate correlations between environmental factors"""
        correlations = {}
        
        for i, p1 in enumerate(patterns):
            for j, p2 in enumerate(patterns[i+1:], i+1):
                key = f"{p1.factor_type.name}_{p2.factor_type.name}"
                correlations[key] = self._calculate_pattern_correlation(p1, p2)
        
        return correlations
    
    def _calculate_pattern_correlation(
        self,
        pattern1: EnvironmentalPattern,
        pattern2: EnvironmentalPattern
    ) -> float:
        """Calculate correlation between two patterns"""
        # Simple correlation calculation (placeholder)
        return 0.0
    
    async def _detect_anomalies(
        self,
        patterns: List[EnvironmentalPattern]
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in environmental patterns"""
        anomalies = []
        
        for pattern in patterns:
            # Check for threshold violations
            for measurement in pattern.measurements:
                if measurement.value < pattern.thresholds["critical_low"]:
                    anomalies.append({
                        "type": "critical_low",
                        "factor_type": pattern.factor_type.name,
                        "value": measurement.value,
                        "threshold": pattern.thresholds["critical_low"],
                        "timestamp": measurement.timestamp.isoformat()
                    })
                elif measurement.value > pattern.thresholds["critical_high"]:
                    anomalies.append({
                        "type": "critical_high",
                        "factor_type": pattern.factor_type.name,
                        "value": measurement.value,
                        "threshold": pattern.thresholds["critical_high"],
                        "timestamp": measurement.timestamp.isoformat()
                    })
        
        return anomalies
    
    async def _generate_recommendations(
        self,
        patterns: List[EnvironmentalPattern],
        anomalies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on patterns and anomalies"""
        recommendations = []
        
        # Group anomalies by factor type
        anomalies_by_factor = {}
        for anomaly in anomalies:
            factor_type = anomaly["factor_type"]
            if factor_type not in anomalies_by_factor:
                anomalies_by_factor[factor_type] = []
            anomalies_by_factor[factor_type].append(anomaly)
        
        # Generate recommendations for each factor type
        for pattern in patterns:
            factor_type = pattern.factor_type.name
            factor_anomalies = anomalies_by_factor.get(factor_type, [])
            
            if factor_anomalies:
                recommendations.append({
                    "factor_type": factor_type,
                    "severity": "high" if len(factor_anomalies) > 5 else "medium",
                    "suggestion": f"Adjust {factor_type.lower()} levels to within optimal range",
                    "optimal_range": [
                        pattern.thresholds["lower"],
                        pattern.thresholds["upper"]
                    ]
                })
        
        return recommendations 