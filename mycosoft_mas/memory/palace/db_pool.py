"""
Shared Database Pool for Memory Palace.
Created: April 7, 2026

Provides a singleton asyncpg connection pool shared by all palace modules,
fixing the 148-connection risk from individual module pools.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger("PalaceDBPool")

_shared_pool = None
_pool_lock = None


def _get_database_url() -> str:
    """Get database URL from environment."""
    url = os.getenv("MINDEX_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise ValueError(
            "MINDEX_DATABASE_URL or DATABASE_URL environment variable is required."
        )
    return url


async def get_shared_pool():
    """Get or create the shared asyncpg connection pool (singleton)."""
    global _shared_pool, _pool_lock

    if _shared_pool is not None:
        return _shared_pool

    import asyncio

    if _pool_lock is None:
        _pool_lock = asyncio.Lock()

    async with _pool_lock:
        if _shared_pool is not None:
            return _shared_pool

        try:
            import asyncpg

            url = _get_database_url()
            _shared_pool = await asyncpg.create_pool(
                url,
                min_size=2,
                max_size=20,
                command_timeout=30,
            )
            logger.info("Shared palace database pool created (max_size=20)")
            return _shared_pool
        except Exception as e:
            logger.error(f"Failed to create shared pool: {e}")
            raise


async def close_shared_pool():
    """Close the shared pool on shutdown."""
    global _shared_pool
    if _shared_pool:
        await _shared_pool.close()
        _shared_pool = None
        logger.info("Shared palace database pool closed")
