"""
Immune System Agent for Mycology BioAgent System

This agent acts as a digital immune system for the Mycosoft MAS, protecting against
security threats, vulnerabilities, and malicious code. It continuously monitors the
system for potential threats and takes appropriate defensive actions.
"""

import asyncio
import logging
import hashlib
import re
import json
import uuid
import os
import time
import random
import aiohttp
import feedparser
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable, Awaitable
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus, TaskType, TaskStatus, TaskPriority

class ThreatType(Enum):
    """Types of security threats"""
    MALWARE = auto()
    VULNERABILITY = auto()
    ZERO_DAY = auto()
    DATA_LEAK = auto()
    UNAUTHORIZED_ACCESS = auto()
    CODE_INJECTION = auto()
    NETWORK_ATTACK = auto()
    AGENT_COMPROMISE = auto()
    DATA_POISONING = auto()
    UNKNOWN = auto()

class ThreatSeverity(Enum):
    """Severity levels for threats"""
    CRITICAL = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()
    INFO = auto()

class DefenseAction(Enum):
    """Actions to take against threats"""
    BLOCK = auto()
    ISOLATE = auto()
    QUARANTINE = auto()
    PATCH = auto()
    MONITOR = auto()
    ALERT = auto()
    IGNORE = auto()

@dataclass
class Threat:
    """Information about a security threat"""
    threat_id: str
    name: str
    description: str
    threat_type: ThreatType
    severity: ThreatSeverity
    source: str
    target: str
    detection_time: datetime
    status: str = "active"
    signature: Optional[str] = None
    indicators: List[str] = field(default_factory=list)
    affected_agents: List[str] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)
    affected_networks: List[str] = field(default_factory=list)
    defense_actions: List[DefenseAction] = field(default_factory=list)
    resolution_time: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Vulnerability:
    """Information about a system vulnerability"""
    vulnerability_id: str
    name: str
    description: str
    cve_id: Optional[str] = None
    severity: ThreatSeverity = ThreatSeverity.MEDIUM
    affected_components: List[str] = field(default_factory=list)
    detection_time: datetime = field(default_factory=datetime.utcnow)
    status: str = "open"
    patch_available: bool = False
    patch_url: Optional[str] = None
    patch_notes: Optional[str] = None
    resolution_time: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class SecurityScan:
    """Information about a security scan"""
    scan_id: str
    scan_type: str
    target: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "running"
    threats_found: List[str] = field(default_factory=list)
    vulnerabilities_found: List[str] = field(default_factory=list)
    scan_results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class DefenseRule:
    """Rule for defending against threats"""
    rule_id: str
    name: str
    description: str
    threat_type: ThreatType
    severity: ThreatSeverity
    conditions: Dict[str, Any]
    actions: List[DefenseAction]
    is_active: bool = True
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

class ImmuneSystemAgent(BaseAgent):
    """Agent for protecting the Mycosoft MAS from security threats"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.threats: Dict[str, Threat] = {}
        self.vulnerabilities: Dict[str, Vulnerability] = {}
        self.security_scans: Dict[str, SecurityScan] = {}
        self.defense_rules: Dict[str, DefenseRule] = {}
        self.agent_signatures: Dict[str, str] = {}
        self.file_signatures: Dict[str, str] = {}
        self.network_signatures: Dict[str, str] = {}
        self.threat_intelligence: Dict[str, Any] = {}
        self.scan_queue: asyncio.Queue = asyncio.Queue()
        self.threat_queue: asyncio.Queue = asyncio.Queue()
        self.defense_queue: asyncio.Queue = asyncio.Queue()
        
        # Create necessary directories
        self.data_dir = Path("data/immune_system")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metrics
        self.metrics.update({
            "threats_detected": 0,
            "threats_blocked": 0,
            "vulnerabilities_found": 0,
            "vulnerabilities_patched": 0,
            "security_scans_run": 0,
            "defense_actions_taken": 0
        })
    
    async def initialize(self) -> None:
        """Initialize the agent"""
        await super().initialize()
        await self._load_data()
        await self._register_default_defense_rules()
        self.status = AgentStatus.READY
        self.logger.info("Immune System Agent initialized")
    
    async def stop(self) -> None:
        """Stop the agent"""
        self.status = AgentStatus.STOPPING
        self.logger.info("Stopping Immune System Agent")
        await self._save_data()
        await super().stop()
    
    async def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: List[str],
        dependencies: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register an agent and calculate its signature"""
        # Calculate agent signature based on its properties
        signature_data = f"{agent_id}:{agent_type}:{','.join(sorted(capabilities))}:{','.join(sorted(dependencies))}"
        signature = hashlib.sha256(signature_data.encode()).hexdigest()
        
        self.agent_signatures[agent_id] = signature
        await self._save_data()
    
    async def scan_agent(self, agent_id: str) -> str:
        """Scan an agent for security issues"""
        scan_id = f"scan_{uuid.uuid4().hex[:8]}"
        
        scan = SecurityScan(
            scan_id=scan_id,
            scan_type="agent_scan",
            target=agent_id,
            start_time=datetime.utcnow()
        )
        
        self.security_scans[scan_id] = scan
        await self._save_data()
        
        # Add to scan queue
        await self.scan_queue.put(scan_id)
        
        return scan_id
    
    async def scan_network(self, network_id: str) -> str:
        """Scan a network for security issues"""
        scan_id = f"scan_{uuid.uuid4().hex[:8]}"
        
        scan = SecurityScan(
            scan_id=scan_id,
            scan_type="network_scan",
            target=network_id,
            start_time=datetime.utcnow()
        )
        
        self.security_scans[scan_id] = scan
        await self._save_data()
        
        # Add to scan queue
        await self.scan_queue.put(scan_id)
        
        return scan_id
    
    async def scan_file(self, file_path: str) -> str:
        """Scan a file for security issues"""
        scan_id = f"scan_{uuid.uuid4().hex[:8]}"
        
        scan = SecurityScan(
            scan_id=scan_id,
            scan_type="file_scan",
            target=file_path,
            start_time=datetime.utcnow()
        )
        
        self.security_scans[scan_id] = scan
        await self._save_data()
        
        # Add to scan queue
        await self.scan_queue.put(scan_id)
        
        return scan_id
    
    async def detect_threat(
        self,
        name: str,
        description: str,
        threat_type: ThreatType,
        severity: ThreatSeverity,
        source: str,
        target: str,
        signature: Optional[str] = None,
        indicators: Optional[List[str]] = None,
        affected_agents: Optional[List[str]] = None,
        affected_files: Optional[List[str]] = None,
        affected_networks: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Detect a new security threat"""
        threat_id = f"threat_{uuid.uuid4().hex[:8]}"
        
        threat = Threat(
            threat_id=threat_id,
            name=name,
            description=description,
            threat_type=threat_type,
            severity=severity,
            source=source,
            target=target,
            detection_time=datetime.utcnow(),
            signature=signature,
            indicators=indicators or [],
            affected_agents=affected_agents or [],
            affected_files=affected_files or [],
            affected_networks=affected_networks or [],
            metadata=metadata or {}
        )
        
        self.threats[threat_id] = threat
        await self._save_data()
        
        self.metrics["threats_detected"] += 1
        
        # Add to threat queue
        await self.threat_queue.put(threat_id)
        
        return threat_id
    
    async def detect_vulnerability(
        self,
        name: str,
        description: str,
        cve_id: Optional[str] = None,
        severity: ThreatSeverity = ThreatSeverity.MEDIUM,
        affected_components: Optional[List[str]] = None,
        patch_available: bool = False,
        patch_url: Optional[str] = None,
        patch_notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Detect a new vulnerability"""
        vulnerability_id = f"vuln_{uuid.uuid4().hex[:8]}"
        
        vulnerability = Vulnerability(
            vulnerability_id=vulnerability_id,
            name=name,
            description=description,
            cve_id=cve_id,
            severity=severity,
            affected_components=affected_components or [],
            patch_available=patch_available,
            patch_url=patch_url,
            patch_notes=patch_notes,
            metadata=metadata or {}
        )
        
        self.vulnerabilities[vulnerability_id] = vulnerability
        await self._save_data()
        
        self.metrics["vulnerabilities_found"] += 1
        
        return vulnerability_id
    
    async def create_defense_rule(
        self,
        name: str,
        description: str,
        threat_type: ThreatType,
        severity: ThreatSeverity,
        conditions: Dict[str, Any],
        actions: List[DefenseAction],
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new defense rule"""
        rule_id = f"rule_{uuid.uuid4().hex[:8]}"
        
        rule = DefenseRule(
            rule_id=rule_id,
            name=name,
            description=description,
            threat_type=threat_type,
            severity=severity,
            conditions=conditions,
            actions=actions,
            priority=priority,
            metadata=metadata or {}
        )
        
        self.defense_rules[rule_id] = rule
        await self._save_data()
        
        return rule_id
    
    async def apply_defense_action(
        self,
        threat_id: str,
        action: DefenseAction,
        notes: Optional[str] = None
    ) -> bool:
        """Apply a defense action to a threat"""
        if threat_id not in self.threats:
            self.logger.error(f"Threat {threat_id} not found")
            return False
        
        threat = self.threats[threat_id]
        
        if action not in threat.defense_actions:
            threat.defense_actions.append(action)
            threat.updated_at = datetime.utcnow()
            
            if action == DefenseAction.BLOCK:
                self.metrics["threats_blocked"] += 1
            
            self.metrics["defense_actions_taken"] += 1
            
            # If the threat is resolved, update its status
            if action in [DefenseAction.BLOCK, DefenseAction.QUARANTINE, DefenseAction.PATCH]:
                threat.status = "resolved"
                threat.resolution_time = datetime.utcnow()
                threat.resolution_notes = notes
            
            await self._save_data()
            return True
        
        return False
    
    async def patch_vulnerability(
        self,
        vulnerability_id: str,
        patch_notes: Optional[str] = None
    ) -> bool:
        """Patch a vulnerability"""
        if vulnerability_id not in self.vulnerabilities:
            self.logger.error(f"Vulnerability {vulnerability_id} not found")
            return False
        
        vulnerability = self.vulnerabilities[vulnerability_id]
        
        if vulnerability.status == "open":
            vulnerability.status = "patched"
            vulnerability.resolution_time = datetime.utcnow()
            vulnerability.resolution_notes = patch_notes
            vulnerability.updated_at = datetime.utcnow()
            
            self.metrics["vulnerabilities_patched"] += 1
            
            await self._save_data()
            return True
        
        return False
    
    async def get_threat(self, threat_id: str) -> Optional[Threat]:
        """Get a threat by ID"""
        return self.threats.get(threat_id)
    
    async def get_vulnerability(self, vulnerability_id: str) -> Optional[Vulnerability]:
        """Get a vulnerability by ID"""
        return self.vulnerabilities.get(vulnerability_id)
    
    async def get_security_scan(self, scan_id: str) -> Optional[SecurityScan]:
        """Get a security scan by ID"""
        return self.security_scans.get(scan_id)
    
    async def get_defense_rule(self, rule_id: str) -> Optional[DefenseRule]:
        """Get a defense rule by ID"""
        return self.defense_rules.get(rule_id)
    
    async def get_active_threats(
        self,
        threat_type: Optional[ThreatType] = None,
        severity: Optional[ThreatSeverity] = None,
        limit: int = 10
    ) -> List[Threat]:
        """Get active threats"""
        active = []
        
        for threat in self.threats.values():
            if threat.status != "active":
                continue
            
            if threat_type and threat.threat_type != threat_type:
                continue
            
            if severity and threat.severity != severity:
                continue
            
            active.append(threat)
        
        # Sort by severity and detection time
        active.sort(key=lambda x: (x.severity.value, x.detection_time), reverse=True)
        
        return active[:limit]
    
    async def get_open_vulnerabilities(
        self,
        severity: Optional[ThreatSeverity] = None,
        limit: int = 10
    ) -> List[Vulnerability]:
        """Get open vulnerabilities"""
        open_vulns = []
        
        for vulnerability in self.vulnerabilities.values():
            if vulnerability.status != "open":
                continue
            
            if severity and vulnerability.severity != severity:
                continue
            
            open_vulns.append(vulnerability)
        
        # Sort by severity and detection time
        open_vulns.sort(key=lambda x: (x.severity.value, x.detection_time), reverse=True)
        
        return open_vulns[:limit]
    
    async def get_recent_security_scans(
        self,
        scan_type: Optional[str] = None,
        limit: int = 10
    ) -> List[SecurityScan]:
        """Get recent security scans"""
        recent = []
        
        for scan in self.security_scans.values():
            if scan_type and scan.scan_type != scan_type:
                continue
            
            recent.append(scan)
        
        # Sort by start time
        recent.sort(key=lambda x: x.start_time, reverse=True)
        
        return recent[:limit]
    
    async def _register_default_defense_rules(self) -> None:
        """Register default defense rules"""
        # Rule for blocking malware
        await self.create_defense_rule(
            name="Block Malware",
            description="Block any detected malware",
            threat_type=ThreatType.MALWARE,
            severity=ThreatSeverity.HIGH,
            conditions={"signature_match": True},
            actions=[DefenseAction.BLOCK, DefenseAction.QUARANTINE],
            priority=10
        )
        
        # Rule for blocking zero-day exploits
        await self.create_defense_rule(
            name="Block Zero-Day Exploits",
            description="Block any detected zero-day exploits",
            threat_type=ThreatType.ZERO_DAY,
            severity=ThreatSeverity.CRITICAL,
            conditions={"signature_match": True},
            actions=[DefenseAction.BLOCK, DefenseAction.ISOLATE],
            priority=10
        )
        
        # Rule for blocking unauthorized access
        await self.create_defense_rule(
            name="Block Unauthorized Access",
            description="Block any unauthorized access attempts",
            threat_type=ThreatType.UNAUTHORIZED_ACCESS,
            severity=ThreatSeverity.HIGH,
            conditions={"authentication_failure": True},
            actions=[DefenseAction.BLOCK, DefenseAction.ALERT],
            priority=8
        )
        
        # Rule for blocking code injection
        await self.create_defense_rule(
            name="Block Code Injection",
            description="Block any detected code injection attempts",
            threat_type=ThreatType.CODE_INJECTION,
            severity=ThreatSeverity.HIGH,
            conditions={"pattern_match": True},
            actions=[DefenseAction.BLOCK, DefenseAction.ALERT],
            priority=8
        )
        
        # Rule for blocking network attacks
        await self.create_defense_rule(
            name="Block Network Attacks",
            description="Block any detected network attacks",
            threat_type=ThreatType.NETWORK_ATTACK,
            severity=ThreatSeverity.HIGH,
            conditions={"traffic_pattern": "malicious"},
            actions=[DefenseAction.BLOCK, DefenseAction.ALERT],
            priority=8
        )
        
        # Rule for monitoring agent compromise
        await self.create_defense_rule(
            name="Monitor Agent Compromise",
            description="Monitor any suspected agent compromise",
            threat_type=ThreatType.AGENT_COMPROMISE,
            severity=ThreatSeverity.CRITICAL,
            conditions={"behavior_anomaly": True},
            actions=[DefenseAction.MONITOR, DefenseAction.ALERT],
            priority=9
        )
        
        # Rule for monitoring data poisoning
        await self.create_defense_rule(
            name="Monitor Data Poisoning",
            description="Monitor any suspected data poisoning",
            threat_type=ThreatType.DATA_POISONING,
            severity=ThreatSeverity.HIGH,
            conditions={"data_anomaly": True},
            actions=[DefenseAction.MONITOR, DefenseAction.ALERT],
            priority=7
        )
    
    async def _scan_agent_implementation(self, agent_id: str) -> List[str]:
        """Scan an agent's implementation for security issues"""
        self.logger.info(f"Scanning agent implementation: {agent_id}")
        
        # In a real implementation, this would analyze the agent's code
        # For now, we'll simulate findings
        
        threat_ids = []
        
        # Simulate finding a vulnerability
        if random.random() < 0.3:  # 30% chance of finding a vulnerability
            vulnerability_id = await self.detect_vulnerability(
                name="Insecure Data Handling",
                description="The agent is handling sensitive data without proper encryption",
                cve_id="CVE-2023-12345",
                severity=ThreatSeverity.HIGH,
                affected_components=[agent_id],
                patch_available=True,
                patch_url="https://example.com/patches/secure-data-handling",
                patch_notes="Implement proper encryption for sensitive data"
            )
            
            # Create a threat based on the vulnerability
            threat_id = await self.detect_threat(
                name="Data Exposure Risk",
                description="Risk of data exposure due to insecure data handling",
                threat_type=ThreatType.VULNERABILITY,
                severity=ThreatSeverity.HIGH,
                source="internal_scan",
                target=agent_id,
                affected_agents=[agent_id],
                metadata={"vulnerability_id": vulnerability_id}
            )
            
            threat_ids.append(threat_id)
        
        # Simulate finding a potential backdoor
        if random.random() < 0.1:  # 10% chance of finding a backdoor
            threat_id = await self.detect_threat(
                name="Suspicious Network Connection",
                description="The agent is making connections to unknown external servers",
                threat_type=ThreatType.MALWARE,
                severity=ThreatSeverity.CRITICAL,
                source="internal_scan",
                target=agent_id,
                indicators=["unknown_domain.com", "suspicious_ip:1234"],
                affected_agents=[agent_id],
                metadata={"connection_type": "outbound", "protocol": "tcp"}
            )
            
            threat_ids.append(threat_id)
        
        return threat_ids
    
    async def _scan_network_implementation(self, network_id: str) -> List[str]:
        """Scan a network for security issues"""
        self.logger.info(f"Scanning network: {network_id}")
        
        # In a real implementation, this would analyze the network
        # For now, we'll simulate findings
        
        threat_ids = []
        
        # Simulate finding a network vulnerability
        if random.random() < 0.2:  # 20% chance of finding a vulnerability
            vulnerability_id = await self.detect_vulnerability(
                name="Open Port",
                description="An unnecessary port is open and accessible",
                severity=ThreatSeverity.MEDIUM,
                affected_components=[network_id],
                patch_available=True,
                patch_notes="Close the unnecessary port"
            )
            
            # Create a threat based on the vulnerability
            threat_id = await self.detect_threat(
                name="Network Exposure",
                description="Risk of network exposure due to open port",
                threat_type=ThreatType.VULNERABILITY,
                severity=ThreatSeverity.MEDIUM,
                source="internal_scan",
                target=network_id,
                affected_networks=[network_id],
                metadata={"vulnerability_id": vulnerability_id}
            )
            
            threat_ids.append(threat_id)
        
        # Simulate finding a potential attack
        if random.random() < 0.15:  # 15% chance of finding an attack
            threat_id = await self.detect_threat(
                name="Suspicious Network Traffic",
                description="Detected suspicious network traffic patterns",
                threat_type=ThreatType.NETWORK_ATTACK,
                severity=ThreatSeverity.HIGH,
                source="internal_scan",
                target=network_id,
                indicators=["port_scan", "brute_force_attempt"],
                affected_networks=[network_id],
                metadata={"traffic_type": "inbound", "protocol": "tcp"}
            )
            
            threat_ids.append(threat_id)
        
        return threat_ids
    
    async def _scan_file_implementation(self, file_path: str) -> List[str]:
        """Scan a file for security issues"""
        self.logger.info(f"Scanning file: {file_path}")
        
        # In a real implementation, this would analyze the file
        # For now, we'll simulate findings
        
        threat_ids = []
        
        # Simulate finding malware
        if random.random() < 0.05:  # 5% chance of finding malware
            threat_id = await self.detect_threat(
                name="Malware Detected",
                description="Detected malware in the file",
                threat_type=ThreatType.MALWARE,
                severity=ThreatSeverity.CRITICAL,
                source="file_scan",
                target=file_path,
                signature="malware_signature_123",
                affected_files=[file_path],
                metadata={"file_type": "python", "file_size": 1024}
            )
            
            threat_ids.append(threat_id)
        
        # Simulate finding a vulnerability
        if random.random() < 0.1:  # 10% chance of finding a vulnerability
            vulnerability_id = await self.detect_vulnerability(
                name="Code Vulnerability",
                description="Detected a code vulnerability in the file",
                severity=ThreatSeverity.MEDIUM,
                affected_components=[file_path],
                patch_available=True,
                patch_notes="Fix the vulnerability in the code"
            )
            
            # Create a threat based on the vulnerability
            threat_id = await self.detect_threat(
                name="Code Vulnerability",
                description="Risk of code exploitation due to vulnerability",
                threat_type=ThreatType.VULNERABILITY,
                severity=ThreatSeverity.MEDIUM,
                source="file_scan",
                target=file_path,
                affected_files=[file_path],
                metadata={"vulnerability_id": vulnerability_id}
            )
            
            threat_ids.append(threat_id)
        
        return threat_ids
    
    async def _process_threat(self, threat_id: str) -> None:
        """Process a detected threat"""
        if threat_id not in self.threats:
            return
        
        threat = self.threats[threat_id]
        
        # Find matching defense rules
        matching_rules = []
        
        for rule in self.defense_rules.values():
            if not rule.is_active:
                continue
            
            if rule.threat_type != threat.threat_type:
                continue
            
            if rule.severity.value > threat.severity.value:
                continue
            
            # Check conditions
            conditions_met = True
            
            for key, value in rule.conditions.items():
                if key == "signature_match" and value:
                    if not threat.signature:
                        conditions_met = False
                        break
                
                elif key == "pattern_match" and value:
                    if not any(re.search(pattern, threat.description) for pattern in threat.indicators):
                        conditions_met = False
                        break
                
                elif key == "authentication_failure" and value:
                    if "authentication" not in threat.description.lower():
                        conditions_met = False
                        break
                
                elif key == "traffic_pattern" and value == "malicious":
                    if not any(pattern in threat.description.lower() for pattern in ["traffic", "network", "connection"]):
                        conditions_met = False
                        break
                
                elif key == "behavior_anomaly" and value:
                    if not any(pattern in threat.description.lower() for pattern in ["behavior", "anomaly", "unusual"]):
                        conditions_met = False
                        break
                
                elif key == "data_anomaly" and value:
                    if not any(pattern in threat.description.lower() for pattern in ["data", "poison", "corrupt"]):
                        conditions_met = False
                        break
            
            if conditions_met:
                matching_rules.append(rule)
        
        # Sort rules by priority
        matching_rules.sort(key=lambda x: x.priority, reverse=True)
        
        # Apply actions from matching rules
        for rule in matching_rules:
            for action in rule.actions:
                await self.apply_defense_action(threat_id, action)
    
    async def _load_data(self) -> None:
        """Load data from disk"""
        # Load threats
        threats_file = self.data_dir / "threats.json"
        if threats_file.exists():
            with open(threats_file, "r") as f:
                threats_data = json.load(f)
                
                for threat_data in threats_data:
                    threat = Threat(
                        threat_id=threat_data["threat_id"],
                        name=threat_data["name"],
                        description=threat_data["description"],
                        threat_type=ThreatType[threat_data["threat_type"]],
                        severity=ThreatSeverity[threat_data["severity"]],
                        source=threat_data["source"],
                        target=threat_data["target"],
                        detection_time=datetime.fromisoformat(threat_data["detection_time"]),
                        status=threat_data.get("status", "active"),
                        signature=threat_data.get("signature"),
                        indicators=threat_data.get("indicators", []),
                        affected_agents=threat_data.get("affected_agents", []),
                        affected_files=threat_data.get("affected_files", []),
                        affected_networks=threat_data.get("affected_networks", []),
                        defense_actions=[DefenseAction[action] for action in threat_data.get("defense_actions", [])],
                        resolution_time=datetime.fromisoformat(threat_data["resolution_time"]) if threat_data.get("resolution_time") else None,
                        resolution_notes=threat_data.get("resolution_notes"),
                        metadata=threat_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(threat_data["created_at"]),
                        updated_at=datetime.fromisoformat(threat_data["updated_at"])
                    )
                    
                    self.threats[threat.threat_id] = threat
        
        # Load vulnerabilities
        vulnerabilities_file = self.data_dir / "vulnerabilities.json"
        if vulnerabilities_file.exists():
            with open(vulnerabilities_file, "r") as f:
                vulnerabilities_data = json.load(f)
                
                for vulnerability_data in vulnerabilities_data:
                    vulnerability = Vulnerability(
                        vulnerability_id=vulnerability_data["vulnerability_id"],
                        name=vulnerability_data["name"],
                        description=vulnerability_data["description"],
                        cve_id=vulnerability_data.get("cve_id"),
                        severity=ThreatSeverity[vulnerability_data["severity"]],
                        affected_components=vulnerability_data.get("affected_components", []),
                        detection_time=datetime.fromisoformat(vulnerability_data["detection_time"]),
                        status=vulnerability_data.get("status", "open"),
                        patch_available=vulnerability_data.get("patch_available", False),
                        patch_url=vulnerability_data.get("patch_url"),
                        patch_notes=vulnerability_data.get("patch_notes"),
                        resolution_time=datetime.fromisoformat(vulnerability_data["resolution_time"]) if vulnerability_data.get("resolution_time") else None,
                        resolution_notes=vulnerability_data.get("resolution_notes"),
                        metadata=vulnerability_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(vulnerability_data["created_at"]),
                        updated_at=datetime.fromisoformat(vulnerability_data["updated_at"])
                    )
                    
                    self.vulnerabilities[vulnerability.vulnerability_id] = vulnerability
        
        # Load security scans
        scans_file = self.data_dir / "security_scans.json"
        if scans_file.exists():
            with open(scans_file, "r") as f:
                scans_data = json.load(f)
                
                for scan_data in scans_data:
                    scan = SecurityScan(
                        scan_id=scan_data["scan_id"],
                        scan_type=scan_data["scan_type"],
                        target=scan_data["target"],
                        start_time=datetime.fromisoformat(scan_data["start_time"]),
                        end_time=datetime.fromisoformat(scan_data["end_time"]) if scan_data.get("end_time") else None,
                        status=scan_data.get("status", "running"),
                        threats_found=scan_data.get("threats_found", []),
                        vulnerabilities_found=scan_data.get("vulnerabilities_found", []),
                        scan_results=scan_data.get("scan_results", {}),
                        metadata=scan_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(scan_data["created_at"]),
                        updated_at=datetime.fromisoformat(scan_data["updated_at"])
                    )
                    
                    self.security_scans[scan.scan_id] = scan
        
        # Load defense rules
        rules_file = self.data_dir / "defense_rules.json"
        if rules_file.exists():
            with open(rules_file, "r") as f:
                rules_data = json.load(f)
                
                for rule_data in rules_data:
                    rule = DefenseRule(
                        rule_id=rule_data["rule_id"],
                        name=rule_data["name"],
                        description=rule_data["description"],
                        threat_type=ThreatType[rule_data["threat_type"]],
                        severity=ThreatSeverity[rule_data["severity"]],
                        conditions=rule_data.get("conditions", {}),
                        actions=[DefenseAction[action] for action in rule_data.get("actions", [])],
                        is_active=rule_data.get("is_active", True),
                        priority=rule_data.get("priority", 0),
                        metadata=rule_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(rule_data["created_at"]),
                        updated_at=datetime.fromisoformat(rule_data["updated_at"])
                    )
                    
                    self.defense_rules[rule.rule_id] = rule
        
        # Load agent signatures
        signatures_file = self.data_dir / "agent_signatures.json"
        if signatures_file.exists():
            with open(signatures_file, "r") as f:
                self.agent_signatures = json.load(f)
        
        # Load file signatures
        file_signatures_file = self.data_dir / "file_signatures.json"
        if file_signatures_file.exists():
            with open(file_signatures_file, "r") as f:
                self.file_signatures = json.load(f)
        
        # Load network signatures
        network_signatures_file = self.data_dir / "network_signatures.json"
        if network_signatures_file.exists():
            with open(network_signatures_file, "r") as f:
                self.network_signatures = json.load(f)
        
        # Load threat intelligence
        intelligence_file = self.data_dir / "threat_intelligence.json"
        if intelligence_file.exists():
            with open(intelligence_file, "r") as f:
                self.threat_intelligence = json.load(f)
    
    async def _save_data(self) -> None:
        """Save data to disk"""
        # Save threats
        threats_file = self.data_dir / "threats.json"
        threats_data = []
        
        for threat in self.threats.values():
            threat_data = {
                "threat_id": threat.threat_id,
                "name": threat.name,
                "description": threat.description,
                "threat_type": threat.threat_type.name,
                "severity": threat.severity.name,
                "source": threat.source,
                "target": threat.target,
                "detection_time": threat.detection_time.isoformat(),
                "status": threat.status,
                "signature": threat.signature,
                "indicators": threat.indicators,
                "affected_agents": threat.affected_agents,
                "affected_files": threat.affected_files,
                "affected_networks": threat.affected_networks,
                "defense_actions": [action.name for action in threat.defense_actions],
                "resolution_time": threat.resolution_time.isoformat() if threat.resolution_time else None,
                "resolution_notes": threat.resolution_notes,
                "metadata": threat.metadata,
                "created_at": threat.created_at.isoformat(),
                "updated_at": threat.updated_at.isoformat()
            }
            threats_data.append(threat_data)
        
        with open(threats_file, "w") as f:
            json.dump(threats_data, f, indent=2)
        
        # Save vulnerabilities
        vulnerabilities_file = self.data_dir / "vulnerabilities.json"
        vulnerabilities_data = []
        
        for vulnerability in self.vulnerabilities.values():
            vulnerability_data = {
                "vulnerability_id": vulnerability.vulnerability_id,
                "name": vulnerability.name,
                "description": vulnerability.description,
                "cve_id": vulnerability.cve_id,
                "severity": vulnerability.severity.name,
                "affected_components": vulnerability.affected_components,
                "detection_time": vulnerability.detection_time.isoformat(),
                "status": vulnerability.status,
                "patch_available": vulnerability.patch_available,
                "patch_url": vulnerability.patch_url,
                "patch_notes": vulnerability.patch_notes,
                "resolution_time": vulnerability.resolution_time.isoformat() if vulnerability.resolution_time else None,
                "resolution_notes": vulnerability.resolution_notes,
                "metadata": vulnerability.metadata,
                "created_at": vulnerability.created_at.isoformat(),
                "updated_at": vulnerability.updated_at.isoformat()
            }
            vulnerabilities_data.append(vulnerability_data)
        
        with open(vulnerabilities_file, "w") as f:
            json.dump(vulnerabilities_data, f, indent=2)
        
        # Save security scans
        scans_file = self.data_dir / "security_scans.json"
        scans_data = []
        
        for scan in self.security_scans.values():
            scan_data = {
                "scan_id": scan.scan_id,
                "scan_type": scan.scan_type,
                "target": scan.target,
                "start_time": scan.start_time.isoformat(),
                "end_time": scan.end_time.isoformat() if scan.end_time else None,
                "status": scan.status,
                "threats_found": scan.threats_found,
                "vulnerabilities_found": scan.vulnerabilities_found,
                "scan_results": scan.scan_results,
                "metadata": scan.metadata,
                "created_at": scan.created_at.isoformat(),
                "updated_at": scan.updated_at.isoformat()
            }
            scans_data.append(scan_data)
        
        with open(scans_file, "w") as f:
            json.dump(scans_data, f, indent=2)
        
        # Save defense rules
        rules_file = self.data_dir / "defense_rules.json"
        rules_data = []
        
        for rule in self.defense_rules.values():
            rule_data = {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "threat_type": rule.threat_type.name,
                "severity": rule.severity.name,
                "conditions": rule.conditions,
                "actions": [action.name for action in rule.actions],
                "is_active": rule.is_active,
                "priority": rule.priority,
                "metadata": rule.metadata,
                "created_at": rule.created_at.isoformat(),
                "updated_at": rule.updated_at.isoformat()
            }
            rules_data.append(rule_data)
        
        with open(rules_file, "w") as f:
            json.dump(rules_data, f, indent=2)
        
        # Save agent signatures
        signatures_file = self.data_dir / "agent_signatures.json"
        with open(signatures_file, "w") as f:
            json.dump(self.agent_signatures, f, indent=2)
        
        # Save file signatures
        file_signatures_file = self.data_dir / "file_signatures.json"
        with open(file_signatures_file, "w") as f:
            json.dump(self.file_signatures, f, indent=2)
        
        # Save network signatures
        network_signatures_file = self.data_dir / "network_signatures.json"
        with open(network_signatures_file, "w") as f:
            json.dump(self.network_signatures, f, indent=2)
        
        # Save threat intelligence
        intelligence_file = self.data_dir / "threat_intelligence.json"
        with open(intelligence_file, "w") as f:
            json.dump(self.threat_intelligence, f, indent=2)
    
    async def _process_scan_queue(self) -> None:
        """Process the scan queue"""
        while self.status == AgentStatus.RUNNING:
            try:
                # Get next scan to run
                scan_id = await self.scan_queue.get()
                
                # Run the scan
                await self._run_scan(scan_id)
                
                # Mark task as complete
                self.scan_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing scan queue: {str(e)}")
                continue
    
    async def _process_threat_queue(self) -> None:
        """Process the threat queue"""
        while self.status == AgentStatus.RUNNING:
            try:
                # Get next threat to process
                threat_id = await self.threat_queue.get()
                
                # Process the threat
                await self._process_threat(threat_id)
                
                # Mark task as complete
                self.threat_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing threat queue: {str(e)}")
                continue
    
    async def _run_scan(self, scan_id: str) -> None:
        """Run a security scan"""
        if scan_id not in self.security_scans:
            return
        
        scan = self.security_scans[scan_id]
        scan.status = "running"
        scan.updated_at = datetime.utcnow()
        
        self.metrics["security_scans_run"] += 1
        
        # Run scan based on type
        threat_ids = []
        
        if scan.scan_type == "agent_scan":
            threat_ids = await self._scan_agent_implementation(scan.target)
        elif scan.scan_type == "network_scan":
            threat_ids = await self._scan_network_implementation(scan.target)
        elif scan.scan_type == "file_scan":
            threat_ids = await self._scan_file_implementation(scan.target)
        
        # Update scan results
        scan.threats_found = threat_ids
        scan.end_time = datetime.utcnow()
        scan.status = "completed"
        scan.updated_at = datetime.utcnow()
        
        await self._save_data() 