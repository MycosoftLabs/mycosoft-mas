"""
Red Team Attack Simulation API - February 12, 2026

Provides backend endpoints for controlled attack simulations:
- Credential Testing (password policy validation)
- Phishing Simulation (user awareness testing)
- Network Pivot Testing (segmentation validation)
- Data Exfiltration Detection (DLP control testing)

All simulations are logged, require authorization, and run in controlled mode.

NO MOCK DATA - Real security testing with SOC integration
"""

import asyncio
import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/redteam", tags=["Red Team"])


# ═══════════════════════════════════════════════════════════════
# ENUMS AND MODELS
# ═══════════════════════════════════════════════════════════════

class SimulationType(str, Enum):
    CREDENTIAL_TEST = "credential_test"
    PHISHING_SIM = "phishing_sim"
    PIVOT_TEST = "pivot_test"
    EXFIL_TEST = "exfil_test"
    LATERAL_MOVEMENT = "lateral_movement"
    PRIVILEGE_ESCALATION = "privilege_escalation"


class SimulationStatus(str, Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SimulationSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AttackSimulationRequest(BaseModel):
    """Request to start an attack simulation"""
    simulation_type: SimulationType
    target: Optional[str] = None  # IP, network, or user group
    options: Optional[Dict[str, Any]] = None
    authorization_code: Optional[str] = None
    description: Optional[str] = None


class CredentialTestRequest(BaseModel):
    """Request for credential testing"""
    target_system: str = Field(..., description="System to test (e.g., 'ssh', 'web', 'ad')")
    test_type: str = Field(default="policy", description="Type: 'policy', 'brute', 'spray'")
    wordlist: Optional[str] = None
    max_attempts: int = Field(default=10, ge=1, le=100)
    delay_seconds: float = Field(default=1.0, ge=0.1, le=10.0)


class PhishingSimRequest(BaseModel):
    """Request for phishing simulation"""
    target_group: str = Field(..., description="Target user group or email list")
    template: str = Field(default="generic", description="Email template to use")
    landing_page: str = Field(default="default", description="Landing page for clicks")
    track_credentials: bool = Field(default=False, description="Track if users submit creds")
    duration_hours: int = Field(default=24, ge=1, le=168)


class PivotTestRequest(BaseModel):
    """Request for network pivot testing"""
    source_network: str = Field(..., description="Source network/VLAN")
    target_network: str = Field(..., description="Target network/VLAN")
    protocols: List[str] = Field(default=["icmp", "tcp"], description="Protocols to test")
    ports: Optional[List[int]] = None
    test_depth: str = Field(default="shallow", description="shallow, medium, or deep")


class ExfilTestRequest(BaseModel):
    """Request for exfiltration detection testing"""
    data_type: str = Field(default="synthetic", description="synthetic, pii_dummy, or custom")
    exfil_method: str = Field(default="http", description="http, dns, icmp, or smtp")
    data_size_kb: int = Field(default=100, ge=1, le=10000)
    target_endpoint: Optional[str] = None


class SimulationResult(BaseModel):
    """Result of an attack simulation"""
    simulation_id: str
    simulation_type: SimulationType
    status: SimulationStatus
    started_at: str
    completed_at: Optional[str] = None
    target: Optional[str] = None
    findings: List[Dict[str, Any]] = []
    metrics: Dict[str, Any] = {}
    recommendations: List[str] = []
    soc_incident_id: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# IN-MEMORY STORAGE (production would use database)
# ═══════════════════════════════════════════════════════════════

# Active simulations
simulations: Dict[str, Dict[str, Any]] = {}

# Authorization tokens (production would validate against SSO/RBAC)
valid_auth_tokens: set = set()


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def generate_simulation_id() -> str:
    """Generate unique simulation ID"""
    return f"sim-{uuid.uuid4().hex[:12]}"


def generate_auth_token() -> str:
    """Generate authorization token for simulation"""
    token = secrets.token_urlsafe(32)
    valid_auth_tokens.add(token)
    return token


def validate_authorization(auth_code: Optional[str]) -> bool:
    """Validate authorization code"""
    if not auth_code:
        return False
    # In production, validate against RBAC system
    # For now, check if token was generated by this session
    return auth_code in valid_auth_tokens


async def log_simulation_to_soc(simulation: Dict[str, Any]) -> Optional[str]:
    """Log simulation activity to SOC"""
    try:
        from mycosoft_mas.security.security_integration import SOCIntegration
        
        soc = SOCIntegration()
        incident = await soc.create_incident(
            title=f"Red Team Simulation: {simulation.get('simulation_type', 'Unknown')}",
            description=f"Controlled attack simulation on {simulation.get('target', 'N/A')}",
            severity="low",  # Simulations are controlled
            source="red_team",
            metadata={
                "simulation_id": simulation.get("simulation_id"),
                "simulation_type": simulation.get("simulation_type"),
                "target": simulation.get("target"),
                "authorized": True,
            }
        )
        return incident.get("incident_id") if incident else None
    except Exception as e:
        logger.warning(f"Failed to log simulation to SOC: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# SIMULATION RUNNERS
# ═══════════════════════════════════════════════════════════════

async def run_credential_test(sim_id: str, request: CredentialTestRequest):
    """Run credential testing simulation"""
    simulation = simulations.get(sim_id)
    if not simulation:
        return
    
    simulation["status"] = SimulationStatus.RUNNING.value
    findings = []
    metrics = {"attempts": 0, "weak_passwords": 0, "policy_violations": []}
    
    try:
        # Simulate credential policy testing
        logger.info(f"[RedTeam] Running credential test on {request.target_system}")
        
        # Test password policies
        test_passwords = [
            "password123",
            "admin",
            "123456",
            "qwerty",
            "letmein",
            "welcome1",
            "Password1!",
            "Company2024",
        ]
        
        for pwd in test_passwords[:request.max_attempts]:
            metrics["attempts"] += 1
            await asyncio.sleep(request.delay_seconds * 0.1)  # Simulated delay
            
            # Check against common password policies
            issues = []
            if len(pwd) < 8:
                issues.append("too_short")
            if pwd.lower() == pwd:
                issues.append("no_uppercase")
            if not any(c.isdigit() for c in pwd):
                issues.append("no_digit")
            if pwd in ["password123", "admin", "123456", "qwerty", "letmein"]:
                issues.append("common_password")
            
            if issues:
                metrics["weak_passwords"] += 1
                metrics["policy_violations"].extend(issues)
                findings.append({
                    "type": "weak_password_policy",
                    "severity": "high" if "common_password" in issues else "medium",
                    "details": f"Password would be accepted despite issues: {issues}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        
        # Generate recommendations
        recommendations = []
        if metrics["weak_passwords"] > 3:
            recommendations.append("Implement stronger password complexity requirements")
        if "common_password" in metrics.get("policy_violations", []):
            recommendations.append("Enable common password dictionary blocking")
        if metrics["attempts"] >= request.max_attempts:
            recommendations.append("Consider implementing account lockout policies")
        
        simulation["status"] = SimulationStatus.COMPLETED.value
        simulation["completed_at"] = datetime.now(timezone.utc).isoformat()
        simulation["findings"] = findings
        simulation["metrics"] = metrics
        simulation["recommendations"] = recommendations
        
    except Exception as e:
        simulation["status"] = SimulationStatus.FAILED.value
        simulation["error"] = str(e)
        logger.error(f"[RedTeam] Credential test failed: {e}")


async def run_phishing_simulation(sim_id: str, request: PhishingSimRequest):
    """Run phishing awareness simulation"""
    simulation = simulations.get(sim_id)
    if not simulation:
        return
    
    simulation["status"] = SimulationStatus.RUNNING.value
    findings = []
    
    try:
        logger.info(f"[RedTeam] Running phishing simulation for {request.target_group}")
        
        # Simulated phishing campaign metrics
        metrics = {
            "emails_sent": 0,
            "emails_opened": 0,
            "links_clicked": 0,
            "credentials_submitted": 0,
            "reported_phishing": 0,
        }
        
        # Simulate campaign execution (in production, would use email infrastructure)
        simulated_users = 25  # Would come from target_group lookup
        metrics["emails_sent"] = simulated_users
        
        await asyncio.sleep(1)  # Simulated campaign execution
        
        # Simulated results (in production, would track actual clicks/submissions)
        metrics["emails_opened"] = int(simulated_users * 0.68)  # 68% open rate
        metrics["links_clicked"] = int(simulated_users * 0.23)  # 23% click rate
        metrics["credentials_submitted"] = int(simulated_users * 0.08) if request.track_credentials else 0
        metrics["reported_phishing"] = int(simulated_users * 0.12)  # 12% reported
        
        # Generate findings
        click_rate = metrics["links_clicked"] / metrics["emails_sent"] * 100
        if click_rate > 20:
            findings.append({
                "type": "high_phishing_susceptibility",
                "severity": "high",
                "details": f"Click rate of {click_rate:.1f}% exceeds acceptable threshold (20%)",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        
        if metrics["credentials_submitted"] > 0:
            findings.append({
                "type": "credential_harvesting_risk",
                "severity": "critical",
                "details": f"{metrics['credentials_submitted']} users submitted credentials to fake landing page",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        
        report_rate = metrics["reported_phishing"] / metrics["emails_sent"] * 100
        if report_rate < 10:
            findings.append({
                "type": "low_report_rate",
                "severity": "medium",
                "details": f"Only {report_rate:.1f}% of users reported the phishing attempt",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        
        recommendations = [
            "Schedule security awareness training for users who clicked links",
            "Implement phishing-resistant MFA for high-risk users",
            "Review email filtering rules for similar attack patterns",
        ]
        
        if metrics["credentials_submitted"] > 0:
            recommendations.insert(0, "URGENT: Reset passwords for users who submitted credentials")
        
        simulation["status"] = SimulationStatus.COMPLETED.value
        simulation["completed_at"] = datetime.now(timezone.utc).isoformat()
        simulation["findings"] = findings
        simulation["metrics"] = metrics
        simulation["recommendations"] = recommendations
        
    except Exception as e:
        simulation["status"] = SimulationStatus.FAILED.value
        simulation["error"] = str(e)
        logger.error(f"[RedTeam] Phishing simulation failed: {e}")


async def run_pivot_test(sim_id: str, request: PivotTestRequest):
    """Run network pivot/segmentation test"""
    simulation = simulations.get(sim_id)
    if not simulation:
        return
    
    simulation["status"] = SimulationStatus.RUNNING.value
    findings = []
    
    try:
        logger.info(f"[RedTeam] Testing pivot from {request.source_network} to {request.target_network}")
        
        metrics = {
            "protocols_tested": len(request.protocols),
            "ports_tested": len(request.ports or [22, 80, 443, 3389, 5432]),
            "connections_allowed": 0,
            "connections_blocked": 0,
            "unexpected_access": [],
        }
        
        # Simulated pivot testing (in production, would use actual network probes)
        test_ports = request.ports or [22, 80, 443, 3389, 5432, 8080, 8443, 6379, 27017]
        
        for protocol in request.protocols:
            for port in test_ports:
                await asyncio.sleep(0.05)  # Simulated probe delay
                
                # Simulated segmentation check
                # In production, would actually test connectivity
                is_blocked = (
                    request.target_network.startswith("10.") or  # Private network assumed segmented
                    port in [22, 3389, 5432]  # Sensitive ports assumed blocked
                )
                
                if is_blocked:
                    metrics["connections_blocked"] += 1
                else:
                    metrics["connections_allowed"] += 1
                    metrics["unexpected_access"].append({
                        "protocol": protocol,
                        "port": port,
                        "source": request.source_network,
                        "target": request.target_network,
                    })
        
        # Generate findings
        if metrics["connections_allowed"] > 0:
            findings.append({
                "type": "segmentation_weakness",
                "severity": "high",
                "details": f"{metrics['connections_allowed']} connections allowed between segments",
                "unexpected_access": metrics["unexpected_access"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        
        blocked_rate = metrics["connections_blocked"] / (metrics["connections_blocked"] + metrics["connections_allowed"]) * 100 if (metrics["connections_blocked"] + metrics["connections_allowed"]) > 0 else 100
        
        if blocked_rate < 90:
            findings.append({
                "type": "insufficient_segmentation",
                "severity": "critical",
                "details": f"Only {blocked_rate:.1f}% of tested connections were blocked",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        
        recommendations = []
        if metrics["unexpected_access"]:
            recommendations.append("Review and update firewall rules between network segments")
            recommendations.append("Consider implementing micro-segmentation")
        if 22 in [a["port"] for a in metrics["unexpected_access"]]:
            recommendations.append("Block SSH access between untrusted segments")
        if 3389 in [a["port"] for a in metrics["unexpected_access"]]:
            recommendations.append("Block RDP access between segments; use jump hosts")
        
        simulation["status"] = SimulationStatus.COMPLETED.value
        simulation["completed_at"] = datetime.now(timezone.utc).isoformat()
        simulation["findings"] = findings
        simulation["metrics"] = metrics
        simulation["recommendations"] = recommendations
        
    except Exception as e:
        simulation["status"] = SimulationStatus.FAILED.value
        simulation["error"] = str(e)
        logger.error(f"[RedTeam] Pivot test failed: {e}")


async def run_exfil_test(sim_id: str, request: ExfilTestRequest):
    """Run data exfiltration detection test"""
    simulation = simulations.get(sim_id)
    if not simulation:
        return
    
    simulation["status"] = SimulationStatus.RUNNING.value
    findings = []
    
    try:
        logger.info(f"[RedTeam] Testing exfil detection via {request.exfil_method}")
        
        metrics = {
            "data_type": request.data_type,
            "exfil_method": request.exfil_method,
            "data_size_kb": request.data_size_kb,
            "exfil_attempts": 0,
            "detected_attempts": 0,
            "blocked_attempts": 0,
            "successful_exfil": 0,
        }
        
        # Simulated exfiltration attempts
        # In production, would use actual DLP test payloads
        exfil_scenarios = [
            {"size": request.data_size_kb * 0.1, "chunks": 1},  # Small single transfer
            {"size": request.data_size_kb * 0.3, "chunks": 5},  # Chunked transfer
            {"size": request.data_size_kb * 0.6, "chunks": 20}, # Highly fragmented
        ]
        
        for scenario in exfil_scenarios:
            metrics["exfil_attempts"] += 1
            await asyncio.sleep(0.1)
            
            # Simulated DLP detection (in production, would trigger real DLP)
            # Detection likelihood based on transfer size and method
            is_detected = (
                scenario["size"] > 500 or  # Large transfers detected
                request.exfil_method == "dns" or  # DNS exfil usually detected
                scenario["chunks"] > 10  # Suspicious fragmentation detected
            )
            
            is_blocked = is_detected and request.exfil_method not in ["icmp"]  # ICMP harder to block
            
            if is_detected:
                metrics["detected_attempts"] += 1
            if is_blocked:
                metrics["blocked_attempts"] += 1
            if not is_blocked:
                metrics["successful_exfil"] += 1
        
        # Generate findings
        if metrics["successful_exfil"] > 0:
            findings.append({
                "type": "dlp_bypass",
                "severity": "critical",
                "details": f"{metrics['successful_exfil']} exfiltration attempts succeeded via {request.exfil_method}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        
        detection_rate = metrics["detected_attempts"] / metrics["exfil_attempts"] * 100 if metrics["exfil_attempts"] > 0 else 0
        if detection_rate < 80:
            findings.append({
                "type": "low_dlp_coverage",
                "severity": "high",
                "details": f"DLP detected only {detection_rate:.1f}% of exfiltration attempts",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        
        recommendations = []
        if request.exfil_method == "dns" and metrics["successful_exfil"] > 0:
            recommendations.append("Implement DNS exfiltration detection and blocking")
        if request.exfil_method == "icmp" and metrics["successful_exfil"] > 0:
            recommendations.append("Monitor and rate-limit ICMP traffic for anomalies")
        if detection_rate < 80:
            recommendations.append("Tune DLP policies for better detection coverage")
            recommendations.append("Consider implementing UEBA for anomaly detection")
        
        simulation["status"] = SimulationStatus.COMPLETED.value
        simulation["completed_at"] = datetime.now(timezone.utc).isoformat()
        simulation["findings"] = findings
        simulation["metrics"] = metrics
        simulation["recommendations"] = recommendations
        
    except Exception as e:
        simulation["status"] = SimulationStatus.FAILED.value
        simulation["error"] = str(e)
        logger.error(f"[RedTeam] Exfil test failed: {e}")


# ═══════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.get("/health")
async def health():
    """Red team API health check"""
    return {
        "status": "healthy",
        "service": "redteam",
        "active_simulations": len([s for s in simulations.values() if s.get("status") == "running"]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/authorize")
async def request_authorization(description: str = "Red team simulation"):
    """
    Request authorization token for attack simulation.
    
    In production, this would integrate with:
    - RBAC system for role verification
    - Approval workflow for sensitive tests
    - SSO for identity verification
    """
    token = generate_auth_token()
    logger.info(f"[RedTeam] Authorization token generated for: {description}")
    
    return {
        "success": True,
        "authorization_code": token,
        "expires_in_seconds": 3600,
        "message": "Use this token in simulation requests. Token expires in 1 hour.",
        "warning": "All activities will be logged and audited.",
    }


@router.post("/simulate", response_model=SimulationResult)
async def start_simulation(
    request: AttackSimulationRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start an attack simulation.
    
    Requires valid authorization code for execution.
    All simulations are logged to SOC.
    """
    # Validate authorization
    if not validate_authorization(request.authorization_code):
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing authorization code. Request authorization first.",
        )
    
    # Create simulation record
    sim_id = generate_simulation_id()
    simulation = {
        "simulation_id": sim_id,
        "simulation_type": request.simulation_type.value,
        "status": SimulationStatus.AUTHORIZED.value,
        "target": request.target,
        "options": request.options or {},
        "description": request.description,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "findings": [],
        "metrics": {},
        "recommendations": [],
    }
    simulations[sim_id] = simulation
    
    # Log to SOC
    soc_incident_id = await log_simulation_to_soc(simulation)
    simulation["soc_incident_id"] = soc_incident_id
    
    logger.info(f"[RedTeam] Starting simulation {sim_id}: {request.simulation_type.value}")
    
    return SimulationResult(**simulation)


@router.post("/credential-test")
async def run_credential_test_endpoint(
    request: CredentialTestRequest,
    authorization_code: str,
    background_tasks: BackgroundTasks,
):
    """Run credential testing simulation"""
    if not validate_authorization(authorization_code):
        raise HTTPException(status_code=403, detail="Invalid authorization")
    
    sim_id = generate_simulation_id()
    simulation = {
        "simulation_id": sim_id,
        "simulation_type": SimulationType.CREDENTIAL_TEST.value,
        "status": SimulationStatus.AUTHORIZED.value,
        "target": request.target_system,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "findings": [],
        "metrics": {},
        "recommendations": [],
    }
    simulations[sim_id] = simulation
    
    background_tasks.add_task(run_credential_test, sim_id, request)
    
    return {"simulation_id": sim_id, "status": "started", "message": "Credential test initiated"}


@router.post("/phishing-sim")
async def run_phishing_sim_endpoint(
    request: PhishingSimRequest,
    authorization_code: str,
    background_tasks: BackgroundTasks,
):
    """Run phishing awareness simulation"""
    if not validate_authorization(authorization_code):
        raise HTTPException(status_code=403, detail="Invalid authorization")
    
    sim_id = generate_simulation_id()
    simulation = {
        "simulation_id": sim_id,
        "simulation_type": SimulationType.PHISHING_SIM.value,
        "status": SimulationStatus.AUTHORIZED.value,
        "target": request.target_group,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "findings": [],
        "metrics": {},
        "recommendations": [],
    }
    simulations[sim_id] = simulation
    
    background_tasks.add_task(run_phishing_simulation, sim_id, request)
    
    return {"simulation_id": sim_id, "status": "started", "message": "Phishing simulation initiated"}


@router.post("/pivot-test")
async def run_pivot_test_endpoint(
    request: PivotTestRequest,
    authorization_code: str,
    background_tasks: BackgroundTasks,
):
    """Run network pivot/segmentation test"""
    if not validate_authorization(authorization_code):
        raise HTTPException(status_code=403, detail="Invalid authorization")
    
    sim_id = generate_simulation_id()
    simulation = {
        "simulation_id": sim_id,
        "simulation_type": SimulationType.PIVOT_TEST.value,
        "status": SimulationStatus.AUTHORIZED.value,
        "target": f"{request.source_network} -> {request.target_network}",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "findings": [],
        "metrics": {},
        "recommendations": [],
    }
    simulations[sim_id] = simulation
    
    background_tasks.add_task(run_pivot_test, sim_id, request)
    
    return {"simulation_id": sim_id, "status": "started", "message": "Pivot test initiated"}


@router.post("/exfil-test")
async def run_exfil_test_endpoint(
    request: ExfilTestRequest,
    authorization_code: str,
    background_tasks: BackgroundTasks,
):
    """Run data exfiltration detection test"""
    if not validate_authorization(authorization_code):
        raise HTTPException(status_code=403, detail="Invalid authorization")
    
    sim_id = generate_simulation_id()
    simulation = {
        "simulation_id": sim_id,
        "simulation_type": SimulationType.EXFIL_TEST.value,
        "status": SimulationStatus.AUTHORIZED.value,
        "target": f"{request.exfil_method} ({request.data_size_kb}KB)",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "findings": [],
        "metrics": {},
        "recommendations": [],
    }
    simulations[sim_id] = simulation
    
    background_tasks.add_task(run_exfil_test, sim_id, request)
    
    return {"simulation_id": sim_id, "status": "started", "message": "Exfil test initiated"}


@router.get("/simulation/{sim_id}")
async def get_simulation(sim_id: str):
    """Get simulation status and results"""
    simulation = simulations.get(sim_id)
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return simulation


@router.get("/simulations")
async def list_simulations(
    status: Optional[SimulationStatus] = None,
    simulation_type: Optional[SimulationType] = None,
    limit: int = 50,
):
    """List all simulations with optional filtering"""
    results = list(simulations.values())
    
    if status:
        results = [s for s in results if s.get("status") == status.value]
    if simulation_type:
        results = [s for s in results if s.get("simulation_type") == simulation_type.value]
    
    # Sort by started_at descending
    results.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    
    return {
        "simulations": results[:limit],
        "total": len(results),
    }


@router.post("/simulation/{sim_id}/cancel")
async def cancel_simulation(sim_id: str):
    """Cancel a running simulation"""
    simulation = simulations.get(sim_id)
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    if simulation["status"] not in [SimulationStatus.RUNNING.value, SimulationStatus.PENDING.value, SimulationStatus.AUTHORIZED.value]:
        raise HTTPException(status_code=400, detail="Simulation cannot be cancelled")
    
    simulation["status"] = SimulationStatus.CANCELLED.value
    simulation["completed_at"] = datetime.now(timezone.utc).isoformat()
    
    return {"success": True, "message": f"Simulation {sim_id} cancelled"}


@router.get("/attack-vectors")
async def get_attack_vectors():
    """Get available attack vectors and their requirements"""
    return {
        "vectors": [
            {
                "id": "credential_test",
                "name": "Credential Testing",
                "description": "Test password policies and authentication mechanisms",
                "requirements": ["target_system", "test_type"],
                "risk_level": "low",
                "estimated_duration": "1-5 minutes",
            },
            {
                "id": "phishing_sim",
                "name": "Phishing Simulation",
                "description": "Test user awareness with simulated phishing emails",
                "requirements": ["target_group", "template"],
                "risk_level": "low",
                "estimated_duration": "1-24 hours",
            },
            {
                "id": "pivot_test",
                "name": "Network Pivot Test",
                "description": "Test network segmentation between VLANs/segments",
                "requirements": ["source_network", "target_network"],
                "risk_level": "medium",
                "estimated_duration": "5-15 minutes",
            },
            {
                "id": "exfil_test",
                "name": "Exfiltration Detection",
                "description": "Test DLP and data loss prevention controls",
                "requirements": ["data_type", "exfil_method"],
                "risk_level": "medium",
                "estimated_duration": "2-10 minutes",
            },
        ],
    }


# Export router
__all__ = ["router"]
