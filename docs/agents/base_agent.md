# Base Agent Documentation

## Overview
The Base Agent is the foundation for all agents in the Mycosoft MAS system. It provides core functionality and interfaces that all specialized agents must implement.

## Purpose
- Provide a standardized interface for agent communication
- Handle common agent operations
- Manage agent lifecycle
- Implement core agent capabilities

## Core Functions

### Initialization
```python
async def initialize(self):
    """
    Initialize the agent with its capabilities and register with the knowledge graph
    """
    await self.register_capabilities(['base_capabilities'])
    await self.connect_to_message_broker()
```

### Message Processing
```python
async def process_message(self, message: Message):
    """
    Process incoming messages and route them to appropriate handlers
    """
    if message.type == MessageType.CAPABILITY_REQUEST:
        await self.handle_capability_request(message)
    elif message.type == MessageType.STATUS_UPDATE:
        await self.handle_status_update(message)
```

### Health Monitoring
```python
async def check_health(self):
    """
    Monitor agent health and report status
    """
    return {
        "status": "healthy",
        "metrics": self._collect_metrics(),
        "capabilities": self.capabilities
    }
```

## Required Implementations

### Capability Registration
```python
async def register_capabilities(self, capabilities: List[str]):
    """
    Register agent capabilities with the knowledge graph
    """
    await self.knowledge_graph.add_agent(
        agent_id=self.agent_id,
        capabilities=capabilities,
        relationships=self.relationships
    )
```

### Message Handling
```python
async def handle_message(self, message: Message):
    """
    Handle incoming messages based on type
    """
    handlers = {
        MessageType.CAPABILITY_REQUEST: self.handle_capability_request,
        MessageType.STATUS_UPDATE: self.handle_status_update,
        MessageType.ERROR: self.handle_error
    }
    handler = handlers.get(message.type)
    if handler:
        await handler(message)
```

## Configuration

### Required Settings
```yaml
agent:
  id: "unique-agent-id"
  name: "Agent Name"
  capabilities: ["capability1", "capability2"]
  relationships: ["related-agent-1", "related-agent-2"]
  message_broker:
    url: "redis://localhost:6379"
    queue_prefix: "agent-queue"
```

### Optional Settings
```yaml
agent:
  health_check_interval: 30
  message_timeout: 60
  retry_count: 3
  logging_level: "INFO"
```

## Rules and Guidelines

1. **Message Handling**
   - All messages must be processed asynchronously
   - Messages must be acknowledged after processing
   - Failed messages must be retried according to configuration

2. **Health Monitoring**
   - Agents must report health status at configured intervals
   - Critical errors must be reported immediately
   - Resource usage must be monitored and reported

3. **Capability Management**
   - Capabilities must be registered before use
   - Capabilities can be added or removed dynamically
   - Capability conflicts must be resolved

4. **Error Handling**
   - All errors must be logged
   - Critical errors must trigger alerts
   - Error recovery must be attempted

## Integration Points

### Knowledge Graph
- Register agent capabilities
- Update agent relationships
- Query system state

### Message Broker
- Send and receive messages
- Handle message routing
- Manage message queues

### Monitoring System
- Report health metrics
- Log agent activities
- Track performance

## Best Practices

1. **Error Handling**
   - Implement comprehensive error handling
   - Use appropriate logging levels
   - Provide detailed error messages

2. **Performance**
   - Use async operations for I/O
   - Implement caching where appropriate
   - Monitor resource usage

3. **Security**
   - Validate all incoming messages
   - Implement proper authentication
   - Follow security best practices

4. **Testing**
   - Write unit tests for all functions
   - Implement integration tests
   - Test error scenarios

## Example Usage

```python
class MyAgent(BaseAgent):
    async def initialize(self):
        await self.register_capabilities(['my_capability'])
        
    async def process_message(self, message: Message):
        if message.type == MessageType.MY_CAPABILITY_REQUEST:
            await self.handle_my_capability(message)
            
    async def handle_my_capability(self, message: Message):
        # Implement capability-specific logic
        result = await self.process_my_capability(message.content)
        await self.send_response(message, result)
```

## Troubleshooting

### Common Issues

1. **Message Processing**
   - Check message broker connection
   - Verify message format
   - Monitor queue sizes

2. **Health Monitoring**
   - Check resource usage
   - Verify capability registration
   - Monitor error rates

3. **Integration**
   - Verify knowledge graph connection
   - Check message broker configuration
   - Monitor system dependencies

### Debugging Steps

1. Check agent logs
2. Verify configuration
3. Monitor system metrics
4. Test individual capabilities
5. Check integration points 