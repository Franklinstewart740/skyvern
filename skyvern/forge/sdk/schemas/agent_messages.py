"""
Agent-to-agent messaging schema for multi-agent swarm coordination.

This module defines the message types and schemas used for communication
between different agent roles (planner, executor, validator) in the multi-agent system.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    """Roles for agents in the multi-agent swarm."""

    PLANNER = "planner"
    EXECUTOR = "executor"
    VALIDATOR = "validator"
    COORDINATOR = "coordinator"


class MessageType(str, Enum):
    """Types of messages agents can send to each other."""

    THOUGHT = "thought"
    PLAN = "plan"
    ACTION_PROPOSAL = "action_proposal"
    ACTION_APPROVAL = "action_approval"
    ACTION_REJECTION = "action_rejection"
    EXECUTION_RESULT = "execution_result"
    VALIDATION_REQUEST = "validation_request"
    VALIDATION_RESULT = "validation_result"
    CRITIQUE = "critique"
    CONSENSUS_REQUEST = "consensus_request"
    CONSENSUS_RESPONSE = "consensus_response"
    ERROR = "error"
    STATUS_UPDATE = "status_update"


class AgentMessage(BaseModel):
    """Base message structure for agent-to-agent communication."""

    message_id: str = Field(description="Unique identifier for the message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sender_role: AgentRole = Field(description="Role of the agent sending the message")
    sender_id: str = Field(description="Unique identifier of the sender agent")
    recipient_role: AgentRole | None = Field(
        default=None, description="Role of the recipient agent (None for broadcast)"
    )
    recipient_id: str | None = Field(default=None, description="Specific recipient agent ID (None for broadcast)")
    message_type: MessageType = Field(description="Type of message being sent")
    content: dict[str, Any] = Field(default_factory=dict, description="Message payload")
    task_id: str | None = Field(default=None, description="Associated task ID")
    step_id: str | None = Field(default=None, description="Associated step ID")
    priority: int = Field(default=0, description="Message priority (higher = more urgent)")
    requires_response: bool = Field(default=False, description="Whether this message requires a response")
    in_response_to: str | None = Field(default=None, description="ID of the message this is responding to")


class ThoughtMessage(BaseModel):
    """Thought message content - agent's reasoning process."""

    thought: str = Field(description="The agent's thought or reasoning")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this thought (0-1)")
    reasoning_chain: list[str] = Field(default_factory=list, description="Chain of reasoning steps")
    context: dict[str, Any] = Field(default_factory=dict, description="Contextual information")


class PlanMessage(BaseModel):
    """Plan message content - proposed action plan."""

    plan_description: str = Field(description="Description of the proposed plan")
    steps: list[dict[str, Any]] = Field(description="Planned steps to execute")
    expected_outcome: str = Field(description="Expected outcome of the plan")
    risk_level: str = Field(description="Risk assessment: low, medium, high")
    alternatives: list[str] = Field(default_factory=list, description="Alternative plans considered")


class ActionProposalMessage(BaseModel):
    """Action proposal message content."""

    action_type: str = Field(description="Type of action being proposed")
    action_data: dict[str, Any] = Field(description="Action parameters and data")
    rationale: str = Field(description="Reasoning for this action")
    risk_assessment: str = Field(description="Risk level: low, medium, high")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the action (0-1)")
    fallback_actions: list[dict[str, Any]] = Field(
        default_factory=list, description="Fallback actions if this fails"
    )


class ActionApprovalMessage(BaseModel):
    """Action approval message content."""

    approved: bool = Field(description="Whether the action is approved")
    approver_reasoning: str = Field(description="Reasoning behind the approval/rejection")
    modifications: dict[str, Any] = Field(
        default_factory=dict, description="Suggested modifications to the action"
    )
    conditions: list[str] = Field(default_factory=list, description="Conditions for execution")


class ExecutionResultMessage(BaseModel):
    """Execution result message content."""

    success: bool = Field(description="Whether execution was successful")
    action_type: str = Field(description="Type of action that was executed")
    action_data: dict[str, Any] = Field(description="Action parameters that were executed")
    result: dict[str, Any] = Field(description="Result of the execution")
    error_message: str | None = Field(default=None, description="Error message if execution failed")
    duration_ms: float = Field(description="Duration of execution in milliseconds")
    side_effects: list[str] = Field(default_factory=list, description="Observed side effects")


class ValidationRequestMessage(BaseModel):
    """Validation request message content."""

    validation_type: str = Field(description="Type of validation needed")
    subject: dict[str, Any] = Field(description="Subject to validate")
    criteria: list[str] = Field(description="Validation criteria")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class ValidationResultMessage(BaseModel):
    """Validation result message content."""

    valid: bool = Field(description="Whether validation passed")
    validation_type: str = Field(description="Type of validation performed")
    findings: list[str] = Field(default_factory=list, description="Validation findings")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in validation (0-1)")
    recommendations: list[str] = Field(default_factory=list, description="Recommendations based on validation")


class CritiqueMessage(BaseModel):
    """Critique message content - constructive feedback."""

    critique_target: str = Field(description="What is being critiqued")
    critique_text: str = Field(description="The critique itself")
    severity: str = Field(description="Severity: info, warning, critical")
    suggestions: list[str] = Field(default_factory=list, description="Suggestions for improvement")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Evidence supporting the critique")


class ConsensusRequestMessage(BaseModel):
    """Consensus request message content."""

    decision_topic: str = Field(description="Topic requiring consensus")
    options: list[dict[str, Any]] = Field(description="Available options for decision")
    voting_agents: list[str] = Field(description="Agent IDs that should vote")
    deadline: datetime | None = Field(default=None, description="Deadline for consensus")
    context: dict[str, Any] = Field(default_factory=dict, description="Context for the decision")


class ConsensusResponseMessage(BaseModel):
    """Consensus response message content."""

    decision_topic: str = Field(description="Topic being voted on")
    selected_option: dict[str, Any] = Field(description="The option being voted for")
    reasoning: str = Field(description="Reasoning behind the vote")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this choice (0-1)")


class ErrorMessage(BaseModel):
    """Error message content."""

    error_type: str = Field(description="Type of error")
    error_message: str = Field(description="Error message")
    error_details: dict[str, Any] = Field(default_factory=dict, description="Detailed error information")
    recoverable: bool = Field(description="Whether the error is recoverable")
    suggested_actions: list[str] = Field(default_factory=list, description="Suggested recovery actions")


class StatusUpdateMessage(BaseModel):
    """Status update message content."""

    status: str = Field(description="Current status")
    progress: float = Field(ge=0.0, le=1.0, description="Progress indicator (0-1)")
    message: str = Field(description="Status message")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional status metadata")


class AgentMessageBatch(BaseModel):
    """Batch of messages for efficient processing."""

    messages: list[AgentMessage] = Field(description="List of messages in the batch")
    batch_id: str = Field(description="Unique identifier for the batch")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MessageFilter(BaseModel):
    """Filter criteria for querying messages."""

    sender_role: AgentRole | None = None
    recipient_role: AgentRole | None = None
    message_type: MessageType | None = None
    task_id: str | None = None
    step_id: str | None = None
    from_timestamp: datetime | None = None
    to_timestamp: datetime | None = None
    min_priority: int | None = None
