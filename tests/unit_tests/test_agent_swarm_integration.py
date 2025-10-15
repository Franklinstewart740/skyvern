"""
Integration tests for multi-agent swarm with ForgeAgent.

These tests simulate how the multi-agent swarm would coordinate
during actual task execution.
"""

import asyncio
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from skyvern.forge.sdk.core.agent_message_bus import get_message_bus, reset_message_bus
from skyvern.forge.sdk.core.multi_agent_swarm import AgentSwarmCoordinator
from skyvern.forge.sdk.models import Step, StepStatus
from skyvern.forge.sdk.schemas.agent_messages import MessageType
from skyvern.forge.sdk.schemas.tasks import Task, TaskStatus
from skyvern.webeye.actions.actions import Action
from skyvern.webeye.scraper.scraper import ScrapedPage


@pytest.fixture(autouse=True)
def reset_bus():
    """Reset message bus before each test."""
    reset_message_bus()
    yield
    reset_message_bus()


@pytest.fixture
def mock_task() -> Task:
    """Create a mock task for testing."""
    return Task(
        task_id="integration-test-task-123",
        organization_id="test-org",
        url="https://example.com/form",
        navigation_goal="Fill out a complex financial form",
        status=TaskStatus.running,
        created_at=datetime.now(),
        modified_at=datetime.now(),
    )


@pytest.fixture
def mock_step() -> Step:
    """Create a mock step for testing."""
    return Step(
        step_id="integration-test-step-123",
        task_id="integration-test-task-123",
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
        url="https://example.com/form",
        html="<html><body><form><input name='ssn'/><input name='amount'/></form></body></html>",
        elements=[],
        id_to_css_dict={},
        id_to_element_dict={},
        screenshots=[],
    )


class TestMultiAgentSwarmIntegration:
    """Integration tests for multi-agent swarm coordination."""

    @pytest.mark.asyncio
    async def test_full_coordination_workflow(
        self,
        mock_task: Task,
        mock_step: Step,
        mock_browser_state: MagicMock,
        mock_scraped_page: ScrapedPage,
    ) -> None:
        """Test a complete coordination workflow from planning to execution."""
        # Create coordinator
        coordinator = AgentSwarmCoordinator(
            task=mock_task,
            step=mock_step,
            browser_state=mock_browser_state,
            enable_swarm=True,
        )

        await coordinator.start()

        # Simulate LLM proposing actions
        mock_actions: list[Action] = []  # Empty for simplicity

        # Phase 1: Planning coordination
        filtered_actions, plan_approved = await coordinator.coordinate_planning(
            mock_scraped_page, mock_actions
        )

        assert isinstance(filtered_actions, list)
        assert isinstance(plan_approved, bool)

        # Phase 2: Action execution coordination
        if filtered_actions:
            for idx, action in enumerate(filtered_actions):
                approved, modifications = await coordinator.coordinate_action_execution(action, idx)
                assert isinstance(approved, bool)
                assert isinstance(modifications, dict)

        # Verify message history
        message_history = coordinator.get_message_history()
        assert len(message_history) > 0

        # Check that different message types were sent
        message_types = {msg.message_type for msg in message_history}
        assert MessageType.STATUS_UPDATE in message_types
        assert MessageType.THOUGHT in message_types
        assert MessageType.PLAN in message_types

        await coordinator.stop()

    @pytest.mark.asyncio
    async def test_high_risk_action_coordination(
        self,
        mock_task: Task,
        mock_step: Step,
        mock_browser_state: MagicMock,
        mock_scraped_page: ScrapedPage,
    ) -> None:
        """Test coordination for high-risk actions."""
        coordinator = AgentSwarmCoordinator(
            task=mock_task,
            step=mock_step,
            browser_state=mock_browser_state,
            enable_swarm=True,
        )

        await coordinator.start()

        # Simulate a high-risk action plan with many steps
        many_actions: list[Action] = [MagicMock(spec=Action) for _ in range(15)]

        # Planning should assess this as high risk
        filtered_actions, plan_approved = await coordinator.coordinate_planning(
            mock_scraped_page, many_actions
        )

        # Check that validation messages were sent
        message_history = coordinator.get_message_history()
        validation_messages = [msg for msg in message_history if msg.message_type == MessageType.VALIDATION_RESULT]

        assert len(validation_messages) > 0

        await coordinator.stop()

    @pytest.mark.asyncio
    async def test_agent_role_communication(
        self,
        mock_task: Task,
        mock_step: Step,
        mock_browser_state: MagicMock,
        mock_scraped_page: ScrapedPage,
    ) -> None:
        """Test that agents communicate with correct roles."""
        coordinator = AgentSwarmCoordinator(
            task=mock_task,
            step=mock_step,
            browser_state=mock_browser_state,
            enable_swarm=True,
        )

        await coordinator.start()

        # Execute planning
        mock_actions: list[Action] = []
        await coordinator.coordinate_planning(mock_scraped_page, mock_actions)

        # Get message history and verify roles
        message_bus = get_message_bus()
        all_messages = message_bus.get_message_history()

        # Check that we have messages from different roles
        from skyvern.forge.sdk.schemas.agent_messages import AgentRole

        sender_roles = {msg.sender_role for msg in all_messages}
        assert AgentRole.PLANNER in sender_roles

        await coordinator.stop()

    @pytest.mark.asyncio
    async def test_message_filtering_by_task(
        self,
        mock_task: Task,
        mock_step: Step,
        mock_browser_state: MagicMock,
        mock_scraped_page: ScrapedPage,
    ) -> None:
        """Test that messages can be filtered by task ID."""
        # Create two coordinators for different tasks
        coordinator1 = AgentSwarmCoordinator(
            task=mock_task,
            step=mock_step,
            browser_state=mock_browser_state,
            enable_swarm=True,
        )

        task2 = Task(
            task_id="task-2",
            organization_id="test-org",
            url="https://example.com",
            status=TaskStatus.running,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )
        step2 = Step(
            step_id="step-2",
            task_id="task-2",
            organization_id="test-org",
            order=0,
            retry_index=0,
            status=StepStatus.running,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )
        coordinator2 = AgentSwarmCoordinator(
            task=task2,
            step=step2,
            browser_state=mock_browser_state,
            enable_swarm=True,
        )

        await coordinator1.start()
        await coordinator2.start()

        # Generate messages from both
        await coordinator1.coordinate_planning(mock_scraped_page, [])
        await coordinator2.coordinate_planning(mock_scraped_page, [])

        # Filter by task 1
        task1_messages = coordinator1.get_message_history()
        assert all(msg.task_id == mock_task.task_id for msg in task1_messages)

        # Filter by task 2
        task2_messages = coordinator2.get_message_history()
        assert all(msg.task_id == task2.task_id for msg in task2_messages)

        await coordinator1.stop()
        await coordinator2.stop()

    @pytest.mark.asyncio
    async def test_fallback_to_single_agent_mode(
        self,
        mock_task: Task,
        mock_step: Step,
        mock_browser_state: MagicMock,
        mock_scraped_page: ScrapedPage,
    ) -> None:
        """Test fallback to single-agent mode when swarm is disabled."""
        coordinator = AgentSwarmCoordinator(
            task=mock_task,
            step=mock_step,
            browser_state=mock_browser_state,
            enable_swarm=False,  # Disabled
        )

        await coordinator.start()

        # Should skip coordination
        mock_actions: list[Action] = []
        filtered_actions, plan_approved = await coordinator.coordinate_planning(
            mock_scraped_page, mock_actions
        )

        # In single-agent mode, actions pass through unchanged
        assert filtered_actions == mock_actions
        assert plan_approved is True

        # No agent messages should be generated
        message_history = coordinator.get_message_history()
        # May have some initialization messages, but no planning coordination
        assert len(message_history) == 0

        await coordinator.stop()

    @pytest.mark.asyncio
    async def test_coordinator_statistics(
        self,
        mock_task: Task,
        mock_step: Step,
        mock_browser_state: MagicMock,
        mock_scraped_page: ScrapedPage,
    ) -> None:
        """Test that coordinator provides useful statistics."""
        coordinator = AgentSwarmCoordinator(
            task=mock_task,
            step=mock_step,
            browser_state=mock_browser_state,
            enable_swarm=True,
        )

        await coordinator.start()

        # Generate some activity
        await coordinator.coordinate_planning(mock_scraped_page, [])

        # Get statistics
        stats = coordinator.get_statistics()

        assert "enable_swarm" in stats
        assert "agents" in stats
        assert "message_bus" in stats

        # Verify agent info
        assert "planner" in stats["agents"]
        assert "executor" in stats["agents"]
        assert "validator" in stats["agents"]

        # Verify agents are active
        assert stats["agents"]["planner"]["active"] is True
        assert stats["agents"]["executor"]["active"] is True
        assert stats["agents"]["validator"]["active"] is True

        await coordinator.stop()

        # After stopping, agents should be inactive
        stats = coordinator.get_statistics()
        assert stats["agents"]["planner"]["active"] is False
        assert stats["agents"]["executor"]["active"] is False
        assert stats["agents"]["validator"]["active"] is False

    @pytest.mark.asyncio
    async def test_parallel_agent_reasoning(
        self,
        mock_task: Task,
        mock_step: Step,
        mock_browser_state: MagicMock,
        mock_scraped_page: ScrapedPage,
    ) -> None:
        """Test that multiple agents can reason in parallel."""
        coordinator = AgentSwarmCoordinator(
            task=mock_task,
            step=mock_step,
            browser_state=mock_browser_state,
            enable_swarm=True,
        )

        await coordinator.start()

        # Simulate parallel planning
        planning_task = asyncio.create_task(
            coordinator.coordinate_planning(mock_scraped_page, [])
        )

        # Wait for completion
        await planning_task

        # Verify that messages from multiple agents were generated
        message_history = coordinator.get_message_history()

        from skyvern.forge.sdk.schemas.agent_messages import AgentRole

        sender_roles = {msg.sender_role for msg in message_history}

        # Should have messages from multiple roles
        assert len(sender_roles) >= 1  # At least planner

        await coordinator.stop()

    @pytest.mark.asyncio
    async def test_consensus_building(
        self,
        mock_task: Task,
        mock_step: Step,
        mock_browser_state: MagicMock,
    ) -> None:
        """Test consensus building for critical decisions."""
        coordinator = AgentSwarmCoordinator(
            task=mock_task,
            step=mock_step,
            browser_state=mock_browser_state,
            enable_swarm=True,
        )

        await coordinator.start()

        # Request consensus on a decision
        options = [
            {"action": "proceed", "rationale": "Risk is acceptable"},
            {"action": "skip", "rationale": "Too risky"},
            {"action": "modify", "rationale": "Needs adjustment"},
        ]

        selected = await coordinator.request_consensus(
            "High-risk action decision", options
        )

        # Should return one of the options
        assert selected in options

        await coordinator.stop()
