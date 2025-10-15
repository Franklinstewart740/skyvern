"""
Agent Message Bus for multi-agent communication.

This module provides a message bus for agents to communicate with each other.
Supports both in-memory (asyncio queues) and Redis-backed message channels.
"""

import asyncio
import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable

import structlog

from skyvern.forge.sdk.schemas.agent_messages import AgentMessage, AgentRole, MessageFilter, MessageType

LOG = structlog.get_logger()


class AgentMessageBus:
    """
    Message bus for agent-to-agent communication.

    Provides publish/subscribe pattern for agents to communicate,
    with support for message filtering, priority queues, and history.
    """

    def __init__(self, max_history_size: int = 1000, use_redis: bool = False) -> None:
        """
        Initialize the message bus.

        Args:
            max_history_size: Maximum number of messages to keep in history
            use_redis: Whether to use Redis as the backend (not implemented yet)
        """
        self.max_history_size = max_history_size
        self.use_redis = use_redis

        # In-memory storage
        self._message_history: list[AgentMessage] = []
        self._subscribers: defaultdict[str, list[asyncio.Queue]] = defaultdict(list)
        self._role_subscribers: defaultdict[AgentRole, list[asyncio.Queue]] = defaultdict(list)
        self._message_type_subscribers: defaultdict[MessageType, list[asyncio.Queue]] = defaultdict(list)
        self._task_subscribers: defaultdict[str, list[asyncio.Queue]] = defaultdict(list)
        self._broadcast_subscribers: list[asyncio.Queue] = []

        # Message handlers for synchronous processing
        self._message_handlers: list[Callable[[AgentMessage], Any]] = []

        # Statistics
        self._stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "subscribers_count": 0,
        }

        LOG.info("AgentMessageBus initialized", use_redis=use_redis, max_history_size=max_history_size)

    async def publish(self, message: AgentMessage) -> None:
        """
        Publish a message to all relevant subscribers.

        Args:
            message: The message to publish
        """
        LOG.debug(
            "Publishing message",
            message_id=message.message_id,
            sender_role=message.sender_role,
            recipient_role=message.recipient_role,
            message_type=message.message_type,
        )

        # Store in history
        self._message_history.append(message)
        if len(self._message_history) > self.max_history_size:
            self._message_history.pop(0)

        # Update statistics
        self._stats["messages_sent"] += 1

        # Call synchronous handlers
        for handler in self._message_handlers:
            try:
                handler(message)
            except Exception as e:
                LOG.error("Error in message handler", error=str(e), handler=handler)

        # Deliver to subscribers
        queues_to_deliver = set()

        # Broadcast subscribers get all messages
        queues_to_deliver.update(self._broadcast_subscribers)

        # Specific recipient
        if message.recipient_id:
            queues_to_deliver.update(self._subscribers.get(message.recipient_id, []))

        # Role-based delivery
        if message.recipient_role:
            queues_to_deliver.update(self._role_subscribers.get(message.recipient_role, []))

        # Message type subscribers
        queues_to_deliver.update(self._message_type_subscribers.get(message.message_type, []))

        # Task-based subscribers
        if message.task_id:
            queues_to_deliver.update(self._task_subscribers.get(message.task_id, []))

        # Deliver to all relevant queues
        for queue in queues_to_deliver:
            try:
                await queue.put(message)
            except Exception as e:
                LOG.error("Error delivering message to queue", error=str(e))

        LOG.debug(
            "Message published",
            message_id=message.message_id,
            queues_delivered=len(queues_to_deliver),
        )

    async def subscribe(
        self,
        agent_id: str | None = None,
        role: AgentRole | None = None,
        message_type: MessageType | None = None,
        task_id: str | None = None,
        broadcast: bool = False,
    ) -> asyncio.Queue:
        """
        Subscribe to messages based on filters.

        Args:
            agent_id: Subscribe to messages for specific agent ID
            role: Subscribe to messages for specific role
            message_type: Subscribe to specific message types
            task_id: Subscribe to messages for specific task
            broadcast: Subscribe to all messages

        Returns:
            Queue that will receive matching messages
        """
        queue: asyncio.Queue = asyncio.Queue()

        if broadcast:
            self._broadcast_subscribers.append(queue)
            LOG.info("Agent subscribed to all messages", agent_id=agent_id)
        else:
            if agent_id:
                self._subscribers[agent_id].append(queue)
                LOG.info("Agent subscribed by ID", agent_id=agent_id)
            if role:
                self._role_subscribers[role].append(queue)
                LOG.info("Agent subscribed by role", role=role)
            if message_type:
                self._message_type_subscribers[message_type].append(queue)
                LOG.info("Agent subscribed by message type", message_type=message_type)
            if task_id:
                self._task_subscribers[task_id].append(queue)
                LOG.info("Agent subscribed by task", task_id=task_id)

        self._stats["subscribers_count"] = self._count_subscribers()
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """
        Unsubscribe a queue from all subscriptions.

        Args:
            queue: The queue to unsubscribe
        """
        # Remove from all subscriber lists
        if queue in self._broadcast_subscribers:
            self._broadcast_subscribers.remove(queue)

        for queues in self._subscribers.values():
            if queue in queues:
                queues.remove(queue)

        for queues in self._role_subscribers.values():
            if queue in queues:
                queues.remove(queue)

        for queues in self._message_type_subscribers.values():
            if queue in queues:
                queues.remove(queue)

        for queues in self._task_subscribers.values():
            if queue in queues:
                queues.remove(queue)

        self._stats["subscribers_count"] = self._count_subscribers()
        LOG.info("Agent unsubscribed", queue=queue)

    def get_message_history(self, filter: MessageFilter | None = None) -> list[AgentMessage]:
        """
        Get message history with optional filtering.

        Args:
            filter: Optional filter criteria

        Returns:
            List of messages matching the filter
        """
        if not filter:
            return self._message_history.copy()

        filtered_messages = []
        for msg in self._message_history:
            if filter.sender_role and msg.sender_role != filter.sender_role:
                continue
            if filter.recipient_role and msg.recipient_role != filter.recipient_role:
                continue
            if filter.message_type and msg.message_type != filter.message_type:
                continue
            if filter.task_id and msg.task_id != filter.task_id:
                continue
            if filter.step_id and msg.step_id != filter.step_id:
                continue
            if filter.from_timestamp and msg.timestamp < filter.from_timestamp:
                continue
            if filter.to_timestamp and msg.timestamp > filter.to_timestamp:
                continue
            if filter.min_priority is not None and msg.priority < filter.min_priority:
                continue
            filtered_messages.append(msg)

        return filtered_messages

    def add_message_handler(self, handler: Callable[[AgentMessage], Any]) -> None:
        """
        Add a synchronous message handler.

        Args:
            handler: Function that will be called for each message
        """
        self._message_handlers.append(handler)
        LOG.info("Message handler added", handler=handler)

    def remove_message_handler(self, handler: Callable[[AgentMessage], Any]) -> None:
        """
        Remove a message handler.

        Args:
            handler: Handler to remove
        """
        if handler in self._message_handlers:
            self._message_handlers.remove(handler)
            LOG.info("Message handler removed", handler=handler)

    def get_statistics(self) -> dict[str, Any]:
        """
        Get message bus statistics.

        Returns:
            Dictionary of statistics
        """
        return {
            **self._stats,
            "history_size": len(self._message_history),
            "max_history_size": self.max_history_size,
        }

    def clear_history(self) -> None:
        """Clear message history."""
        self._message_history.clear()
        LOG.info("Message history cleared")

    def _count_subscribers(self) -> int:
        """Count total number of subscriber queues."""
        count = len(self._broadcast_subscribers)
        for queues in self._subscribers.values():
            count += len(queues)
        for queues in self._role_subscribers.values():
            count += len(queues)
        for queues in self._message_type_subscribers.values():
            count += len(queues)
        for queues in self._task_subscribers.values():
            count += len(queues)
        return count


# Global message bus instance
_global_message_bus: AgentMessageBus | None = None


def get_message_bus() -> AgentMessageBus:
    """
    Get the global message bus instance.

    Returns:
        The global AgentMessageBus instance
    """
    global _global_message_bus
    if _global_message_bus is None:
        _global_message_bus = AgentMessageBus()
    return _global_message_bus


def reset_message_bus() -> None:
    """Reset the global message bus (useful for testing)."""
    global _global_message_bus
    _global_message_bus = None
