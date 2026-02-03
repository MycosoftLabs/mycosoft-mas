"""NatureOS Memory Connector - February 3, 2026

Connects NatureOS telemetry and device data to the unified memory system.
Handles telemetry archival, environmental events, and device state sync.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger("NatureOSMemoryConnector")


class NatureOSMemoryConnector:
    """Connects NatureOS to the unified memory system."""
    
    def __init__(self):
        self._pool = None
        self._url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/mycosoft")
        self._memory_service = None
    
    async def connect(self) -> bool:
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(self._url, min_size=1, max_size=5)
            logger.info("NatureOS Memory Connector connected")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def store_telemetry(
        self,
        device_id: str,
        device_type: str,
        readings: Dict[str, Any],
        window_minutes: int = 5
    ) -> Optional[int]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchval('''
                    SELECT memory.store_telemetry_snapshot($1::uuid, $2, $3, $4)
                ''', device_id, device_type, readings, window_minutes)
            logger.debug(f"Stored telemetry snapshot {result} for device {device_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to store telemetry: {e}")
            return None
    
    async def store_environmental_event(
        self,
        event_type: str,
        severity: str,
        device_id: Optional[str] = None,
        location: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchval('''
                    SELECT memory.store_environmental_event($1, $2, $3::uuid, $4, $5)
                ''', event_type, severity, device_id, location or {}, data or {})
            logger.info(f"Stored environmental event: {event_type} ({severity})")
            return str(result) if result else None
        except Exception as e:
            logger.error(f"Failed to store event: {e}")
            return None
    
    async def capture_device_state(
        self,
        device_id: str,
        status: str,
        firmware_version: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        calibration_data: Optional[Dict[str, Any]] = None,
        change_reason: str = "periodic"
    ) -> Optional[int]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchval('''
                    SELECT memory.capture_device_state($1::uuid, $2, $3, $4, $5, $6)
                ''', device_id, status, firmware_version, config or {}, calibration_data or {}, change_reason)
            logger.debug(f"Captured device state for {device_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to capture device state: {e}")
            return None
    
    async def get_device_telemetry_history(
        self,
        device_id: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT window_start, window_end, readings, stats
                    FROM memory.telemetry_snapshots
                    WHERE device_id = $1::uuid
                      AND window_start > NOW() - ($2 || ' hours')::INTERVAL
                    ORDER BY window_start DESC
                ''', device_id, str(hours))
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get telemetry history: {e}")
            return []
    
    async def get_device_state_history(
        self,
        device_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT status, firmware_version, config, health_score,
                           changed_fields, change_reason, captured_at
                    FROM memory.device_state_history
                    WHERE device_id = $1::uuid
                    ORDER BY captured_at DESC
                    LIMIT $2
                ''', device_id, limit)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get state history: {e}")
            return []
    
    async def get_environmental_events(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        device_id: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                query = '''
                    SELECT memory_id, namespace, key, event_type, severity,
                           source_device_id, location, event_data, confidence, detected_at
                    FROM memory.environmental_events
                    WHERE detected_at > NOW() - ($1 || ' hours')::INTERVAL
                '''
                params = [str(hours)]
                
                if event_type:
                    query += " AND event_type = $" + str(len(params) + 1)
                    params.append(event_type)
                if severity:
                    query += " AND severity = $" + str(len(params) + 1)
                    params.append(severity)
                if device_id:
                    query += " AND source_device_id = $" + str(len(params) + 1) + "::uuid"
                    params.append(device_id)
                
                query += f" ORDER BY detected_at DESC LIMIT {limit}"
                
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            return []
    
    async def sync_device_registry(self, devices: List[Dict[str, Any]]) -> int:
        if not self._pool:
            await self.connect()
        
        synced = 0
        for device in devices:
            result = await self.capture_device_state(
                device_id=str(device.get("device_id")),
                status=device.get("status", "unknown"),
                firmware_version=device.get("firmware_version"),
                config=device.get("config"),
                calibration_data=device.get("calibration_data"),
                change_reason="registry_sync"
            )
            if result:
                synced += 1
        
        logger.info(f"Synced {synced}/{len(devices)} devices to memory")
        return synced
    
    async def get_device_memory_summary(self) -> Dict[str, Any]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                device_count = await conn.fetchval('''
                    SELECT COUNT(DISTINCT (value->>'device_id')) 
                    FROM memory.entries WHERE scope = 'device'
                ''')
                telemetry_count = await conn.fetchval('''
                    SELECT COUNT(*) FROM memory.telemetry_snapshots
                ''')
                event_count = await conn.fetchval('''
                    SELECT COUNT(*) FROM memory.entries 
                    WHERE scope = 'system' AND namespace LIKE 'natureos:events:%'
                ''')
                
                return {
                    "devices_in_memory": device_count or 0,
                    "telemetry_snapshots": telemetry_count or 0,
                    "environmental_events": event_count or 0,
                }
        except Exception as e:
            logger.error(f"Failed to get summary: {e}")
            return {}


_connector: Optional[NatureOSMemoryConnector] = None


def get_natureos_connector() -> NatureOSMemoryConnector:
    global _connector
    if _connector is None:
        _connector = NatureOSMemoryConnector()
    return _connector


async def init_natureos_connector() -> NatureOSMemoryConnector:
    connector = get_natureos_connector()
    await connector.connect()
    return connector
