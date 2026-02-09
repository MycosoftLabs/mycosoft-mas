"""
Satellite Predictor - February 6, 2026

Predicts satellite positions using SGP4/SDP4 orbit propagation.
Uses Two-Line Element (TLE) sets from NORAD.
"""

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from .base_predictor import BasePredictor
from .prediction_types import (
    EntityState,
    EntityType,
    GeoPoint,
    PredictedPosition,
    PredictionSource,
    Velocity,
)

logger = logging.getLogger("SatellitePredictor")


# SGP4 constants
EARTH_RADIUS_KM = 6378.137
MU = 398600.4418  # Earth gravitational parameter km^3/s^2


class SatellitePredictor(BasePredictor):
    """
    Predicts satellite positions using SGP4 orbit propagation.
    
    Very accurate for short to medium term predictions (hours to days).
    Requires TLE data to be available.
    """
    
    entity_type = EntityType.SATELLITE
    prediction_source = PredictionSource.ORBIT_PROPAGATION
    model_version = "1.0.0"
    
    # Satellite predictions are very accurate
    initial_confidence = 0.99
    confidence_half_life_seconds = 86400  # 24 hours
    minimum_confidence = 0.8
    
    max_prediction_horizon = timedelta(days=7)
    
    # Minimal uncertainty for orbital mechanics
    base_uncertainty_meters = 10
    uncertainty_growth_rate = 0.001  # Very slow growth
    
    def __init__(self):
        super().__init__()
        self._sgp4_available = self._check_sgp4()
    
    def _check_sgp4(self) -> bool:
        """Check if sgp4 library is available."""
        try:
            from sgp4.api import Satrec
            return True
        except ImportError:
            logger.warning("sgp4 library not available, using simplified model")
            return False
    
    async def get_current_state(self, entity_id: str) -> Optional[EntityState]:
        """Get current satellite state from TLE database."""
        # In production, would query TLE database
        return None
    
    async def predict_positions(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Generate predicted positions using orbital mechanics.
        """
        predictions: List[PredictedPosition] = []
        
        if not state.tle_line1 or not state.tle_line2:
            logger.warning(f"No TLE data for satellite {state.entity_id}")
            return predictions
        
        if self._sgp4_available:
            predictions = await self._predict_with_sgp4(
                state, from_time, to_time, resolution_seconds
            )
        else:
            predictions = await self._predict_simplified(
                state, from_time, to_time, resolution_seconds
            )
        
        return predictions
    
    async def _predict_with_sgp4(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Predict using full SGP4 propagation.
        """
        from sgp4.api import Satrec, jday
        
        predictions = []
        
        # Parse TLE
        satellite = Satrec.twoline2rv(state.tle_line1, state.tle_line2)
        
        current_time = from_time
        while current_time <= to_time:
            # Convert to Julian date
            jd, fr = jday(
                current_time.year,
                current_time.month,
                current_time.day,
                current_time.hour,
                current_time.minute,
                current_time.second + current_time.microsecond / 1e6
            )
            
            # Propagate
            e, r, v = satellite.sgp4(jd, fr)
            
            if e != 0:
                logger.warning(f"SGP4 error {e} for satellite {state.entity_id}")
                current_time += timedelta(seconds=resolution_seconds)
                continue
            
            # Convert ECI to geodetic
            lat, lng, alt = self._eci_to_geodetic(r, current_time)
            
            # Calculate velocity magnitude and direction
            speed = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)  # km/s
            
            predictions.append(PredictedPosition(
                entity_id=state.entity_id,
                entity_type=EntityType.SATELLITE,
                timestamp=current_time,
                position=GeoPoint(
                    lat=lat,
                    lng=lng,
                    altitude=alt * 1000,  # km to meters
                ),
                velocity=Velocity(
                    speed=speed * 1000,  # km/s to m/s
                    heading=0,  # Would calculate from velocity vector
                ),
                confidence=1.0,
                prediction_source=PredictionSource.ORBIT_PROPAGATION,
                model_version=self.model_version,
                metadata={
                    "norad_id": state.entity_id,
                    "altitude_km": alt,
                },
            ))
            
            current_time += timedelta(seconds=resolution_seconds)
        
        return predictions
    
    async def _predict_simplified(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Simplified orbital prediction without sgp4 library.
        Uses basic Keplerian elements extracted from TLE.
        """
        predictions = []
        
        # Parse basic orbital elements from TLE
        elements = self._parse_tle_elements(state.tle_line1, state.tle_line2)
        if not elements:
            return predictions
        
        # Calculate orbital period
        n = elements["mean_motion"]  # revolutions per day
        period_seconds = 86400 / n
        
        # Starting mean anomaly
        M0 = elements["mean_anomaly"]
        epoch = elements["epoch"]
        
        current_time = from_time
        while current_time <= to_time:
            # Time since epoch
            dt = (current_time - epoch).total_seconds()
            
            # Current mean anomaly (simplified)
            M = (M0 + 360 * (dt / period_seconds)) % 360
            
            # Very simplified position (circular orbit approximation)
            inclination = elements["inclination"]
            raan = elements["raan"]
            
            # Calculate position in orbital plane
            theta = math.radians(M)
            
            # Simple ground track (ignoring many factors)
            lat = math.degrees(math.asin(
                math.sin(math.radians(inclination)) * math.sin(theta)
            ))
            lng = (raan + math.degrees(theta) - 
                   (dt / 86400) * 360.98564736629) % 360
            if lng > 180:
                lng -= 360
            
            altitude = elements["altitude_km"]
            
            predictions.append(PredictedPosition(
                entity_id=state.entity_id,
                entity_type=EntityType.SATELLITE,
                timestamp=current_time,
                position=GeoPoint(lat=lat, lng=lng, altitude=altitude * 1000),
                confidence=1.0,
                prediction_source=PredictionSource.ORBIT_PROPAGATION,
                model_version=self.model_version + "-simplified",
            ))
            
            current_time += timedelta(seconds=resolution_seconds)
        
        return predictions
    
    def _parse_tle_elements(self, line1: str, line2: str) -> Optional[Dict]:
        """Parse TLE into orbital elements."""
        try:
            # Line 2 parsing
            inclination = float(line2[8:16].strip())
            raan = float(line2[17:25].strip())
            eccentricity = float("0." + line2[26:33].strip())
            arg_perigee = float(line2[34:42].strip())
            mean_anomaly = float(line2[43:51].strip())
            mean_motion = float(line2[52:63].strip())
            
            # Calculate altitude (simplified)
            # n = sqrt(mu/a^3), solve for a
            n_rad = mean_motion * 2 * math.pi / 86400  # rad/s
            a_km = (MU / (n_rad * n_rad)) ** (1/3)
            altitude_km = a_km - EARTH_RADIUS_KM
            
            # Parse epoch from line 1
            epoch_year = int(line1[18:20])
            epoch_day = float(line1[20:32])
            
            if epoch_year < 57:
                epoch_year += 2000
            else:
                epoch_year += 1900
            
            epoch = datetime(epoch_year, 1, 1, tzinfo=timezone.utc) + timedelta(days=epoch_day - 1)
            
            return {
                "inclination": inclination,
                "raan": raan,
                "eccentricity": eccentricity,
                "arg_perigee": arg_perigee,
                "mean_anomaly": mean_anomaly,
                "mean_motion": mean_motion,
                "altitude_km": altitude_km,
                "epoch": epoch,
            }
        except Exception as e:
            logger.error(f"Failed to parse TLE: {e}")
            return None
    
    def _eci_to_geodetic(
        self,
        r: Tuple[float, float, float],
        time: datetime
    ) -> Tuple[float, float, float]:
        """
        Convert ECI coordinates to geodetic (lat, lng, alt).
        
        Simplified conversion.
        """
        x, y, z = r  # km
        
        # Calculate longitude (considering Earth rotation)
        lst = self._local_sidereal_time(time, 0)
        lng = math.degrees(math.atan2(y, x)) - lst
        lng = ((lng + 180) % 360) - 180
        
        # Calculate latitude (simplified, assumes spherical Earth)
        r_xy = math.sqrt(x*x + y*y)
        lat = math.degrees(math.atan2(z, r_xy))
        
        # Altitude
        r_mag = math.sqrt(x*x + y*y + z*z)
        alt = r_mag - EARTH_RADIUS_KM
        
        return lat, lng, alt
    
    def _local_sidereal_time(self, time: datetime, longitude: float) -> float:
        """Calculate Greenwich Mean Sidereal Time."""
        # Julian date
        jd = (time - datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)).total_seconds() / 86400 + 2451545.0
        
        T = (jd - 2451545.0) / 36525.0
        gmst = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * T * T
        
        return gmst % 360