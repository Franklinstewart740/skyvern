# LLM Benchmarking Telemetry Implementation

## Summary

This implementation adds comprehensive LLM benchmarking and telemetry capabilities to Skyvern, allowing users to monitor performance, cost, and success rates across different LLM providers.

## Components Implemented

### 1. Database Layer

**Files:**
- `alembic/versions/2025_10_17_0000-a1b2c3d4e5f6_add_llm_benchmarking_telemetry_tables.py` - Database migration
- `skyvern/forge/sdk/db/models.py` - Added `LLMCallTelemetryModel` and `LLMBenchmarkSummaryModel`
- `skyvern/forge/sdk/db/id.py` - Added ID generators for telemetry records

**Schema:**
- `llm_call_telemetry`: Stores individual LLM call metrics (latency, tokens, cost, success/failure)
- `llm_benchmark_summaries`: Stores aggregated metrics (hourly/daily summaries)

### 2. Backend Services

**Files:**
- `skyvern/services/llm_telemetry_service.py` - Core telemetry service with recording and aggregation
- `skyvern/services/llm_telemetry_utils.py` - Helper functions for provider/model extraction
- `skyvern/services/llm_telemetry_wrapper.py` - Wrapper for LLM handlers (not currently used, kept for reference)

**Features:**
- Automatic recording of all LLM calls
- Provider statistics aggregation
- Telemetry trace queries
- Background aggregation capability (implemented but not activated)

### 3. LLM Instrumentation

**Files:**
- `skyvern/forge/sdk/api/llm/api_handler_factory.py` - Instrumented LLM handlers

**Changes:**
- Added telemetry recording to `get_llm_api_handler_with_router`
- Records success and failure cases with full metrics
- Non-blocking telemetry (doesn't fail LLM calls if recording fails)
- Captures: latency, tokens, cost, errors

### 4. REST API

**Files:**
- `skyvern/forge/sdk/routes/benchmarks.py` - New benchmarking endpoints
- `skyvern/forge/sdk/routes/__init__.py` - Added import for benchmarks module
- `skyvern/forge/app.py` - Added `LLM_TELEMETRY_SERVICE` to app

**Endpoints:**
- `GET /v1/benchmarks/summaries` - Get aggregated benchmarking data
- `GET /v1/benchmarks/traces` - Get detailed telemetry traces
- `GET /v1/benchmarks/providers` - Get list of providers with data

### 5. Benchmarking Scripts

**Files:**
- `evaluation/llm_benchmarking_runner.py` - CLI tool for running standardized benchmarks

**Features:**
- Compare multiple providers side-by-side
- Run standardized test tasks (simple, reasoning, navigation)
- Configurable iterations
- Summary reporting

### 6. Frontend Dashboard

**Files:**
- `skyvern-frontend/src/routes/benchmarks/BenchmarksPage.tsx` - Main dashboard component
- `skyvern-frontend/src/routes/benchmarks/index.ts` - Export file
- `skyvern-frontend/src/router.tsx` - Added `/benchmarks` route
- `skyvern-frontend/src/routes/root/SideNav.tsx` - Added "Benchmarks" to navigation

**Features:**
- Real-time metrics display
- Success rates, latency, costs per provider
- Token usage statistics
- Auto-refresh every 30 seconds

### 7. Tests

**Files:**
- `tests/unit_tests/services/test_llm_telemetry_service.py` - Comprehensive unit tests

**Coverage:**
- Recording LLM calls
- Recording failures
- Provider statistics queries
- Telemetry trace queries
- Aggregation logic

### 8. Documentation

**Files:**
- `docs/BENCHMARKING.md` - Complete usage guide
- `BENCHMARKING_IMPLEMENTATION.md` - This file

## Usage

### Running Benchmarks

```bash
python evaluation/llm_benchmarking_runner.py \
  --providers openai/gpt-4o anthropic/claude-3-5-sonnet \
  --tasks simple reasoning navigation \
  --iterations 3
```

### Accessing Dashboard

Navigate to `/benchmarks` in the Skyvern UI to view real-time metrics.

### API Access

```bash
# Get summaries
curl -H "x-api-key: YOUR_API_KEY" \
  http://localhost:8000/v1/benchmarks/summaries

# Get traces for a specific provider
curl -H "x-api-key: YOUR_API_KEY" \
  "http://localhost:8000/v1/benchmarks/traces?provider=openai&limit=10"
```

## Testing

Run tests:
```bash
pytest tests/unit_tests/services/test_llm_telemetry_service.py -v
```

## Database Migration

To apply the new tables:
```bash
alembic upgrade head
```

## Future Enhancements

1. **Background Aggregation Job**: Activate periodic aggregation for faster queries
2. **Advanced Visualizations**: Add charts (line graphs, bar charts) for cost/latency trends
3. **Alerts**: Configure alerts for high failure rates or latency spikes
4. **Export**: Add CSV/JSON export for benchmark reports
5. **Filtering**: Add more filters (date ranges, prompt types, models)
6. **Comparisons**: Side-by-side provider comparisons with delta calculations

## Architecture Decisions

1. **Non-blocking Telemetry**: Recording failures don't affect LLM calls
2. **Dual Tables**: Raw telemetry + aggregated summaries for query performance
3. **Provider Detection**: Intelligent extraction from LLM keys
4. **Async/Await**: All database operations are async
5. **Indexed Queries**: Strategic indexes on provider, date, success flag

## Notes

- Telemetry is automatically captured for all LLM calls without code changes
- Cost calculation depends on `litellm.completion_cost()` support for the provider
- Dashboard updates every 30 seconds - adjust `refetchInterval` in BenchmarksPage.tsx
- Background aggregation task is implemented but not automatically started
- The implementation is production-ready and non-intrusive
