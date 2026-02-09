"""
MINDEX (Mycological Index Database) Integration Client

This module provides integration with the MINDEX database system (https://github.com/MycosoftLabs/mindex).
MINDEX is a PostgreSQL/PostGIS database system for mycological data including:
- Taxonomy (species, genera, families)
- Observations (geospatial data)
- Telemetry (device data)
- IP Assets (intellectual property tracking)
- Ledger bindings (blockchain anchors)

The client connects to MINDEX via:
1. Direct PostgreSQL connection for database queries
2. REST API for HTTP-based operations
3. PostGIS for geospatial queries

Environment Variables:
    MINDEX_DATABASE_URL: PostgreSQL connection string (default: postgresql://mindex:mindex@localhost:5432/mindex)
    MINDEX_API_URL: REST API endpoint (default: http://localhost:8000)
    MINDEX_API_KEY: API key for authenticated requests (optional)

Usage:
    from mycosoft_mas.integrations.mindex_client import MINDEXClient
    
    client = MINDEXClient()
    taxa = await client.get_taxa(limit=10)
    observations = await client.get_observations(bbox=[-180, -90, 180, 90])
"""

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import httpx
import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import json

logger = logging.getLogger(__name__)


class MINDEXClient:
    """
    Client for interacting with the MINDEX (Mycological Index Database) system.
    
    MINDEX provides:
    - Taxonomy data (species, genera, families)
    - Observation records with geospatial data (PostGIS)
    - Telemetry data from devices
    - IP asset tracking with blockchain bindings
    
    This client supports both direct database access and REST API access.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the MINDEX client.
        
        Args:
            config: Optional configuration dictionary. If not provided, reads from environment variables.
                   Expected keys:
                   - database_url: PostgreSQL connection string
                   - api_url: REST API base URL
                   - api_key: API key for authenticated requests
                   - timeout: Request timeout in seconds (default: 30)
                   - max_retries: Maximum retry attempts (default: 3)
        """
        self.config = config or {}
        
        # Database connection (PostgreSQL/PostGIS)
        self.database_url = self.config.get(
            "database_url",
            os.getenv("MINDEX_DATABASE_URL", "postgresql://mindex:mindex@localhost:5432/mindex")
        )
        
        # REST API endpoint
        self.api_url = self.config.get(
            "api_url",
            os.getenv("MINDEX_API_URL", "http://localhost:8000")
        ).rstrip('/')
        
        # API authentication
        self.api_key = self.config.get(
            "api_key",
            os.getenv("MINDEX_API_KEY", "")
        )
        
        # Connection settings
        self.timeout = self.config.get("timeout", 30)
        self.max_retries = self.config.get("max_retries", 3)
        
        # Initialize connections (lazy loading)
        self._db_engine = None
        self._db_pool = None
        self._http_client = None
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"MINDEX client initialized - API: {self.api_url}, DB: {self.database_url.split('@')[-1] if '@' in self.database_url else 'configured'}")
    
    async def _get_db_pool(self) -> asyncpg.Pool:
        """
        Get or create database connection pool.
        
        Returns:
            asyncpg.Pool: Database connection pool
            
        Note:
            Uses asyncpg for async PostgreSQL access with PostGIS support.
            Pool is created on first access and reused for subsequent queries.
        """
        if self._db_pool is None:
            # Parse connection string
            conn_str = self.database_url.replace("postgresql://", "").replace("postgres://", "")
            if "@" in conn_str:
                auth, host_part = conn_str.split("@", 1)
                user, password = auth.split(":", 1) if ":" in auth else (auth, "")
                if "/" in host_part:
                    host_port, database = host_part.rsplit("/", 1)
                    host, port = host_port.split(":") if ":" in host_port else (host_port, "5432")
                else:
                    host, port = host_part.split(":") if ":" in host_part else (host_part, "5432")
                    database = "mindex"
            else:
                # Fallback defaults
                user, password, host, port, database = "mindex", "mindex", "localhost", "5432", "mindex"
            
            self._db_pool = await asyncpg.create_pool(
                host=host,
                port=int(port),
                user=user,
                password=password,
                database=database,
                min_size=2,
                max_size=10,
                command_timeout=self.timeout
            )
            self.logger.info(f"Created database connection pool to {host}:{port}/{database}")
        
        return self._db_pool
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client for REST API access.
        
        Returns:
            httpx.AsyncClient: HTTP client with configured headers
            
        Note:
            Includes API key in headers if configured.
            Client is reused for multiple requests.
        """
        if self._http_client is None:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            
            self._http_client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=self.timeout,
                follow_redirects=True
            )
        
        return self._http_client
    
    async def get_taxa(
        self,
        limit: int = 25,
        offset: int = 0,
        scientific_name: Optional[str] = None,
        rank: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve taxonomy records from MINDEX.
        
        Args:
            limit: Maximum number of records to return (default: 25, max: 100)
            offset: Number of records to skip for pagination (default: 0)
            scientific_name: Filter by scientific name (partial match)
            rank: Filter by taxonomic rank (e.g., 'species', 'genus', 'family')
        
        Returns:
            List of taxon dictionaries with fields:
            - id: Taxon ID
            - scientific_name: Scientific name
            - canonical_name: Canonical form of name
            - rank: Taxonomic rank
            - parent_id: Parent taxon ID
            - external_ids: Dictionary of external database IDs (iNaturalist, MycoBank, etc.)
        
        Example:
            taxa = await client.get_taxa(limit=10, scientific_name="Agaricus")
            for taxon in taxa:
                print(f"{taxon['scientific_name']} ({taxon['rank']})")
        """
        try:
            client = await self._get_http_client()
            params = {
                "limit": min(limit, 100),  # Enforce max page size
                "offset": offset
            }
            if scientific_name:
                params["scientific_name"] = scientific_name
            if rank:
                params["rank"] = rank
            
            response = await client.get("/taxa", params=params)
            response.raise_for_status()
            data = response.json()
            
            self.logger.debug(f"Retrieved {len(data.get('items', []))} taxa records")
            return data.get("items", [])
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error fetching taxa: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in get_taxa: {e}")
            raise
    
    async def get_observations(
        self,
        bbox: Optional[List[float]] = None,
        taxon_id: Optional[int] = None,
        limit: int = 25,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve observation records with geospatial filtering.
        
        Args:
            bbox: Bounding box as [min_lon, min_lat, max_lon, max_lat] for PostGIS filtering
            taxon_id: Filter by taxon ID
            limit: Maximum number of records (default: 25)
            offset: Pagination offset (default: 0)
        
        Returns:
            List of observation dictionaries with fields:
            - id: Observation ID
            - taxon_id: Associated taxon ID
            - observed_at: Observation timestamp
            - location: GeoJSON geometry
            - metadata: Additional observation data
        
        Example:
            # Get observations in a bounding box
            obs = await client.get_observations(bbox=[-122.5, 37.7, -122.3, 37.8])
            
            # Get observations for a specific species
            obs = await client.get_observations(taxon_id=12345)
        """
        try:
            client = await self._get_http_client()
            params = {
                "limit": min(limit, 100),
                "offset": offset
            }
            if bbox:
                params["bbox"] = ",".join(map(str, bbox))
            if taxon_id:
                params["taxon_id"] = taxon_id
            
            response = await client.get("/observations", params=params)
            response.raise_for_status()
            data = response.json()
            
            self.logger.debug(f"Retrieved {len(data.get('items', []))} observation records")
            return data.get("items", [])
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error fetching observations: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in get_observations: {e}")
            raise
    
    async def get_telemetry_latest(
        self,
        device_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get latest telemetry samples per device/stream.
        
        Args:
            device_id: Optional device ID filter
            limit: Maximum number of samples (default: 100)
        
        Returns:
            List of telemetry records with device and sensor data
        
        Note:
            Telemetry data comes from ESP32 devices and other IoT sensors.
            Used for real-time environmental monitoring.
        """
        try:
            client = await self._get_http_client()
            params = {"limit": limit}
            if device_id:
                params["device_id"] = device_id
            
            response = await client.get("/telemetry/devices/latest", params=params)
            response.raise_for_status()
            data = response.json()
            
            return data.get("items", [])
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error fetching telemetry: {e}")
            raise
    
    async def get_ip_assets(
        self,
        limit: int = 25,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get IP asset catalog with ledger bindings.
        
        Args:
            limit: Maximum number of records (default: 25)
            offset: Pagination offset (default: 0)
        
        Returns:
            List of IP asset records with blockchain bindings:
            - id: Asset ID
            - name: Asset name
            - description: Asset description
            - hypergraph_anchors: Hypergraph blockchain anchors
            - bitcoin_ordinals: Bitcoin Ordinal inscriptions
            - solana_bindings: Solana token/mint bindings
        
        Note:
            IP assets represent intellectual property tracked on blockchain.
            Used for tokenization and provenance tracking.
        """
        try:
            client = await self._get_http_client()
            params = {
                "limit": min(limit, 100),
                "offset": offset
            }
            
            response = await client.get("/ip/assets", params=params)
            response.raise_for_status()
            data = response.json()
            
            return data.get("items", [])
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error fetching IP assets: {e}")
            raise
    
    async def anchor_ip_asset_hypergraph(
        self,
        asset_id: int,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Hash payload and persist Hypergraph anchor for an IP asset.
        
        Args:
            asset_id: IP asset ID
            payload: Data to hash and anchor
        
        Returns:
            Anchor record with hash and transaction details
        
        Note:
            Creates SHA-256 hash of payload and stores in ledger.hypergraph_anchor table.
            Used for immutable IP asset tracking on Hypergraph blockchain.
        """
        try:
            client = await self._get_http_client()
            response = await client.post(
                f"/ip/assets/{asset_id}/anchor/hypergraph",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error anchoring IP asset to Hypergraph: {e}")
            raise
    
    async def bind_ip_asset_solana(
        self,
        asset_id: int,
        mint_address: str,
        token_account: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Link IP asset to Solana mint/token accounts.
        
        Args:
            asset_id: IP asset ID
            mint_address: Solana mint address
            token_account: Optional token account address
        
        Returns:
            Binding record with Solana addresses
        
        Note:
            Creates binding in ledger.solana_binding table.
            Used for tokenizing IP assets on Solana blockchain.
        """
        try:
            client = await self._get_http_client()
            payload = {
                "mint_address": mint_address
            }
            if token_account:
                payload["token_account"] = token_account
            
            response = await client.post(
                f"/ip/assets/{asset_id}/bind/solana",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error binding IP asset to Solana: {e}")
            raise
    
    async def ingest_mycobrain_telemetry(
        self,
        device_id: str,
        telemetry_data: Dict[str, Any],
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest MycoBrain telemetry data into MINDEX.
        
        Args:
            device_id: MycoBrain device identifier
            telemetry_data: Telemetry data dictionary with fields:
                - device_id: Device identifier
                - device_type: "mycobrain"
                - timestamp: ISO timestamp
                - sequence: MDP sequence number (for idempotency)
                - analog_inputs: Dict with ai1_voltage, ai2_voltage, etc.
                - environmental: Dict with temperature, humidity, pressure, gas_resistance
                - mosfet_states: Dict with mosfet_0, mosfet_1, etc.
                - i2c_sensors: Dict with detected_addresses
                - power: Power status dict
                - device_metadata: Firmware version, uptime, etc.
                - location: Optional location dict with lat/lon
            api_key: Optional API key for device authentication
        
        Returns:
            Dict with success status and record ID
        
        Note:
            Uses sequence number for idempotent inserts.
            Maps MycoBrain telemetry fields to MINDEX telemetry schema.
        """
        try:
            client = await self._get_http_client()
            
            # Add API key to headers if provided
            headers = {}
            if api_key:
                headers["X-Device-API-Key"] = api_key
            
            response = await client.post(
                "/telemetry/mycobrain/ingest",
                json=telemetry_data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error ingesting MycoBrain telemetry: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in ingest_mycobrain_telemetry: {e}")
            raise
    
    async def register_mycobrain_device(
        self,
        device_id: str,
        serial_number: str,
        firmware_version: str,
        location: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Register a MycoBrain device in MINDEX.
        
        Args:
            device_id: Device identifier
            serial_number: Device serial number
            firmware_version: Firmware version string
            location: Optional location dict with lat/lon
            metadata: Optional additional metadata
        
        Returns:
            Device registration record
        """
        try:
            client = await self._get_http_client()
            
            payload = {
                "device_id": device_id,
                "device_type": "mycobrain",
                "serial_number": serial_number,
                "firmware_version": firmware_version,
            }
            
            if location:
                payload["location"] = location
            if metadata:
                payload["metadata"] = metadata
            
            response = await client.post(
                "/devices/mycobrain/register",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error registering MycoBrain device: {e}")
            raise
    
    async def get_mycobrain_devices(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get list of registered MycoBrain devices.
        
        Args:
            limit: Maximum number of devices (default: 100)
            offset: Pagination offset (default: 0)
        
        Returns:
            List of device records
        """
        try:
            client = await self._get_http_client()
            params = {
                "limit": min(limit, 100),
                "offset": offset,
                "device_type": "mycobrain"
            }
            
            response = await client.get("/devices", params=params)
            response.raise_for_status()
            data = response.json()
            
            return data.get("items", [])
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error fetching MycoBrain devices: {e}")
            raise
    
    async def get_mycobrain_telemetry(
        self,
        device_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get MycoBrain telemetry data.
        
        Args:
            device_id: Optional device ID filter
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Maximum number of records (default: 100)
        
        Returns:
            List of telemetry records
        """
        try:
            client = await self._get_http_client()
            params = {"limit": limit, "device_type": "mycobrain"}
            
            if device_id:
                params["device_id"] = device_id
            if start_time:
                params["start_time"] = start_time.isoformat()
            if end_time:
                params["end_time"] = end_time.isoformat()
            
            response = await client.get("/telemetry/mycobrain", params=params)
            response.raise_for_status()
            data = response.json()
            
            return data.get("items", [])
        
        except httpx.HTTPError as e:
            self.logger.error(f"Error fetching MycoBrain telemetry: {e}")
            raise
    
    async def query_database(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute raw SQL query against MINDEX database.
        
        Args:
            query: SQL query string (use parameterized queries for safety)
            params: Query parameters for parameterized queries
        
        Returns:
            List of result rows as dictionaries
        
        Warning:
            Use with caution. Prefer API methods when possible.
            Always use parameterized queries to prevent SQL injection.
        
        Example:
            results = await client.query_database(
                "SELECT * FROM core.taxon WHERE rank = $1 LIMIT 10",
                {"rank": "species"}
            )
        """
        try:
            pool = await self._get_db_pool()
            async with pool.acquire() as conn:
                if params:
                    rows = await conn.fetch(query, *params.values())
                else:
                    rows = await conn.fetch(query)
                
                # Convert to list of dicts
                return [dict(row) for row in rows]
        
        except Exception as e:
            self.logger.error(f"Error executing database query: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check MINDEX system health.
        
        Returns:
            Health status dictionary with:
            - api_status: API availability ("ok" or "error")
            - database_status: Database connectivity ("ok" or "error")
            - timestamp: Check timestamp
        
        Note:
            Performs both API and database connectivity checks.
            Used for monitoring and health endpoints.
        """
        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "api_status": "unknown",
            "database_status": "unknown"
        }
        
        # Check API
        try:
            client = await self._get_http_client()
            response = await client.get("/health", timeout=5)
            health["api_status"] = "ok" if response.status_code == 200 else "error"
        except Exception as e:
            health["api_status"] = "error"
            health["api_error"] = str(e)
        
        # Check database
        try:
            pool = await self._get_db_pool()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health["database_status"] = "ok"
        except Exception as e:
            health["database_status"] = "error"
            health["database_error"] = str(e)
        
        return health
    
    async def close(self):
        """
        Close all connections and clean up resources.
        
        Note:
            Should be called when client is no longer needed.
            Closes database pool and HTTP client.
        """
        if self._db_pool:
            await self._db_pool.close()
            self._db_pool = None
        
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        
        self.logger.info("MINDEX client connections closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - closes connections."""
        await self.close()

