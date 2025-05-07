# Mycosoft MAS Services

This directory contains the core services that support the Multi-Agent System (MAS) functionality.

## Core Services

### 1. EvolutionMonitor
Monitors system evolution and technology changes.

```python
from mycosoft_mas.services.evolution_monitor import EvolutionMonitor

# Initialize the monitor
monitor = EvolutionMonitor()

# Check for updates
updates = await monitor.check_for_updates()

# Example response
{
    "new_technologies": [
        {
            "name": "new-package",
            "version": "1.0.0",
            "description": "New technology package",
            "impact": "high"
        }
    ],
    "evolution_alerts": [
        {
            "type": "deprecation",
            "message": "Package X will be deprecated",
            "severity": "warning"
        }
    ],
    "system_updates": [
        {
            "type": "security",
            "details": "Critical security update available",
            "priority": "high"
        }
    ]
}
```

### 2. SecurityMonitor
Manages security monitoring and alerts.

```python
from mycosoft_mas.services.security_monitor import SecurityMonitor

# Initialize the monitor
security = SecurityMonitor()

# Check for security issues
issues = await security.check_security()

# Example response
{
    "vulnerabilities": [
        {
            "package": "package-name",
            "version": "1.0.0",
            "severity": "critical",
            "description": "Security vulnerability found"
        }
    ],
    "security_alerts": [
        {
            "type": "intrusion",
            "message": "Suspicious activity detected",
            "severity": "high"
        }
    ],
    "security_updates": [
        {
            "package": "security-package",
            "version": "2.0.0",
            "description": "Security patch available"
        }
    ]
}
```

### 3. TechnologyTracker
Tracks and manages technology information.

```python
from mycosoft_mas.services.technology_tracker import TechnologyTracker

# Initialize the tracker
tracker = TechnologyTracker()

# Register a new technology
await tracker.register_technology(
    name="new-tech",
    version="1.0.0",
    description="New technology",
    capabilities=["feature1", "feature2"]
)

# Get technology information
tech_info = await tracker.get_technology("new-tech")

# Example response
{
    "name": "new-tech",
    "version": "1.0.0",
    "description": "New technology",
    "capabilities": ["feature1", "feature2"],
    "dependencies": ["dep1", "dep2"],
    "status": "active"
}
```

## Service Integration

### 1. With Orchestrator
```python
from mycosoft_mas.orchestrator import Orchestrator
from mycosoft_mas.services import EvolutionMonitor, SecurityMonitor, TechnologyTracker

class EnhancedOrchestrator(Orchestrator):
    def __init__(self):
        super().__init__()
        self.evolution_monitor = EvolutionMonitor()
        self.security_monitor = SecurityMonitor()
        self.technology_tracker = TechnologyTracker()
        
    async def monitor_system(self):
        # Monitor evolution
        evolution_updates = await self.evolution_monitor.check_for_updates()
        if evolution_updates["new_technologies"]:
            await self.handle_new_technologies(evolution_updates["new_technologies"])
            
        # Monitor security
        security_issues = await self.security_monitor.check_security()
        if security_issues["vulnerabilities"]:
            await self.handle_security_issues(security_issues["vulnerabilities"])
```

### 2. With Agents
```python
from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.services import EvolutionMonitor

class EnhancedAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.evolution_monitor = EvolutionMonitor()
        
    async def check_technology_updates(self):
        updates = await self.evolution_monitor.check_for_updates()
        if updates["new_technologies"]:
            await self.handle_technology_updates(updates["new_technologies"])
```

## Configuration

Example configuration in `config.yaml`:

```yaml
services:
  evolution_monitor:
    check_interval: 3600  # seconds
    alert_threshold: "medium"
    technology_sources:
      - "pypi"
      - "npm"
      - "docker"
    
  security_monitor:
    check_interval: 1800  # seconds
    vulnerability_scanners:
      - "snyk"
      - "owasp"
    alert_channels:
      - "email"
      - "slack"
    
  technology_tracker:
    update_interval: 86400  # seconds
    tracking_level: "detailed"
    storage:
      type: "database"
      connection: "postgresql://user:pass@localhost/db"
```

## Error Handling

All services implement comprehensive error handling:

```python
try:
    updates = await monitor.check_for_updates()
except EvolutionMonitorError as e:
    logger.error(f"Evolution monitoring failed: {e}")
    # Implement fallback or recovery
except SecurityMonitorError as e:
    logger.error(f"Security monitoring failed: {e}")
    # Implement security-specific recovery
except TechnologyTrackerError as e:
    logger.error(f"Technology tracking failed: {e}")
    # Implement tracking-specific recovery
```

## Metrics and Monitoring

Services expose metrics for monitoring:

```python
# Get service status
status = monitor.get_status()

# Example response
{
    "last_check": "2024-02-19T12:00:00Z",
    "updates_found": 5,
    "alerts_generated": 2,
    "processing_time": 0.5,
    "error_count": 0
}
```

## Security Considerations

1. **Authentication**
   - All services require proper authentication
   - Token-based access control
   - Role-based permissions

2. **Data Protection**
   - Encrypted communication
   - Secure storage
   - Audit logging

3. **Access Control**
   - Service-level permissions
   - Resource-based access
   - Action authorization

## Performance Optimization

1. **Caching**
   - Implemented at service level
   - Configurable cache duration
   - Cache invalidation strategies

2. **Resource Management**
   - Connection pooling
   - Resource limits
   - Cleanup procedures

## Testing

Example test cases:

```python
import pytest
from mycosoft_mas.services import EvolutionMonitor

@pytest.mark.asyncio
async def test_evolution_monitor():
    monitor = EvolutionMonitor()
    updates = await monitor.check_for_updates()
    assert isinstance(updates, dict)
    assert "new_technologies" in updates
    assert "evolution_alerts" in updates
    assert "system_updates" in updates
```

## Deployment

Services can be deployed independently or as part of the MAS:

```yaml
# docker-compose.yml
services:
  evolution-monitor:
    image: mycosoft-mas-evolution-monitor
    environment:
      - CHECK_INTERVAL=3600
      - ALERT_THRESHOLD=medium
    
  security-monitor:
    image: mycosoft-mas-security-monitor
    environment:
      - CHECK_INTERVAL=1800
      - SCANNERS=snyk,owasp
    
  technology-tracker:
    image: mycosoft-mas-technology-tracker
    environment:
      - UPDATE_INTERVAL=86400
      - STORAGE_TYPE=database
``` 