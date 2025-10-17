"""Tests for LLM telemetry service."""

import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from skyvern.services import llm_telemetry_service
from skyvern.services.llm_telemetry_service import LLMTelemetryService


@pytest.fixture
def telemetry_service():
    """Create a telemetry service with mock session maker."""
    mock_session_maker = AsyncMock()
    return LLMTelemetryService(session_maker=mock_session_maker)


@pytest.mark.asyncio
async def test_record_llm_call(telemetry_service):
    """Test recording an LLM call."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    telemetry_service.session_maker.return_value = mock_session

    telemetry_id = await telemetry_service.record_llm_call(
        llm_key="openai/gpt-4o",
        provider="openai",
        prompt_name="test_prompt",
        latency_ms=1500,
        success=True,
        organization_id="test_org",
        model_name="gpt-4o",
        input_tokens=100,
        output_tokens=50,
        cost=0.01,
    )

    assert telemetry_id is not None
    assert telemetry_id.startswith("llmt_")
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_record_llm_call_with_error(telemetry_service):
    """Test recording a failed LLM call."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    telemetry_service.session_maker.return_value = mock_session

    telemetry_id = await telemetry_service.record_llm_call(
        llm_key="anthropic/claude-3-5-sonnet",
        provider="anthropic",
        prompt_name="test_prompt",
        latency_ms=2000,
        success=False,
        error_type="APIError",
        error_message="Rate limit exceeded",
    )

    assert telemetry_id is not None
    mock_session.add.assert_called_once()
    
    # Get the telemetry object that was added
    added_telemetry = mock_session.add.call_args[0][0]
    assert added_telemetry.success is False
    assert added_telemetry.error_type == "APIError"
    assert added_telemetry.error_message == "Rate limit exceeded"


@pytest.mark.asyncio
async def test_get_provider_statistics(telemetry_service):
    """Test getting provider statistics."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    
    # Mock query results
    mock_row = Mock()
    mock_row.provider = "openai"
    mock_row.total_calls = 100
    mock_row.successful_calls = 95
    mock_row.avg_latency_ms = 1500.0
    mock_row.total_input_tokens = 10000
    mock_row.total_output_tokens = 5000
    mock_row.total_cost = 1.50
    mock_row.avg_cost = 0.015
    
    mock_result = AsyncMock()
    mock_result.all.return_value = [mock_row]
    
    mock_session.execute.return_value = mock_result
    telemetry_service.session_maker.return_value = mock_session

    stats = await telemetry_service.get_provider_statistics(
        organization_id="test_org"
    )

    assert len(stats) == 1
    assert stats[0]["provider"] == "openai"
    assert stats[0]["total_calls"] == 100
    assert stats[0]["successful_calls"] == 95
    assert stats[0]["failed_calls"] == 5
    assert stats[0]["success_rate"] == 95.0
    assert stats[0]["avg_latency_ms"] == 1500.0


@pytest.mark.asyncio
async def test_get_telemetry_by_provider(telemetry_service):
    """Test getting telemetry records by provider."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    
    # Mock telemetry records
    mock_record = Mock()
    mock_record.telemetry_id = "llmt_123"
    mock_record.llm_key = "openai/gpt-4o"
    mock_record.provider = "openai"
    mock_record.model_name = "gpt-4o"
    mock_record.prompt_name = "test_prompt"
    mock_record.latency_ms = 1500
    mock_record.input_tokens = 100
    mock_record.output_tokens = 50
    mock_record.reasoning_tokens = None
    mock_record.cached_tokens = None
    mock_record.total_tokens = 150
    mock_record.cost = 0.01
    mock_record.success = True
    mock_record.error_type = None
    mock_record.created_at = datetime.datetime.utcnow()
    
    mock_result = AsyncMock()
    mock_result.scalars.return_value.all.return_value = [mock_record]
    
    mock_session.execute.return_value = mock_result
    telemetry_service.session_maker.return_value = mock_session

    traces = await telemetry_service.get_telemetry_by_provider(
        provider="openai",
        organization_id="test_org",
        limit=10,
    )

    assert len(traces) == 1
    assert traces[0]["telemetry_id"] == "llmt_123"
    assert traces[0]["provider"] == "openai"
    assert traces[0]["latency_ms"] == 1500
    assert traces[0]["success"] is True


@pytest.mark.asyncio
async def test_aggregate_summaries_creates_summary(monkeypatch, telemetry_service):
    """Test aggregation of telemetry into summaries."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_session.add = Mock()
    mock_session.commit = AsyncMock()

    provider_models_result = [("openai", "gpt-4o", "org1")]

    existing_result = AsyncMock()
    existing_result.scalar_one_or_none.return_value = None

    stats_row = SimpleNamespace(
        total_calls=10,
        successful_calls=8,
        avg_latency_ms=100.0,
        p50_latency_ms=90.0,
        p95_latency_ms=150.0,
        p99_latency_ms=200.0,
        total_input_tokens=1000,
        total_output_tokens=500,
        total_reasoning_tokens=0,
        total_cached_tokens=0,
        total_cost=1.25,
        avg_cost=0.125,
    )
    stats_result = AsyncMock()
    stats_result.one_or_none.return_value = stats_row

    mock_session.execute = AsyncMock(side_effect=[provider_models_result, existing_result, stats_result])
    telemetry_service.session_maker.return_value = mock_session

    fixed_now = datetime.datetime(2024, 1, 1, 10, 0, 0)

    class FixedDateTime(datetime.datetime):
        @classmethod
        def utcnow(cls):
            return fixed_now

    fake_datetime_module = SimpleNamespace(datetime=FixedDateTime, timedelta=datetime.timedelta)

    monkeypatch.setattr(llm_telemetry_service, "datetime", fake_datetime_module)

    summaries_created = await telemetry_service.aggregate_summaries(
        time_period="hourly",
        lookback_hours=1,
    )

    assert summaries_created == 1
    mock_session.add.assert_called()
    mock_session.commit.assert_awaited()
