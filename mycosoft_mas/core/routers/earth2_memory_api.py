"""
Earth2 Memory API Router - February 5, 2026

Provides API endpoints for accessing Earth2 weather AI memory:
- Forecast history retrieval
- User weather preferences
- Model usage statistics
- Popular locations
- Cached forecast lookup
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

router = APIRouter(prefix="/earth2-memory", tags=["Earth2 Memory"])


# Pydantic models for API
class ForecastHistoryRequest(BaseModel):
    user_id: str
    limit: int = Field(default=10, ge=1, le=100)
    model: Optional[str] = None


class ForecastHistoryResponse(BaseModel):
    forecasts: List[Dict[str, Any]]
    total: int


class UserPreferencesResponse(BaseModel):
    user_id: str
    favorite_locations: List[Dict[str, Any]]
    preferred_models: List[str]
    common_lead_times: List[int]
    variables_of_interest: List[str]
    forecast_frequency: int


class ModelStatsResponse(BaseModel):
    model: Optional[str]
    stats: Dict[str, Any]


class PopularLocationsResponse(BaseModel):
    locations: List[Dict[str, Any]]


class CachedForecastRequest(BaseModel):
    user_id: str
    model: str
    lat: float
    lng: float
    lead_time_hours: int = 24
    max_age_hours: int = 6


# Singleton memory instance
_earth2_memory = None


async def get_memory():
    """Get Earth2 memory instance."""
    global _earth2_memory
    if _earth2_memory is None:
        from mycosoft_mas.memory.earth2_memory import get_earth2_memory
        _earth2_memory = await get_earth2_memory()
    return _earth2_memory


@router.get("/health")
async def health_check():
    """Health check for Earth2 memory API."""
    memory = await get_memory()
    stats = await memory.get_stats()
    return {
        "status": "healthy",
        "service": "earth2-memory",
        "stats": stats
    }


@router.get("/forecasts/{user_id}", response_model=ForecastHistoryResponse)
async def get_forecast_history(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    model: Optional[str] = None
):
    """Get a user's forecast history."""
    memory = await get_memory()
    forecasts = await memory.get_user_forecasts(user_id, limit=limit, model=model)
    
    return ForecastHistoryResponse(
        forecasts=[f.to_dict() for f in forecasts],
        total=len(forecasts)
    )


@router.get("/preferences/{user_id}", response_model=UserPreferencesResponse)
async def get_user_preferences(user_id: str):
    """Get a user's weather preferences learned from usage."""
    memory = await get_memory()
    prefs = await memory.get_user_preferences(user_id)
    
    return UserPreferencesResponse(
        user_id=prefs.user_id,
        favorite_locations=prefs.favorite_locations,
        preferred_models=[m.value for m in prefs.preferred_models],
        common_lead_times=prefs.common_lead_times,
        variables_of_interest=[v.value for v in prefs.variables_of_interest],
        forecast_frequency=prefs.forecast_frequency
    )


@router.get("/model-stats")
async def get_model_stats(model: Optional[str] = None):
    """Get model usage statistics."""
    memory = await get_memory()
    stats = await memory.get_model_stats(model=model)
    
    return ModelStatsResponse(
        model=model,
        stats=stats
    )


@router.get("/popular-locations", response_model=PopularLocationsResponse)
async def get_popular_locations(limit: int = Query(default=10, ge=1, le=50)):
    """Get the most popular forecast locations."""
    memory = await get_memory()
    locations = await memory.get_popular_locations(limit=limit)
    
    return PopularLocationsResponse(locations=locations)


@router.post("/check-cache")
async def check_cached_forecast(request: CachedForecastRequest):
    """Check for a cached forecast that matches the parameters."""
    memory = await get_memory()
    
    cached = await memory.get_cached_forecast(
        user_id=request.user_id,
        model=request.model,
        location={"lat": request.lat, "lng": request.lng},
        lead_time_hours=request.lead_time_hours,
        max_age_hours=request.max_age_hours
    )
    
    if cached:
        return {
            "cached": True,
            "forecast": cached.to_dict()
        }
    
    return {"cached": False, "forecast": None}


@router.get("/voice-context/{user_id}")
async def get_voice_context(user_id: str):
    """Get Earth2 context formatted for voice interactions."""
    memory = await get_memory()
    context = await memory.get_context_for_voice(user_id)
    return context


@router.get("/stats")
async def get_memory_stats():
    """Get overall Earth2 memory statistics."""
    memory = await get_memory()
    return await memory.get_stats()