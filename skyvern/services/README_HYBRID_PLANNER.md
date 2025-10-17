# Hybrid Symbolic + LLM Planner

## Overview

The Hybrid Symbolic + LLM Planner introduces a validation layer that combines symbolic reasoning with LLM-generated plans. It evaluates LLM-proposed actions against structural rules, affordances, and guard conditions before execution.

## Architecture

### Core Components

1. **SymbolicPredicate**: Evaluable predicates against page state
   - Element existence, visibility, enabled state
   - URL pattern matching
   - Element text content checks
   - Custom predicates

2. **ActionAffordance**: Declares what actions are possible
   - Preconditions (predicates that must be true)
   - Postconditions (expected state after action)
   - Priority (for resolving conflicts)

3. **GuardCondition**: Blocks actions when conditions are met
   - Active when predicates evaluate to true
   - Blocks specific action types
   - Provides audit trail with messages

4. **HybridPlanner**: Main orchestrator
   - Validates LLM-generated actions
   - Filters actions based on constraints
   - Detects potential infinite loops
   - Provides fallback reconciliation
   - Exports audit logs

## Integration

### In Workflow Blocks

Add `symbolic_config` to any workflow block:

```json
{
  "label": "login_task",
  "block_type": "task",
  "symbolic_config": {
    "affordances": [
      {
        "action_type": "click",
        "element_id": "submit_btn",
        "preconditions": [
          {
            "predicate_type": "element_exists",
            "target": "submit_btn"
          },
          {
            "predicate_type": "element_visible",
            "target": "submit_btn"
          }
        ],
        "priority": 10
      }
    ],
    "guards": [
      {
        "name": "error_state",
        "predicates": [
          {
            "predicate_type": "element_exists",
            "target": "error_message"
          }
        ],
        "action_types_blocked": ["terminate"],
        "message": "Cannot terminate when error is present"
      }
    ]
  }
}
```

### In Agent Execution

The planner is automatically invoked in `ForgeAgent.agent_step()` when a block has `symbolic_config`:

1. LLM generates action plan
2. Hybrid planner validates against symbolic constraints
3. Invalid actions are filtered out
4. Valid actions proceed to execution
5. Audit log is created for debugging

## Use Cases

### 1. Prevent Invalid Actions

```python
# Guard against terminating on error pages
guard = GuardCondition(
    name="no_terminate_on_error",
    predicates=[
        SymbolicPredicate(
            predicate_type=PredicateType.ELEMENT_EXISTS,
            target="error_banner"
        )
    ],
    action_types_blocked=[ActionType.TERMINATE],
    message="Cannot terminate - error state detected"
)
```

### 2. Enforce Preconditions

```python
# Only allow form submission when all required fields are filled
affordance = ActionAffordance(
    action_type=ActionType.CLICK,
    element_id="submit_button",
    preconditions=[
        SymbolicPredicate(
            predicate_type=PredicateType.ELEMENT_EXISTS,
            target="name_input"
        ),
        SymbolicPredicate(
            predicate_type=PredicateType.ELEMENT_EXISTS,
            target="email_input"
        )
    ]
)
```

### 3. Loop Detection

The planner automatically detects repeating action sequences:

```python
planner = HybridPlanner()
planner.loop_detection_window = 5  # Check last 5 actions

# Will warn if same sequence repeats
validation_result = planner.validate_and_filter_actions(
    actions=actions,
    scraped_page=page,
    current_url=url,
    task=task
)

if validation_result.warnings:
    # Handle loop detection warning
    pass
```

### 4. Branching Logic

Use guards and affordances to implement branching:

```python
# Different actions based on page state
login_guard = GuardCondition(
    name="already_logged_in",
    predicates=[
        SymbolicPredicate(
            predicate_type=PredicateType.URL_PATTERN,
            target=r".*/dashboard"
        )
    ],
    action_types_blocked=[ActionType.INPUT_TEXT],  # Don't try to login again
    message="Already logged in"
)
```

### 5. Failure Recovery

Provide fallback actions when validation fails:

```python
validation_result = planner.validate_and_filter_actions(
    actions=llm_actions,
    scraped_page=page,
    current_url=url,
    task=task
)

# Define fallback actions if LLM plan is rejected
fallback_actions = [
    ClickAction(element_id="retry_button"),
    WaitAction(seconds=5)
]

final_actions = planner.reconcile_with_fallback(
    validation_result,
    fallback_actions
)
```

## Audit Trail

Every validation produces an audit log:

```python
audit_log = planner.export_audit_log(validation_result)
# Returns JSON with:
# - Validation results
# - Rejected actions with reasons
# - Active affordances and guards
# - Audit metadata
```

## Testing

Run unit tests:

```bash
pytest tests/unit_tests/services/test_hybrid_planner.py -v
```

Test coverage includes:
- Predicate evaluation
- Affordance precondition checking
- Guard blocking logic
- Loop detection
- Branching scenarios
- Failure recovery

## Best Practices

1. **Start Simple**: Add guards first, then affordances as needed
2. **Use Priorities**: Set affordance priorities to resolve conflicts
3. **Monitor Audit Logs**: Review rejected actions to tune constraints
4. **Test Branching**: Use scenario-based tests for complex workflows
5. **Fallback Actions**: Always provide fallback for critical paths

## Future Enhancements

- [ ] Temporal logic (predicates over time)
- [ ] Action sequence patterns (e.g., "always verify after submit")
- [ ] Learning from rejections (auto-tune constraints)
- [ ] Visual predicate builder UI
- [ ] Performance optimization for large page states
