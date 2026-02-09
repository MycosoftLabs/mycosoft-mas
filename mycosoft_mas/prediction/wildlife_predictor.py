"""
Wildlife Predictor - February 6, 2026

Predicts wildlife/species movement using:
1. Recent trajectory continuation (for tracked individuals)
2. Seasonal migration patterns (historical data)
3. Habitat suitability modeling
"""

import logging
import math
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

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
    Velocity,
)

logger = logging.getLogger("WildlifePredictor")


# Known migration routes (simplified examples)
MIGRATION_ROUTES = {
    "arctic_tern": [
        {"month_start": 8, "month_end": 10, "direction": "south", "lat_change": -50},
        {"month_start": 3, "month_end": 5, "direction": "north", "lat_change": 50},
    ],
    "monarch_butterfly": [
        {"month_start": 9, "month_end": 11, "direction": "south", "end_lat": 19.5, "end_lng": -100.0},
        {"month_start": 3, "month_end": 5, "direction": "north", "end_lat": 45.0, "end_lng": -90.0},
    ],
    "humpback_whale": [
        {"month_start": 10, "month_end": 1, "direction": "equator", "lat_change": -30},
        {"month_start": 4, "month_end": 7, "direction": "poles", "lat_change": 30},
    ],
    "wildebeest": [
        {"month_start": 1, "month_end": 3, "direction": "south", "lat_change": -2},
        {"month_start": 5, "month_end": 7, "direction": "north", "lat_change": 2},
        {"month_start": 8, "month_end": 10, "direction": "west", "lng_change": -1},
    ],
}

# Typical movement speeds (km/day)
SPECIES_SPEEDS = {
    "elephant": 20,
    "lion": 10,
    "wildebeest": 30,
    "zebra": 25,
    "bird": 200,  # Generic bird
    "whale": 100,
    "arctic_tern": 500,
    "monarch_butterfly": 80,
    "humpback_whale": 50,
    "default": 15,
}


class WildlifePredictor(BasePredictor):
    """
    Predicts wildlife movement.
    
    Less accurate than aircraft/satellite due to behavioral unpredictability,
    but useful for general trends and migration patterns.
    """
    
    entity_type = EntityType.WILDLIFE
    prediction_source = PredictionSource.MIGRATION_MODEL
    model_version = "1.0.0"
    
    # Wildlife predictions are less certain
    initial_confidence = 0.70
    confidence_half_life_seconds = 3600  # 1 hour
    minimum_confidence = 0.1
    
    max_prediction_horizon = timedelta(days=7)
    
    # Higher uncertainty
    base_uncertainty_meters = 5000  # 5 km
    uncertainty_growth_rate = 2.0  # meters per second
    
    def __init__(self):
        super().__init__()
    
    async def get_current_state(self, entity_id: str) -> Optional[EntityState]:
        """Get current wildlife observation."""
        return None
    
    async def predict_positions(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Generate predicted positions for wildlife.
        """
        predictions: List[PredictedPosition] = []
        
        species = state.species or "default"
        
        # Check for known migration pattern
        migration = self._get_migration_pattern(species, from_time)
        
        if migration:
            predictions = await self._predict_migration(
                state, migration, from_time, to_time, resolution_seconds
            )
            self.prediction_source = PredictionSource.MIGRATION_MODEL
        elif state.velocity:
            predictions = await self._predict_from_trajectory(
                state, from_time, to_time, resolution_seconds
            )
            self.prediction_source = PredictionSource.EXTRAPOLATION
        else:
            predictions = await self._predict_random_walk(
                state, from_time, to_time, resolution_seconds
            )
            self.prediction_source = PredictionSource.STATISTICAL
        
        return predictions
    
    def _get_migration_pattern(
        self,
        species: str,
        time: datetime
    ) -> Optional[Dict]:
        """Get active migration pattern for species at given time."""
        patterns = MIGRATION_ROUTES.get(species.lower().replace(" ", "_"), [])
        
        month = time.month
        for pattern in patterns:
            start = pattern["month_start"]
            end = pattern["month_end"]
            
            # Handle year wrap
            if start <= end:
                if start <= month <= end:
                    return pattern
            else:
                if month >= start or month <= end:
                    return pattern
        
        return None
    
    def _get_species_speed(self, species: str) -> float:
        """Get typical movement speed for species in km/day."""
        return SPECIES_SPEEDS.get(
            species.lower().replace(" ", "_"),
            SPECIES_SPEEDS["default"]
        )
    
    async def _predict_migration(
        self,
        state: EntityState,
        migration: Dict,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Predict positions along migration route.
        """
        predictions = []
        
        species = state.species or "default"
        speed_km_day = self._get_species_speed(species)
        speed_ms = speed_km_day * 1000 / 86400  # Convert to m/s
        
        current_time = from_time
        current_pos = state.position
        
        # Determine migration direction
        if "end_lat" in migration:
            # Migrate to specific location
            target = GeoPoint(
                lat=migration["end_lat"],
                lng=migration.get("end_lng", current_pos.lng),
            )
            heading = bearing_between(current_pos, target)
        elif "lat_change" in migration:
            # Migrate by latitude change
            if migration["lat_change"] > 0:
                heading = 0  # North
            else:
                heading = 180  # South
        elif "lng_change" in migration:
            # Migrate by longitude change
            if migration["lng_change"] > 0:
                heading = 90  # East
            else:
                heading = 270  # West
        else:
            heading = 0
        
        while current_time <= to_time:
            # Add some randomness to simulate natural behavior
            jitter_heading = heading + random.gauss(0, 15)  # +/- 15 degrees
            jitter_speed = speed_ms * random.uniform(0.7, 1.3)
            
            distance = jitter_speed * resolution_seconds
            new_pos = destination_point(current_pos, jitter_heading, distance)
            
            predictions.append(PredictedPosition(
                entity_id=state.entity_id,
                entity_type=EntityType.WILDLIFE,
                timestamp=current_time,
                position=new_pos,
                velocity=Velocity(
                    speed=jitter_speed,
                    heading=jitter_heading,
                ),
                confidence=1.0,
                prediction_source=PredictionSource.MIGRATION_MODEL,
                model_version=self.model_version,
                metadata={
                    "species": species,
                    "migration_direction": migration.get("direction"),
                },
            ))
            
            current_time += timedelta(seconds=resolution_seconds)
            current_pos = new_pos
        
        return predictions
    
    async def _predict_from_trajectory(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Predict from recent movement trajectory.
        """
        predictions = []
        
        speed_ms = state.velocity.speed if state.velocity else 0.5  # Default slow
        heading = state.velocity.heading if state.velocity else random.uniform(0, 360)
        
        current_time = from_time
        current_pos = state.position
        
        while current_time <= to_time:
            # Add behavioral noise
            jitter_heading = heading + random.gauss(0, 20)
            jitter_speed = speed_ms * random.uniform(0.5, 1.5)
            
            distance = jitter_speed * resolution_seconds
            new_pos = destination_point(current_pos, jitter_heading, distance)
            
            predictions.append(PredictedPosition(
                entity_id=state.entity_id,
                entity_type=EntityType.WILDLIFE,
                timestamp=current_time,
                position=new_pos,
                velocity=Velocity(speed=jitter_speed, heading=jitter_heading),
                confidence=1.0,
                prediction_source=PredictionSource.EXTRAPOLATION,
                model_version=self.model_version,
                metadata={"species": state.species},
            ))
            
            current_time += timedelta(seconds=resolution_seconds)
            current_pos = new_pos
            
            # Gradually change heading (wandering behavior)
            heading = (heading + random.gauss(0, 5)) % 360
        
        return predictions
    
    async def _predict_random_walk(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Random walk prediction when no other data available.
        
        Used for stationary or slow-moving species with no trajectory data.
        """
        predictions = []
        
        species = state.species or "default"
        speed_km_day = self._get_species_speed(species) * 0.3  # Reduced for random walk
        speed_ms = speed_km_day * 1000 / 86400
        
        current_time = from_time
        current_pos = state.position
        heading = random.uniform(0, 360)
        
        while current_time <= to_time:
            # Random direction changes
            heading = (heading + random.gauss(0, 45)) % 360
            
            # Variable speed
            step_speed = speed_ms * random.uniform(0.0, 2.0)
            distance = step_speed * resolution_seconds
            
            new_pos = destination_point(current_pos, heading, distance)
            
            predictions.append(PredictedPosition(
                entity_id=state.entity_id,
                entity_type=EntityType.WILDLIFE,
                timestamp=current_time,
                position=new_pos,
                velocity=Velocity(speed=step_speed, heading=heading) if step_speed > 0 else None,
                confidence=1.0,
                prediction_source=PredictionSource.STATISTICAL,
                model_version=self.model_version,
                metadata={
                    "species": species,
                    "method": "random_walk",
                },
            ))
            
            current_time += timedelta(seconds=resolution_seconds)
            current_pos = new_pos
        
        return predictions