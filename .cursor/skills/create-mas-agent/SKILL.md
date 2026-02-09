---
name: create-mas-agent
description: Create a new MAS agent following the BaseAgent pattern. Use when adding a new agent to the Multi-Agent System, creating a specialized agent, or extending agent capabilities.
---

# Create a New MAS Agent

## Pattern

All agents inherit from `BaseAgent` and follow a consistent structure.

## Steps

```
Agent Creation Progress:
- [ ] Step 1: Create agent file
- [ ] Step 2: Update agents/__init__.py
- [ ] Step 3: Register in system registry
- [ ] Step 4: Test the agent
```

### Step 1: Create the agent file

Create `mycosoft_mas/agents/your_agent.py`:

```python
"""Your Agent - Brief description of what this agent does."""

from typing import Any, Dict, List, Optional
from mycosoft_mas.agents.base_agent import BaseAgent


class YourAgent(BaseAgent):
    """Description of agent's purpose and capabilities."""

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        super().__init__(agent_id=agent_id, name=name, config=config)
        # Agent-specific initialization
        self.capabilities = ["capability_1", "capability_2"]

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming task."""
        task_type = task.get("type", "")
        # Route to appropriate handler
        handlers = {
            "action_1": self._handle_action_1,
            "action_2": self._handle_action_2,
        }
        handler = handlers.get(task_type)
        if handler:
            return await handler(task)
        return {"status": "error", "message": f"Unknown task type: {task_type}"}

    async def _handle_action_1(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle action 1."""
        # Implementation here
        return {"status": "success", "result": {}}
```

### Step 2: Update agents/__init__.py

Add the import and export:

```python
from .your_agent import YourAgent

# Add to __all__ list
__all__ = [
    # ... existing agents ...
    'YourAgent',
]
```

### Step 3: Register in system registry

Update `docs/SYSTEM_REGISTRY_FEB04_2026.md` with the new agent entry.

Or register via API:

```bash
curl -X POST http://192.168.0.188:8001/api/registry/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "your_agent",
    "type": "specialist",
    "description": "What this agent does",
    "capabilities": ["cap1", "cap2"],
    "version": "1.0.0"
  }'
```

### Step 4: Test

```python
# In tests/test_your_agent.py
import pytest
from mycosoft_mas.agents.your_agent import YourAgent

@pytest.mark.asyncio
async def test_agent_creation():
    agent = YourAgent(
        agent_id="test-agent",
        name="Test Agent",
        config={}
    )
    assert agent.name == "Test Agent"
```

## Key Rules

- Always inherit from `BaseAgent`
- Constructor signature: `__init__(self, agent_id: str, name: str, config: Dict[str, Any])`
- Always call `super().__init__(agent_id=agent_id, name=name, config=config)`
- Use async methods for task processing
- Include proper type hints
- Update `__init__.py` with import and `__all__` entry
