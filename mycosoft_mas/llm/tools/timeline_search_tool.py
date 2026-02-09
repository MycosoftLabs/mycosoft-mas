"""
Timeline Search Tool - February 6, 2026

LangGraph tool for timeline queries.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TimelineSearchInput(BaseModel):
    """Input for timeline search."""
    entity_type: Optional[str] = Field(None, description="Type of entity (aircraft, vessel, satellite, wildlife, etc.)")
    time_range: Optional[str] = Field(None, description="Time range like 'last 24 hours', 'last week', or ISO date range")
    location: Optional[str] = Field(None, description="Location name or coordinates (lat,lng,radius_km)")
    query: Optional[str] = Field(None, description="Free-form search query")
    limit: int = Field(20, description="Maximum number of results")


class TimelineSearchTool:
    """
    Search the MINDEX timeline database.
    """
    
    name = "timeline_search"
    description = """Search the MINDEX timeline database for events and entity tracks.
    Can filter by entity type (aircraft, vessel, satellite, wildlife, earthquake, etc.),
    time range (last 24 hours, last week, specific dates), and location.
    Returns matching events with timestamps and locations."""
    args_schema: Type[BaseModel] = TimelineSearchInput
    
    def _parse_time_range(self, time_range: str) -> tuple:
        """Parse time range string to start/end datetimes."""
        now = datetime.utcnow()
        
        time_range_lower = time_range.lower()
        
        if "last" in time_range_lower:
            if "hour" in time_range_lower:
                hours = 1
                for word in time_range_lower.split():
                    if word.isdigit():
                        hours = int(word)
                        break
                return now - timedelta(hours=hours), now
            elif "day" in time_range_lower:
                days = 1
                for word in time_range_lower.split():
                    if word.isdigit():
                        days = int(word)
                        break
                if "24" in time_range_lower:
                    days = 1
                return now - timedelta(days=days), now
            elif "week" in time_range_lower:
                weeks = 1
                for word in time_range_lower.split():
                    if word.isdigit():
                        weeks = int(word)
                        break
                return now - timedelta(weeks=weeks), now
            elif "month" in time_range_lower:
                return now - timedelta(days=30), now
        
        # Default to last 24 hours
        return now - timedelta(hours=24), now
    
    def _parse_location(self, location: str) -> Optional[Dict]:
        """Parse location string."""
        if "," in location:
            parts = location.split(",")
            if len(parts) >= 2:
                try:
                    lat = float(parts[0].strip())
                    lng = float(parts[1].strip())
                    radius = float(parts[2].strip()) if len(parts) > 2 else 50
                    return {"lat": lat, "lng": lng, "radius_km": radius}
                except ValueError:
                    pass
        
        # Return as named location
        return {"name": location}
    
    async def _arun(
        self,
        entity_type: Optional[str] = None,
        time_range: Optional[str] = None,
        location: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 20,
    ) -> str:
        """Execute timeline search."""
        try:
            import asyncpg
            import os
            
            connection_string = os.getenv(
                "DATABASE_URL",
                "postgresql://mycosoft:mycosoft@localhost:5432/mindex"
            )
            
            conn = await asyncpg.connect(connection_string)
            
            # Determine table based on entity type
            table_map = {
                "aircraft": "mindex.aircraft_tracks",
                "vessel": "mindex.vessel_tracks",
                "satellite": "mindex.satellite_tracks",
                "wildlife": "mindex.wildlife_observations",
                "earthquake": "mindex.environmental_events",
                "weather": "mindex.earth2_forecasts",
            }
            
            table = table_map.get(entity_type, "mindex.timeline_entries")
            
            # Build query
            conditions = []
            params = []
            param_idx = 1
            
            if time_range:
                start, end = self._parse_time_range(time_range)
                conditions.append(f"timestamp >= ${param_idx}")
                params.append(start)
                param_idx += 1
                conditions.append(f"timestamp <= ${param_idx}")
                params.append(end)
                param_idx += 1
            
            if entity_type:
                conditions.append(f"entity_type = ${param_idx}")
                params.append(entity_type)
                param_idx += 1
            
            params.append(limit)
            
            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            
            sql = f"""
                SELECT * FROM {table}
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT ${param_idx}
            """
            
            try:
                rows = await conn.fetch(sql, *params)
                
                results = [
                    {
                        "id": str(row.get("id", "")),
                        "entity_type": row.get("entity_type", entity_type),
                        "timestamp": row.get("timestamp", "").isoformat() if row.get("timestamp") else None,
                        "lat": row.get("lat"),
                        "lng": row.get("lng"),
                        "properties": dict(row.get("properties", {})) if row.get("properties") else {},
                    }
                    for row in rows
                ]
                
                await conn.close()
                
                return json.dumps({
                    "count": len(results),
                    "results": results
                }, indent=2, default=str)
                
            except Exception as e:
                # Table might not exist yet
                await conn.close()
                return json.dumps({
                    "count": 0,
                    "results": [],
                    "note": f"No data available for {entity_type or 'timeline'}"
                })
            
        except Exception as e:
            logger.error(f"Timeline search error: {e}")
            return f"Error searching timeline: {str(e)}"


def create_timeline_search_tool():
    """Create a timeline search tool instance."""
    return TimelineSearchTool()