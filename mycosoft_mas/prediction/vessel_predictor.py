"""
Vessel Predictor - February 6, 2026

Predicts vessel positions using:
1. Destination port routing (if AIS destination available)
2. Course extrapolation (using current heading and speed)
"""

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .base_predictor import (
    BasePredictor,
    bearing_between,
    destination_point,
    haversine_distance,
    interpolate_position,
)
from .prediction_types import (
    EntityState,
    EntityType,
    GeoPoint,
    PredictedPosition,
    PredictionSource,
    Route,
    Velocity,
    Waypoint,
)

logger = logging.getLogger("VesselPredictor")


# Common port locations (subset for demo)
MAJOR_PORTS = {
    "USLAX": GeoPoint(lat=33.7397, lng=-118.2601),  # Los Angeles
    "USSEA": GeoPoint(lat=47.6205, lng=-122.3493),  # Seattle
    "NLRTM": GeoPoint(lat=51.9244, lng=4.4777),     # Rotterdam
    "SGSIN": GeoPoint(lat=1.2644, lng=103.8198),    # Singapore
    "CNSHA": GeoPoint(lat=31.2304, lng=121.4737),   # Shanghai
    "JPYOK": GeoPoint(lat=35.4437, lng=139.6380),   # Yokohama
    "AUBNE": GeoPoint(lat=-27.3841, lng=153.1175),  # Brisbane
    "GBFXT": GeoPoint(lat=51.9533, lng=1.3500),     # Felixstowe
}


class VesselPredictor(BasePredictor):
    """
    Predicts vessel positions.
    
    Vessels move slower than aircraft, so predictions can extend further
    into the future with reasonable accuracy.
    """
    
    entity_type = EntityType.VESSEL
    prediction_source = PredictionSource.ROUTE_PLAN
    model_version = "1.0.0"
    
    # Vessel-specific parameters
    initial_confidence = 0.90
    confidence_half_life_seconds = 3600  # 1 hour (vessels are more predictable)
    minimum_confidence = 0.3
    
    max_prediction_horizon = timedelta(hours=48)
    
    # Uncertainty growth (slower than aircraft)
    base_uncertainty_meters = 200
    uncertainty_growth_rate = 0.2  # meters per second
    
    def __init__(self, timeline_cache=None):
        super().__init__()
        self.timeline_cache = timeline_cache
    
    async def get_current_state(self, entity_id: str) -> Optional[EntityState]:
        """Get current vessel state."""
        # Would query AIS data in production
        return None
    
    async def predict_positions(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Generate predicted positions for a vessel.
        """
        predictions: List[PredictedPosition] = []
        
        # Check if we have destination info
        if state.destination:
            destination = self._lookup_destination(state.destination)
            if destination:
                predictions = await self._predict_to_destination(
                    state, destination, from_time, to_time, resolution_seconds
                )
                self.prediction_source = PredictionSource.ROUTE_PLAN
                return predictions
        
        # Fall back to course extrapolation
        predictions = await self._predict_from_course(
            state, from_time, to_time, resolution_seconds
        )
        self.prediction_source = PredictionSource.EXTRAPOLATION
        
        return predictions
    
    def _lookup_destination(self, destination_code: str) -> Optional[GeoPoint]:
        """Look up destination port coordinates."""
        # Check common ports
        if destination_code.upper() in MAJOR_PORTS:
            return MAJOR_PORTS[destination_code.upper()]
        
        # In production, would query port database
        return None
    
    async def _predict_to_destination(
        self,
        state: EntityState,
        destination: GeoPoint,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Predict vessel route to destination.
        
        Uses great circle route with waypoints for realism.
        """
        predictions = []
        
        # Calculate total distance
        total_distance = haversine_distance(state.position, destination)
        
        # Get speed (default to 12 knots if not available)
        speed_knots = state.velocity.speed if state.velocity else 12
        speed_ms = speed_knots * 0.514444  # Convert to m/s
        
        # Estimate total travel time
        total_time_seconds = total_distance / speed_ms if speed_ms > 0 else float('inf')
        
        # Generate waypoints along great circle
        num_waypoints = max(2, int(total_distance / 100000))  # One every ~100km
        waypoints = []
        for i in range(num_waypoints + 1):
            fraction = i / num_waypoints
            pos = interpolate_position(state.position, destination, fraction)
            waypoints.append(pos)
        
        # Generate predictions along route
        current_time = from_time
        elapsed_total = 0
        
        for i in range(len(waypoints) - 1):
            wp_start = waypoints[i]
            wp_end = waypoints[i + 1]
            segment_distance = haversine_distance(wp_start, wp_end)
            segment_time = segment_distance / speed_ms if speed_ms > 0 else 0
            
            segment_elapsed = 0
            while segment_elapsed < segment_time and current_time <= to_time:
                fraction = segment_elapsed / segment_time if segment_time > 0 else 0
                pos = interpolate_position(wp_start, wp_end, fraction)
                
                heading = bearing_between(wp_start, wp_end)
                
                predictions.append(PredictedPosition(
                    entity_id=state.entity_id,
                    entity_type=EntityType.VESSEL,
                    timestamp=current_time,
                    position=pos,
                    velocity=Velocity(speed=speed_knots, heading=heading),
                    confidence=1.0,
                    prediction_source=PredictionSource.ROUTE_PLAN,
                    model_version=self.model_version,
                    metadata={"destination": state.destination},
                ))
                
                current_time += timedelta(seconds=resolution_seconds)
                segment_elapsed += resolution_seconds
                elapsed_total += resolution_seconds
        
        return predictions
    
    async def _predict_from_course(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Predict positions using simple course extrapolation.
        """
        predictions = []
        
        if not state.velocity:
            logger.warning(f"No velocity data for vessel {state.entity_id}")
            return predictions
        
        speed_ms = state.velocity.speed * 0.514444
        heading = state.velocity.heading
        
        current_time = from_time
        current_pos = state.position
        
        while current_time <= to_time:
            distance = speed_ms * resolution_seconds
            new_pos = destination_point(current_pos, heading, distance)
            
            predictions.append(PredictedPosition(
                entity_id=state.entity_id,
                entity_type=EntityType.VESSEL,
                timestamp=current_time,
                position=new_pos,
                velocity=Velocity(speed=state.velocity.speed, heading=heading),
                confidence=1.0,
                prediction_source=PredictionSource.EXTRAPOLATION,
                model_version=self.model_version,
            ))
            
            current_time += timedelta(seconds=resolution_seconds)
            current_pos = new_pos
        
        return predictions