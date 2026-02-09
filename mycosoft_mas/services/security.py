from typing import Dict, List, Any, Set, Optional
import os
import uuid
from datetime import datetime, timedelta
import jwt
import logging
from mycosoft_mas.services.security_interface import AgentSecurable

logger = logging.getLogger(__name__)

class SecurityService:
    def __init__(self):
        self.secret_key = os.getenv("SECRET_KEY", "CHANGE-ME-set-SECRET_KEY-env-var")
        self.token_expiry = timedelta(hours=1)
        self.revoked_tokens: set[str] = set()
        self.access_controls: Dict[str, Dict[str, Set[str]]] = {}  # resource -> {agent_id -> permissions}
        self.security_logs: List[Dict[str, Any]] = []
        self.incident_reports: List[Dict[str, Any]] = []
        self.security_metrics: Dict[str, Dict[str, Any]] = {}
        
    def authenticate_agent(self, agent: AgentSecurable) -> str:
        """Authenticate an agent and return a security token."""
        try:
            token = jwt.encode({
                'agent_id': agent.get_agent_id(),
                'name': agent.get_name(),
                'capabilities': agent.get_capabilities(),
                'exp': datetime.utcnow() + self.token_expiry
            }, self.secret_key, algorithm='HS256')
            
            agent.set_security_token(token)
            return token
            
        except Exception as e:
            logger.error(f"Failed to authenticate agent {agent.get_name()}: {str(e)}")
            raise
            
    def validate_token(self, token: str) -> bool:
        """Validate a security token."""
        try:
            if token in self.revoked_tokens:
                return False
                
            jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return True
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return False
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return False
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return False
            
    def revoke_token(self, token: str) -> None:
        """Revoke a security token."""
        self.revoked_tokens.add(token)
        
    def add_access_control(self, resource: str, agent_ids: List[str], permissions: List[str]) -> None:
        """Add access control for a resource."""
        if resource not in self.access_controls:
            self.access_controls[resource] = {}
            
        for agent_id in agent_ids:
            if agent_id not in self.access_controls[resource]:
                self.access_controls[resource][agent_id] = set()
            self.access_controls[resource][agent_id].update(permissions)
            
    def remove_access_control(self, resource: str, agent_id: str) -> None:
        """Remove access control for an agent on a resource."""
        if resource in self.access_controls:
            self.access_controls[resource].pop(agent_id, None)
            
    def check_access(self, token: str, resource: str, action: str) -> bool:
        """Check if an agent has access to perform an action on a resource."""
        try:
            if not self.validate_token(token):
                return False
                
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            capabilities = payload.get('capabilities', [])
            
            # Check if agent has required capability
            required_capability = f"{resource}:{action}"
            return required_capability in capabilities
            
        except Exception as e:
            logger.error(f"Access check error: {str(e)}")
            return False
        
    def log_security_event(self, event_type: str, message: str, level: str) -> None:
        """Log a security event."""
        self.security_logs.append({
            "type": level,
            "event": event_type,
            "message": message,
            "timestamp": datetime.now()
        })
        
    def clear_security_logs(self) -> None:
        """Clear all security logs."""
        self.security_logs.clear()
        
    def report_incident(self, incident_id: str, description: str, severity: str) -> None:
        """Report a security incident."""
        self.incident_reports.append({
            "id": incident_id,
            "description": description,
            "severity": severity,
            "status": "open",
            "timestamp": datetime.now()
        })
        
    def resolve_incident(self, incident_id: str) -> None:
        """Mark an incident as resolved."""
        for incident in self.incident_reports:
            if incident["id"] == incident_id:
                incident["status"] = "resolved"
                incident["resolved_at"] = datetime.now()
                break
                
    def monitor_security(self, agent: AgentSecurable) -> None:
        """Monitor security metrics for an agent."""
        if agent.get_agent_id() not in self.security_metrics:
            self.security_metrics[agent.get_agent_id()] = {
                "last_activity": None,
                "access_attempts": 0,
                "failed_attempts": 0
            }
            
        self.security_metrics[agent.get_agent_id()]["last_activity"] = datetime.now()
        
    def generate_security_report(self) -> Dict[str, Any]:
        """Generate a comprehensive security report."""
        return {
            "security_logs": self.security_logs,
            "incident_reports": self.incident_reports,
            "security_metrics": self.security_metrics
        } 