# Multi-Agent Swarm Architecture

This document describes the multi-agent swarm system implemented in Skyvern, which enables coordinated browser automation through specialized agent roles.

## Overview

The multi-agent swarm architecture introduces three specialized agent roles that coordinate via an internal message bus to achieve more robust and reliable browser automation:

- **Planner Agent**: Analyzes the current state and creates execution plans
- **Executor Agent**: Executes actions on the browser
- **Validator Agent**: Validates plans and actions before execution

## Architecture Components

### 1. Agent Message Bus (`forge/sdk/core/agent_message_bus.py`)

The message bus provides a publish/subscribe pattern for agent-to-agent communication:

```python
from skyvern.forge.sdk.core.agent_message_bus import get_message_bus

message_bus = get_message_bus()

# Subscribe to messages
queue = await message_bus.subscribe(
    role=AgentRole.PLANNER,
    message_type=MessageType.ACTION_PROPOSAL
)

# Publish a message
await message_bus.publish(message)
```

**Features:**
- In-memory message storage with configurable history size
- Multiple subscription patterns (by ID, role, message type, task ID)
- Broadcast messaging for coordination
- Message filtering and querying
- Statistics tracking

### 2. Agent Roles

#### Planner Agent
Responsible for creating action plans based on the current page state:

```python
planner = PlannerAgent(
    agent_id="planner-1",
    message_bus=message_bus,
    task=task,
    step=step
)

await planner.start()
filtered_actions, plan = await planner.create_plan(scraped_page, actions)
```

**Responsibilities:**
- Analyze scraped page content
- Filter and organize proposed actions
- Assess risk levels
- Send plan messages to validators
- Stream reasoning thoughts

#### Executor Agent
Executes approved actions on the browser:

```python
executor = ExecutorAgent(
    agent_id="executor-1",
    message_bus=message_bus,
    task=task,
    step=step,
    browser_state=browser_state
)

await executor.start()
message_id = await executor.propose_action_execution(action, action_index)
```

**Responsibilities:**
- Propose actions for validation
- Execute approved actions
- Report execution results
- Handle action failures

#### Validator Agent
Reviews and validates plans and actions:

```python
validator = ValidatorAgent(
    agent_id="validator-1",
    message_bus=message_bus,
    task=task,
    step=step
)

await validator.start()
is_valid = await validator.validate_plan(plan_message)
approved, modifications = await validator.validate_action(action_proposal)
```

**Responsibilities:**
- Validate action plans
- Approve or reject action proposals
- Assess risk levels
- Provide critiques and feedback
- Suggest modifications

### 3. Agent Swarm Coordinator

The coordinator manages the lifecycle of all agents and orchestrates their interactions:

```python
from skyvern.forge.sdk.core.multi_agent_swarm import AgentSwarmCoordinator

coordinator = AgentSwarmCoordinator(
    task=task,
    step=step,
    browser_state=browser_state,
    enable_swarm=True
)

await coordinator.start()

# Coordinate planning
filtered_actions, plan_approved = await coordinator.coordinate_planning(
    scraped_page, actions
)

# Coordinate action execution
approved, modifications = await coordinator.coordinate_action_execution(
    action, action_index
)

await coordinator.stop()
```

**Features:**
- Manages agent lifecycle (start/stop)
- Coordinates planning phase
- Coordinates action execution
- Consensus building for critical decisions
- Fallback to single-agent mode
- Message history and statistics

## Message Schema

The multi-agent system uses a comprehensive message schema defined in `forge/sdk/schemas/agent_messages.py`:

### Message Types

- `THOUGHT`: Agent's reasoning process
- `PLAN`: Proposed action plan
- `ACTION_PROPOSAL`: Proposed action for execution
- `ACTION_APPROVAL`: Approval/rejection of an action
- `EXECUTION_RESULT`: Result of action execution
- `VALIDATION_REQUEST`: Request for validation
- `VALIDATION_RESULT`: Result of validation
- `CRITIQUE`: Constructive feedback
- `CONSENSUS_REQUEST`: Request for consensus
- `CONSENSUS_RESPONSE`: Vote for consensus
- `ERROR`: Error information
- `STATUS_UPDATE`: Status update

### Example Message

```python
from skyvern.forge.sdk.schemas.agent_messages import (
    AgentMessage,
    MessageType,
    AgentRole,
    ThoughtMessage
)

message = AgentMessage(
    message_id="msg-123",
    sender_role=AgentRole.PLANNER,
    sender_id="planner-1",
    recipient_role=AgentRole.VALIDATOR,
    message_type=MessageType.THOUGHT,
    content=ThoughtMessage(
        thought="Analyzing page structure",
        confidence=0.85,
        reasoning_chain=["Step 1", "Step 2"],
        context={"page_url": "https://example.com"}
    ).model_dump(),
    task_id="task-123",
    step_id="step-456",
    priority=5
)
```

## API Endpoints

The multi-agent swarm exposes monitoring endpoints at `/agent-swarm`:

### Get Swarm Status
```bash
GET /agent-swarm/status
```

Returns:
```json
{
  "enabled": true,
  "message_bus_stats": {
    "messages_sent": 42,
    "messages_received": 40,
    "subscribers_count": 3,
    "history_size": 42
  }
}
```

### Get Agent Messages
```bash
GET /agent-swarm/messages?task_id=task-123&message_type=THOUGHT&limit=50
```

Query parameters:
- `task_id`: Filter by task ID
- `step_id`: Filter by step ID
- `sender_role`: Filter by sender role
- `recipient_role`: Filter by recipient role
- `message_type`: Filter by message type
- `from_timestamp`: Filter from timestamp
- `to_timestamp`: Filter to timestamp
- `min_priority`: Filter by minimum priority
- `limit`: Maximum number of messages (default: 100)

Returns:
```json
{
  "messages": [...],
  "total": 1000,
  "filtered": 50
}
```

### Get Task Messages
```bash
GET /agent-swarm/tasks/{task_id}/messages
```

Returns all messages for a specific task.

### Clear Message History
```bash
POST /agent-swarm/clear-history
```

Clears the message history (useful for testing).

## Configuration

The multi-agent swarm can be configured via environment variables:

```bash
# Enable multi-agent swarm (currently only enabled in DEBUG_MODE)
DEBUG_MODE=true
```

By default, the system falls back to single-agent mode when `enable_swarm=False`.

## Integration with Existing Agent

The multi-agent swarm is designed to integrate seamlessly with the existing `ForgeAgent`:

```python
# In agent_step method
coordinator = AgentSwarmCoordinator(
    task=task,
    step=step,
    browser_state=browser_state,
    enable_swarm=settings.DEBUG_MODE
)

await coordinator.start()

# Use coordinator for planning
filtered_actions, plan_approved = await coordinator.coordinate_planning(
    scraped_page, actions
)

# Execute actions with coordination
for action_idx, action in enumerate(filtered_actions):
    approved, modifications = await coordinator.coordinate_action_execution(
        action, action_idx
    )
    if approved:
        # Execute action
        results = await ActionHandler.handle_action(...)

await coordinator.stop()
```

## Testing

Comprehensive unit tests are provided in `tests/unit_tests/test_multi_agent_swarm.py`:

```bash
# Run multi-agent swarm tests
pytest tests/unit_tests/test_multi_agent_swarm.py -v
```

Test coverage includes:
- Message bus publish/subscribe
- Role-based and type-based subscriptions
- Message filtering and history
- Agent lifecycle (start/stop)
- Plan creation and validation
- Action proposal and approval
- Coordinator orchestration
- Single-agent fallback

## Future Enhancements

### Redis Backend
Currently uses in-memory message bus. Redis backend can be implemented for:
- Distributed agent coordination
- Persistent message history
- Cross-process communication

### LLM-Based Agents
Integrate LLM calls for:
- More sophisticated planning
- Better risk assessment
- Adaptive validation criteria
- Natural language critiques

### Advanced Consensus
Implement voting mechanisms:
- Weighted voting by confidence
- Majority/supermajority requirements
- Tie-breaking strategies

### Agent Learning
Add learning capabilities:
- Learn from successful/failed actions
- Adapt risk thresholds
- Improve plan quality over time

## Best Practices

1. **Enable for Complex Tasks**: Use multi-agent swarm for high-risk or complex tasks
2. **Monitor Messages**: Use API endpoints to monitor agent communications
3. **Set Appropriate Risk Levels**: Configure risk thresholds based on use case
4. **Fallback Strategy**: Always have single-agent fallback for reliability
5. **Message History Management**: Clear history periodically to prevent memory issues

## Example Use Cases

### 1. High-Stakes Form Submission
```python
coordinator = AgentSwarmCoordinator(
    task=financial_form_task,
    step=step,
    browser_state=browser_state,
    enable_swarm=True
)

# Planner analyzes form fields
# Validator checks for high-risk fields (SSN, credit card)
# Executor only proceeds with explicit approval
```

### 2. Multi-Step Workflow
```python
# Planner creates comprehensive multi-step plan
# Validator reviews entire plan before execution
# Executor executes steps one by one with validation
# Coordinator requests consensus for critical decisions
```

### 3. Error Recovery
```python
# Executor encounters error
# Validator critiques the failure
# Planner creates alternative plan
# Coordinator requests consensus on recovery strategy
```

## Troubleshooting

### Messages Not Received
- Check subscription filters
- Verify message routing (role, ID, type)
- Check message bus statistics

### Performance Issues
- Reduce message history size
- Use more specific subscriptions
- Consider Redis backend for large deployments

### Coordination Failures
- Check agent lifecycle (start/stop)
- Verify message types match expected types
- Review message content validation

## Contributing

When contributing to the multi-agent swarm:

1. Add tests for new agent behaviors
2. Document new message types in schemas
3. Update API documentation for new endpoints
4. Follow existing agent patterns
5. Maintain backward compatibility with single-agent mode

## References

- Agent Message Schema: `skyvern/forge/sdk/schemas/agent_messages.py`
- Message Bus: `skyvern/forge/sdk/core/agent_message_bus.py`
- Multi-Agent Swarm: `skyvern/forge/sdk/core/multi_agent_swarm.py`
- API Routes: `skyvern/forge/sdk/routes/agent_swarm.py`
- Tests: `tests/unit_tests/test_multi_agent_swarm.py`
