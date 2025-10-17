from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskPlanStep(BaseModel):
    """Represents a single step in the LLM-generated task plan."""

    id: str = Field(description="Stable identifier for the step")
    index: int = Field(description="1-indexed ordering of the step inside the plan")
    summary: str = Field(description="Short name for the step")
    action: str = Field(description="Concrete browser or automation actions to take")
    expected_outcome: str = Field(description="What success looks like for this step")
    reasoning: str = Field(description="Why this step is necessary")
    inputs: list[str] = Field(default_factory=list, description="Inputs or context needed before running the step")
    dependencies: list[str] = Field(
        default_factory=list,
        description="IDs for prerequisite steps that must complete before this one",
    )
    outputs: list[str] = Field(
        default_factory=list,
        description="Key artefacts or data produced by completing the step",
    )
    notes: list[str] = Field(default_factory=list, description="Additional execution tips or caveats")


class TaskPlan(BaseModel):
    """Structured plan that describes how to execute a natural language task."""

    strategy: str = Field(description="High-level strategy summarising the approach")
    steps: list[TaskPlanStep] = Field(default_factory=list, description="Ordered list of steps to execute")


class ReasoningTrace(BaseModel):
    """Captures intermediate reasoning details that justify the generated plan."""

    trace_id: str = Field(description="Stable identifier for this reasoning snippet")
    label: str = Field(description="Short label describing the reasoning entry")
    content: str = Field(description="Full reasoning text from the LLM")
    related_step_id: str | None = Field(
        default=None,
        description="Optional step identifier that this reasoning is most relevant to",
    )
    confidence: str | None = Field(
        default=None,
        description="LLM-provided confidence or qualitative strength signal",
    )
    category: str | None = Field(default=None, description="Type of reasoning, e.g. assumption, risk, fallback")
    created_at: datetime | None = Field(
        default=None,
        description="Timestamp when the reasoning was generated (filled when persisted)",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Additional provider-specific metadata for downstream inspection",
    )


__all__ = ["TaskPlanStep", "TaskPlan", "ReasoningTrace"]
