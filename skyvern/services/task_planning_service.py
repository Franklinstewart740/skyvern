from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable

import structlog
from pydantic import BaseModel, Field, ValidationError

from skyvern.config import settings
from skyvern.forge import app
from skyvern.forge.prompts import prompt_engine
from skyvern.forge.sdk.api.llm.api_handler_factory import LLMAPIHandlerFactory
from skyvern.forge.sdk.schemas.planning import ReasoningTrace, TaskPlan
from skyvern.forge.sdk.schemas.task_v2 import ThoughtScenario, ThoughtType

LOG = structlog.get_logger(__name__)

PLAN_PROMPT_TEMPLATE = "task_planning_generate_plan"


class PlanningArtifacts(BaseModel):
    """Container for plan data and supporting reasoning traces."""

    plan: TaskPlan | None = None
    reasoning_traces: list[ReasoningTrace] = Field(default_factory=list)
    llm_key: str | None = None
    thought_id: str | None = None

    def has_content(self) -> bool:
        return self.plan is not None or bool(self.reasoning_traces)


async def ensure_plan_for_task(
    *,
    organization_id: str,
    task_id: str,
    user_prompt: str | None,
    starting_url: str | None = None,
    llm_key: str | None = None,
) -> PlanningArtifacts:
    """Idempotently make sure a task has a persisted LLM plan.

    If a plan already exists it is returned; otherwise a fresh one is generated
    and stored.
    """

    existing = await get_plan_and_traces(task_id=task_id, organization_id=organization_id)
    if existing.has_content():
        return existing

    return await generate_plan_for_task(
        organization_id=organization_id,
        task_id=task_id,
        user_prompt=user_prompt,
        starting_url=starting_url,
        llm_key=llm_key,
    )


async def generate_plan_for_task(
    *,
    organization_id: str,
    task_id: str,
    user_prompt: str | None,
    starting_url: str | None = None,
    llm_key: str | None = None,
) -> PlanningArtifacts:
    """Generate a fresh plan for the supplied task and persist it as a thought."""

    if not user_prompt or user_prompt.strip() == "":
        LOG.debug("Skipping plan generation due to empty prompt", task_id=task_id)
        return PlanningArtifacts(plan=None, reasoning_traces=[], llm_key=llm_key, thought_id=None)

    prompt = prompt_engine.load_prompt(
        PLAN_PROMPT_TEMPLATE,
        user_prompt=user_prompt.strip(),
        starting_url=starting_url or "NOT_PROVIDED",
    )

    handler, resolved_llm_key = _resolve_llm_handler(llm_key)

    thought = await app.DATABASE.create_thought(
        task_v2_id=task_id,
        organization_id=organization_id,
        thought_type=ThoughtType.plan,
        thought_scenario=ThoughtScenario.generate_plan,
        user_input=user_prompt,
    )

    response_payload: dict[str, Any] | None = None
    plan: TaskPlan | None = None
    reasoning_traces: list[ReasoningTrace] = []

    try:
        raw_response = await handler(
            prompt=prompt,
            prompt_name=PLAN_PROMPT_TEMPLATE,
            organization_id=organization_id,
            thought=thought,
        )
        response_payload = _coerce_to_json(raw_response)
        plan = _parse_plan(response_payload)
        reasoning_traces = _parse_reasoning_traces(
            response_payload,
            fallback_created_at=thought.created_at,
            source_thought_id=thought.observer_thought_id,
        )
    except Exception as exc:  # noqa: BLE001
        LOG.warning(
            "Failed to generate planning steps", task_id=task_id, organization_id=organization_id, exc_info=True
        )
        await _update_thought_with_failure(
            thought_id=thought.observer_thought_id,
            organization_id=organization_id,
            failure_reason=str(exc),
        )
        return PlanningArtifacts(
            plan=None,
            reasoning_traces=[],
            llm_key=resolved_llm_key,
            thought_id=thought.observer_thought_id,
        )

    output_payload: dict[str, Any] = {
        "raw_response": response_payload,
        "llm_key": resolved_llm_key,
    }
    if plan:
        output_payload["plan"] = plan.model_dump()
    if reasoning_traces:
        output_payload["reasoning_traces"] = [trace.model_dump() for trace in reasoning_traces]

    await app.DATABASE.update_thought(
        thought_id=thought.observer_thought_id,
        organization_id=organization_id,
        thought=plan.strategy if plan else None,
        output=output_payload,
    )

    return PlanningArtifacts(
        plan=plan,
        reasoning_traces=reasoning_traces,
        llm_key=resolved_llm_key,
        thought_id=thought.observer_thought_id,
    )


async def get_plan_and_traces(*, task_id: str, organization_id: str | None) -> PlanningArtifacts:
    """Fetch the latest stored plan & reasoning traces for the provided task."""

    if not organization_id:
        return PlanningArtifacts()

    thoughts = await app.DATABASE.get_thoughts(
        task_v2_id=task_id,
        thought_types=[ThoughtType.plan],
        organization_id=organization_id,
    )
    if not thoughts:
        return PlanningArtifacts()

    for thought in reversed(thoughts):
        output = thought.output or {}
        if not isinstance(output, dict):
            continue

        plan_payload = output.get("plan")
        plan = None
        if isinstance(plan_payload, dict):
            try:
                plan = TaskPlan.model_validate(plan_payload)
            except ValidationError:
                LOG.debug("Stored plan payload failed validation", plan_payload=plan_payload)
                plan = None

        traces_payload = output.get("reasoning_traces") if isinstance(output, dict) else None
        reasoning_traces = _parse_reasoning_traces(
            {"reasoning_traces": traces_payload} if traces_payload is not None else {},
            fallback_created_at=thought.created_at,
            source_thought_id=thought.observer_thought_id,
        )

        if plan or reasoning_traces:
            return PlanningArtifacts(
                plan=plan,
                reasoning_traces=reasoning_traces,
                llm_key=output.get("llm_key") if isinstance(output, dict) else None,
                thought_id=thought.observer_thought_id,
            )

    return PlanningArtifacts()


def _resolve_llm_handler(llm_key: str | None) -> tuple[Callable[..., Any], str]:
    """Choose an LLM handler for planning with sensible fallbacks."""

    resolved_key = (
        llm_key
        or settings.PROMPT_BLOCK_LLM_KEY
        or settings.SECONDARY_LLM_KEY
        or settings.LLM_KEY
    )

    if resolved_key == settings.LLM_KEY:
        return app.LLM_API_HANDLER, resolved_key
    if settings.SECONDARY_LLM_KEY and resolved_key == settings.SECONDARY_LLM_KEY:
        return app.SECONDARY_LLM_API_HANDLER, resolved_key

    return LLMAPIHandlerFactory.get_llm_api_handler(resolved_key), resolved_key


def _coerce_to_json(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        return response
    if isinstance(response, str):
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            LOG.debug("Planner response is not valid JSON", response=response)
            return {}
    LOG.debug("Planner response type not supported", response_type=type(response).__name__)
    return {}


def _parse_plan(payload: dict[str, Any] | None) -> TaskPlan | None:
    if not payload or "plan" not in payload or not isinstance(payload["plan"], dict):
        return None

    plan_payload = payload["plan"]
    steps = plan_payload.get("steps")
    if isinstance(steps, list):
        for idx, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                continue
            step.setdefault("index", idx)
            step.setdefault("id", f"step-{idx}")
    try:
        return TaskPlan.model_validate(plan_payload)
    except ValidationError as exc:
        LOG.warning("Unable to parse plan payload", errors=exc.errors())
        return None


def _parse_reasoning_traces(
    payload: dict[str, Any],
    *,
    fallback_created_at,
    source_thought_id: str | None,
) -> list[ReasoningTrace]:
    traces_payload = payload.get("reasoning_traces")
    if not isinstance(traces_payload, list):
        return []

    reasoning_traces: list[ReasoningTrace] = []
    for idx, trace in enumerate(traces_payload, start=1):
        if not isinstance(trace, dict):
            continue
        trace = trace.copy()
        trace.setdefault("trace_id", f"trace-{idx}")
        trace.setdefault("label", trace.get("label") or f"Trace {idx}")
        trace_content = trace.get("content")
        if not isinstance(trace_content, str) or trace_content.strip() == "":
            continue
        if trace.get("created_at") is None and fallback_created_at is not None:
            trace["created_at"] = fallback_created_at
        metadata = trace.get("metadata")
        if metadata is None:
            trace["metadata"] = {"source_thought_id": source_thought_id}
        elif isinstance(metadata, dict):
            metadata.setdefault("source_thought_id", source_thought_id)
        try:
            parsed = ReasoningTrace.model_validate(trace)
        except ValidationError as exc:
            LOG.debug("Skipping invalid reasoning trace", errors=exc.errors())
            continue
        if parsed.created_at is None and fallback_created_at is not None:
            parsed.created_at = fallback_created_at
        reasoning_traces.append(parsed)
    return reasoning_traces


async def _update_thought_with_failure(
    *,
    thought_id: str,
    organization_id: str,
    failure_reason: str,
) -> None:
    try:
        await app.DATABASE.update_thought(
            thought_id=thought_id,
            organization_id=organization_id,
            thought=f"Planner generation failed: {failure_reason}",
        )
    except Exception:  # noqa: BLE001
        LOG.debug("Failed to update planning failure thought", thought_id=thought_id, exc_info=True)


__all__ = [
    "PlanningArtifacts",
    "ensure_plan_for_task",
    "generate_plan_for_task",
    "get_plan_and_traces",
]
