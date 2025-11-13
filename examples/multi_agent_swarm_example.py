"""
Example demonstrating multi-agent swarm coordination in Skyvern.

This example shows how the planner, executor, and validator agents
coordinate to execute a complex form-filling task safely.
"""

import asyncio
from datetime import datetime
from unittest.mock import MagicMock

from skyvern.forge.sdk.core.multi_agent_swarm import AgentSwarmCoordinator
from skyvern.forge.sdk.models import Step, StepStatus
from skyvern.forge.sdk.schemas.agent_messages import MessageType, AgentRole
from skyvern.forge.sdk.schemas.tasks import Task, TaskStatus
from skyvern.webeye.actions.actions import Action
from skyvern.webeye.scraper.scraper import ScrapedPage


async def example_multi_agent_task():
    """
    Example of multi-agent coordination for a high-stakes task.
    
    Scenario: Filling out a financial transfer form
    - Planner analyzes the form and creates a safe execution plan
    - Validator checks each field for risks (SSN, account numbers, amounts)
    - Executor only proceeds with validator approval
    """
    
    # Create a mock task representing a financial transfer
    task = Task(
        task_id="financial-transfer-123",
        organization_id="example-org",
        url="https://bank.example.com/transfer",
        navigation_goal="Transfer $5,000 from checking to savings",
        status=TaskStatus.running,
        created_at=datetime.now(),
        modified_at=datetime.now(),
    )
    
    step = Step(
        step_id="step-1",
        task_id=task.task_id,
        organization_id=task.organization_id,
        order=0,
        retry_index=0,
        status=StepStatus.running,
        created_at=datetime.now(),
        modified_at=datetime.now(),
    )
    
    # Mock browser state
    browser_state = MagicMock()
    
    # Create the agent swarm coordinator
    print("🤖 Initializing multi-agent swarm...")
    coordinator = AgentSwarmCoordinator(
        task=task,
        step=step,
        browser_state=browser_state,
        enable_swarm=True,
    )
    
    # Start the agents
    await coordinator.start()
    print("✅ Agents started: Planner, Executor, Validator\n")
    
    # Mock scraped page with form fields
    scraped_page = ScrapedPage(
        url=task.url,
        html="""
        <form>
            <input name="from_account" placeholder="From Account" />
            <input name="to_account" placeholder="To Account" />
            <input name="amount" placeholder="Amount" />
            <input name="ssn" placeholder="SSN for verification" />
            <button type="submit">Transfer</button>
        </form>
        """,
        elements=[],
        id_to_css_dict={},
        id_to_element_dict={},
        screenshots=[],
    )
    
    # Simulate LLM proposing actions
    proposed_actions: list[Action] = []  # Would contain actual actions
    
    print("📋 Phase 1: Planning")
    print("-" * 50)
    
    # Planner creates a plan
    print("🧠 Planner: Analyzing form and creating execution plan...")
    filtered_actions, plan_approved = await coordinator.coordinate_planning(
        scraped_page, proposed_actions
    )
    
    print(f"📝 Planner: Created plan with {len(filtered_actions)} actions")
    print(f"✓ Validator: Plan reviewed - {'APPROVED' if plan_approved else 'REJECTED'}")
    print()
    
    # Get and display planning messages
    messages = coordinator.get_message_history()
    planning_messages = [m for m in messages if m.message_type in [MessageType.THOUGHT, MessageType.PLAN]]
    
    print("💭 Planning Messages:")
    for msg in planning_messages:
        print(f"  [{msg.sender_role}] {msg.message_type}: {list(msg.content.keys())}")
    print()
    
    print("🎯 Phase 2: Action Execution")
    print("-" * 50)
    
    # Simulate action execution with validation
    if filtered_actions and plan_approved:
        for idx, action in enumerate(filtered_actions[:3]):  # First 3 actions
            print(f"\n⚡ Executing action {idx + 1}...")
            
            # Executor proposes action
            approved, modifications = await coordinator.coordinate_action_execution(action, idx)
            
            if approved:
                print(f"  ✅ Validator: Action {idx + 1} APPROVED")
                print(f"  🎬 Executor: Executing action...")
                # In real scenario: await ActionHandler.handle_action(...)
            else:
                print(f"  ⚠️  Validator: Action {idx + 1} REJECTED")
                print(f"  🛑 Executor: Skipping risky action")
    
    # Display execution messages
    execution_messages = [m for m in messages if m.message_type in [
        MessageType.ACTION_PROPOSAL, 
        MessageType.ACTION_APPROVAL,
        MessageType.ACTION_REJECTION
    ]]
    
    if execution_messages:
        print("\n🔄 Execution Messages:")
        for msg in execution_messages:
            print(f"  [{msg.sender_role}] {msg.message_type}")
    
    print("\n" + "=" * 50)
    print("📊 Coordination Statistics")
    print("=" * 50)
    
    # Get statistics
    stats = coordinator.get_statistics()
    
    print(f"Multi-agent swarm: {'ENABLED' if stats['enable_swarm'] else 'DISABLED'}")
    print(f"\nActive Agents:")
    for agent_type, agent_info in stats['agents'].items():
        status = "🟢 Active" if agent_info['active'] else "🔴 Inactive"
        print(f"  {agent_type.capitalize()}: {status}")
    
    print(f"\nMessage Bus:")
    print(f"  Total messages: {stats['message_bus']['messages_sent']}")
    print(f"  Subscribers: {stats['message_bus']['subscribers_count']}")
    print(f"  History size: {stats['message_bus']['history_size']}")
    
    # Display message breakdown
    print("\n📨 Message Breakdown:")
    message_counts = {}
    for msg in messages:
        msg_type = msg.message_type.value
        message_counts[msg_type] = message_counts.get(msg_type, 0) + 1
    
    for msg_type, count in sorted(message_counts.items()):
        print(f"  {msg_type}: {count}")
    
    # Stop the agents
    print("\n🛑 Stopping agents...")
    await coordinator.stop()
    print("✅ All agents stopped\n")


async def example_single_agent_fallback():
    """
    Example showing fallback to single-agent mode.
    
    When multi-agent swarm is disabled, the system falls back
    to single-agent mode for compatibility.
    """
    
    print("\n" + "=" * 50)
    print("Single-Agent Fallback Example")
    print("=" * 50 + "\n")
    
    # Create task and step
    task = Task(
        task_id="simple-task-456",
        organization_id="example-org",
        url="https://example.com",
        navigation_goal="Simple navigation task",
        status=TaskStatus.running,
        created_at=datetime.now(),
        modified_at=datetime.now(),
    )
    
    step = Step(
        step_id="step-1",
        task_id=task.task_id,
        organization_id=task.organization_id,
        order=0,
        retry_index=0,
        status=StepStatus.running,
        created_at=datetime.now(),
        modified_at=datetime.now(),
    )
    
    browser_state = MagicMock()
    
    # Coordinator with swarm disabled
    print("🤖 Initializing with swarm DISABLED...")
    coordinator = AgentSwarmCoordinator(
        task=task,
        step=step,
        browser_state=browser_state,
        enable_swarm=False,  # Disabled
    )
    
    await coordinator.start()
    
    scraped_page = ScrapedPage(
        url=task.url,
        html="<html><body>Simple page</body></html>",
        elements=[],
        id_to_css_dict={},
        id_to_element_dict={},
        screenshots=[],
    )
    
    proposed_actions: list[Action] = []
    
    print("⚡ Executing in single-agent mode...")
    filtered_actions, plan_approved = await coordinator.coordinate_planning(
        scraped_page, proposed_actions
    )
    
    print(f"✅ Actions: {len(filtered_actions)}")
    print(f"✅ Auto-approved: {plan_approved}")
    print(f"📊 Messages generated: {len(coordinator.get_message_history())}")
    
    print("\n💡 Note: In single-agent mode, coordination is skipped for performance")
    
    await coordinator.stop()


async def main():
    """Run all examples."""
    print("=" * 50)
    print("Multi-Agent Swarm Examples")
    print("=" * 50 + "\n")
    
    # Example 1: Multi-agent coordination
    await example_multi_agent_task()
    
    # Example 2: Single-agent fallback
    await example_single_agent_fallback()
    
    print("\n" + "=" * 50)
    print("Examples Complete!")
    print("=" * 50)
    print("\nNext steps:")
    print("1. Enable multi-agent swarm: ENABLE_MULTI_AGENT_SWARM=true")
    print("2. View agent messages: GET /v1/agent-swarm/messages")
    print("3. Monitor in UI: Add AgentSwarmVisualization component")
    print("4. Read docs: MULTI_AGENT_SWARM.md")


if __name__ == "__main__":
    asyncio.run(main())
