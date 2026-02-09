"""
Aircraft Predictor - February 6, 2026

Predicts aircraft positions using:
1. Flight plan data (if available) - most accurate
2. ADS-B intent data - short-term accurate
3. Vector extrapolation - fallback
"""

import asyncio
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

logger = logging.getLogger("AircraftPredictor")


class AircraftPredictor(BasePredictor):
    """
    Predicts aircraft positions.
    
    Uses flight plan data when available, otherwise falls back to
    vector extrapolation based on current speed and heading.
    """
    
    entity_type = EntityType.AIRCRAFT
    prediction_source = PredictionSource.EXTRAPOLATION
    model_version = "1.0.0"
    
    # Aircraft-specific parameters
    initial_confidence = 0.95
    confidence_half_life_seconds = 600  # 10 minutes
    minimum_confidence = 0.2
    
    max_prediction_horizon = timedelta(hours=4)
    
    # Uncertainty growth (aircraft are more predictable than ships)
    base_uncertainty_meters = 50
    uncertainty_growth_rate = 0.5  # meters per second
    
    # Flight dynamics limits
    max_turn_rate_deg_per_sec = 3.0  # Standard rate turn
    max_climb_rate_fpm = 3000  # feet per minute
    max_descent_rate_fpm = 2500
    
    def __init__(self, timeline_cache=None):
        super().__init__()
        self.timeline_cache = timeline_cache
        self._flight_plan_cache: Dict[str, Route] = {}
    
    async def get_current_state(self, entity_id: str) -> Optional[EntityState]:
        """
        Get current aircraft state from timeline cache or database.
        """
        # In production, this would query the timeline cache
        # For now, return None to indicate we need state passed in
        
        if self.timeline_cache:
            try:
                from mycosoft_mas.cache import get_timeline_cache, TimelineQuery, EntityType as CacheEntityType
                cache = await get_timeline_cache()
                
                result = await cache.get(TimelineQuery(
                    entity_type=CacheEntityType.AIRCRAFT,
                    entity_id=entity_id,
                    limit=1,
                ))
                
                if result.data:
                    entry = result.data[0]
                    return EntityState(
                        entity_id=entity_id,
                        entity_type=EntityType.AIRCRAFT,
                        timestamp=datetime.fromtimestamp(entry.timestamp / 1000, tz=timezone.utc),
                        position=GeoPoint(
                            lat=entry.data.get("position", {}).get("lat", 0),
                            lng=entry.data.get("position", {}).get("lng", 0),
                            altitude=entry.data.get("position", {}).get("altitude"),
                        ),
                        velocity=Velocity(
                            speed=entry.data.get("velocity", {}).get("speed", 0),
                            heading=entry.data.get("velocity", {}).get("heading", 0),
                            climb_rate=entry.data.get("velocity", {}).get("climb_rate"),
                        ) if entry.data.get("velocity") else None,
                        flight_plan=entry.data.get("flight_plan"),
                    )
            except Exception as e:
                logger.warning(f"Failed to get aircraft state from cache: {e}")
        
        return None
    
    async def predict_positions(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Generate predicted positions for an aircraft.
        
        Strategy:
        1. Check for flight plan â†’ follow planned route
        2. Check for ADS-B intent â†’ follow intent track
        3. Fall back to vector extrapolation
        """
        predictions: List[PredictedPosition] = []
        
        # Determine prediction source
        if state.flight_plan:
            predictions = await self._predict_from_flight_plan(
                state, from_time, to_time, resolution_seconds
            )
            self.prediction_source = PredictionSource.FLIGHT_PLAN
        else:
            predictions = await self._predict_from_vector(
                state, from_time, to_time, resolution_seconds
            )
            self.prediction_source = PredictionSource.EXTRAPOLATION
        
        return predictions
    
    async def _predict_from_flight_plan(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Predict positions along a flight plan route.
        """
        predictions = []
        
        # Parse flight plan into waypoints
        route = self._parse_flight_plan(state.flight_plan)
        if not route or not route.waypoints:
            # Fall back to vector extrapolation
            return await self._predict_from_vector(
                state, from_time, to_time, resolution_seconds
            )
        
        # Find current position along route
        current_wp_index = self._find_current_waypoint(state.position, route)
        
        # Calculate average ground speed
        speed = state.velocity.speed if state.velocity else 450  # knots default
        speed_ms = speed * 0.514444  # Convert knots to m/s
        
        # Generate predictions along route
        current_time = from_time
        current_pos = state.position
        current_alt = state.position.altitude or 35000 * 0.3048  # Default cruise altitude
        
        while current_time <= to_time:
            # Find next waypoint
            next_wp = self._get_next_waypoint(current_wp_index, route)
            
            if next_wp is None:
                # Past last waypoint - extrapolate from final heading
                predictions.extend(
                    self._extrapolate_to_end(
                        current_pos,
                        current_alt,
                        speed_ms,
                        state.velocity.heading if state.velocity else 0,
                        current_time,
                        to_time,
                        resolution_seconds,
                    )
                )
                break
            
            # Calculate time to next waypoint
            dist = haversine_distance(current_pos, next_wp.position)
            time_to_wp = dist / speed_ms if speed_ms > 0 else float('inf')
            
            # Add predictions until waypoint or end time
            elapsed = 0
            while elapsed < time_to_wp and current_time <= to_time:
                # Interpolate position along segment
                fraction = elapsed / time_to_wp if time_to_wp > 0 else 0
                pos = interpolate_position(current_pos, next_wp.position, fraction)
                
                # Interpolate altitude if waypoint has altitude
                if next_wp.position.altitude:
                    pos.altitude = current_alt + fraction * (next_wp.position.altitude - current_alt)
                else:
                    pos.altitude = current_alt
                
                # Calculate velocity
                heading = bearing_between(current_pos, next_wp.position)
                climb_rate = None
                if next_wp.position.altitude and current_alt:
                    alt_change = next_wp.position.altitude - current_alt
                    climb_rate = alt_change / time_to_wp if time_to_wp > 0 else 0
                
                predictions.append(PredictedPosition(
                    entity_id=state.entity_id,
                    entity_type=EntityType.AIRCRAFT,
                    timestamp=current_time,
                    position=pos,
                    velocity=Velocity(
                        speed=speed,
                        heading=heading,
                        climb_rate=climb_rate,
                    ),
                    confidence=1.0,  # Will be adjusted later
                    prediction_source=PredictionSource.FLIGHT_PLAN,
                    model_version=self.model_version,
                    metadata={"waypoint": next_wp.name},
                ))
                
                current_time += timedelta(seconds=resolution_seconds)
                elapsed += resolution_seconds
            
            # Move to next waypoint
            current_pos = next_wp.position
            current_alt = next_wp.position.altitude or current_alt
            current_wp_index += 1
        
        return predictions
    
    async def _predict_from_vector(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Predict positions using simple vector extrapolation.
        
        Assumes aircraft continues on current heading at current speed.
        """
        predictions = []
        
        if not state.velocity:
            logger.warning(f"No velocity data for aircraft {state.entity_id}")
            return predictions
        
        speed_ms = state.velocity.speed * 0.514444  # knots to m/s
        heading = state.velocity.heading
        climb_rate = state.velocity.climb_rate or 0  # m/s
        
        current_time = from_time
        current_pos = state.position
        current_alt = state.position.altitude or 10000 * 0.3048  # Default 10000 ft
        
        while current_time <= to_time:
            # Calculate distance traveled
            distance = speed_ms * resolution_seconds
            
            # Calculate new position
            new_pos = destination_point(current_pos, heading, distance)
            new_alt = current_alt + (climb_rate * resolution_seconds)
            
            # Clamp altitude to reasonable range
            new_alt = max(0, min(new_alt, 45000 * 0.3048))  # 0 to 45000 ft
            new_pos.altitude = new_alt
            
            predictions.append(PredictedPosition(
                entity_id=state.entity_id,
                entity_type=EntityType.AIRCRAFT,
                timestamp=current_time,
                position=new_pos,
                velocity=Velocity(
                    speed=state.velocity.speed,
                    heading=heading,
                    climb_rate=climb_rate,
                ),
                confidence=1.0,
                prediction_source=PredictionSource.EXTRAPOLATION,
                model_version=self.model_version,
            ))
            
            current_time += timedelta(seconds=resolution_seconds)
            current_pos = new_pos
            current_alt = new_alt
        
        return predictions
    
    def _parse_flight_plan(self, flight_plan: Optional[Dict]) -> Optional[Route]:
        """Parse flight plan dictionary into Route object."""
        if not flight_plan:
            return None
        
        waypoints = []
        for wp in flight_plan.get("waypoints", []):
            waypoints.append(Waypoint(
                position=GeoPoint(
                    lat=wp.get("lat", 0),
                    lng=wp.get("lng", 0),
                    altitude=wp.get("altitude"),
                ),
                name=wp.get("name"),
                expected_time=datetime.fromisoformat(wp["time"]) if wp.get("time") else None,
            ))
        
        if not waypoints:
            return None
        
        return Route(
            waypoints=waypoints,
            departure_time=datetime.fromisoformat(flight_plan["departure"]) if flight_plan.get("departure") else None,
            arrival_time=datetime.fromisoformat(flight_plan["arrival"]) if flight_plan.get("arrival") else None,
        )
    
    def _find_current_waypoint(self, current_pos: GeoPoint, route: Route) -> int:
        """Find the index of the waypoint we're approaching or have just passed."""
        if not route.waypoints:
            return 0
        
        # Find closest waypoint
        min_dist = float('inf')
        closest_idx = 0
        
        for i, wp in enumerate(route.waypoints):
            dist = haversine_distance(current_pos, wp.position)
            if dist < min_dist:
                min_dist = dist
                closest_idx = i
        
        return closest_idx
    
    def _get_next_waypoint(self, current_idx: int, route: Route) -> Optional[Waypoint]:
        """Get the next waypoint after current index."""
        if current_idx + 1 < len(route.waypoints):
            return route.waypoints[current_idx + 1]
        return None
    
    def _extrapolate_to_end(
        self,
        current_pos: GeoPoint,
        current_alt: float,
        speed_ms: float,
        heading: float,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """Extrapolate beyond the last waypoint."""
        predictions = []
        current_time = from_time
        pos = current_pos
        
        while current_time <= to_time:
            distance = speed_ms * resolution_seconds
            pos = destination_point(pos, heading, distance)
            pos.altitude = current_alt
            
            predictions.append(PredictedPosition(
                entity_id="",  # Will be filled by caller
                entity_type=EntityType.AIRCRAFT,
                timestamp=current_time,
                position=pos,
                velocity=Velocity(speed=speed_ms / 0.514444, heading=heading),
                confidence=1.0,
                prediction_source=PredictionSource.EXTRAPOLATION,
                model_version=self.model_version,
            ))
            
            current_time += timedelta(seconds=resolution_seconds)
        
        return predictions


# Convenience function
async def predict_aircraft(
    entity_id: str,
    current_state: Optional[EntityState] = None,
    from_time: Optional[datetime] = None,
    to_time: Optional[datetime] = None,
    resolution_seconds: int = 60
) -> List[PredictedPosition]:
    """
    Convenience function to predict aircraft positions.
    """
    predictor = AircraftPredictor()
    
    if current_state is None:
        current_state = await predictor.get_current_state(entity_id)
        if current_state is None:
            return []
    
    from_time = from_time or datetime.now(timezone.utc)
    to_time = to_time or (from_time + timedelta(hours=2))
    
    return await predictor.predict_positions(
        state=current_state,
        from_time=from_time,
        to_time=to_time,
        resolution_seconds=resolution_seconds,
    )