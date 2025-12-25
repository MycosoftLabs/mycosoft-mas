"""
Defense Integration Client

Comprehensive client for defense and government platform integrations:
- Palantir Foundry: Enterprise data integration and analytics
- Anduril Lattice: Autonomous defense systems
- Platform One: DoD DevSecOps platform
- Tactical Data Links: Military communication systems

SECURITY NOTICE: This module handles classified and sensitive data.
Access requires appropriate clearance levels and CAC authentication.

Environment Variables:
    PALANTIR_API_URL: Palantir Foundry API endpoint
    PALANTIR_API_TOKEN: Palantir authentication token
    ANDURIL_API_URL: Anduril Lattice API endpoint
    ANDURIL_API_KEY: Anduril API key
    PLATFORM_ONE_API_URL: Platform One API endpoint
    PLATFORM_ONE_TOKEN: Platform One authentication token
    TACTICAL_API_URL: Tactical Data Link gateway
    TACTICAL_API_KEY: Tactical authentication key
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Classification levels for defense data."""
    UNCLASSIFIED = "UNCLASSIFIED"
    FOUO = "UNCLASSIFIED//FOUO"
    CONFIDENTIAL = "CONFIDENTIAL"
    SECRET = "SECRET"
    TOP_SECRET = "TOP SECRET"
    TOP_SECRET_SCI = "TOP SECRET//SCI"


class PlatformStatus(Enum):
    """Platform connection statuses."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RESTRICTED = "restricted"
    AUTHENTICATING = "authenticating"


class PalantirClient:
    """
    Palantir Foundry Integration Client.
    
    Provides access to Palantir's enterprise data platform:
    - Ontology: Data modeling and object definitions
    - Data Fusion: Multi-source data integration
    - Object Explorer: Visual data exploration
    - Code Workbooks: Python/SQL analytics
    - Quiver: Geospatial analysis
    - Contour: Analytical dashboards
    - Vertex: AI/ML modeling
    - Pipeline Builder: ETL workflow automation
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_url = self.config.get("api_url") or os.getenv("PALANTIR_API_URL", "https://foundry.palantir.com/api")
        self.api_token = self.config.get("api_token") or os.getenv("PALANTIR_API_TOKEN", "")
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None
        self.security_level = SecurityLevel.TOP_SECRET_SCI
        logger.info("Palantir Foundry client initialized")
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=self.timeout
            )
        return self._client
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Palantir Foundry connectivity."""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            return {
                "status": "connected" if response.status_code == 200 else "error",
                "platform": "Palantir Foundry",
                "security_level": self.security_level.value,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Palantir health check failed: {e}")
            return {"status": "disconnected", "error": str(e)}
    
    async def query_ontology(self, object_type: str, filters: Optional[Dict] = None, limit: int = 100) -> Dict[str, Any]:
        """
        Query the Palantir Ontology for objects.
        
        Args:
            object_type: Type of object to query (Person, Organization, Event, etc.)
            filters: Optional filter criteria
            limit: Maximum results to return
            
        Returns:
            Query results with object data
        """
        try:
            client = await self._get_client()
            payload = {
                "objectType": object_type,
                "filters": filters or {},
                "limit": limit
            }
            response = await client.post("/ontology/query", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Ontology query failed: {e}")
            return {"error": str(e), "objects": []}
    
    async def list_datasets(self, folder_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available datasets in Foundry."""
        try:
            client = await self._get_client()
            params = {}
            if folder_path:
                params["folderPath"] = folder_path
            response = await client.get("/datasets", params=params)
            response.raise_for_status()
            return response.json().get("datasets", [])
        except Exception as e:
            logger.error(f"Dataset listing failed: {e}")
            return []
    
    async def run_pipeline(self, pipeline_id: str, parameters: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a data pipeline."""
        try:
            client = await self._get_client()
            payload = {"parameters": parameters or {}}
            response = await client.post(f"/pipelines/{pipeline_id}/run", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            return {"error": str(e)}
    
    async def get_object_graph(self, object_id: str, depth: int = 2) -> Dict[str, Any]:
        """Get object relationship graph."""
        try:
            client = await self._get_client()
            response = await client.get(f"/ontology/objects/{object_id}/graph", params={"depth": depth})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Object graph fetch failed: {e}")
            return {"error": str(e)}
    
    async def create_code_workbook(self, name: str, language: str = "python") -> Dict[str, Any]:
        """Create a new Code Workbook for analysis."""
        try:
            client = await self._get_client()
            payload = {"name": name, "language": language}
            response = await client.post("/workbooks/create", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Workbook creation failed: {e}")
            return {"error": str(e)}
    
    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


class AndurilClient:
    """
    Anduril Lattice Integration Client.
    
    Provides access to Anduril's autonomous defense platform:
    - Sentry Towers: Ground-based sensor systems
    - Ghost UAS: Autonomous unmanned aerial systems
    - Anvil: Counter-UAS interceptor
    - Menace: Autonomous maritime vessel
    - Dive-LD: Autonomous underwater vehicle
    - Roadrunner: Reusable interceptor
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_url = self.config.get("api_url") or os.getenv("ANDURIL_API_URL", "https://lattice.anduril.com/api")
        self.api_key = self.config.get("api_key") or os.getenv("ANDURIL_API_KEY", "")
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None
        self.security_level = SecurityLevel.SECRET
        logger.info("Anduril Lattice client initialized")
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=self.timeout
            )
        return self._client
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Anduril Lattice connectivity."""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            return {
                "status": "connected" if response.status_code == 200 else "error",
                "platform": "Anduril Lattice",
                "security_level": self.security_level.value,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Anduril health check failed: {e}")
            return {"status": "disconnected", "error": str(e)}
    
    async def list_assets(self, asset_type: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List Lattice-connected assets.
        
        Args:
            asset_type: Filter by type (sentry, ghost, anvil, menace, dive)
            status: Filter by status (online, offline, mission, charging)
            
        Returns:
            List of asset objects with status and location
        """
        try:
            client = await self._get_client()
            params = {}
            if asset_type:
                params["type"] = asset_type
            if status:
                params["status"] = status
            response = await client.get("/assets", params=params)
            response.raise_for_status()
            return response.json().get("assets", [])
        except Exception as e:
            logger.error(f"Asset listing failed: {e}")
            return []
    
    async def get_asset(self, asset_id: str) -> Dict[str, Any]:
        """Get detailed asset information."""
        try:
            client = await self._get_client()
            response = await client.get(f"/assets/{asset_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Asset fetch failed: {e}")
            return {"error": str(e)}
    
    async def get_detections(self, time_range_minutes: int = 60, confidence_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Get recent detections from Lattice sensors.
        
        Args:
            time_range_minutes: How far back to look for detections
            confidence_threshold: Minimum confidence score (0-1)
            
        Returns:
            List of detection events with classification and location
        """
        try:
            client = await self._get_client()
            params = {
                "timeRange": time_range_minutes,
                "confidenceThreshold": confidence_threshold
            }
            response = await client.get("/detections", params=params)
            response.raise_for_status()
            return response.json().get("detections", [])
        except Exception as e:
            logger.error(f"Detection fetch failed: {e}")
            return []
    
    async def track_target(self, detection_id: str, priority: str = "normal") -> Dict[str, Any]:
        """Initiate target tracking for a detection."""
        try:
            client = await self._get_client()
            payload = {"detectionId": detection_id, "priority": priority}
            response = await client.post("/tracking/initiate", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Tracking initiation failed: {e}")
            return {"error": str(e)}
    
    async def deploy_asset(self, asset_id: str, mission_type: str, waypoints: List[Dict] = None) -> Dict[str, Any]:
        """Deploy an asset on a mission."""
        try:
            client = await self._get_client()
            payload = {
                "assetId": asset_id,
                "missionType": mission_type,
                "waypoints": waypoints or []
            }
            response = await client.post("/missions/deploy", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Asset deployment failed: {e}")
            return {"error": str(e)}
    
    async def get_threat_assessment(self, area_of_interest: Dict[str, float]) -> Dict[str, Any]:
        """Get AI-generated threat assessment for an area."""
        try:
            client = await self._get_client()
            response = await client.post("/ai/threat-assessment", json=area_of_interest)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Threat assessment failed: {e}")
            return {"error": str(e)}
    
    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


class PlatformOneClient:
    """
    Platform One Integration Client.
    
    DoD Enterprise DevSecOps Platform providing:
    - Big Bang: DevSecOps platform deployment
    - Iron Bank: Hardened container registry
    - Party Bus: Service mesh and API gateway
    - Repo One: Git repository hosting
    - SSO/SAML: CAC authentication
    - Keycloak: Identity management
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_url = self.config.get("api_url") or os.getenv("PLATFORM_ONE_API_URL", "https://login.dso.mil/api")
        self.token = self.config.get("token") or os.getenv("PLATFORM_ONE_TOKEN", "")
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None
        self.security_level = SecurityLevel.FOUO
        logger.info("Platform One client initialized")
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=self.timeout
            )
        return self._client
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Platform One connectivity."""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            return {
                "status": "connected" if response.status_code == 200 else "error",
                "platform": "Platform One",
                "security_level": self.security_level.value,
                "il_level": "IL4",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Platform One health check failed: {e}")
            return {"status": "disconnected", "error": str(e)}
    
    async def list_deployments(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """List Kubernetes deployments."""
        try:
            client = await self._get_client()
            params = {}
            if namespace:
                params["namespace"] = namespace
            response = await client.get("/deployments", params=params)
            response.raise_for_status()
            return response.json().get("deployments", [])
        except Exception as e:
            logger.error(f"Deployment listing failed: {e}")
            return []
    
    async def get_iron_bank_images(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """List approved Iron Bank container images."""
        try:
            client = await self._get_client()
            params = {}
            if search:
                params["search"] = search
            response = await client.get("/ironbank/images", params=params)
            response.raise_for_status()
            return response.json().get("images", [])
        except Exception as e:
            logger.error(f"Iron Bank image fetch failed: {e}")
            return []
    
    async def deploy_application(self, manifest: Dict[str, Any], namespace: str) -> Dict[str, Any]:
        """Deploy an application to the cluster."""
        try:
            client = await self._get_client()
            payload = {"manifest": manifest, "namespace": namespace}
            response = await client.post("/deployments", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Application deployment failed: {e}")
            return {"error": str(e)}
    
    async def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get CI/CD pipeline status."""
        try:
            client = await self._get_client()
            response = await client.get(f"/pipelines/{pipeline_id}/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Pipeline status fetch failed: {e}")
            return {"error": str(e)}
    
    async def trigger_scan(self, image: str) -> Dict[str, Any]:
        """Trigger security scan for a container image."""
        try:
            client = await self._get_client()
            payload = {"image": image}
            response = await client.post("/scans/trigger", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Security scan trigger failed: {e}")
            return {"error": str(e)}
    
    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


class TacticalDataLinkClient:
    """
    Tactical Data Link Integration Client.
    
    Military communication systems integration:
    - Link 16 (TADIL-J): NATO tactical data link
    - Link 22: Improved data link
    - SADL: Situational Awareness Data Link (USAF)
    - VMF: Variable Message Format (USMC)
    - JREAP: Joint Range Extension Application Protocol
    
    SECURITY NOTICE: Access restricted to authorized personnel only.
    Requires appropriate security clearance and CAC authentication.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_url = self.config.get("api_url") or os.getenv("TACTICAL_API_URL", "https://tdl-gateway.mil/api")
        self.api_key = self.config.get("api_key") or os.getenv("TACTICAL_API_KEY", "")
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None
        self.security_level = SecurityLevel.SECRET
        logger.info("Tactical Data Link client initialized")
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "X-TDL-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=self.timeout
            )
        return self._client
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Tactical Data Link gateway connectivity."""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            return {
                "status": "connected" if response.status_code == 200 else "error",
                "platform": "Tactical Data Link Gateway",
                "security_level": self.security_level.value,
                "networks": ["Link 16", "Link 22", "SADL", "VMF"],
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"TDL health check failed: {e}")
            return {"status": "restricted", "error": "CAC authentication required"}
    
    async def get_network_status(self) -> List[Dict[str, Any]]:
        """Get status of all tactical data link networks."""
        try:
            client = await self._get_client()
            response = await client.get("/networks/status")
            response.raise_for_status()
            return response.json().get("networks", [])
        except Exception as e:
            logger.error(f"Network status fetch failed: {e}")
            return []
    
    async def get_tracks(self, network: str = "link16") -> List[Dict[str, Any]]:
        """Get current track data from tactical network."""
        try:
            client = await self._get_client()
            response = await client.get(f"/tracks/{network}")
            response.raise_for_status()
            return response.json().get("tracks", [])
        except Exception as e:
            logger.error(f"Track data fetch failed: {e}")
            return []
    
    async def send_message(self, network: str, message_type: str, content: Dict) -> Dict[str, Any]:
        """Send a tactical message on specified network."""
        try:
            client = await self._get_client()
            payload = {
                "network": network,
                "messageType": message_type,
                "content": content
            }
            response = await client.post("/messages/send", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Message send failed: {e}")
            return {"error": str(e)}
    
    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


class DefenseIntegrationManager:
    """
    Unified manager for all defense integrations.
    
    Provides centralized access to:
    - Palantir Foundry
    - Anduril Lattice
    - Platform One
    - Tactical Data Links
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._palantir: Optional[PalantirClient] = None
        self._anduril: Optional[AndurilClient] = None
        self._platform_one: Optional[PlatformOneClient] = None
        self._tactical: Optional[TacticalDataLinkClient] = None
        logger.info("Defense Integration Manager initialized")
    
    @property
    def palantir(self) -> PalantirClient:
        if self._palantir is None:
            self._palantir = PalantirClient(self.config.get("palantir", {}))
        return self._palantir
    
    @property
    def anduril(self) -> AndurilClient:
        if self._anduril is None:
            self._anduril = AndurilClient(self.config.get("anduril", {}))
        return self._anduril
    
    @property
    def platform_one(self) -> PlatformOneClient:
        if self._platform_one is None:
            self._platform_one = PlatformOneClient(self.config.get("platform_one", {}))
        return self._platform_one
    
    @property
    def tactical(self) -> TacticalDataLinkClient:
        if self._tactical is None:
            self._tactical = TacticalDataLinkClient(self.config.get("tactical", {}))
        return self._tactical
    
    async def check_all_health(self) -> Dict[str, Any]:
        """Check health of all defense platforms."""
        results = {}
        
        for name, client_prop in [
            ("palantir", self.palantir),
            ("anduril", self.anduril),
            ("platform_one", self.platform_one),
            ("tactical", self.tactical)
        ]:
            try:
                results[name] = await client_prop.health_check()
            except Exception as e:
                results[name] = {"status": "error", "error": str(e)}
        
        return {
            "platforms": results,
            "summary": {
                "total": 4,
                "connected": sum(1 for r in results.values() if r.get("status") == "connected"),
                "restricted": sum(1 for r in results.values() if r.get("status") == "restricted"),
                "error": sum(1 for r in results.values() if r.get("status") == "error")
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def close(self):
        """Close all client connections."""
        for client in [self._palantir, self._anduril, self._platform_one, self._tactical]:
            if client:
                await client.close()
        logger.info("Defense Integration Manager closed")
