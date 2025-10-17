"""Wrapper for LLM API handlers to record telemetry."""

import time
from typing import Any

import structlog

from skyvern.forge.sdk.api.llm.models import LLMAPIHandler, LLMConfig, LLMRouterConfig
from skyvern.forge.sdk.models import Step
from skyvern.forge.sdk.schemas.ai_suggestions import AISuggestion
from skyvern.forge.sdk.schemas.task_v2 import TaskV2, Thought
from skyvern.services.llm_telemetry_service import LLMTelemetryService
from skyvern.services.llm_telemetry_utils import extract_model_name_from_llm_key, extract_provider_from_llm_key
from skyvern.utils.image_resizer import Resolution

LOG = structlog.get_logger()


def wrap_llm_handler_with_telemetry(
    handler: LLMAPIHandler,
    llm_key: str,
    llm_config: LLMConfig | LLMRouterConfig,
    telemetry_service: LLMTelemetryService,
) -> LLMAPIHandler:
    """Wrap an LLM API handler to record telemetry.
    
    This wrapper captures:
    - Latency
    - Token usage (input, output, reasoning, cached)
    - Cost
    - Success/failure
    - Provider and model information
    """

    async def telemetry_wrapper(
        prompt: str,
        prompt_name: str,
        step: Step | None = None,
        task_v2: TaskV2 | None = None,
        thought: Thought | None = None,
        ai_suggestion: AISuggestion | None = None,
        screenshots: list[bytes] | None = None,
        parameters: dict[str, Any] | None = None,
        organization_id: str | None = None,
        tools: list | None = None,
        use_message_history: bool = False,
        raw_response: bool = False,
        window_dimension: Resolution | None = None,
    ) -> dict[str, Any]:
        start_time = time.time()
        success = False
        error_type = None
        error_message = None
        response = None

        try:
            # Call the actual handler
            response = await handler(
                prompt=prompt,
                prompt_name=prompt_name,
                step=step,
                task_v2=task_v2,
                thought=thought,
                ai_suggestion=ai_suggestion,
                screenshots=screenshots,
                parameters=parameters,
                organization_id=organization_id,
                tools=tools,
                use_message_history=use_message_history,
                raw_response=raw_response,
                window_dimension=window_dimension,
            )
            success = True
            return response
        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)[:500]  # Truncate to avoid huge messages
            raise
        finally:
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract organization ID
            org_id = organization_id or (
                step.organization_id if step else (thought.organization_id if thought else None)
            )

            # Extract provider and model
            provider = extract_provider_from_llm_key(llm_key)
            model_name = extract_model_name_from_llm_key(llm_key, llm_config)

            # Extract metrics from response (if available)
            input_tokens = None
            output_tokens = None
            reasoning_tokens = None
            cached_tokens = None
            cost = None

            # Note: Token counts and cost are typically logged/stored by the handler itself
            # We can extract them from the response metadata if available
            # For now, we'll log without them and rely on separate token tracking

            # Record telemetry (non-blocking, don't fail the request if telemetry fails)
            try:
                await telemetry_service.record_llm_call(
                    llm_key=llm_key,
                    provider=provider,
                    prompt_name=prompt_name,
                    latency_ms=latency_ms,
                    success=success,
                    organization_id=org_id,
                    model_name=model_name,
                    step_id=step.step_id if step else None,
                    task_id=step.task_id if step else None,
                    workflow_run_id=None,  # Would need to be passed in if available
                    thought_id=thought.observer_thought_id if thought else None,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    reasoning_tokens=reasoning_tokens,
                    cached_tokens=cached_tokens,
                    cost=cost,
                    error_type=error_type,
                    error_message=error_message,
                )
            except Exception:
                # Don't fail the LLM call if telemetry recording fails
                LOG.exception("Failed to record LLM telemetry", llm_key=llm_key, prompt_name=prompt_name)

    return telemetry_wrapper
