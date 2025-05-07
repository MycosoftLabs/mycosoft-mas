# Mycosoft MAS Dependency Management

This directory contains the dependency management system for the Mycosoft Multi-Agent System (MAS).

## DependencyManager

The DependencyManager class provides comprehensive dependency management capabilities:

### Key Features

1. **Agent-Specific Dependencies**
   - Track dependencies per agent
   - Manage agent-specific version requirements
   - Handle dependency conflicts between agents

2. **Version Conflict Resolution**
   - Automatic conflict detection
   - Intelligent version resolution
   - Compatibility checking
   - Version constraint management

3. **Dependency Operations**
   - Add/remove dependencies
   - Update dependencies
   - Check dependency status
   - Generate dependency reports
   - Install dependencies

4. **Security and Validation**
   - Dependency verification
   - Security vulnerability checking
   - Package integrity validation
   - Access control for dependency operations

### Usage

```python
from mycosoft_mas.dependencies.dependency_manager import DependencyManager

# Initialize the manager
dependency_manager = DependencyManager()

# Register agent dependencies
await dependency_manager.register_agent_dependencies(
    agent_id="my_agent",
    dependencies={
        "package1": ">=1.0.0",
        "package2": "~2.3.0"
    }
)

# Add a dependency
await dependency_manager.add_dependency(
    package="package3",
    version="1.2.3",
    agent_id="my_agent"
)

# Check dependencies
status = await dependency_manager.check_dependencies(agent_id="my_agent")

# Update dependencies
await dependency_manager.update_dependency(
    package="package1",
    version="1.1.0",
    agent_id="my_agent"
)

# Generate report
report = await dependency_manager.generate_dependency_report(agent_id="my_agent")
```

### Configuration

Dependencies can be configured through the main configuration file (`config.yaml`):

```yaml
dependencies:
  global:
    - package1: ">=1.0.0"
    - package2: "~2.3.0"
  
  agents:
    my_agent:
      - package3: "1.2.3"
      - package4: ">=2.0.0"
    
    other_agent:
      - package5: "~3.1.0"
      - package6: ">=1.0.0"
```

### Integration

The DependencyManager integrates with:
- Orchestrator for system-wide dependency management
- SecurityService for dependency security checks
- EvolutionMonitor for technology updates
- TaskManager for automated dependency updates

### Security Considerations

1. **Package Verification**
   - All packages are verified before installation
   - Checksums are validated
   - Digital signatures are verified when available

2. **Access Control**
   - Only authorized agents can modify dependencies
   - Global dependency changes require elevated privileges
   - All changes are logged and audited

3. **Vulnerability Scanning**
   - Regular vulnerability checks
   - Automatic security updates
   - Critical vulnerability alerts

### Error Handling

The DependencyManager includes comprehensive error handling:
- Dependency conflict resolution
- Installation failure recovery
- Version compatibility checks
- Network error handling
- Permission error handling 