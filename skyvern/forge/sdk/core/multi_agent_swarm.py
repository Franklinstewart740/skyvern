"""
Multi-Agent Swarm orchestration system.

This module implements a multi-agent system with separate roles (planner, executor, validator)
that coordinate through a message bus to solve complex automation tasks.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any

import structlog

from skyvern.config import settings
from skyvern.forge.sdk.core.agent_message_bus import AgentMessageBus, get_message_bus
from skyvern.forge.sdk.models import Step
from skyvern.forge.sdk.schemas.agent_messages import (
    ActionApprovalMessage,
    ActionProposalMessage,
    AgentMessage,
    AgentRole,
    ConsensusRequestMessage,
    ConsensusResponseMessage,
    CritiqueMessage,
    ErrorMessage,
    ExecutionResultMessage,
    MessageType,
    PlanMessage,
    StatusUpdateMessage,
    ThoughtMessage,
    ValidationRequestMessage,
    ValidationResultMessage,
)
from skyvern.forge.sdk.schemas.tasks import Task
from skyvern.webeye.actions.actions import Action
from skyvern.webeye.browser_factory import BrowserState
from skyvern.webeye.scraper.scraper import ScrapedPage

LOG = structlog.get_logger()


class BaseAgent:
    """Base class for all agents in the swarm."""

    def __init__(
        self,
        agent_id: str,
        role: AgentRole,
        message_bus: AgentMessageBus,
        task_id: str | None = None,
        step_id: str | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.role = role
        self.message_bus = message_bus
        self.task_id = task_id
        self.step_id = step_id
        self.active = False
        self._message_queue: asyncio.Queue | None = None

    async def start(self) -> None:
        """Start the agent and subscribe to messages."""
        self.active = True
        self._message_queue = await self.message_bus.subscribe(
            agent_id=self.agent_id,
            role=self.role,
            task_id=self.task_id,
        )
        LOG.info("Agent started", agent_id=self.agent_id, role=self.role)

    async def stop(self) -> None:
        """Stop the agent and unsubscribe from messages."""
        self.active = False
        if self._message_queue:
            await self.message_bus.unsubscribe(self._message_queue)
        LOG.info("Agent stopped", agent_id=self.agent_id, role=self.role)

    async def send_message(
        self,
        message_type: MessageType,
        content: dict[str, Any],
        recipient_role: AgentRole | None = None,
        recipient_id: str | None = None,
        priority: int = 0,
        requires_response: bool = False,
        in_response_to: str | None = None,
    ) -> str:
        """Send a message to other agents."""
        message_id = str(uuid.uuid4())
        message = AgentMessage(
            message_id=message_id,
            sender_role=self.role,
            sender_id=self.agent_id,
            recipient_role=recipient_role,
            recipient_id=recipient_id,
            message_type=message_type,
            content=content,
            task_id=self.task_id,
            step_id=self.step_id,
            priority=priority,
            requires_response=requires_response,
            in_response_to=in_response_to,
        )
        await self.message_bus.publish(message)
        return message_id

    async def receive_message(self, timeout: float | None = None) -> AgentMessage | None:
        """Receive a message from the queue."""
        if not self._message_queue:
            return None

        try:
            if timeout:
                message = await asyncio.wait_for(self._message_queue.get(), timeout=timeout)
            else:
                message = await self._message_queue.get()
            return message
        except asyncio.TimeoutError:
            return None

    async def process_message(self, message: AgentMessage) -> None:
        """Process an incoming message. Override in subclasses."""
        LOG.debug("Processing message", agent_id=self.agent_id, message_type=message.message_type)


class PlannerAgent(BaseAgent):
    """
    Planner agent responsible for creating action plans.

    Analyzes the current state and creates a plan for achieving the goal.
    """

    def __init__(self, agent_id: str, message_bus: AgentMessageBus, task: Task, step: Step) -> None:
        super().__init__(agent_id, AgentRole.PLANNER, message_bus, task.task_id, step.step_id)
        self.task = task
        self.step = step

    async def create_plan(
        self, scraped_page: ScrapedPage, actions: list[Action]
    ) -> tuple[list[Action], PlanMessage]:
        """
        Create a plan based on the scraped page and proposed actions.

        Args:
            scraped_page: The current page state
            actions: Proposed actions from LLM

        Returns:
            Tuple of (filtered actions, plan message)
        """
        LOG.info("Planner creating plan", agent_id=self.agent_id, num_actions=len(actions))

        # Send thought message
        await self.send_message(
            MessageType.THOUGHT,
            content=ThoughtMessage(
                thought=f"Analyzing {len(actions)} proposed actions for task: {self.task.navigation_goal or self.task.data_extraction_goal}",
                confidence=0.8,
                reasoning_chain=[
                    "Examining current page state",
                    "Evaluating proposed actions",
                    "Assessing risks and alternatives",
                ],
                context={"page_url": scraped_page.url, "num_elements": len(scraped_page.elements)},
            ).model_dump(),
        )

        # Assess risk level
        risk_level = self._assess_risk(actions)

        # Create plan
        plan = PlanMessage(
            plan_description=f"Execute {len(actions)} actions to achieve goal",
            steps=[
                {
                    "action_type": action.action_type.value if hasattr(action, "action_type") else "unknown",
                    "description": str(action),
                }
                for action in actions
            ],
            expected_outcome=self.task.navigation_goal
            or self.task.data_extraction_goal
            or "Complete task successfully",
            risk_level=risk_level,
            alternatives=["Skip high-risk actions", "Request human intervention"] if risk_level == "high" else [],
        )

        # Send plan message
        await self.send_message(
            MessageType.PLAN,
            content=plan.model_dump(),
            recipient_role=AgentRole.VALIDATOR,
            priority=5,
        )

        return actions, plan

    def _assess_risk(self, actions: list[Action]) -> str:
        """Assess the risk level of proposed actions."""
        # Simple heuristic: more actions = higher risk
        if len(actions) > 10:
            return "high"
        elif len(actions) > 5:
            return "medium"
        return "low"


class ExecutorAgent(BaseAgent):
    """
    Executor agent responsible for executing actions.

    Executes approved actions on the browser and reports results.
    """

    def __init__(
        self,
        agent_id: str,
        message_bus: AgentMessageBus,
        task: Task,
        step: Step,
        browser_state: BrowserState,
    ) -> None:
        super().__init__(agent_id, AgentRole.EXECUTOR, message_bus, task.task_id, step.step_id)
        self.task = task
        self.step = step
        self.browser_state = browser_state

    async def propose_action_execution(self, action: Action, action_index: int) -> str:
        """
        Propose an action for execution.

        Args:
            action: The action to execute
            action_index: Index of the action in the plan

        Returns:
            Message ID of the proposal
        """
        proposal = ActionProposalMessage(
            action_type=action.action_type.value if hasattr(action, "action_type") else "unknown",
            action_data={
                "action_index": action_index,
                "action_str": str(action),
                "action_dict": action.model_dump() if hasattr(action, "model_dump") else {},
            },
            rationale=f"Executing action {action_index} as part of the plan",
            risk_assessment="low",  # Default to low, validator will assess
            confidence=0.9,
            fallback_actions=[],
        )

        message_id = await self.send_message(
            MessageType.ACTION_PROPOSAL,
            content=proposal.model_dump(),
            recipient_role=AgentRole.VALIDATOR,
            priority=8,
            requires_response=True,
        )

        LOG.info(
            "Action proposed for execution",
            agent_id=self.agent_id,
            action_index=action_index,
            message_id=message_id,
        )

        return message_id

    async def report_execution_result(
        self, action: Action, success: bool, result: dict[str, Any], duration_ms: float
    ) -> None:
        """
        Report the result of an action execution.

        Args:
            action: The executed action
            success: Whether execution was successful
            result: Result data
            duration_ms: Execution duration in milliseconds
        """
        execution_result = ExecutionResultMessage(
            success=success,
            action_type=action.action_type.value if hasattr(action, "action_type") else "unknown",
            action_data=action.model_dump() if hasattr(action, "model_dump") else {},
            result=result,
            error_message=result.get("error") if not success else None,
            duration_ms=duration_ms,
            side_effects=[],
        )

        await self.send_message(
            MessageType.EXECUTION_RESULT,
            content=execution_result.model_dump(),
            priority=7,
        )

        LOG.info(
            "Execution result reported",
            agent_id=self.agent_id,
            success=success,
            duration_ms=duration_ms,
        )


class ValidatorAgent(BaseAgent):
    """
    Validator agent responsible for validating plans and actions.

    Reviews plans and action proposals for risks and correctness.
    """

    def __init__(self, agent_id: str, message_bus: AgentMessageBus, task: Task, step: Step) -> None:
        super().__init__(agent_id, AgentRole.VALIDATOR, message_bus, task.task_id, step.step_id)
        self.task = task
        self.step = step
        self._approval_mode = "auto"  # Can be: auto, cautious, strict
        self._auto_approve_threshold = 0.8

    async def validate_plan(self, plan_message: AgentMessage) -> bool:
        """
        Validate a plan from the planner.

        Args:
            plan_message: Message containing the plan

        Returns:
            Whether the plan is approved
        """
        plan = PlanMessage(**plan_message.content)

        # Send validation request
        await self.send_message(
            MessageType.VALIDATION_REQUEST,
            content=ValidationRequestMessage(
                validation_type="plan",
                subject=plan.model_dump(),
                criteria=["risk_level", "feasibility", "completeness"],
                context={"task_goal": self.task.navigation_goal or self.task.data_extraction_goal},
            ).model_dump(),
        )

        # Evaluate plan
        is_valid = plan.risk_level != "high" or len(plan.steps) <= 10

        # Send validation result
        await self.send_message(
            MessageType.VALIDATION_RESULT,
            content=ValidationResultMessage(
                valid=is_valid,
                validation_type="plan",
                findings=[
                    f"Risk level: {plan.risk_level}",
                    f"Number of steps: {len(plan.steps)}",
                ],
                confidence=0.85,
                recommendations=["Proceed with caution"] if plan.risk_level == "high" else [],
            ).model_dump(),
            in_response_to=plan_message.message_id,
        )

        LOG.info("Plan validated", agent_id=self.agent_id, valid=is_valid, risk_level=plan.risk_level)

        return is_valid

    async def validate_action(self, action_proposal: AgentMessage) -> tuple[bool, dict[str, Any]]:
        """
        Validate an action proposal.

        Args:
            action_proposal: Message containing the action proposal

        Returns:
            Tuple of (approved, modifications)
        """
        proposal = ActionProposalMessage(**action_proposal.content)

        # Evaluate action
        is_high_risk = self._is_high_risk_action(proposal)
        approved = proposal.confidence >= self._auto_approve_threshold and not is_high_risk

        # Send approval/rejection
        approval_message = ActionApprovalMessage(
            approved=approved,
            approver_reasoning=f"Action {'approved' if approved else 'rejected'} based on confidence {proposal.confidence} and risk assessment",
            modifications={},
            conditions=["Monitor for unexpected page changes"] if is_high_risk else [],
        )

        await self.send_message(
            MessageType.ACTION_APPROVAL if approved else MessageType.ACTION_REJECTION,
            content=approval_message.model_dump(),
            in_response_to=action_proposal.message_id,
            priority=9,
        )

        LOG.info(
            "Action validated",
            agent_id=self.agent_id,
            approved=approved,
            action_type=proposal.action_type,
        )

        return approved, approval_message.modifications

    def _is_high_risk_action(self, proposal: ActionProposalMessage) -> bool:
        """Determine if an action is high risk."""
        high_risk_actions = ["terminate", "complete"]
        return proposal.action_type.lower() in high_risk_actions or proposal.risk_assessment == "high"

    async def critique_execution(self, execution_result: AgentMessage) -> None:
        """
        Provide critique on execution results.

        Args:
            execution_result: Message containing execution results
        """
        result = ExecutionResultMessage(**execution_result.content)

        if not result.success:
            critique = CritiqueMessage(
                critique_target="execution",
                critique_text=f"Action execution failed: {result.error_message}",
                severity="warning",
                suggestions=["Retry with modified parameters", "Try alternative action"],
                evidence={"result": result.model_dump()},
            )

            await self.send_message(
                MessageType.CRITIQUE,
                content=critique.model_dump(),
                in_response_to=execution_result.message_id,
            )

            LOG.info("Execution critiqued", agent_id=self.agent_id, success=result.success)


class AgentSwarmCoordinator:
    """
    Coordinator for the multi-agent swarm.

    Manages agent lifecycle, consensus building, and fallback to single-agent mode.
    """

    def __init__(self, task: Task, step: Step, browser_state: BrowserState, enable_swarm: bool = True) -> None:
        self.task = task
        self.step = step
        self.browser_state = browser_state
        self.enable_swarm = enable_swarm and (settings.DEBUG_MODE or settings.ENABLE_MULTI_AGENT_SWARM)  # Only enable in debug mode or when explicitly enabled

        self.message_bus = get_message_bus()

        # Initialize agents
        self.planner = PlannerAgent(
            agent_id=f"planner-{task.task_id}",
            message_bus=self.message_bus,
            task=task,
            step=step,
        )

        self.executor = ExecutorAgent(
            agent_id=f"executor-{task.task_id}",
            message_bus=self.message_bus,
            task=task,
            step=step,
            browser_state=browser_state,
        )

        self.validator = ValidatorAgent(
            agent_id=f"validator-{task.task_id}",
            message_bus=self.message_bus,
            task=task,
            step=step,
        )

        LOG.info(
            "AgentSwarmCoordinator initialized",
            task_id=task.task_id,
            step_id=step.step_id,
            enable_swarm=self.enable_swarm,
        )

    async def start(self) -> None:
        """Start all agents in the swarm."""
        if not self.enable_swarm:
            LOG.info("Multi-agent swarm disabled, using single-agent mode")
            return

        await self.planner.start()
        await self.executor.start()
        await self.validator.start()

        # Send status update
        await self.planner.send_message(
            MessageType.STATUS_UPDATE,
            content=StatusUpdateMessage(
                status="swarm_started",
                progress=0.0,
                message="Multi-agent swarm initialized and ready",
                metadata={
                    "task_id": self.task.task_id,
                    "step_id": self.step.step_id,
                },
            ).model_dump(),
        )

        LOG.info("Agent swarm started", task_id=self.task.task_id)

    async def stop(self) -> None:
        """Stop all agents in the swarm."""
        if not self.enable_swarm:
            return

        await self.planner.stop()
        await self.executor.stop()
        await self.validator.stop()

        LOG.info("Agent swarm stopped", task_id=self.task.task_id)

    async def coordinate_planning(
        self, scraped_page: ScrapedPage, actions: list[Action]
    ) -> tuple[list[Action], bool]:
        """
        Coordinate planning phase with planner and validator.

        Args:
            scraped_page: Current page state
            actions: Proposed actions

        Returns:
            Tuple of (approved actions, plan approved)
        """
        if not self.enable_swarm:
            return actions, True  # Skip coordination in single-agent mode

        # Planner creates plan
        filtered_actions, plan = await self.planner.create_plan(scraped_page, actions)

        # Wait for validator to review (with timeout)
        # In a real implementation, this would wait for the validator's response
        # For now, we'll do it synchronously
        plan_message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_role=AgentRole.PLANNER,
            sender_id=self.planner.agent_id,
            recipient_role=AgentRole.VALIDATOR,
            message_type=MessageType.PLAN,
            content=plan.model_dump(),
            task_id=self.task.task_id,
            step_id=self.step.step_id,
        )

        plan_approved = await self.validator.validate_plan(plan_message)

        LOG.info(
            "Planning coordinated",
            task_id=self.task.task_id,
            plan_approved=plan_approved,
            num_actions=len(filtered_actions),
        )

        return filtered_actions, plan_approved

    async def coordinate_action_execution(
        self, action: Action, action_index: int
    ) -> tuple[bool, dict[str, Any]]:
        """
        Coordinate action execution with executor and validator.

        Args:
            action: Action to execute
            action_index: Index of the action

        Returns:
            Tuple of (approved, modifications)
        """
        if not self.enable_swarm:
            return True, {}  # Skip coordination in single-agent mode

        # Executor proposes action
        message_id = await self.executor.propose_action_execution(action, action_index)

        # Wait for validator approval
        proposal_message = AgentMessage(
            message_id=message_id,
            sender_role=AgentRole.EXECUTOR,
            sender_id=self.executor.agent_id,
            recipient_role=AgentRole.VALIDATOR,
            message_type=MessageType.ACTION_PROPOSAL,
            content=ActionProposalMessage(
                action_type=action.action_type.value if hasattr(action, "action_type") else "unknown",
                action_data={"action_dict": action.model_dump() if hasattr(action, "model_dump") else {}},
                rationale="Executing action",
                risk_assessment="low",
                confidence=0.9,
                fallback_actions=[],
            ).model_dump(),
            task_id=self.task.task_id,
            step_id=self.step.step_id,
        )

        approved, modifications = await self.validator.validate_action(proposal_message)

        LOG.info(
            "Action execution coordinated",
            task_id=self.task.task_id,
            action_index=action_index,
            approved=approved,
        )

        return approved, modifications

    async def request_consensus(self, decision_topic: str, options: list[dict[str, Any]]) -> dict[str, Any] | None:
        """
        Request consensus from agents on a decision.

        Args:
            decision_topic: Topic requiring consensus
            options: Available options

        Returns:
            Selected option or None if no consensus
        """
        if not self.enable_swarm or len(options) == 0:
            return options[0] if options else None

        # Send consensus request
        consensus_request = ConsensusRequestMessage(
            decision_topic=decision_topic,
            options=options,
            voting_agents=[self.planner.agent_id, self.executor.agent_id, self.validator.agent_id],
            context={"task_id": self.task.task_id, "step_id": self.step.step_id},
        )

        await self.planner.send_message(
            MessageType.CONSENSUS_REQUEST,
            content=consensus_request.model_dump(),
            priority=10,
        )

        # For simplicity, return the first option
        # A real implementation would wait for votes and tally results
        LOG.info("Consensus requested", decision_topic=decision_topic, num_options=len(options))

        return options[0]

    def get_message_history(self) -> list[AgentMessage]:
        """Get all messages from the swarm."""
        return self.message_bus.get_message_history(task_id=self.task.task_id)

    def get_statistics(self) -> dict[str, Any]:
        """Get swarm statistics."""
        return {
            "enable_swarm": self.enable_swarm,
            "agents": {
                "planner": {"id": self.planner.agent_id, "active": self.planner.active},
                "executor": {"id": self.executor.agent_id, "active": self.executor.active},
                "validator": {"id": self.validator.agent_id, "active": self.validator.active},
            },
            "message_bus": self.message_bus.get_statistics(),
        }
