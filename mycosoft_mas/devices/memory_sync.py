"""Device State Memory Sync - February 3, 2026

Synchronizes device state with the unified memory system.
Periodic snapshots and change detection for all NatureOS devices.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("DeviceMemorySync")


class DeviceMemorySync:
    """Synchronize device state to memory system."""
    
    def __init__(self):
        self._pool = None
        self._url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/mycosoft")
        self._running = False
        self._task = None
    
    async def connect(self) -> bool:
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(self._url, min_size=1, max_size=3)
            logger.info("Device Memory Sync connected")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def sync_device(
        self,
        device_id: str,
        device_type: str,
        status: str,
        firmware_version: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        calibration_data: Optional[Dict[str, Any]] = None,
        telemetry: Optional[Dict[str, Any]] = None,
        location: Optional[Dict[str, float]] = None
    ) -> bool:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                value = {
                    "device_id": device_id,
                    "device_type": device_type,
                    "status": status,
                    "firmware_version": firmware_version,
                    "config": config or {},
                    "calibration_data": calibration_data or {},
                    "last_telemetry": telemetry,
                    "location": location,
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                }
                
                await conn.execute('''
                    INSERT INTO memory.entries 
                        (scope, namespace, key, value, source)
                    VALUES ('device', 'state:' || $1, 'current', $2, 'device')
                    ON CONFLICT (scope, namespace, key) DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_at = NOW()
                ''', device_id, value)
                
                await conn.execute('''
                    INSERT INTO memory.device_state_history 
                        (device_id, status, firmware_version, config, calibration_data, change_reason)
                    VALUES ($1::uuid, $2, $3, $4, $5, 'sync')
                ''', device_id, status, firmware_version, config or {}, calibration_data or {})
            
            return True
        except Exception as e:
            logger.error(f"Device sync failed: {e}")
            return False
    
    async def sync_telemetry(
        self,
        device_id: str,
        device_type: str,
        readings: Dict[str, Any]
    ) -> bool:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    SELECT memory.store_telemetry_snapshot($1::uuid, $2, $3, 5)
                ''', device_id, device_type, readings)
            return True
        except Exception as e:
            logger.error(f"Telemetry sync failed: {e}")
            return False
    
    async def get_device_current_state(self, device_id: str) -> Optional[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT value, updated_at FROM memory.entries
                    WHERE scope = 'device' 
                      AND namespace = 'state:' || $1 
                      AND key = 'current'
                ''', device_id)
                if row:
                    result = dict(row["value"])
                    result["memory_updated_at"] = row["updated_at"].isoformat() if row["updated_at"] else None
                    return result
                return None
        except Exception as e:
            logger.error(f"Get state failed: {e}")
            return None
    
    async def get_all_devices(self) -> List[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT value, updated_at FROM memory.entries
                    WHERE scope = 'device' AND key = 'current'
                    ORDER BY updated_at DESC
                ''')
                return [dict(row["value"]) for row in rows]
        except Exception as e:
            logger.error(f"Get devices failed: {e}")
            return []
    
    async def get_devices_by_status(self, status: str) -> List[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT value FROM memory.entries
                    WHERE scope = 'device' 
                      AND key = 'current'
                      AND value->>'status' = $1
                ''', status)
                return [dict(row["value"]) for row in rows]
        except Exception as e:
            logger.error(f"Get by status failed: {e}")
            return []
    
    async def get_stale_devices(self, minutes: int = 30) -> List[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT value, updated_at FROM memory.entries
                    WHERE scope = 'device' 
                      AND key = 'current'
                      AND updated_at < NOW() - ($1 || ' minutes')::INTERVAL
                ''', str(minutes))
                return [dict(row["value"]) for row in rows]
        except Exception as e:
            logger.error(f"Get stale failed: {e}")
            return []
    
    async def run_sync_cycle(self, device_fetcher) -> int:
        try:
            devices = await device_fetcher()
            synced = 0
            
            for device in devices:
                success = await self.sync_device(
                    device_id=str(device.get("device_id")),
                    device_type=device.get("device_type", "unknown"),
                    status=device.get("status", "unknown"),
                    firmware_version=device.get("firmware_version"),
                    config=device.get("config"),
                    calibration_data=device.get("calibration_data"),
                    telemetry=device.get("last_telemetry"),
                    location=device.get("location")
                )
                if success:
                    synced += 1
            
            logger.info(f"Synced {synced}/{len(devices)} devices")
            return synced
        except Exception as e:
            logger.error(f"Sync cycle failed: {e}")
            return 0


_device_sync: Optional[DeviceMemorySync] = None


def get_device_sync() -> DeviceMemorySync:
    global _device_sync
    if _device_sync is None:
        _device_sync = DeviceMemorySync()
    return _device_sync
