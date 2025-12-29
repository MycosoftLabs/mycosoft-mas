"""MycoDRONE Mission Planner Agent for MAS."""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import httpx
import os
from uuid import UUID


class DroneMissionPlannerAgent:
    """Agent for planning and managing MycoDRONE missions."""
    
    def __init__(self):
        self.mindex_base_url = os.getenv("MINDEX_API_BASE_URL", "http://localhost:8002")
        self.mindex_api_key = os.getenv("MINDEX_API_KEY", "dev-secret")
    
    async def plan_deployment(
        self,
        target_location: Tuple[float, float, float],  # (lat, lon, alt)
        payload_type: str,
    ) -> Dict[str, Any]:
        """
        Plan a deployment mission.
        
        Args:
            target_location: Tuple of (latitude, longitude, altitude)
            payload_type: Type of payload ('Mushroom1' or 'SporeBase')
        
        Returns:
            Mission plan dictionary
        """
        lat, lon, alt = target_location
        
        # Find available drone
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.mindex_base_url}/drone/status",
                headers={"X-API-Key": self.mindex_api_key},
            )
            response.raise_for_status()
            drones = response.json()
        
        # Select best drone (available, sufficient battery, payload capacity)
        available_drones = [
            d for d in drones
            if d.get("mission_state") in (None, "idle")
            and d.get("battery_percent", 0) > 30
        ]
        
        if not available_drones:
            raise ValueError("No available drones for deployment")
        
        # Select drone with highest battery and sufficient payload capacity
        selected_drone = max(
            available_drones,
            key=lambda d: (
                d.get("battery_percent", 0),
                d.get("max_payload_kg", 0) >= 1.2,  # Mushroom1 weight
            ),
        )
        
        # Create mission
        mission_data = {
            "drone_id": selected_drone["drone_id"],
            "mission_type": "deploy",
            "waypoint_lat": lat,
            "waypoint_lon": lon,
            "waypoint_alt": alt,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.mindex_base_url}/drone/missions",
                headers={
                    "X-API-Key": self.mindex_api_key,
                    "Content-Type": "application/json",
                },
                json=mission_data,
            )
            response.raise_for_status()
            mission = response.json()
        
        return {
            "mission_id": mission["id"],
            "drone_id": selected_drone["drone_id"],
            "drone_name": selected_drone["drone_name"],
            "mission_type": "deploy",
            "target_location": {
                "latitude": lat,
                "longitude": lon,
                "altitude": alt,
            },
            "payload_type": payload_type,
            "status": mission["status"],
            "created_at": mission["created_at"],
        }
    
    async def plan_retrieval(self, device_id: str) -> Dict[str, Any]:
        """
        Plan a retrieval mission for a device.
        
        Args:
            device_id: Target device ID to retrieve
        
        Returns:
            Mission plan dictionary
        """
        # Get device location (from MINDEX device table)
        async with httpx.AsyncClient() as client:
            # TODO: Get device location from device registry
            # For now, assume we have last known location
            device_response = await client.get(
                f"{self.mindex_base_url}/devices/{device_id}",
                headers={"X-API-Key": self.mindex_api_key},
            )
            # If device not found, raise error
            if device_response.status_code == 404:
                raise ValueError(f"Device {device_id} not found")
            
            # Get available drones
            drones_response = await client.get(
                f"{self.mindex_base_url}/drone/status",
                headers={"X-API-Key": self.mindex_api_key},
            )
            drones_response.raise_for_status()
            drones = drones_response.json()
        
        # Select best drone
        available_drones = [
            d for d in drones
            if d.get("mission_state") in (None, "idle")
            and d.get("battery_percent", 0) > 40  # Higher battery for retrieval
        ]
        
        if not available_drones:
            raise ValueError("No available drones for retrieval")
        
        selected_drone = max(available_drones, key=lambda d: d.get("battery_percent", 0))
        
        # Create mission
        mission_data = {
            "drone_id": selected_drone["drone_id"],
            "mission_type": "retrieve",
            "target_device_id": device_id,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.mindex_base_url}/drone/missions",
                headers={
                    "X-API-Key": self.mindex_api_key,
                    "Content-Type": "application/json",
                },
                json=mission_data,
            )
            response.raise_for_status()
            mission = response.json()
        
        return {
            "mission_id": mission["id"],
            "drone_id": selected_drone["drone_id"],
            "drone_name": selected_drone["drone_name"],
            "mission_type": "retrieve",
            "target_device_id": device_id,
            "status": mission["status"],
            "created_at": mission["created_at"],
        }
    
    async def allocate_tasks(self, missions: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Allocate multiple missions to available drones.
        
        Args:
            missions: List of mission requests
        
        Returns:
            Dictionary mapping drone_id to list of mission_ids
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.mindex_base_url}/drone/status",
                headers={"X-API-Key": self.mindex_api_key},
            )
            response.raise_for_status()
            drones = response.json()
        
        # Filter available drones
        available_drones = [
            d for d in drones
            if d.get("mission_state") in (None, "idle")
            and d.get("battery_percent", 0) > 30
        ]
        
        if len(available_drones) < len(missions):
            raise ValueError(f"Not enough drones: {len(available_drones)} available, {len(missions)} missions")
        
        # Simple allocation: assign missions in order
        allocation = {}
        for i, mission in enumerate(missions):
            drone = available_drones[i % len(available_drones)]
            drone_id = drone["drone_id"]
            
            if drone_id not in allocation:
                allocation[drone_id] = []
            
            allocation[drone_id].append(mission.get("mission_id", f"mission_{i}"))
        
        return allocation
    
    async def get_mission_status(self, mission_id: str) -> Dict[str, Any]:
        """Get status of a mission."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.mindex_base_url}/drone/missions/{mission_id}",
                headers={"X-API-Key": self.mindex_api_key},
            )
            response.raise_for_status()
            return response.json()

