"""
Earth2 Memory System - February 5, 2026

Provides specialized memory management for Earth2Studio weather AI:
- Forecast result storage with timestamps and parameters
- User weather query patterns and preferences
- Model usage tracking and optimization
- Inference result caching for quick recall
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

logger = logging.getLogger("Earth2Memory")


class Earth2Model(str, Enum):
    """Available Earth2 models."""
    FCN = "fcn"
    PANGU = "pangu"
    GRAPHCAST = "graphcast"
    SFNO = "sfno"
    CORRDIFF = "corrdiff"
    STORMSCOPE = "stormscope"


class WeatherVariable(str, Enum):
    """Weather variables tracked in forecasts."""
    TEMPERATURE = "temperature"
    WIND_U = "wind_u"
    WIND_V = "wind_v"
    PRESSURE = "pressure"
    PRECIPITATION = "precipitation"
    HUMIDITY = "humidity"
    CLOUD_COVER = "cloud_cover"


@dataclass
class ForecastResult:
    """A single forecast result."""
    id: UUID = field(default_factory=uuid4)
    user_id: str = ""
    model: Earth2Model = Earth2Model.FCN
    location: Dict[str, float] = field(default_factory=dict)  # lat, lng
    location_name: Optional[str] = None
    lead_time_hours: int = 24
    variables: List[WeatherVariable] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    result_summary: Optional[Dict[str, Any]] = None
    inference_time_ms: Optional[int] = None
    source: str = "api"  # 'api', 'voice', 'scheduled'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "model": self.model.value,
            "location": self.location,
            "location_name": self.location_name,
            "lead_time_hours": self.lead_time_hours,
            "variables": [v.value for v in self.variables],
            "timestamp": self.timestamp.isoformat(),
            "result_summary": self.result_summary,
            "inference_time_ms": self.inference_time_ms,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ForecastResult":
        return cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            user_id=data.get("user_id", ""),
            model=Earth2Model(data.get("model", "fcn")),
            location=data.get("location", {}),
            location_name=data.get("location_name"),
            lead_time_hours=data.get("lead_time_hours", 24),
            variables=[WeatherVariable(v) for v in data.get("variables", [])],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(timezone.utc),
            result_summary=data.get("result_summary"),
            inference_time_ms=data.get("inference_time_ms"),
            source=data.get("source", "api")
        )


@dataclass
class UserWeatherPreferences:
    """User's weather preferences learned from usage."""
    user_id: str
    favorite_locations: List[Dict[str, Any]] = field(default_factory=list)
    preferred_models: List[Earth2Model] = field(default_factory=list)
    common_lead_times: List[int] = field(default_factory=list)
    variables_of_interest: List[WeatherVariable] = field(default_factory=list)
    forecast_frequency: int = 0  # forecasts per day average
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "favorite_locations": self.favorite_locations,
            "preferred_models": [m.value for m in self.preferred_models],
            "common_lead_times": self.common_lead_times,
            "variables_of_interest": [v.value for v in self.variables_of_interest],
            "forecast_frequency": self.forecast_frequency,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class ModelUsageStats:
    """Statistics for a single model."""
    model: Earth2Model
    total_runs: int = 0
    total_inference_time_ms: int = 0
    avg_inference_time_ms: float = 0.0
    last_used: Optional[datetime] = None
    error_count: int = 0
    vram_mb: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model.value,
            "total_runs": self.total_runs,
            "total_inference_time_ms": self.total_inference_time_ms,
            "avg_inference_time_ms": self.avg_inference_time_ms,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "error_count": self.error_count,
            "vram_mb": self.vram_mb
        }


class Earth2Memory:
    """
    Memory manager for Earth2Studio weather AI.
    
    Provides:
    - Forecast result storage and retrieval
    - User weather preference learning
    - Model usage statistics tracking
    - Inference result caching
    """
    
    # Cache settings
    CACHE_TTL = timedelta(hours=6)  # Cache forecast results for 6 hours
    MAX_CACHE_SIZE = 100  # Maximum cached forecasts
    
    def __init__(self, database_url: Optional[str] = None):
        self._database_url = database_url or os.getenv(
            "MINDEX_DATABASE_URL",
            "postgresql://mycosoft:Mushroom1!Mushroom1!@192.168.0.189:5432/mindex"
        )
        self._pool = None
        self._initialized = False
        
        # In-memory caches
        self._forecast_cache: Dict[str, ForecastResult] = {}  # cache_key -> result
        self._user_prefs: Dict[str, UserWeatherPreferences] = {}  # user_id -> prefs
        self._model_stats: Dict[Earth2Model, ModelUsageStats] = {}  # model -> stats
        
        # Initialize model stats
        for model in Earth2Model:
            self._model_stats[model] = ModelUsageStats(model=model)
    
    async def initialize(self) -> None:
        """Initialize the Earth2 memory system."""
        if self._initialized:
            return
        
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=1,
                max_size=3
            )
            logger.info("Earth2 memory connected to database")
        except Exception as e:
            logger.warning(f"Database connection failed, using in-memory only: {e}")
        
        self._initialized = True
        logger.info("Earth2 memory manager initialized")
    
    async def record_forecast(
        self,
        user_id: str,
        model: str,
        location: Dict[str, float],
        lead_time_hours: int,
        variables: List[str],
        result_summary: Optional[Dict[str, Any]] = None,
        inference_time_ms: Optional[int] = None,
        source: str = "api",
        location_name: Optional[str] = None
    ) -> ForecastResult:
        """
        Record a forecast execution.
        
        Args:
            user_id: User who requested the forecast
            model: Model used (fcn, pangu, etc.)
            location: Dict with lat/lng
            lead_time_hours: Forecast lead time
            variables: Weather variables requested
            result_summary: Optional summary of results
            inference_time_ms: Inference time in milliseconds
            source: Request source (api, voice, scheduled)
            location_name: Human-readable location name
        
        Returns:
            Created ForecastResult
        """
        if not self._initialized:
            await self.initialize()
        
        # Create forecast record
        try:
            model_enum = Earth2Model(model.lower())
        except ValueError:
            model_enum = Earth2Model.FCN
        
        var_enums = []
        for v in variables:
            try:
                var_enums.append(WeatherVariable(v.lower()))
            except ValueError:
                pass
        
        forecast = ForecastResult(
            user_id=user_id,
            model=model_enum,
            location=location,
            location_name=location_name,
            lead_time_hours=lead_time_hours,
            variables=var_enums,
            result_summary=result_summary,
            inference_time_ms=inference_time_ms,
            source=source
        )
        
        # Cache result
        cache_key = f"{user_id}:{model}:{location.get('lat', 0):.2f},{location.get('lng', 0):.2f}:{lead_time_hours}"
        self._forecast_cache[cache_key] = forecast
        
        # Trim cache if needed
        if len(self._forecast_cache) > self.MAX_CACHE_SIZE:
            oldest_key = next(iter(self._forecast_cache))
            del self._forecast_cache[oldest_key]
        
        # Update model stats
        stats = self._model_stats[model_enum]
        stats.total_runs += 1
        if inference_time_ms:
            stats.total_inference_time_ms += inference_time_ms
            stats.avg_inference_time_ms = stats.total_inference_time_ms / stats.total_runs
        stats.last_used = datetime.now(timezone.utc)
        
        # Update user preferences
        await self._update_user_preferences(user_id, forecast)
        
        # Persist to database
        await self._persist_forecast(forecast)
        
        logger.debug(f"Recorded forecast {forecast.id} for user {user_id}")
        return forecast
    
    async def get_user_forecasts(
        self,
        user_id: str,
        limit: int = 10,
        model: Optional[str] = None
    ) -> List[ForecastResult]:
        """Get a user's recent forecasts."""
        if not self._initialized:
            await self.initialize()
        
        if not self._pool:
            # Return from cache
            return [
                f for f in self._forecast_cache.values()
                if f.user_id == user_id
            ][:limit]
        
        try:
            async with self._pool.acquire() as conn:
                query = """
                    SELECT * FROM mindex.earth2_forecasts
                    WHERE user_id = $1
                """
                params = [user_id]
                
                if model:
                    query += " AND model = $2"
                    params.append(model)
                
                query += " ORDER BY timestamp DESC LIMIT $" + str(len(params) + 1)
                params.append(limit)
                
                rows = await conn.fetch(query, *params)
                
                return [
                    ForecastResult.from_dict({
                        "id": str(row["id"]),
                        "user_id": row["user_id"],
                        "model": row["model"],
                        "location": json.loads(row["location"]) if row["location"] else {},
                        "location_name": row.get("location_name"),
                        "lead_time_hours": row["lead_time_hours"],
                        "variables": json.loads(row["variables"]) if row["variables"] else [],
                        "timestamp": row["timestamp"].isoformat(),
                        "result_summary": json.loads(row["result_summary"]) if row.get("result_summary") else None,
                        "inference_time_ms": row.get("inference_time_ms"),
                        "source": row.get("source", "api")
                    })
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get user forecasts: {e}")
            return []
    
    async def get_user_preferences(self, user_id: str) -> UserWeatherPreferences:
        """Get or create user weather preferences."""
        if not self._initialized:
            await self.initialize()
        
        if user_id in self._user_prefs:
            return self._user_prefs[user_id]
        
        # Try to load from database
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT * FROM mindex.earth2_user_preferences WHERE user_id = $1",
                        user_id
                    )
                    if row:
                        prefs = UserWeatherPreferences(
                            user_id=user_id,
                            favorite_locations=json.loads(row["favorite_locations"]) if row["favorite_locations"] else [],
                            preferred_models=[Earth2Model(m) for m in json.loads(row["preferred_models"])] if row["preferred_models"] else [],
                            common_lead_times=json.loads(row["common_lead_times"]) if row["common_lead_times"] else [],
                            variables_of_interest=[WeatherVariable(v) for v in json.loads(row["variables_of_interest"])] if row["variables_of_interest"] else [],
                            forecast_frequency=row.get("forecast_frequency", 0)
                        )
                        self._user_prefs[user_id] = prefs
                        return prefs
            except Exception as e:
                logger.debug(f"Failed to load preferences: {e}")
        
        # Create new preferences
        prefs = UserWeatherPreferences(user_id=user_id)
        self._user_prefs[user_id] = prefs
        return prefs
    
    async def get_model_stats(self, model: Optional[str] = None) -> Dict[str, Any]:
        """Get model usage statistics."""
        if model:
            try:
                model_enum = Earth2Model(model.lower())
                return self._model_stats[model_enum].to_dict()
            except (ValueError, KeyError):
                return {"error": f"Unknown model: {model}"}
        
        return {
            model.value: stats.to_dict()
            for model, stats in self._model_stats.items()
        }
    
    async def get_cached_forecast(
        self,
        user_id: str,
        model: str,
        location: Dict[str, float],
        lead_time_hours: int,
        max_age_hours: int = 6
    ) -> Optional[ForecastResult]:
        """Get a cached forecast if available and fresh."""
        cache_key = f"{user_id}:{model}:{location.get('lat', 0):.2f},{location.get('lng', 0):.2f}:{lead_time_hours}"
        
        if cache_key in self._forecast_cache:
            forecast = self._forecast_cache[cache_key]
            age = datetime.now(timezone.utc) - forecast.timestamp
            if age < timedelta(hours=max_age_hours):
                logger.debug(f"Cache hit for forecast {cache_key}")
                return forecast
        
        return None
    
    async def get_popular_locations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most popular forecast locations."""
        if not self._pool:
            # Aggregate from cache
            location_counts: Dict[str, int] = {}
            for forecast in self._forecast_cache.values():
                if forecast.location_name:
                    key = forecast.location_name
                else:
                    key = f"{forecast.location.get('lat', 0):.2f},{forecast.location.get('lng', 0):.2f}"
                location_counts[key] = location_counts.get(key, 0) + 1
            
            return [
                {"location": loc, "count": cnt}
                for loc, cnt in sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
            ]
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT location_name, location, COUNT(*) as cnt
                    FROM mindex.earth2_forecasts
                    WHERE timestamp > NOW() - INTERVAL '30 days'
                    GROUP BY location_name, location
                    ORDER BY cnt DESC
                    LIMIT $1
                """, limit)
                
                return [
                    {
                        "location": row["location_name"] or row["location"],
                        "count": row["cnt"]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get popular locations: {e}")
            return []
    
    async def get_context_for_voice(self, user_id: str) -> Dict[str, Any]:
        """Get Earth2 context for voice commands."""
        prefs = await self.get_user_preferences(user_id)
        forecasts = await self.get_user_forecasts(user_id, limit=3)
        
        return {
            "user_id": user_id,
            "favorite_locations": prefs.favorite_locations[:5],
            "preferred_models": [m.value for m in prefs.preferred_models],
            "recent_forecasts": [
                {
                    "location": f.location_name or f"{f.location.get('lat', 0):.1f}, {f.location.get('lng', 0):.1f}",
                    "model": f.model.value,
                    "lead_time": f.lead_time_hours,
                    "when": f.timestamp.isoformat()
                }
                for f in forecasts
            ],
            "common_lead_times": prefs.common_lead_times,
            "variables_of_interest": [v.value for v in prefs.variables_of_interest]
        }
    
    async def _update_user_preferences(
        self,
        user_id: str,
        forecast: ForecastResult
    ) -> None:
        """Update user preferences based on a forecast."""
        prefs = await self.get_user_preferences(user_id)
        
        # Update favorite locations
        loc_entry = {
            "location": forecast.location,
            "name": forecast.location_name,
            "count": 1
        }
        
        # Check if location already in favorites
        found = False
        for loc in prefs.favorite_locations:
            if (loc.get("location", {}).get("lat") == forecast.location.get("lat") and
                loc.get("location", {}).get("lng") == forecast.location.get("lng")):
                loc["count"] = loc.get("count", 0) + 1
                found = True
                break
        
        if not found and forecast.location:
            prefs.favorite_locations.append(loc_entry)
        
        # Sort by count and keep top 10
        prefs.favorite_locations.sort(key=lambda x: x.get("count", 0), reverse=True)
        prefs.favorite_locations = prefs.favorite_locations[:10]
        
        # Update preferred models
        if forecast.model not in prefs.preferred_models:
            prefs.preferred_models.insert(0, forecast.model)
            prefs.preferred_models = prefs.preferred_models[:5]
        
        # Update common lead times
        if forecast.lead_time_hours not in prefs.common_lead_times:
            prefs.common_lead_times.append(forecast.lead_time_hours)
            prefs.common_lead_times = sorted(set(prefs.common_lead_times))[:5]
        
        # Update variables of interest
        for var in forecast.variables:
            if var not in prefs.variables_of_interest:
                prefs.variables_of_interest.append(var)
        prefs.variables_of_interest = prefs.variables_of_interest[:10]
        
        prefs.last_updated = datetime.now(timezone.utc)
        
        # Persist preferences
        await self._persist_preferences(prefs)
    
    async def _persist_forecast(self, forecast: ForecastResult) -> bool:
        """Persist a forecast to the database."""
        if not self._pool:
            return False
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO mindex.earth2_forecasts
                        (id, user_id, model, location, location_name, lead_time_hours,
                         variables, timestamp, result_summary, inference_time_ms, source)
                    VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7::jsonb, $8, $9::jsonb, $10, $11)
                    ON CONFLICT (id) DO UPDATE SET
                        result_summary = EXCLUDED.result_summary,
                        inference_time_ms = EXCLUDED.inference_time_ms
                """, str(forecast.id), forecast.user_id, forecast.model.value,
                    json.dumps(forecast.location), forecast.location_name,
                    forecast.lead_time_hours, json.dumps([v.value for v in forecast.variables]),
                    forecast.timestamp, json.dumps(forecast.result_summary) if forecast.result_summary else None,
                    forecast.inference_time_ms, forecast.source)
            return True
        except Exception as e:
            logger.error(f"Failed to persist forecast: {e}")
            return False
    
    async def _persist_preferences(self, prefs: UserWeatherPreferences) -> bool:
        """Persist user preferences to the database."""
        if not self._pool:
            return False
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO mindex.earth2_user_preferences
                        (user_id, favorite_locations, preferred_models, common_lead_times,
                         variables_of_interest, forecast_frequency, last_updated)
                    VALUES ($1, $2::jsonb, $3::jsonb, $4::jsonb, $5::jsonb, $6, $7)
                    ON CONFLICT (user_id) DO UPDATE SET
                        favorite_locations = EXCLUDED.favorite_locations,
                        preferred_models = EXCLUDED.preferred_models,
                        common_lead_times = EXCLUDED.common_lead_times,
                        variables_of_interest = EXCLUDED.variables_of_interest,
                        forecast_frequency = EXCLUDED.forecast_frequency,
                        last_updated = EXCLUDED.last_updated
                """, prefs.user_id, json.dumps(prefs.favorite_locations),
                    json.dumps([m.value for m in prefs.preferred_models]),
                    json.dumps(prefs.common_lead_times),
                    json.dumps([v.value for v in prefs.variables_of_interest]),
                    prefs.forecast_frequency, prefs.last_updated)
            return True
        except Exception as e:
            logger.error(f"Failed to persist preferences: {e}")
            return False
    
    async def record_model_error(self, model: str) -> None:
        """Record a model error."""
        try:
            model_enum = Earth2Model(model.lower())
            self._model_stats[model_enum].error_count += 1
        except ValueError:
            pass
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Earth2 memory statistics."""
        return {
            "initialized": self._initialized,
            "database_connected": self._pool is not None,
            "cached_forecasts": len(self._forecast_cache),
            "cached_user_prefs": len(self._user_prefs),
            "model_stats": {m.value: s.to_dict() for m, s in self._model_stats.items()}
        }
    
    async def shutdown(self) -> None:
        """Shutdown the Earth2 memory manager."""
        if self._pool:
            await self._pool.close()
        logger.info("Earth2 memory manager shutdown")


# Singleton instance
_earth2_memory: Optional[Earth2Memory] = None


async def get_earth2_memory() -> Earth2Memory:
    """Get or create the singleton Earth2 memory instance."""
    global _earth2_memory
    if _earth2_memory is None:
        _earth2_memory = Earth2Memory()
        await _earth2_memory.initialize()
    return _earth2_memory