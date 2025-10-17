"""Symbolic planning models for workflow definitions."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from skyvern.webeye.actions.action_types import ActionType


class SymbolicPredicateType(str, Enum):
    """Supported predicate types for symbolic reasoning."""

    ELEMENT_EXISTS = "element_exists"
    ELEMENT_VISIBLE = "element_visible"
    ELEMENT_ENABLED = "element_enabled"
    URL_PATTERN = "url_pattern"
    ELEMENT_COUNT = "element_count"
    ELEMENT_TEXT_CONTAINS = "element_text_contains"
    CUSTOM = "custom"


class SymbolicConstraintOperator(str, Enum):
    """Logical operators for combining predicates."""

    AND = "and"
    OR = "or"
    NOT = "not"
    IMPLIES = "implies"


class SymbolicPredicate(BaseModel):
    """A symbolic predicate definition stored on workflow blocks."""

    predicate_type: SymbolicPredicateType
    target: str | None = None
    expected_value: Any = None
    operator: SymbolicConstraintOperator = SymbolicConstraintOperator.AND
    metadata: dict[str, Any] = Field(default_factory=dict)


class SymbolicAffordance(BaseModel):
    """A symbolic affordance that connects predicates to an actionable intent."""

    action_type: ActionType
    element_id: str | None = None
    preconditions: list[SymbolicPredicate] = Field(default_factory=list)
    postconditions: list[SymbolicPredicate] = Field(default_factory=list)
    priority: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class SymbolicGuard(BaseModel):
    """Guard condition preventing actions when predicates evaluate to true."""

    name: str
    predicates: list[SymbolicPredicate] = Field(default_factory=list)
    action_types_blocked: list[ActionType] = Field(default_factory=list)
    message: str | None = None


class SymbolicActionBlueprint(BaseModel):
    """Declarative fallback action description."""

    action_type: ActionType
    element_id: str | None = None
    text: str | None = None
    option: dict[str, Any] | None = None
    reasoning: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SymbolicPlanConfig(BaseModel):
    """Top-level symbolic configuration for workflow blocks."""

    predicates: list[SymbolicPredicate] = Field(default_factory=list)
    affordances: list[SymbolicAffordance] = Field(default_factory=list)
    guards: list[SymbolicGuard] = Field(default_factory=list)
    fallback_actions: list[SymbolicActionBlueprint] = Field(default_factory=list)
    loop_guard_window: int | None = None
