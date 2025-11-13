"""
Unit tests for multi-agent swarm functionality.
"""

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from skyvern.forge.sdk.core.agent_message_bus import AgentMessageBus, get_message_bus, reset_message_bus
from skyvern.forge.sdk.core.multi_agent_swarm import (
    AgentSwarmCoordinator,
    BaseAgent,
    ExecutorAgent,
    PlannerAgent,
    ValidatorAgent,
)
from skyvern.forge.sdk.models import Step, StepStatus
from skyvern.forge.sdk.schemas.agent_messages import (
    ActionProposalMessage,
    AgentMessage,
    AgentRole,
    MessageFilter,
    MessageType,
    PlanMessage,
    ThoughtMessage,
)
from skyvern.forge.sdk.schemas.tasks import Task, TaskStatus
from skyvern.webeye.actions.actions import Action
from skyvern.webeye.scraper.scraper import ScrapedPage


@pytest.fixture
def message_bus() -> AgentMessageBus:
    """Create a fresh message bus for each test."""
    reset_message_bus()
    return get_message_bus()


@pytest.fixture
def mock_task() -> Task:
    """Create a mock task for testing."""
    return Task(
        task_id="test-task-123",
        organization_id="test-org",
        url="https://example.com",
        navigation_goal="Test navigation goal",
        status=TaskStatus.running,
        created_at=datetime.now(),
        modified_at=datetime.now(),
    )


@pytest.fixture
def mock_step() -> Step:
    """Create a mock step for testing."""
    return Step(
        step_id="test-step-123",
        task_id="test-task-123",
        organization_id="test-org",
        order=0,
        retry_index=0,
        status=StepStatus.running,
        created_at=datetime.now(),
        modified_at=datetime.now(),
    )


@pytest.fixture
def mock_browser_state() -> MagicMock:
    """Create a mock browser state."""
    return MagicMock()


@pytest.fixture
def mock_scraped_page() -> ScrapedPage:
    """Create a mock scraped page."""
    return ScrapedPage(
        url="https://example.com",
        html="<html><body>Test</body></html>",
        elements=[],
        id_to_css_dict={},
        id_to_element_dict={},
        screenshots=[],
    )


class TestAgentMessageBus:
    """Test cases for AgentMessageBus."""

    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self, message_bus: AgentMessageBus) -> None:
        """Test basic publish and subscribe functionality."""
        # Subscribe to messages
        queue = await message_bus.subscribe(agent_id="test-agent", role=AgentRole.PLANNER)

        # Publish a message
        message = AgentMessage(
            message_id="msg-1",
            sender_role=AgentRole.COORDINATOR,
            sender_id="coordinator-1",
            recipient_id="test-agent",
            message_type=MessageType.THOUGHT,
            content={"thought": "Test thought"},
        )
        await message_bus.publish(message)

        # Receive the message
        received = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received.message_id == "msg-1"
        assert received.message_type == MessageType.THOUGHT

    @pytest.mark.asyncio
    async def test_role_based_subscription(self, message_bus: AgentMessageBus) -> None:
        """Test role-based message subscription."""
        # Subscribe by role
        queue = await message_bus.subscribe(role=AgentRole.PLANNER)

        # Publish message to role
        message = AgentMessage(
            message_id="msg-2",
            sender_role=AgentRole.COORDINATOR,
            sender_id="coordinator-1",
            recipient_role=AgentRole.PLANNER,
            message_type=MessageType.PLAN,
            content={"plan": "Test plan"},
        )
        await message_bus.publish(message)

        # Receive the message
        received = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received.message_id == "msg-2"
        assert received.recipient_role == AgentRole.PLANNER

    @pytest.mark.asyncio
    async def test_message_type_subscription(self, message_bus: AgentMessageBus) -> None:
        """Test message type-based subscription."""
        # Subscribe to specific message type
        queue = await message_bus.subscribe(message_type=MessageType.ACTION_PROPOSAL)

        # Publish message of that type
        message = AgentMessage(
            message_id="msg-3",
            sender_role=AgentRole.EXECUTOR,
            sender_id="executor-1",
            message_type=MessageType.ACTION_PROPOSAL,
            content={"action": "Test action"},
        )
        await message_bus.publish(message)

        # Receive the message
        received = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received.message_type == MessageType.ACTION_PROPOSAL

    @pytest.mark.asyncio
    async def test_broadcast_subscription(self, message_bus: AgentMessageBus) -> None:
        """Test broadcast subscription."""
        # Subscribe to all messages
        queue = await message_bus.subscribe(broadcast=True)

        # Publish a message
        message = AgentMessage(
            message_id="msg-4",
            sender_role=AgentRole.COORDINATOR,
            sender_id="coordinator-1",
            message_type=MessageType.STATUS_UPDATE,
            content={"status": "Test status"},
        )
        await message_bus.publish(message)

        # Receive the message
        received = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received.message_id == "msg-4"

    def test_message_history(self, message_bus: AgentMessageBus) -> None:
        """Test message history storage and retrieval."""
        # The publish method is async, so we need to run it
        async def publish_messages():
            for i in range(5):
                message = AgentMessage(
                    message_id=f"msg-{i}",
                    sender_role=AgentRole.PLANNER,
                    sender_id="planner-1",
                    message_type=MessageType.THOUGHT,
                    content={"thought": f"Thought {i}"},
                )
                await message_bus.publish(message)

        asyncio.run(publish_messages())

        # Get history
        history = message_bus.get_message_history()
        assert len(history) == 5

    def test_message_filtering(self, message_bus: AgentMessageBus) -> None:
        """Test message filtering."""

        async def publish_messages():
            # Publish messages with different attributes
            await message_bus.publish(
                AgentMessage(
                    message_id="msg-1",
                    sender_role=AgentRole.PLANNER,
                    sender_id="planner-1",
                    message_type=MessageType.THOUGHT,
                    content={},
                    task_id="task-1",
                )
            )
            await message_bus.publish(
                AgentMessage(
                    message_id="msg-2",
                    sender_role=AgentRole.EXECUTOR,
                    sender_id="executor-1",
                    message_type=MessageType.ACTION_PROPOSAL,
                    content={},
                    task_id="task-2",
                )
            )

        asyncio.run(publish_messages())

        # Filter by sender role
        filter_by_role = MessageFilter(sender_role=AgentRole.PLANNER)
        filtered = message_bus.get_message_history(filter=filter_by_role)
        assert len(filtered) == 1
        assert filtered[0].sender_role == AgentRole.PLANNER

        # Filter by task ID
        filter_by_task = MessageFilter(task_id="task-2")
        filtered = message_bus.get_message_history(filter=filter_by_task)
        assert len(filtered) == 1
        assert filtered[0].task_id == "task-2"

    def test_statistics(self, message_bus: AgentMessageBus) -> None:
        """Test message bus statistics."""
        stats = message_bus.get_statistics()
        assert "messages_sent" in stats
        assert "subscribers_count" in stats
        assert "history_size" in stats


class TestBaseAgent:
    """Test cases for BaseAgent."""

    @pytest.mark.asyncio
    async def test_agent_start_stop(self, message_bus: AgentMessageBus) -> None:
        """Test agent start and stop lifecycle."""
        agent = BaseAgent(
            agent_id="test-agent-1",
            role=AgentRole.PLANNER,
            message_bus=message_bus,
            task_id="task-1",
        )

        assert not agent.active

        await agent.start()
        assert agent.active
        assert agent._message_queue is not None

        await agent.stop()
        assert not agent.active

    @pytest.mark.asyncio
    async def test_agent_send_message(self, message_bus: AgentMessageBus) -> None:
        """Test agent sending messages."""
        agent = BaseAgent(
            agent_id="test-agent-1",
            role=AgentRole.PLANNER,
            message_bus=message_bus,
        )

        # Send a message
        message_id = await agent.send_message(
            MessageType.THOUGHT,
            content={"thought": "Test thought"},
            recipient_role=AgentRole.EXECUTOR,
        )

        assert message_id is not None

        # Verify message was published
        history = message_bus.get_message_history()
        assert len(history) == 1
        assert history[0].message_id == message_id

    @pytest.mark.asyncio
    async def test_agent_receive_message(self, message_bus: AgentMessageBus) -> None:
        """Test agent receiving messages."""
        agent = BaseAgent(
            agent_id="test-agent-1",
            role=AgentRole.PLANNER,
            message_bus=message_bus,
        )

        await agent.start()

        # Send a message to the agent
        message = AgentMessage(
            message_id="msg-1",
            sender_role=AgentRole.COORDINATOR,
            sender_id="coordinator-1",
            recipient_id="test-agent-1",
            message_type=MessageType.STATUS_UPDATE,
            content={"status": "active"},
        )
        await message_bus.publish(message)

        # Receive the message
        received = await agent.receive_message(timeout=1.0)
        assert received is not None
        assert received.message_id == "msg-1"

        await agent.stop()


class TestPlannerAgent:
    """Test cases for PlannerAgent."""

    @pytest.mark.asyncio
    async def test_planner_create_plan(
        self, message_bus: AgentMessageBus, mock_task: Task, mock_step: Step, mock_scraped_page: ScrapedPage
    ) -> None:
        """Test planner creating a plan."""
        planner = PlannerAgent(
            agent_id="planner-1",
            message_bus=message_bus,
            task=mock_task,
            step=mock_step,
        )

        await planner.start()

        # Create mock actions
        actions: list[Action] = []  # Empty list for simplicity

        # Create plan
        filtered_actions, plan = await planner.create_plan(mock_scraped_page, actions)

        assert filtered_actions == actions
        assert isinstance(plan, PlanMessage)
        assert plan.risk_level in ["low", "medium", "high"]

        # Check that messages were sent
        history = message_bus.get_message_history()
        assert len(history) >= 2  # At least thought and plan messages

        await planner.stop()


class TestExecutorAgent:
    """Test cases for ExecutorAgent."""

    @pytest.mark.asyncio
    async def test_executor_propose_action(
        self,
        message_bus: AgentMessageBus,
        mock_task: Task,
        mock_step: Step,
        mock_browser_state: MagicMock,
    ) -> None:
        """Test executor proposing an action."""
        executor = ExecutorAgent(
            agent_id="executor-1",
            message_bus=message_bus,
            task=mock_task,
            step=mock_step,
            browser_state=mock_browser_state,
        )

        await executor.start()

        # Create a mock action
        mock_action = MagicMock(spec=Action)
        mock_action.action_type = MagicMock(value="click")
        mock_action.model_dump = MagicMock(return_value={})

        # Propose action
        message_id = await executor.propose_action_execution(mock_action, 0)

        assert message_id is not None

        # Verify message was sent
        history = message_bus.get_message_history()
        assert len(history) == 1
        assert history[0].message_type == MessageType.ACTION_PROPOSAL

        await executor.stop()


class TestValidatorAgent:
    """Test cases for ValidatorAgent."""

    @pytest.mark.asyncio
    async def test_validator_validate_plan(
        self, message_bus: AgentMessageBus, mock_task: Task, mock_step: Step
    ) -> None:
        """Test validator validating a plan."""
        validator = ValidatorAgent(
            agent_id="validator-1",
            message_bus=message_bus,
            task=mock_task,
            step=mock_step,
        )

        await validator.start()

        # Create a plan message
        plan = PlanMessage(
            plan_description="Test plan",
            steps=[{"action": "test"}],
            expected_outcome="Success",
            risk_level="low",
        )

        plan_message = AgentMessage(
            message_id="plan-1",
            sender_role=AgentRole.PLANNER,
            sender_id="planner-1",
            recipient_role=AgentRole.VALIDATOR,
            message_type=MessageType.PLAN,
            content=plan.model_dump(),
        )

        # Validate plan
        is_valid = await validator.validate_plan(plan_message)

        assert isinstance(is_valid, bool)

        # Check that validation messages were sent
        history = message_bus.get_message_history()
        assert len(history) >= 2  # Validation request and result

        await validator.stop()

    @pytest.mark.asyncio
    async def test_validator_validate_action(
        self, message_bus: AgentMessageBus, mock_task: Task, mock_step: Step
    ) -> None:
        """Test validator validating an action."""
        validator = ValidatorAgent(
            agent_id="validator-1",
            message_bus=message_bus,
            task=mock_task,
            step=mock_step,
        )

        await validator.start()

        # Create an action proposal
        proposal = ActionProposalMessage(
            action_type="click",
            action_data={},
            rationale="Test action",
            risk_assessment="low",
            confidence=0.9,
        )

        proposal_message = AgentMessage(
            message_id="proposal-1",
            sender_role=AgentRole.EXECUTOR,
            sender_id="executor-1",
            recipient_role=AgentRole.VALIDATOR,
            message_type=MessageType.ACTION_PROPOSAL,
            content=proposal.model_dump(),
        )

        # Validate action
        approved, modifications = await validator.validate_action(proposal_message)

        assert isinstance(approved, bool)
        assert isinstance(modifications, dict)

        await validator.stop()


class TestAgentSwarmCoordinator:
    """Test cases for AgentSwarmCoordinator."""

    @pytest.mark.asyncio
    async def test_coordinator_initialization(
        self, mock_task: Task, mock_step: Step, mock_browser_state: MagicMock
    ) -> None:
        """Test coordinator initialization."""
        coordinator = AgentSwarmCoordinator(
            task=mock_task,
            step=mock_step,
            browser_state=mock_browser_state,
            enable_swarm=True,
        )

        assert coordinator.planner is not None
        assert coordinator.executor is not None
        assert coordinator.validator is not None
        assert coordinator.message_bus is not None

    @pytest.mark.asyncio
    async def test_coordinator_start_stop(
        self, mock_task: Task, mock_step: Step, mock_browser_state: MagicMock
    ) -> None:
        """Test coordinator start and stop."""
        coordinator = AgentSwarmCoordinator(
            task=mock_task,
            step=mock_step,
            browser_state=mock_browser_state,
            enable_swarm=True,
        )

        await coordinator.start()

        assert coordinator.planner.active
        assert coordinator.executor.active
        assert coordinator.validator.active

        await coordinator.stop()

        assert not coordinator.planner.active
        assert not coordinator.executor.active
        assert not coordinator.validator.active

    @pytest.mark.asyncio
    async def test_coordinator_single_agent_fallback(
        self, mock_task: Task, mock_step: Step, mock_browser_state: MagicMock, mock_scraped_page: ScrapedPage
    ) -> None:
        """Test coordinator fallback to single-agent mode."""
        coordinator = AgentSwarmCoordinator(
            task=mock_task,
            step=mock_step,
            browser_state=mock_browser_state,
            enable_swarm=False,  # Disable swarm
        )

        await coordinator.start()

        # Should skip coordination in single-agent mode
        actions: list[Action] = []
        filtered_actions, plan_approved = await coordinator.coordinate_planning(mock_scraped_page, actions)

        assert filtered_actions == actions
        assert plan_approved is True  # Always true in single-agent mode

        await coordinator.stop()

    @pytest.mark.asyncio
    async def test_coordinator_get_message_history(
        self, mock_task: Task, mock_step: Step, mock_browser_state: MagicMock
    ) -> None:
        """Test getting message history from coordinator."""
        coordinator = AgentSwarmCoordinator(
            task=mock_task,
            step=mock_step,
            browser_state=mock_browser_state,
            enable_swarm=True,
        )

        await coordinator.start()

        # Generate some messages
        await coordinator.planner.send_message(
            MessageType.THOUGHT,
            content={"thought": "Test"},
        )

        history = coordinator.get_message_history()
        assert len(history) >= 1  # At least the status update and thought messages

        await coordinator.stop()

    def test_coordinator_get_statistics(
        self, mock_task: Task, mock_step: Step, mock_browser_state: MagicMock
    ) -> None:
        """Test getting swarm statistics."""
        coordinator = AgentSwarmCoordinator(
            task=mock_task,
            step=mock_step,
            browser_state=mock_browser_state,
            enable_swarm=True,
        )

        stats = coordinator.get_statistics()

        assert "enable_swarm" in stats
        assert "agents" in stats
        assert "message_bus" in stats
        assert "planner" in stats["agents"]
        assert "executor" in stats["agents"]
        assert "validator" in stats["agents"]
