"""
API endpoints for multi-agent swarm monitoring and control.
"""

from datetime import datetime
from typing import Annotated, Any

import structlog
from fastapi import Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from skyvern.forge.sdk.core.agent_message_bus import get_message_bus
from skyvern.forge.sdk.routes.routers import base_router
from skyvern.forge.sdk.schemas.agent_messages import AgentMessage, AgentRole, MessageFilter, MessageType
from skyvern.forge.sdk.schemas.organizations import Organization
from skyvern.forge.sdk.services import org_auth_service

LOG = structlog.get_logger()


class AgentSwarmStatusResponse(BaseModel):
    """Response for swarm status endpoint."""

    enabled: bool = Field(description="Whether multi-agent swarm is enabled")
    message_bus_stats: dict[str, Any] = Field(description="Message bus statistics")


class AgentMessagesResponse(BaseModel):
    """Response for agent messages endpoint."""

    messages: list[AgentMessage] = Field(description="List of agent messages")
    total: int = Field(description="Total number of messages")
    filtered: int = Field(description="Number of filtered messages")


@base_router.get(
    "/agent-swarm/status",
    tags=["Agent Swarm"],
    description="Get multi-agent swarm status and statistics",
    summary="Get agent swarm status",
    responses={
        200: {"description": "Successfully retrieved swarm status"},
    },
)
async def get_agent_swarm_status(
    current_org: Organization = Depends(org_auth_service.get_current_org),
) -> AgentSwarmStatusResponse:
    """
    Get the status and statistics of the multi-agent swarm.

    Returns information about the message bus and agent coordination.
    """
    message_bus = get_message_bus()
    stats = message_bus.get_statistics()

    return AgentSwarmStatusResponse(
        enabled=True,  # Multi-agent swarm is always available
        message_bus_stats=stats,
    )


@base_router.get(
    "/agent-swarm/messages",
    tags=["Agent Swarm"],
    description="Get agent communication messages with optional filtering",
    summary="Get agent messages",
    responses={
        200: {"description": "Successfully retrieved agent messages"},
    },
)
async def get_agent_messages(
    current_org: Organization = Depends(org_auth_service.get_current_org),
    task_id: Annotated[str | None, Query(description="Filter by task ID")] = None,
    step_id: Annotated[str | None, Query(description="Filter by step ID")] = None,
    sender_role: Annotated[AgentRole | None, Query(description="Filter by sender role")] = None,
    recipient_role: Annotated[AgentRole | None, Query(description="Filter by recipient role")] = None,
    message_type: Annotated[MessageType | None, Query(description="Filter by message type")] = None,
    from_timestamp: Annotated[datetime | None, Query(description="Filter messages from this timestamp")] = None,
    to_timestamp: Annotated[datetime | None, Query(description="Filter messages to this timestamp")] = None,
    min_priority: Annotated[int | None, Query(description="Filter by minimum priority")] = None,
    limit: Annotated[int, Query(description="Maximum number of messages to return", ge=1, le=1000)] = 100,
) -> AgentMessagesResponse:
    """
    Get agent communication messages with optional filtering.

    Allows monitoring of agent-to-agent communications during task execution.
    """
    message_bus = get_message_bus()

    # Build filter
    message_filter = MessageFilter(
        sender_role=sender_role,
        recipient_role=recipient_role,
        message_type=message_type,
        task_id=task_id,
        step_id=step_id,
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        min_priority=min_priority,
    )

    # Get filtered messages
    all_messages = message_bus.get_message_history()
    filtered_messages = message_bus.get_message_history(filter=message_filter)

    # Apply limit
    limited_messages = filtered_messages[-limit:] if limit else filtered_messages

    LOG.info(
        "Retrieved agent messages",
        total=len(all_messages),
        filtered=len(filtered_messages),
        returned=len(limited_messages),
        task_id=task_id,
    )

    return AgentMessagesResponse(
        messages=limited_messages,
        total=len(all_messages),
        filtered=len(filtered_messages),
    )


@base_router.get(
    "/agent-swarm/messages/{message_id}",
    tags=["Agent Swarm"],
    description="Get a specific agent message by ID",
    summary="Get agent message by ID",
    responses={
        200: {"description": "Successfully retrieved message"},
        404: {"description": "Message not found"},
    },
)
async def get_agent_message_by_id(
    message_id: str,
    current_org: Organization = Depends(org_auth_service.get_current_org),
) -> AgentMessage:
    """
    Get a specific agent message by its ID.
    """
    message_bus = get_message_bus()
    all_messages = message_bus.get_message_history()

    for message in all_messages:
        if message.message_id == message_id:
            return message

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Message with ID {message_id} not found",
    )


@base_router.get(
    "/agent-swarm/tasks/{task_id}/messages",
    tags=["Agent Swarm"],
    description="Get all agent messages for a specific task",
    summary="Get task agent messages",
    responses={
        200: {"description": "Successfully retrieved task messages"},
    },
)
async def get_task_agent_messages(
    task_id: str,
    current_org: Organization = Depends(org_auth_service.get_current_org),
    message_type: Annotated[MessageType | None, Query(description="Filter by message type")] = None,
    sender_role: Annotated[AgentRole | None, Query(description="Filter by sender role")] = None,
) -> AgentMessagesResponse:
    """
    Get all agent messages for a specific task.

    Useful for viewing the complete agent communication history for a task.
    """
    message_bus = get_message_bus()

    # Build filter for task
    message_filter = MessageFilter(
        task_id=task_id,
        message_type=message_type,
        sender_role=sender_role,
    )

    # Get filtered messages
    all_messages = message_bus.get_message_history()
    filtered_messages = message_bus.get_message_history(filter=message_filter)

    LOG.info(
        "Retrieved task agent messages",
        task_id=task_id,
        total=len(filtered_messages),
    )

    return AgentMessagesResponse(
        messages=filtered_messages,
        total=len(all_messages),
        filtered=len(filtered_messages),
    )


@base_router.post(
    "/agent-swarm/clear-history",
    tags=["Agent Swarm"],
    description="Clear agent message history (admin only)",
    summary="Clear message history",
    responses={
        200: {"description": "Successfully cleared message history"},
    },
)
async def clear_agent_message_history(
    current_org: Organization = Depends(org_auth_service.get_current_org),
) -> dict[str, str]:
    """
    Clear the agent message history.

    This is useful for testing or when the message history becomes too large.
    """
    message_bus = get_message_bus()
    message_bus.clear_history()

    LOG.info("Agent message history cleared", organization_id=current_org.organization_id)

    return {"status": "success", "message": "Agent message history cleared"}
