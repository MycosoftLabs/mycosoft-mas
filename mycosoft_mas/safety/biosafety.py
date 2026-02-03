"""Biosafety Monitor. Created: February 3, 2026"""
from typing import Any, Dict, List
from enum import Enum

class BiosafetyLevel(str, Enum):
    BSL1 = "BSL-1"
    BSL2 = "BSL-2"
    BSL3 = "BSL-3"
    BSL4 = "BSL-4"

class BiosafetyMonitor:
    """Monitors biosafety compliance."""
    
    def __init__(self, facility_level: BiosafetyLevel = BiosafetyLevel.BSL1):
        self.facility_level = facility_level
        self.incidents: List[Dict[str, Any]] = []
    
    def check_organism(self, organism: str, risk_group: int) -> Dict[str, Any]:
        level_requirements = {1: BiosafetyLevel.BSL1, 2: BiosafetyLevel.BSL2, 3: BiosafetyLevel.BSL3, 4: BiosafetyLevel.BSL4}
        required = level_requirements.get(risk_group, BiosafetyLevel.BSL1)
        levels = [BiosafetyLevel.BSL1, BiosafetyLevel.BSL2, BiosafetyLevel.BSL3, BiosafetyLevel.BSL4]
        compliant = levels.index(self.facility_level) >= levels.index(required)
        return {"organism": organism, "risk_group": risk_group, "required_level": required.value, "facility_level": self.facility_level.value, "compliant": compliant}
    
    def report_incident(self, incident_type: str, description: str) -> str:
        from uuid import uuid4
        incident_id = str(uuid4())
        self.incidents.append({"id": incident_id, "type": incident_type, "description": description})
        return incident_id
    
    def get_incidents(self) -> List[Dict[str, Any]]:
        return self.incidents
