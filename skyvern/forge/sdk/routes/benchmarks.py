"""API routes for LLM benchmarking and telemetry."""

import datetime
from typing import Annotated, Any

import structlog
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel

from skyvern.forge import app
from skyvern.forge.sdk.api.dependencies import get_current_org
from skyvern.forge.sdk.routes.routers import base_router
from skyvern.forge.sdk.schemas.organizations import Organization

LOG = structlog.get_logger()


class BenchmarkSummaryResponse(BaseModel):
    """Response model for benchmark summary."""

    provider: str
    model_name: str | None
    total_calls: int
    successful_calls: int
    failed_calls: int
    success_rate: float
    avg_latency_ms: float | None
    total_input_tokens: int | None
    total_output_tokens: int | None
    total_cost: float | None
    avg_cost: float | None


class TelemetryTraceResponse(BaseModel):
    """Response model for detailed telemetry traces."""

    telemetry_id: str
    llm_key: str
    provider: str
    model_name: str | None
    prompt_name: str
    latency_ms: int
    input_tokens: int | None
    output_tokens: int | None
    reasoning_tokens: int | None
    cached_tokens: int | None
    total_tokens: int | None
    cost: float | None
    success: bool
    error_type: str | None
    created_at: datetime.datetime


@base_router.get("/benchmarks/summaries", response_model=list[BenchmarkSummaryResponse])
async def get_benchmark_summaries(
    organization: Annotated[Organization, Depends(get_current_org)],
    provider: str | None = Query(None, description="Filter by LLM provider"),
    start_date: datetime.datetime | None = Query(None, description="Start date for filtering"),
    end_date: datetime.datetime | None = Query(None, description="End date for filtering"),
) -> list[dict[str, Any]]:
    """Get aggregated benchmark summaries for LLM providers.
    
    Returns statistics like:
    - Total calls, success/failure rates
    - Average latency
    - Token usage and costs
    - Grouped by provider and model
    """
    try:
        if provider:
            # If filtering by provider, get detailed stats from telemetry
            stats = await app.LLM_TELEMETRY_SERVICE.get_provider_statistics(
                organization_id=organization.organization_id,
                start_date=start_date,
                end_date=end_date,
            )
            # Filter to only the requested provider
            stats = [s for s in stats if s["provider"] == provider]
            return [
                {
                    "provider": s["provider"],
                    "model_name": None,
                    "total_calls": s["total_calls"],
                    "successful_calls": s["successful_calls"],
                    "failed_calls": s["failed_calls"],
                    "success_rate": s["success_rate"],
                    "avg_latency_ms": s["avg_latency_ms"],
                    "total_input_tokens": s["total_input_tokens"],
                    "total_output_tokens": s["total_output_tokens"],
                    "total_cost": s["total_cost"],
                    "avg_cost": s["avg_cost"],
                }
                for s in stats
            ]
        else:
            # Get overall statistics for all providers
            stats = await app.LLM_TELEMETRY_SERVICE.get_provider_statistics(
                organization_id=organization.organization_id,
                start_date=start_date,
                end_date=end_date,
            )
            return [
                {
                    "provider": s["provider"],
                    "model_name": None,
                    "total_calls": s["total_calls"],
                    "successful_calls": s["successful_calls"],
                    "failed_calls": s["failed_calls"],
                    "success_rate": s["success_rate"],
                    "avg_latency_ms": s["avg_latency_ms"],
                    "total_input_tokens": s["total_input_tokens"],
                    "total_output_tokens": s["total_output_tokens"],
                    "total_cost": s["total_cost"],
                    "avg_cost": s["avg_cost"],
                }
                for s in stats
            ]
    except Exception:
        LOG.exception("Failed to get benchmark summaries")
        raise HTTPException(status_code=500, detail="Failed to get benchmark summaries")


@base_router.get("/benchmarks/traces", response_model=list[TelemetryTraceResponse])
async def get_telemetry_traces(
    organization: Annotated[Organization, Depends(get_current_org)],
    provider: str | None = Query(None, description="Filter by LLM provider"),
    start_date: datetime.datetime | None = Query(None, description="Start date for filtering"),
    end_date: datetime.datetime | None = Query(None, description="End date for filtering"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of traces to return"),
) -> list[dict[str, Any]]:
    """Get detailed telemetry traces for LLM calls.
    
    Returns individual call records with:
    - Latency, tokens, cost for each call
    - Success/failure status
    - Error information if failed
    - Associated step/task/workflow IDs
    """
    try:
        if not provider:
            raise HTTPException(status_code=400, detail="Provider is required for trace queries")

        traces = await app.LLM_TELEMETRY_SERVICE.get_telemetry_by_provider(
            provider=provider,
            organization_id=organization.organization_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        return traces
    except HTTPException:
        raise
    except Exception:
        LOG.exception("Failed to get telemetry traces")
        raise HTTPException(status_code=500, detail="Failed to get telemetry traces")


@base_router.get("/benchmarks/providers", response_model=list[str])
async def get_available_providers(
    organization: Annotated[Organization, Depends(get_current_org)],
) -> list[str]:
    """Get list of LLM providers that have telemetry data."""
    try:
        stats = await app.LLM_TELEMETRY_SERVICE.get_provider_statistics(
            organization_id=organization.organization_id,
        )
        return [s["provider"] for s in stats]
    except Exception:
        LOG.exception("Failed to get available providers")
        raise HTTPException(status_code=500, detail="Failed to get available providers")
