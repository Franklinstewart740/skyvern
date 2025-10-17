"""Service for LLM telemetry and benchmarking."""

import asyncio
import datetime
from typing import Any

import sqlalchemy
import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from skyvern.forge.sdk.db.id import generate_llm_benchmark_summary_id, generate_llm_telemetry_id
from skyvern.forge.sdk.db.models import LLMCallTelemetryModel, LLMBenchmarkSummaryModel

LOG = structlog.get_logger()


class LLMTelemetryService:
    """Service for recording and querying LLM call telemetry."""

    def __init__(self, session_maker: async_sessionmaker) -> None:
        self.session_maker = session_maker
        self._aggregation_task: asyncio.Task | None = None
        self._aggregation_interval_minutes = 15
        self._aggregation_time_period = "hourly"
        self._aggregation_lookback_hours = 24

    async def record_llm_call(
        self,
        llm_key: str,
        provider: str,
        prompt_name: str,
        latency_ms: int,
        success: bool,
        organization_id: str | None = None,
        model_name: str | None = None,
        step_id: str | None = None,
        task_id: str | None = None,
        workflow_run_id: str | None = None,
        thought_id: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        reasoning_tokens: int | None = None,
        cached_tokens: int | None = None,
        cost: float | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> str:
        """Record an LLM call to the telemetry table."""
        total_tokens = None
        if input_tokens is not None or output_tokens is not None:
            total_tokens = (input_tokens or 0) + (output_tokens or 0)

        telemetry_id = generate_llm_telemetry_id()

        try:
            async with self.session_maker() as session:
                telemetry = LLMCallTelemetryModel(
                    telemetry_id=telemetry_id,
                    organization_id=organization_id,
                    llm_key=llm_key,
                    provider=provider,
                    model_name=model_name,
                    prompt_name=prompt_name,
                    step_id=step_id,
                    task_id=task_id,
                    workflow_run_id=workflow_run_id,
                    thought_id=thought_id,
                    latency_ms=latency_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    reasoning_tokens=reasoning_tokens,
                    cached_tokens=cached_tokens,
                    total_tokens=total_tokens,
                    cost=cost,
                    success=success,
                    error_type=error_type,
                    error_message=error_message,
                )
                session.add(telemetry)
                await session.commit()
                LOG.debug(
                    "Recorded LLM telemetry",
                    telemetry_id=telemetry_id,
                    provider=provider,
                    prompt_name=prompt_name,
                    success=success,
                )
                return telemetry_id
        except Exception:
            LOG.exception("Failed to record LLM telemetry")
            raise

    async def get_telemetry_by_provider(
        self,
        provider: str,
        organization_id: str | None = None,
        start_date: datetime.datetime | None = None,
        end_date: datetime.datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get telemetry records filtered by provider."""
        try:
            async with self.session_maker() as session:
                conditions = [LLMCallTelemetryModel.provider == provider]

                if organization_id:
                    conditions.append(LLMCallTelemetryModel.organization_id == organization_id)

                if start_date:
                    conditions.append(LLMCallTelemetryModel.created_at >= start_date)

                if end_date:
                    conditions.append(LLMCallTelemetryModel.created_at <= end_date)

                stmt = (
                    select(LLMCallTelemetryModel)
                    .where(and_(*conditions))
                    .order_by(LLMCallTelemetryModel.created_at.desc())
                    .limit(limit)
                )

                result = await session.execute(stmt)
                telemetry_records = result.scalars().all()

                return [
                    {
                        "telemetry_id": record.telemetry_id,
                        "llm_key": record.llm_key,
                        "provider": record.provider,
                        "model_name": record.model_name,
                        "prompt_name": record.prompt_name,
                        "latency_ms": record.latency_ms,
                        "input_tokens": record.input_tokens,
                        "output_tokens": record.output_tokens,
                        "reasoning_tokens": record.reasoning_tokens,
                        "cached_tokens": record.cached_tokens,
                        "total_tokens": record.total_tokens,
                        "cost": float(record.cost) if record.cost else None,
                        "success": record.success,
                        "error_type": record.error_type,
                        "created_at": record.created_at,
                    }
                    for record in telemetry_records
                ]
        except Exception:
            LOG.exception("Failed to get telemetry by provider")
            raise

    async def get_provider_statistics(
        self,
        organization_id: str | None = None,
        start_date: datetime.datetime | None = None,
        end_date: datetime.datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get aggregated statistics by provider."""
        try:
            async with self.session_maker() as session:
                conditions = []

                if organization_id:
                    conditions.append(LLMCallTelemetryModel.organization_id == organization_id)

                if start_date:
                    conditions.append(LLMCallTelemetryModel.created_at >= start_date)

                if end_date:
                    conditions.append(LLMCallTelemetryModel.created_at <= end_date)

                where_clause = and_(*conditions) if conditions else None

                stmt = (
                    select(
                        LLMCallTelemetryModel.provider,
                        func.count(LLMCallTelemetryModel.telemetry_id).label("total_calls"),
                        func.sum(func.cast(LLMCallTelemetryModel.success, sqlalchemy.Integer)).label(
                            "successful_calls"
                        ),
                        func.avg(LLMCallTelemetryModel.latency_ms).label("avg_latency_ms"),
                        func.sum(LLMCallTelemetryModel.input_tokens).label("total_input_tokens"),
                        func.sum(LLMCallTelemetryModel.output_tokens).label("total_output_tokens"),
                        func.sum(LLMCallTelemetryModel.cost).label("total_cost"),
                        func.avg(LLMCallTelemetryModel.cost).label("avg_cost"),
                    )
                    .group_by(LLMCallTelemetryModel.provider)
                    .order_by(func.count(LLMCallTelemetryModel.telemetry_id).desc())
                )

                if where_clause is not None:
                    stmt = stmt.where(where_clause)

                result = await session.execute(stmt)
                rows = result.all()

                return [
                    {
                        "provider": row.provider,
                        "total_calls": row.total_calls,
                        "successful_calls": row.successful_calls or 0,
                        "failed_calls": row.total_calls - (row.successful_calls or 0),
                        "success_rate": (
                            (row.successful_calls / row.total_calls * 100) if row.total_calls > 0 else 0
                        ),
                        "avg_latency_ms": float(row.avg_latency_ms) if row.avg_latency_ms else None,
                        "total_input_tokens": row.total_input_tokens,
                        "total_output_tokens": row.total_output_tokens,
                        "total_cost": float(row.total_cost) if row.total_cost else None,
                        "avg_cost": float(row.avg_cost) if row.avg_cost else None,
                    }
                    for row in rows
                ]
        except Exception:
            LOG.exception("Failed to get provider statistics")
            raise

    async def aggregate_summaries(
        self,
        time_period: str = "hourly",
        lookback_hours: int = 24,
    ) -> int:
        """Aggregate telemetry data into summary tables.
        
        Args:
            time_period: "hourly" or "daily"
            lookback_hours: How many hours back to aggregate
            
        Returns:
            Number of summaries created
        """
        try:
            now = datetime.datetime.utcnow()
            start_time = now - datetime.timedelta(hours=lookback_hours)
            
            # Determine period boundaries based on time_period
            if time_period == "hourly":
                period_hours = 1
            elif time_period == "daily":
                period_hours = 24
            else:
                raise ValueError(f"Invalid time_period: {time_period}")
            
            summaries_created = 0
            
            async with self.session_maker() as session:
                # Get all unique provider/model combinations in the time window
                provider_models = await session.execute(
                    select(
                        LLMCallTelemetryModel.provider,
                        LLMCallTelemetryModel.model_name,
                        LLMCallTelemetryModel.organization_id,
                    )
                    .where(LLMCallTelemetryModel.created_at >= start_time)
                    .distinct()
                )
                
                for provider, model_name, org_id in provider_models:
                    # Calculate period boundaries
                    period_start = start_time.replace(minute=0, second=0, microsecond=0)
                    while period_start < now:
                        period_end = period_start + datetime.timedelta(hours=period_hours)
                        
                        # Check if summary already exists
                        existing = await session.execute(
                            select(LLMBenchmarkSummaryModel).where(
                                and_(
                                    LLMBenchmarkSummaryModel.provider == provider,
                                    LLMBenchmarkSummaryModel.model_name == model_name,
                                    LLMBenchmarkSummaryModel.organization_id == org_id,
                                    LLMBenchmarkSummaryModel.time_period == time_period,
                                    LLMBenchmarkSummaryModel.period_start == period_start,
                                )
                            )
                        )
                        
                        if existing.scalar_one_or_none():
                            period_start = period_end
                            continue
                        
                        # Aggregate statistics for this period
                        stats = await session.execute(
                            select(
                                func.count(LLMCallTelemetryModel.telemetry_id).label("total_calls"),
                                func.sum(func.cast(LLMCallTelemetryModel.success, sqlalchemy.Integer)).label(
                                    "successful_calls"
                                ),
                                func.avg(LLMCallTelemetryModel.latency_ms).label("avg_latency_ms"),
                                func.percentile_cont(0.50).within_group(LLMCallTelemetryModel.latency_ms).label(
                                    "p50_latency_ms"
                                ),
                                func.percentile_cont(0.95).within_group(LLMCallTelemetryModel.latency_ms).label(
                                    "p95_latency_ms"
                                ),
                                func.percentile_cont(0.99).within_group(LLMCallTelemetryModel.latency_ms).label(
                                    "p99_latency_ms"
                                ),
                                func.sum(LLMCallTelemetryModel.input_tokens).label("total_input_tokens"),
                                func.sum(LLMCallTelemetryModel.output_tokens).label("total_output_tokens"),
                                func.sum(LLMCallTelemetryModel.reasoning_tokens).label("total_reasoning_tokens"),
                                func.sum(LLMCallTelemetryModel.cached_tokens).label("total_cached_tokens"),
                                func.sum(LLMCallTelemetryModel.cost).label("total_cost"),
                                func.avg(LLMCallTelemetryModel.cost).label("avg_cost"),
                            ).where(
                                and_(
                                    LLMCallTelemetryModel.provider == provider,
                                    LLMCallTelemetryModel.model_name == model_name,
                                    LLMCallTelemetryModel.organization_id == org_id,
                                    LLMCallTelemetryModel.created_at >= period_start,
                                    LLMCallTelemetryModel.created_at < period_end,
                                )
                            )
                        )
                        
                        row = stats.one_or_none()
                        if not row or row.total_calls == 0:
                            period_start = period_end
                            continue
                        
                        # Create summary
                        summary = LLMBenchmarkSummaryModel(
                            summary_id=generate_llm_benchmark_summary_id(),
                            organization_id=org_id,
                            provider=provider,
                            model_name=model_name,
                            prompt_name=None,  # Aggregate all prompts for now
                            time_period=time_period,
                            period_start=period_start,
                            period_end=period_end,
                            total_calls=row.total_calls,
                            successful_calls=row.successful_calls or 0,
                            failed_calls=row.total_calls - (row.successful_calls or 0),
                            avg_latency_ms=row.avg_latency_ms,
                            p50_latency_ms=row.p50_latency_ms,
                            p95_latency_ms=row.p95_latency_ms,
                            p99_latency_ms=row.p99_latency_ms,
                            total_input_tokens=row.total_input_tokens,
                            total_output_tokens=row.total_output_tokens,
                            total_reasoning_tokens=row.total_reasoning_tokens,
                            total_cached_tokens=row.total_cached_tokens,
                            total_cost=row.total_cost,
                            avg_cost=row.avg_cost,
                        )
                        session.add(summary)
                        summaries_created += 1
                        
                        period_start = period_end
                
                await session.commit()
                
            LOG.info(
                "Aggregated LLM telemetry summaries",
                time_period=time_period,
                lookback_hours=lookback_hours,
                summaries_created=summaries_created,
            )
            return summaries_created
        except Exception:
            LOG.exception("Failed to aggregate summaries")
            raise

    async def start_background_aggregation(
        self,
        *,
        time_period: str = "hourly",
        lookback_hours: int = 24,
        interval_minutes: int = 15,
    ) -> None:
        """Start background aggregation loop."""
        self._aggregation_time_period = time_period
        self._aggregation_lookback_hours = lookback_hours
        self._aggregation_interval_minutes = interval_minutes

        if self._aggregation_task and not self._aggregation_task.done():
            return

        loop = asyncio.get_running_loop()
        self._aggregation_task = loop.create_task(self._aggregation_loop())
        LOG.info(
            "Started LLM telemetry aggregation loop",
            time_period=time_period,
            lookback_hours=lookback_hours,
            interval_minutes=interval_minutes,
        )

    async def stop_background_aggregation(self) -> None:
        """Stop the background aggregation loop."""
        if self._aggregation_task is None:
            return
        self._aggregation_task.cancel()
        try:
            await self._aggregation_task
        except asyncio.CancelledError:
            LOG.info("Stopped LLM telemetry aggregation loop")
        finally:
            self._aggregation_task = None

    async def _aggregation_loop(self) -> None:
        """Background task that aggregates telemetry on an interval."""
        while True:
            try:
                await self.aggregate_summaries(
                    time_period=self._aggregation_time_period,
                    lookback_hours=self._aggregation_lookback_hours,
                )
            except asyncio.CancelledError:
                LOG.debug("Aggregation loop cancelled")
                raise
            except Exception:
                LOG.exception("Background telemetry aggregation failed")
            await asyncio.sleep(self._aggregation_interval_minutes * 60)

