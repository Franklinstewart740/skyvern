# Multi-Agent Swarm Quick Start Guide

This guide will help you get started with Skyvern's multi-agent swarm system for coordinated browser automation.

## Overview

The multi-agent swarm architecture introduces three specialized agents that work together to improve browser automation reliability and safety:

- **Planner Agent**: Creates and optimizes action plans
- **Executor Agent**: Executes actions on the browser
- **Validator Agent**: Validates plans and actions before execution

## Quick Start

### 1. Enable Multi-Agent Swarm

Add to your `.env` file:

```bash
# Enable multi-agent swarm coordination
ENABLE_MULTI_AGENT_SWARM=true

# Or enable DEBUG_MODE (which includes swarm features)
DEBUG_MODE=true
```

### 2. Run a Task

The multi-agent swarm works transparently with existing code:

```python
from skyvern import Skyvern

async def main():
    client = Skyvern()
    
    # Multi-agent swarm automatically coordinates when enabled
    task = await client.tasks.create(
        url="https://example.com/form",
        navigation_goal="Fill out the registration form",
    )
    
    # Agents will coordinate planning and execution
    await task.execute()
```

### 3. Monitor Agent Communications

View real-time agent coordination through the API:

```bash
# Get agent swarm status
curl -X GET http://localhost:8000/v1/agent-swarm/status \
  -H "x-api-key: your-api-key"

# Get agent messages for a task
curl -X GET "http://localhost:8000/v1/agent-swarm/tasks/{task_id}/messages" \
  -H "x-api-key: your-api-key"
```

### 4. Visualize in UI

Add the agent swarm visualization component to your task detail page:

```typescript
import { AgentSwarmVisualization } from "@/components/AgentSwarmVisualization";

function TaskDetailPage({ taskId }: { taskId: string }) {
  return (
    <div>
      {/* Your existing task details */}
      
      {/* Agent swarm visualization */}
      <AgentSwarmVisualization 
        taskId={taskId} 
        autoRefresh={true}
        refreshInterval={2000}
      />
    </div>
  );
}
```

## Key Features

### 1. Coordinated Planning

Agents collaborate to create safer execution plans:

```python
# Planner analyzes the page
# Validator checks for high-risk actions
# Coordinator ensures consensus before proceeding
```

### 2. Action Validation

Each action is validated before execution:

```python
# Executor proposes action
# Validator checks risk level
# Action only executes if approved
```

### 3. Real-time Communication

All agent communications are logged and queryable:

```python
from skyvern.forge.sdk.core.agent_message_bus import get_message_bus

message_bus = get_message_bus()
history = message_bus.get_message_history(task_id="your-task-id")

for message in history:
    print(f"{message.sender_role} -> {message.recipient_role}: {message.message_type}")
```

## Configuration Options

### Environment Variables

```bash
# Enable/disable multi-agent swarm
ENABLE_MULTI_AGENT_SWARM=true

# Enable debug mode (includes swarm features)
DEBUG_MODE=true

# Message history size (default: 1000)
# AGENT_MESSAGE_HISTORY_SIZE=1000
```

### Programmatic Control

```python
from skyvern.forge.sdk.core.multi_agent_swarm import AgentSwarmCoordinator

# Create coordinator with custom settings
coordinator = AgentSwarmCoordinator(
    task=task,
    step=step,
    browser_state=browser_state,
    enable_swarm=True  # Explicitly enable/disable
)
```

## Common Use Cases

### 1. High-Stakes Form Submission

```python
# Multi-agent swarm provides extra validation for sensitive data
task = await client.tasks.create(
    url="https://bank.com/transfer",
    navigation_goal="Transfer funds between accounts",
    # Swarm will validate each field before submission
)
```

### 2. Complex Multi-Step Workflows

```python
# Agents coordinate across multiple steps
workflow = await client.workflows.create(
    workflow={
        "blocks": [
            {"type": "navigation", "url": "..."},
            {"type": "action", "goal": "..."},
            {"type": "extraction", "schema": {...}},
        ]
    }
)
# Planner creates comprehensive strategy
# Validator reviews entire plan
# Executor proceeds with approval
```

### 3. Error Recovery

```python
# Agents help recover from failures
# Executor encounters error
# Validator critiques the failure
# Planner creates alternative approach
# Coordinator requests consensus on recovery
```

## Monitoring and Debugging

### View Agent Messages

```python
from skyvern.forge.sdk.schemas.agent_messages import MessageType, AgentRole

# Filter by message type
thoughts = message_bus.get_message_history(
    filter=MessageFilter(message_type=MessageType.THOUGHT)
)

# Filter by agent role
planner_messages = message_bus.get_message_history(
    filter=MessageFilter(sender_role=AgentRole.PLANNER)
)

# Filter by task
task_messages = message_bus.get_message_history(
    filter=MessageFilter(task_id="task-123")
)
```

### Statistics and Insights

```python
stats = coordinator.get_statistics()

print(f"Enabled: {stats['enable_swarm']}")
print(f"Active agents: {len([a for a in stats['agents'].values() if a['active']])}")
print(f"Messages sent: {stats['message_bus']['messages_sent']}")
```

## Performance Considerations

### When to Use Multi-Agent Swarm

✅ **Use for:**
- High-risk operations (financial, legal, healthcare)
- Complex multi-step workflows
- Tasks requiring high reliability
- Production-critical automations

❌ **Skip for:**
- Simple navigation tasks
- High-throughput scraping
- Development/testing (unless specifically testing swarm)
- When latency is critical

### Performance Impact

The multi-agent swarm adds minimal overhead:
- ~50-100ms for planning coordination
- ~20-50ms per action validation
- Memory: ~10KB per 1000 messages

### Optimization Tips

1. **Use selective enabling**: Only enable for critical tasks
2. **Clear history**: Periodically clear message history
3. **Adjust history size**: Reduce if memory is constrained
4. **Single-agent fallback**: Keep fallback enabled

## Troubleshooting

### Swarm Not Activating

Check these settings:
```python
# Ensure one of these is true:
DEBUG_MODE=true
# OR
ENABLE_MULTI_AGENT_SWARM=true
```

### No Messages Appearing

Verify message bus is working:
```python
message_bus = get_message_bus()
stats = message_bus.get_statistics()
print(stats)  # Should show non-zero counts
```

### Performance Issues

Reduce message history:
```python
# Clear history periodically
message_bus.clear_history()

# Or reduce max size when creating bus
# (requires code modification)
```

## Advanced Usage

### Custom Agent Behavior

Extend base agents for custom logic:

```python
from skyvern.forge.sdk.core.multi_agent_swarm import ValidatorAgent

class CustomValidator(ValidatorAgent):
    async def validate_action(self, action_proposal):
        # Custom validation logic
        approved, mods = await super().validate_action(action_proposal)
        
        # Add custom checks
        if is_financial_field(action_proposal):
            approved = await double_check_financial_data()
            
        return approved, mods
```

### Custom Message Handlers

React to specific message types:

```python
def handle_error_message(message: AgentMessage):
    if message.message_type == MessageType.ERROR:
        # Send alert, log to external system, etc.
        notify_admin(message.content)

message_bus.add_message_handler(handle_error_message)
```

### Consensus Building

Request agent consensus on decisions:

```python
options = [
    {"action": "proceed", "risk": "low"},
    {"action": "skip", "risk": "high"},
]

selected = await coordinator.request_consensus(
    "Should we proceed with this action?",
    options
)
```

## Testing

### Unit Tests

```bash
# Run multi-agent swarm tests
pytest tests/unit_tests/test_multi_agent_swarm.py -v

# Run integration tests
pytest tests/unit_tests/test_agent_swarm_integration.py -v
```

### Manual Testing

```python
# Test coordination manually
from skyvern.forge.sdk.core.agent_message_bus import reset_message_bus

# Reset for clean test
reset_message_bus()

# Run your test
coordinator = AgentSwarmCoordinator(...)
await coordinator.start()
# ... test logic ...
await coordinator.stop()

# Verify messages
history = coordinator.get_message_history()
assert len(history) > 0
```

## Next Steps

- Read the full documentation: [MULTI_AGENT_SWARM.md](../MULTI_AGENT_SWARM.md)
- Explore API endpoints: [Agent Swarm API](../skyvern/forge/sdk/routes/agent_swarm.py)
- Review message schemas: [Agent Messages](../skyvern/forge/sdk/schemas/agent_messages.py)
- Check out examples: [Integration Tests](../tests/unit_tests/test_agent_swarm_integration.py)

## Support

For issues or questions:
- GitHub Issues: [Report a bug](https://github.com/skyvern-ai/skyvern/issues)
- Documentation: [Full docs](https://docs.skyvern.com)
- Community: [Join discussions](https://github.com/skyvern-ai/skyvern/discussions)
