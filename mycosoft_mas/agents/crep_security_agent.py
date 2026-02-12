"""
CREP Security Agent

Monitors CREP (Common Relevant Environmental Picture) data for security threats
and creates SOC incidents automatically.

Threat Monitoring:
- Flight deviations and restricted airspace violations
- Maritime vessel anomalies and AIS spoofing
- Satellite position anomalies
- Severe weather affecting infrastructure
- Critical emissions levels

Author: Morgan Rockwell / MYCA
Created: February 12, 2026
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import httpx

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.security.security_integration import (
    SOCIntegration,
    SeverityLevel,
    ThreatCategory,
)

logger = logging.getLogger(__name__)


class CREPSecurityAgent(BaseAgent):
    """
    Security agent that monitors CREP data streams for threats.
    
    Integrates with:
    - CREP API (192.168.0.187:3000/api/crep)
    - SOC Integration for incident creation
    - Website API for alerts
    
    Capabilities:
    - crep_flight_monitoring: Monitor flight deviations
    - crep_maritime_monitoring: Monitor vessel anomalies
    - crep_weather_monitoring: Monitor severe weather
    - crep_satellite_monitoring: Monitor satellite anomalies
    - crep_threat_detection: Detect cross-domain threats
    """
    
    # CREP API endpoints
    CREP_API_BASE = "http://192.168.0.187:3000/api/crep"
    WEBSITE_API = "http://192.168.0.187:3000/api/security/incidents"
    
    # Threat thresholds
    FLIGHT_ALTITUDE_DEVIATION_FT = 1000  # Alert if >1000ft from expected
    VESSEL_SPEED_ANOMALY_KN = 30  # Alert if vessel suddenly >30kn
    SEVERE_WEATHER_ALERT_LEVEL = 3  # 1-5 scale
    
    def __init__(
        self,
        agent_id: str = "crep-security-agent",
        name: str = "CREPSecurityAgent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            agent_id=agent_id,
            name=name,
            config=config or {}
        )
        
        self.capabilities = [
            "crep_flight_monitoring",
            "crep_maritime_monitoring",
            "crep_weather_monitoring",
            "crep_satellite_monitoring",
            "crep_threat_detection",
        ]
        
        self._client: Optional[httpx.AsyncClient] = None
        self._soc: Optional[SOCIntegration] = None
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_interval = 60  # seconds
        self._last_check: Dict[str, datetime] = {}
        self._active_threats: Dict[str, Dict[str, Any]] = {}
        
        # Statistics
        self.metrics = {
            "total_checks": 0,
            "threats_detected": 0,
            "incidents_created": 0,
            "flights_monitored": 0,
            "vessels_monitored": 0,
        }
    
    async def initialize(self) -> bool:
        """Initialize the CREP security agent."""
        try:
            self._client = httpx.AsyncClient(timeout=30.0)
            self._soc = SOCIntegration()
            
            # Test CREP API connectivity
            try:
                response = await self._client.get(f"{self.CREP_API_BASE}/health")
                if response.status_code != 200:
                    logger.warning("CREP API not responding, will retry during monitoring")
            except Exception as e:
                logger.warning(f"CREP API connectivity test failed: {e}")
            
            logger.info(f"CREPSecurityAgent initialized: {self.agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize CREPSecurityAgent: {e}")
            return False
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task assigned to this agent."""
        task_type = task.get("type", "")
        
        if task_type == "start_monitoring":
            return await self._start_monitoring()
        elif task_type == "stop_monitoring":
            return await self._stop_monitoring()
        elif task_type == "check_flights":
            return await self._check_flight_threats()
        elif task_type == "check_maritime":
            return await self._check_maritime_threats()
        elif task_type == "check_weather":
            return await self._check_weather_threats()
        elif task_type == "check_satellites":
            return await self._check_satellite_threats()
        elif task_type == "full_scan":
            return await self._full_threat_scan()
        elif task_type == "get_status":
            return await self._get_status()
        else:
            return {
                "status": "error",
                "error": f"Unknown task type: {task_type}",
                "available_tasks": [
                    "start_monitoring",
                    "stop_monitoring",
                    "check_flights",
                    "check_maritime",
                    "check_weather",
                    "check_satellites",
                    "full_scan",
                    "get_status",
                ],
            }
    
    async def _start_monitoring(self) -> Dict[str, Any]:
        """Start continuous CREP monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            return {"status": "already_running", "message": "Monitoring already active"}
        
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("CREP security monitoring started")
        
        return {"status": "started", "interval_seconds": self._monitoring_interval}
    
    async def _stop_monitoring(self) -> Dict[str, Any]:
        """Stop continuous CREP monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        
        logger.info("CREP security monitoring stopped")
        return {"status": "stopped"}
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while True:
            try:
                await self._full_threat_scan()
                await asyncio.sleep(self._monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in CREP monitoring loop: {e}")
                await asyncio.sleep(10)  # Short delay before retry
    
    async def _full_threat_scan(self) -> Dict[str, Any]:
        """Run a full threat scan across all CREP domains."""
        self.metrics["total_checks"] += 1
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "threats": [],
            "domains_checked": [],
        }
        
        # Check all domains
        for check_fn, domain in [
            (self._check_flight_threats, "aviation"),
            (self._check_maritime_threats, "maritime"),
            (self._check_weather_threats, "weather"),
            (self._check_satellite_threats, "satellite"),
        ]:
            try:
                domain_result = await check_fn()
                results["domains_checked"].append(domain)
                if domain_result.get("threats"):
                    results["threats"].extend(domain_result["threats"])
            except Exception as e:
                logger.error(f"Error checking {domain}: {e}")
        
        # Update metrics
        self.metrics["threats_detected"] += len(results["threats"])
        
        return results
    
    async def _check_flight_threats(self) -> Dict[str, Any]:
        """Check for aviation-related threats."""
        threats = []
        
        try:
            response = await self._client.get(f"{self.CREP_API_BASE}/flights")
            if response.status_code != 200:
                return {"domain": "aviation", "threats": [], "error": "API unavailable"}
            
            data = response.json()
            flights = data.get("aircraft", data.get("flights", []))
            self.metrics["flights_monitored"] = len(flights)
            
            for flight in flights:
                # Check for altitude deviations
                if flight.get("baro_altitude") and flight.get("expected_altitude"):
                    deviation = abs(flight["baro_altitude"] - flight["expected_altitude"])
                    if deviation > self.FLIGHT_ALTITUDE_DEVIATION_FT:
                        threat = await self._create_threat(
                            title=f"Flight Altitude Deviation: {flight.get('callsign', 'Unknown')}",
                            description=f"Aircraft {flight.get('callsign')} deviated {deviation}ft from expected altitude",
                            severity=SeverityLevel.MEDIUM,
                            category=ThreatCategory.ANOMALY,
                            metadata={"flight": flight, "deviation_ft": deviation},
                        )
                        threats.append(threat)
                
                # Check for restricted airspace entry
                if flight.get("in_restricted_airspace"):
                    threat = await self._create_threat(
                        title=f"Restricted Airspace Violation: {flight.get('callsign', 'Unknown')}",
                        description=f"Aircraft entered restricted airspace at {flight.get('latitude')}, {flight.get('longitude')}",
                        severity=SeverityLevel.HIGH,
                        category=ThreatCategory.INTRUSION,
                        metadata={"flight": flight},
                    )
                    threats.append(threat)
                
                # Check for transponder issues
                if flight.get("squawk") in ["7500", "7600", "7700"]:
                    squawk_meanings = {
                        "7500": "Hijacking",
                        "7600": "Radio Failure",
                        "7700": "Emergency",
                    }
                    threat = await self._create_threat(
                        title=f"Emergency Squawk: {flight.get('callsign', 'Unknown')}",
                        description=f"Aircraft squawking {flight.get('squawk')} ({squawk_meanings.get(flight.get('squawk'), 'Unknown')})",
                        severity=SeverityLevel.CRITICAL if flight.get("squawk") == "7500" else SeverityLevel.HIGH,
                        category=ThreatCategory.OTHER,
                        metadata={"flight": flight, "squawk_meaning": squawk_meanings.get(flight.get("squawk"))},
                    )
                    threats.append(threat)
            
            self._last_check["aviation"] = datetime.utcnow()
            return {"domain": "aviation", "threats": threats, "flights_checked": len(flights)}
            
        except Exception as e:
            logger.error(f"Error checking flight threats: {e}")
            return {"domain": "aviation", "threats": [], "error": str(e)}
    
    async def _check_maritime_threats(self) -> Dict[str, Any]:
        """Check for maritime-related threats."""
        threats = []
        
        try:
            response = await self._client.get(f"{self.CREP_API_BASE}/vessels")
            if response.status_code != 200:
                return {"domain": "maritime", "threats": [], "error": "API unavailable"}
            
            data = response.json()
            vessels = data.get("vessels", [])
            self.metrics["vessels_monitored"] = len(vessels)
            
            for vessel in vessels:
                # Check for AIS anomalies (possible spoofing)
                if vessel.get("ais_anomaly"):
                    threat = await self._create_threat(
                        title=f"AIS Anomaly: {vessel.get('name', 'Unknown')}",
                        description=f"Vessel {vessel.get('name')} showing AIS data inconsistencies",
                        severity=SeverityLevel.HIGH,
                        category=ThreatCategory.ANOMALY,
                        metadata={"vessel": vessel},
                    )
                    threats.append(threat)
                
                # Check for speed anomalies
                speed = vessel.get("speed", 0)
                if speed > self.VESSEL_SPEED_ANOMALY_KN:
                    threat = await self._create_threat(
                        title=f"Vessel Speed Anomaly: {vessel.get('name', 'Unknown')}",
                        description=f"Vessel traveling at {speed} knots (threshold: {self.VESSEL_SPEED_ANOMALY_KN}kn)",
                        severity=SeverityLevel.MEDIUM,
                        category=ThreatCategory.ANOMALY,
                        metadata={"vessel": vessel, "speed_kn": speed},
                    )
                    threats.append(threat)
                
                # Check for distress signals
                if vessel.get("distress_signal"):
                    threat = await self._create_threat(
                        title=f"Maritime Distress: {vessel.get('name', 'Unknown')}",
                        description=f"Vessel transmitting distress signal at {vessel.get('latitude')}, {vessel.get('longitude')}",
                        severity=SeverityLevel.CRITICAL,
                        category=ThreatCategory.OTHER,
                        metadata={"vessel": vessel},
                    )
                    threats.append(threat)
            
            self._last_check["maritime"] = datetime.utcnow()
            return {"domain": "maritime", "threats": threats, "vessels_checked": len(vessels)}
            
        except Exception as e:
            logger.error(f"Error checking maritime threats: {e}")
            return {"domain": "maritime", "threats": [], "error": str(e)}
    
    async def _check_weather_threats(self) -> Dict[str, Any]:
        """Check for severe weather threats affecting infrastructure."""
        threats = []
        
        try:
            response = await self._client.get(f"{self.CREP_API_BASE}/weather")
            if response.status_code != 200:
                return {"domain": "weather", "threats": [], "error": "API unavailable"}
            
            data = response.json()
            weather_data = data.get("conditions", data.get("weather", []))
            
            if isinstance(weather_data, dict):
                weather_data = [weather_data]
            
            for condition in weather_data:
                severity_level = condition.get("severity_level", 0)
                
                if severity_level >= self.SEVERE_WEATHER_ALERT_LEVEL:
                    threat = await self._create_threat(
                        title=f"Severe Weather: {condition.get('type', 'Unknown')}",
                        description=f"Severe weather condition ({condition.get('description', 'N/A')}) affecting region",
                        severity=SeverityLevel.HIGH if severity_level >= 4 else SeverityLevel.MEDIUM,
                        category=ThreatCategory.OTHER,
                        metadata={"weather": condition, "severity_level": severity_level},
                    )
                    threats.append(threat)
            
            self._last_check["weather"] = datetime.utcnow()
            return {"domain": "weather", "threats": threats}
            
        except Exception as e:
            logger.error(f"Error checking weather threats: {e}")
            return {"domain": "weather", "threats": [], "error": str(e)}
    
    async def _check_satellite_threats(self) -> Dict[str, Any]:
        """Check for satellite-related threats."""
        threats = []
        
        try:
            response = await self._client.get(f"{self.CREP_API_BASE}/satellites")
            if response.status_code != 200:
                return {"domain": "satellite", "threats": [], "error": "API unavailable"}
            
            data = response.json()
            satellites = data.get("satellites", [])
            
            for sat in satellites:
                # Check for position anomalies
                if sat.get("position_anomaly"):
                    threat = await self._create_threat(
                        title=f"Satellite Position Anomaly: {sat.get('name', 'Unknown')}",
                        description=f"Satellite {sat.get('name')} showing unexpected position deviation",
                        severity=SeverityLevel.HIGH,
                        category=ThreatCategory.ANOMALY,
                        metadata={"satellite": sat},
                    )
                    threats.append(threat)
                
                # Check for communication issues
                if sat.get("communication_loss"):
                    threat = await self._create_threat(
                        title=f"Satellite Communication Loss: {sat.get('name', 'Unknown')}",
                        description=f"Lost communication with satellite {sat.get('name')}",
                        severity=SeverityLevel.CRITICAL,
                        category=ThreatCategory.OTHER,
                        metadata={"satellite": sat},
                    )
                    threats.append(threat)
            
            self._last_check["satellite"] = datetime.utcnow()
            return {"domain": "satellite", "threats": threats, "satellites_checked": len(satellites)}
            
        except Exception as e:
            logger.error(f"Error checking satellite threats: {e}")
            return {"domain": "satellite", "threats": [], "error": str(e)}
    
    async def _create_threat(
        self,
        title: str,
        description: str,
        severity: SeverityLevel,
        category: ThreatCategory,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a threat entry and SOC incident."""
        threat_id = f"crep_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{len(self._active_threats)}"
        
        threat = {
            "id": threat_id,
            "title": title,
            "description": description,
            "severity": severity.name,
            "category": category.value,
            "source": "crep",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        
        self._active_threats[threat_id] = threat
        
        # Create SOC incident
        if self._soc:
            try:
                incident = await self._soc.create_incident(
                    title=title,
                    description=description,
                    severity=severity,
                    category=category,
                    affected_systems=["CREP", category.value],
                )
                threat["incident_id"] = incident.incident_id
                self.metrics["incidents_created"] += 1
                logger.info(f"Created SOC incident {incident.incident_id} for CREP threat: {title}")
            except Exception as e:
                logger.error(f"Failed to create SOC incident: {e}")
        
        # Also push to website API
        try:
            await self._client.post(
                self.WEBSITE_API,
                json={
                    "title": title,
                    "description": description,
                    "severity": severity.name.lower(),
                    "tags": [category.value, "crep", "auto-generated"],
                    "source": "agent",
                    "reporter_id": self.agent_id,
                    "reporter_name": "CREPSecurityAgent",
                },
            )
            logger.debug(f"Pushed incident to website API: {title}")
        except Exception as e:
            logger.debug(f"Could not push incident to website API: {e}")
        
        return threat
    
    async def _get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "monitoring_active": bool(self._monitoring_task and not self._monitoring_task.done()),
            "monitoring_interval": self._monitoring_interval,
            "last_checks": {k: v.isoformat() for k, v in self._last_check.items()},
            "active_threats": len(self._active_threats),
            "metrics": self.metrics,
            "capabilities": self.capabilities,
        }
    
    async def shutdown(self):
        """Shutdown the agent."""
        await self._stop_monitoring()
        if self._client:
            await self._client.aclose()
        logger.info(f"CREPSecurityAgent shutdown: {self.agent_id}")
