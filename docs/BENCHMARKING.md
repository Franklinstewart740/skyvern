# LLM Benchmarking & Telemetry

Skyvern now includes comprehensive LLM benchmarking and telemetry capabilities to help you:
- Monitor performance across different LLM providers
- Compare costs and latencies
- Track success rates and errors
- Make data-driven decisions about which models to use

## Features

### Automatic Telemetry Collection

All LLM calls are automatically instrumented to capture:
- **Latency**: Response time in milliseconds
- **Token Usage**: Input, output, reasoning, and cached tokens
- **Cost**: Per-call and aggregated costs
- **Success/Failure**: With error types and messages
- **Context**: Associated step, task, workflow, and organization

### Benchmarking Dashboard

Access the benchmarking dashboard at `/benchmarks` to view:
- Success rates by provider
- Average latency metrics
- Cost comparisons
- Token usage statistics
- Real-time updates (refreshes every 30 seconds)

### REST API Endpoints

#### Get Benchmark Summaries
```
GET /v1/benchmarks/summaries
```

Query parameters:
- `provider` (optional): Filter by specific provider
- `start_date` (optional): Filter from this date
- `end_date` (optional): Filter until this date

Response:
```json
[
  {
    "provider": "openai",
    "model_name": null,
    "total_calls": 1000,
    "successful_calls": 985,
    "failed_calls": 15,
    "success_rate": 98.5,
    "avg_latency_ms": 1250.5,
    "total_input_tokens": 100000,
    "total_output_tokens": 50000,
    "total_cost": 15.25,
    "avg_cost": 0.01525
  }
]
```

#### Get Telemetry Traces
```
GET /v1/benchmarks/traces?provider=openai&limit=100
```

Returns detailed trace data for individual LLM calls.

#### Get Available Providers
```
GET /v1/benchmarks/providers
```

Returns list of providers with telemetry data.

## Running Benchmarks

Use the benchmarking runner script to compare providers:

```bash
python evaluation/llm_benchmarking_runner.py \
  --providers openai/gpt-4o anthropic/claude-3-5-sonnet gemini/gemini-2.0-flash \
  --tasks simple reasoning navigation \
  --iterations 5
```

This will:
1. Run standardized test prompts
2. Collect metrics for each provider
3. Store telemetry in the database
4. Print a summary comparison

### Benchmark Tasks

**simple**: Basic arithmetic question (tests baseline performance)
**reasoning**: Logic puzzle (tests reasoning capabilities)
**navigation**: Web interaction planning (tests domain-specific knowledge)

## Database Schema

### llm_call_telemetry

Stores individual LLM call metrics:
- `telemetry_id`: Unique identifier
- `organization_id`: Organization context
- `llm_key`: LLM configuration key
- `provider`: Provider name (openai, anthropic, etc.)
- `model_name`: Specific model used
- `prompt_name`: Identifier for the prompt type
- `step_id`, `task_id`, `workflow_run_id`, `thought_id`: Context links
- `latency_ms`: Response time
- `input_tokens`, `output_tokens`, `reasoning_tokens`, `cached_tokens`: Token counts
- `total_tokens`: Sum of all tokens
- `cost`: Per-call cost
- `success`: Boolean success flag
- `error_type`, `error_message`: Error details if failed
- `created_at`: Timestamp

### llm_benchmark_summaries

Stores aggregated metrics (populated by background job):
- `summary_id`: Unique identifier
- `organization_id`: Organization context
- `provider`, `model_name`: Provider/model being summarized
- `prompt_name`: Optional prompt filter
- `time_period`: "hourly" or "daily"
- `period_start`, `period_end`: Time window
- `total_calls`, `successful_calls`, `failed_calls`: Call counts
- `avg_latency_ms`, `p50_latency_ms`, `p95_latency_ms`, `p99_latency_ms`: Latency percentiles
- `total_input_tokens`, `total_output_tokens`, etc.: Token aggregates
- `total_cost`, `avg_cost`: Cost metrics

## Background Aggregation

(Future enhancement)
A background job periodically aggregates telemetry data into summaries for faster dashboard queries.

Run manually:
```python
from skyvern.forge import app

await app.LLM_TELEMETRY_SERVICE.aggregate_summaries(
    time_period="hourly",
    lookback_hours=24
)
```

## Best Practices

1. **Use consistent prompt_name values** across your codebase to enable meaningful comparisons
2. **Review benchmarks regularly** to identify performance regressions
3. **Consider costs** when choosing providers - cheaper isn't always better for complex tasks
4. **Monitor success rates** to catch provider issues early
5. **Use the benchmarking runner** before making provider changes to production

## Troubleshooting

### No data showing in dashboard
- Ensure LLM calls are being made
- Check that telemetry service is initialized (`app.LLM_TELEMETRY_SERVICE`)
- Verify database migration has been applied: `alembic upgrade head`

### Slow dashboard loading
- Use date filters to limit the query range
- Consider implementing the background aggregation job
- Add database indexes if needed

### Missing cost data
- Ensure `litellm.completion_cost()` supports your provider
- Some providers may not return cost information
- Check logs for cost calculation errors

## Implementation Details

### Telemetry Wrapper

All LLM API handlers are wrapped with telemetry recording in `api_handler_factory.py`.
The wrapper:
1. Captures start time
2. Calls the underlying LLM handler
3. Calculates latency
4. Extracts metrics from response
5. Records to database (non-blocking)
6. Logs failures without failing the request

### Provider Detection

Provider names are extracted from LLM keys using `extract_provider_from_llm_key()`:
- `openai/gpt-4` → `openai`
- `anthropic/claude-3-5-sonnet` → `anthropic`
- `gpt-4o` → `openai` (inferred from model name)

### Performance Impact

Telemetry recording is designed to have minimal impact:
- Database writes are asynchronous
- Failures in telemetry don't affect LLM calls
- Queries are indexed for fast retrieval
- Dashboard uses cached/aggregated data when available
