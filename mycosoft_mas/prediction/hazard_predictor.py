"""
Hazard Predictor - February 6, 2026

Predicts environmental hazards:
1. Earthquake aftershocks (statistical models)
2. Wildfire spread (fire behavior models)
3. Storm tracks (extrapolation + Earth-2)
4. Tsunami propagation (wave modeling)
5. Volcanic ash (dispersion modeling)
"""

import logging
import math
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from .base_predictor import (
    BasePredictor,
    destination_point,
    haversine_distance,
)
from .prediction_types import (
    EntityState,
    EntityType,
    GeoPoint,
    PredictedPosition,
    PredictionSource,
    Velocity,
)

logger = logging.getLogger("HazardPredictor")


class HazardPredictor(BasePredictor):
    """
    Predicts environmental hazard evolution.
    
    Covers earthquakes, wildfires, storms, tsunamis, and volcanic activity.
    """
    
    entity_type = EntityType.EARTHQUAKE  # Generic, actual type varies
    prediction_source = PredictionSource.HAZARD_MODEL
    model_version = "1.0.0"
    
    # Hazard predictions vary widely in confidence
    initial_confidence = 0.60
    confidence_half_life_seconds = 1800  # 30 minutes
    minimum_confidence = 0.1
    
    max_prediction_horizon = timedelta(hours=72)
    
    def __init__(self, earth2_forecaster=None):
        super().__init__()
        self.earth2_forecaster = earth2_forecaster
    
    async def get_current_state(self, entity_id: str) -> Optional[EntityState]:
        """Get current hazard state."""
        return None
    
    async def predict_positions(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Route to appropriate hazard prediction model.
        """
        hazard_type = state.metadata.get("hazard_type", "generic")
        
        if hazard_type == "earthquake":
            return await self._predict_aftershocks(
                state, from_time, to_time, resolution_seconds
            )
        elif hazard_type == "wildfire":
            return await self._predict_wildfire_spread(
                state, from_time, to_time, resolution_seconds
            )
        elif hazard_type == "storm":
            return await self._predict_storm_track(
                state, from_time, to_time, resolution_seconds
            )
        elif hazard_type == "tsunami":
            return await self._predict_tsunami(
                state, from_time, to_time, resolution_seconds
            )
        elif hazard_type == "volcano":
            return await self._predict_ash_cloud(
                state, from_time, to_time, resolution_seconds
            )
        else:
            logger.warning(f"Unknown hazard type: {hazard_type}")
            return []
    
    async def _predict_aftershocks(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Predict earthquake aftershocks using Omori's law.
        
        Aftershock rate: n(t) = K / (c + t)^p
        where t is time since mainshock.
        """
        predictions = []
        
        mainshock_magnitude = state.metadata.get("magnitude", 6.0)
        mainshock_time = state.timestamp
        
        # Omori parameters (typical values)
        K = 10 ** (mainshock_magnitude - 3.5)  # More aftershocks for larger quakes
        c = 0.1  # days
        p = 1.1  # decay rate
        
        # Generate predicted aftershock locations
        current_time = from_time
        
        while current_time <= to_time:
            # Time since mainshock in days
            t_days = (current_time - mainshock_time).total_seconds() / 86400
            
            # Expected aftershock rate (per day)
            if t_days > 0:
                rate = K / ((c + t_days) ** p)
            else:
                rate = K
            
            # Convert to probability in this time window
            window_days = resolution_seconds / 86400
            expected_count = rate * window_days
            
            # Aftershock zone radius (roughly scales with magnitude)
            zone_radius_km = 10 * (mainshock_magnitude - 4)
            
            # Generate random aftershock location within zone
            distance = random.uniform(0, zone_radius_km * 1000)
            bearing = random.uniform(0, 360)
            location = destination_point(state.position, bearing, distance)
            
            # Aftershock magnitude (typically smaller than mainshock)
            # Bath's law: largest aftershock is ~1.2 magnitudes smaller
            max_aftershock_mag = mainshock_magnitude - 1.2
            aftershock_mag = random.uniform(
                max(2.0, mainshock_magnitude - 3),
                max_aftershock_mag
            )
            
            predictions.append(PredictedPosition(
                entity_id=f"{state.entity_id}_aftershock_{int(current_time.timestamp())}",
                entity_type=EntityType.EARTHQUAKE,
                timestamp=current_time,
                position=location,
                confidence=min(0.8, expected_count),  # Lower if aftershock unlikely
                prediction_source=PredictionSource.STATISTICAL,
                model_version=self.model_version,
                metadata={
                    "hazard_type": "earthquake",
                    "type": "aftershock",
                    "expected_magnitude": round(aftershock_mag, 1),
                    "expected_count": round(expected_count, 3),
                    "mainshock_id": state.entity_id,
                },
            ))
            
            current_time += timedelta(seconds=resolution_seconds)
        
        return predictions
    
    async def _predict_wildfire_spread(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Predict wildfire spread based on wind, terrain, and fuel.
        """
        predictions = []
        
        # Get fire parameters
        wind_speed = state.metadata.get("wind_speed_kmh", 20)
        wind_direction = state.metadata.get("wind_direction", 180)  # From south
        fuel_moisture = state.metadata.get("fuel_moisture", 0.2)
        current_area = state.metadata.get("area_hectares", 10)
        
        # Base spread rate (simplified Rothermel)
        base_rate_mps = 0.1  # 0.1 m/s base
        wind_factor = 1 + (wind_speed / 30)
        moisture_factor = max(0.1, 1 - fuel_moisture * 2)
        spread_rate = base_rate_mps * wind_factor * moisture_factor
        
        current_time = from_time
        current_pos = state.position
        current_perimeter = math.sqrt(current_area * 10000 / math.pi) * 2 * math.pi
        
        while current_time <= to_time:
            # Fire spreads fastest downwind
            downwind_spread = spread_rate * resolution_seconds * 1.5
            crosswind_spread = spread_rate * resolution_seconds * 0.5
            upwind_spread = spread_rate * resolution_seconds * 0.1
            
            # Move fire center slightly downwind
            center_shift = downwind_spread * 0.3
            new_center = destination_point(
                current_pos,
                (wind_direction + 180) % 360,  # Fire moves opposite to wind source
                center_shift
            )
            
            # Estimate new area
            avg_radius = (downwind_spread + crosswind_spread) / 2
            new_perimeter = current_perimeter + 2 * math.pi * avg_radius
            new_area = (new_perimeter / (2 * math.pi)) ** 2 * math.pi / 10000  # hectares
            
            predictions.append(PredictedPosition(
                entity_id=state.entity_id,
                entity_type=EntityType.WILDFIRE,
                timestamp=current_time,
                position=new_center,
                confidence=1.0,
                prediction_source=PredictionSource.HAZARD_MODEL,
                model_version=self.model_version,
                metadata={
                    "hazard_type": "wildfire",
                    "area_hectares": round(new_area, 1),
                    "perimeter_km": round(new_perimeter / 1000, 2),
                    "spread_rate_mps": round(spread_rate, 3),
                    "wind_speed_kmh": wind_speed,
                    "wind_direction": wind_direction,
                },
            ))
            
            current_time += timedelta(seconds=resolution_seconds)
            current_pos = new_center
            current_perimeter = new_perimeter
            current_area = new_area
        
        return predictions
    
    async def _predict_storm_track(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Predict storm/hurricane track.
        """
        predictions = []
        
        # Get storm parameters
        storm_speed = state.velocity.speed if state.velocity else 20  # km/h
        storm_heading = state.velocity.heading if state.velocity else 315  # NW
        intensity = state.metadata.get("intensity", "tropical_storm")
        wind_speed = state.metadata.get("max_wind_kmh", 100)
        
        speed_ms = storm_speed * 1000 / 3600  # Convert to m/s
        
        current_time = from_time
        current_pos = state.position
        current_heading = storm_heading
        
        while current_time <= to_time:
            # Storms tend to recurve (simplified)
            lat = current_pos.lat
            if lat > 25:
                # Recurve eastward in higher latitudes
                current_heading = (current_heading + 0.5) % 360
            
            # Move storm
            distance = speed_ms * resolution_seconds
            new_pos = destination_point(current_pos, current_heading, distance)
            
            # Intensity changes (simplified)
            # Storms weaken over land and cold water
            if lat > 30:
                wind_speed *= 0.99  # Gradual weakening
            
            predictions.append(PredictedPosition(
                entity_id=state.entity_id,
                entity_type=EntityType.STORM,
                timestamp=current_time,
                position=new_pos,
                velocity=Velocity(speed=storm_speed, heading=current_heading),
                confidence=1.0,
                prediction_source=PredictionSource.HAZARD_MODEL,
                model_version=self.model_version,
                metadata={
                    "hazard_type": "storm",
                    "intensity": intensity,
                    "max_wind_kmh": round(wind_speed),
                },
            ))
            
            current_time += timedelta(seconds=resolution_seconds)
            current_pos = new_pos
        
        return predictions
    
    async def _predict_tsunami(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Predict tsunami wave propagation.
        """
        predictions = []
        
        # Tsunami speed depends on water depth
        # v = sqrt(g * h) where g = 9.8 m/s^2
        # Average ocean depth ~4000m -> ~200 m/s -> ~700 km/h
        
        wave_speed_ms = 200  # Simplified average
        origin = state.position
        
        current_time = from_time
        
        while current_time <= to_time:
            # Time since event
            dt = (current_time - state.timestamp).total_seconds()
            
            # Wave has traveled this far
            radius = wave_speed_ms * dt
            
            # Generate points on wave front (simplified circular)
            for bearing in range(0, 360, 30):
                wave_point = destination_point(origin, bearing, radius)
                
                predictions.append(PredictedPosition(
                    entity_id=f"{state.entity_id}_front_{bearing}",
                    entity_type=EntityType.EARTHQUAKE,  # Using earthquake type for now
                    timestamp=current_time,
                    position=wave_point,
                    confidence=1.0,
                    prediction_source=PredictionSource.HAZARD_MODEL,
                    model_version=self.model_version,
                    metadata={
                        "hazard_type": "tsunami",
                        "wave_radius_km": round(radius / 1000, 1),
                        "bearing": bearing,
                        "origin": origin.to_dict(),
                    },
                ))
            
            current_time += timedelta(seconds=resolution_seconds)
        
        return predictions
    
    async def _predict_ash_cloud(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Predict volcanic ash cloud dispersion.
        """
        predictions = []
        
        # Get wind conditions
        wind_speed_ms = state.metadata.get("wind_speed_ms", 15)
        wind_direction = state.metadata.get("wind_direction", 270)  # From west
        eruption_height_m = state.metadata.get("plume_height_m", 10000)
        
        current_time = from_time
        cloud_center = state.position
        cloud_width_km = 5  # Initial plume width
        
        while current_time <= to_time:
            # Cloud moves with wind
            distance = wind_speed_ms * resolution_seconds
            new_center = destination_point(
                cloud_center,
                (wind_direction + 180) % 360,  # Moves opposite to wind source
                distance
            )
            
            # Cloud spreads laterally
            dt_hours = (current_time - from_time).total_seconds() / 3600
            new_width = cloud_width_km + dt_hours * 2  # 2 km/hr lateral spread
            
            # Cloud descends over time
            descent_rate = 500  # m/hour
            current_height = max(
                1000,  # Minimum height
                eruption_height_m - descent_rate * dt_hours
            )
            
            predictions.append(PredictedPosition(
                entity_id=state.entity_id,
                entity_type=EntityType.WEATHER,  # Using weather type
                timestamp=current_time,
                position=GeoPoint(
                    lat=new_center.lat,
                    lng=new_center.lng,
                    altitude=current_height,
                ),
                velocity=Velocity(
                    speed=wind_speed_ms,
                    heading=(wind_direction + 180) % 360,
                ),
                confidence=1.0,
                prediction_source=PredictionSource.HAZARD_MODEL,
                model_version=self.model_version,
                metadata={
                    "hazard_type": "volcanic_ash",
                    "cloud_width_km": round(new_width, 1),
                    "plume_height_m": round(current_height),
                    "source_volcano": state.entity_id,
                },
            ))
            
            current_time += timedelta(seconds=resolution_seconds)
            cloud_center = new_center
        
        return predictions