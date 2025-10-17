# Prompt Caching and Replay Infrastructure

This document describes the LLM prompt caching and replay infrastructure implemented in Skyvern.

## Overview

The prompt caching system stores LLM request/response pairs to:
- **Reduce costs** by avoiding duplicate API calls for identical prompts
- **Improve performance** by returning cached responses instantly
- **Enable debugging** through prompt replay functionality
- **Support benchmarking** by replaying historical prompts

## Architecture

### Components

1. **Database Model** (`PromptCacheModel`)
   - Stores cached prompts and responses in PostgreSQL
   - Tracks usage statistics (hit count, timestamps)
   - Supports TTL-based expiration

2. **Caching Service** (`PromptCacheService`)
   - Computes deterministic hashes for prompts
   - Manages cache retrieval and storage
   - Handles cache eviction and replay

3. **Configuration** (`settings`)
   - Feature toggles for caching and replay
   - TTL and eviction policies
   - Backend selection (PostgreSQL/Redis)

4. **API Endpoints**
   - `GET /api/v1/prompt-cache/info` - Cache configuration
   - `POST /api/v1/prompt-cache/evict` - Manual eviction
   - `GET /api/v1/prompt-cache/replay/{id}` - Replay cached prompt

5. **CLI Commands**
   - `skyvern cache info` - View configuration
   - `skyvern cache evict` - Evict expired entries

## Configuration

Add these environment variables to `.env`:

```bash
# Enable prompt caching
ENABLE_PROMPT_CACHE=true

# Backend: "postgres" or "redis" (postgres is default)
PROMPT_CACHE_BACKEND=postgres

# Cache TTL in hours (default: 168 = 7 days)
PROMPT_CACHE_TTL_HOURS=168

# Enable replay functionality
ENABLE_PROMPT_CACHE_REPLAY=true

# Enable automatic eviction of expired entries
PROMPT_CACHE_EVICTION_ENABLED=true

# Eviction interval in hours (default: 24)
PROMPT_CACHE_EVICTION_INTERVAL_HOURS=24
```

## Database Schema

The `prompt_cache` table includes:

```sql
CREATE TABLE prompt_cache (
    prompt_cache_id VARCHAR PRIMARY KEY,
    organization_id VARCHAR,
    prompt_hash VARCHAR NOT NULL,
    llm_key VARCHAR NOT NULL,
    model_config JSON,
    prompt_text TEXT,
    response_payload JSON NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    reasoning_tokens INTEGER,
    cached_tokens INTEGER,
    cache_cost NUMERIC,
    hit_count INTEGER DEFAULT 0,
    ttl_expires_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    modified_at TIMESTAMP NOT NULL,
    accessed_at TIMESTAMP NOT NULL
);

-- Indexes for efficient lookups
CREATE INDEX ix_prompt_cache_hash_llm_key ON prompt_cache (prompt_hash, llm_key);
CREATE INDEX ix_prompt_cache_org_created ON prompt_cache (organization_id, created_at);
CREATE INDEX ix_prompt_cache_expires_at ON prompt_cache (ttl_expires_at);
```

## Usage

### Run Database Migration

```bash
alembic upgrade head
```

### Enable Caching

Set `ENABLE_PROMPT_CACHE=true` in your `.env` file.

### View Cache Statistics

```bash
# CLI
skyvern cache info

# API
curl http://localhost:8000/api/v1/prompt-cache/info
```

### Evict Expired Entries

```bash
# CLI
skyvern cache evict

# API
curl -X POST http://localhost:8000/api/v1/prompt-cache/evict
```

### Replay a Cached Prompt

```bash
# API
curl http://localhost:8000/api/v1/prompt-cache/replay/{prompt_cache_id}
```

## Cache Key Computation

The cache key is a SHA-256 hash of:
1. **LLM Key** - The model identifier (e.g., "OPENAI_GPT4O")
2. **Prompt** - The normalized prompt text or messages
3. **Model Config** - Deterministic parameters only:
   - `temperature`
   - `max_tokens`
   - `top_p`
   - `frequency_penalty`
   - `presence_penalty`

Non-deterministic parameters (timeout, retry, etc.) are excluded.

## Cache Hit/Miss Behavior

### Cache Hit
1. Prompt hash is computed
2. Database lookup by `(prompt_hash, llm_key)`
3. If found and not expired:
   - Response returned immediately
   - `hit_count` incremented
   - `accessed_at` updated
4. No LLM API call made

### Cache Miss
1. Prompt hash computed
2. Database lookup fails or entry expired
3. LLM API call executed normally
4. Response saved to cache for future requests

## Expiration and Eviction

### TTL (Time-To-Live)
- Configurable via `PROMPT_CACHE_TTL_HOURS`
- Default: 168 hours (7 days)
- Set to 0 for no expiration

### Automatic Eviction
- Runs periodically if `PROMPT_CACHE_EVICTION_ENABLED=true`
- Interval: `PROMPT_CACHE_EVICTION_INTERVAL_HOURS`
- Removes entries where `ttl_expires_at <= now()`

### Manual Eviction
Use CLI or API to manually trigger eviction.

## Testing

Run unit tests:

```bash
pytest tests/unit_tests/test_prompt_cache.py -v
```

## Multi-Tenant Support

Cache entries are scoped by:
- `organization_id` (optional, for multi-tenant deployments)
- `llm_key` (model identifier)
- `prompt_hash` (prompt + config hash)

## Debugging and Replay

The replay feature allows:
1. **Debugging** - Examine exactly what was sent to/returned from LLM
2. **Testing** - Replay prompts to test prompt changes
3. **Benchmarking** - Compare responses across models or configurations

### Example Replay Workflow

```bash
# 1. Find a cache entry (via database query or logs)
prompt_cache_id="pcache_123456789"

# 2. Replay the cached response
curl http://localhost:8000/api/v1/prompt-cache/replay/$prompt_cache_id
```

## Performance Considerations

### Storage
- Prompt text and responses stored as JSON
- Typical entry size: 10-100 KB
- Plan for storage based on prompt volume

### Database Indexes
- Three indexes optimize common queries
- Index on `(prompt_hash, llm_key)` for cache lookups
- Index on `(organization_id, created_at)` for analytics
- Index on `ttl_expires_at` for eviction

### Memory vs Disk
- PostgreSQL backend stores in database
- Future: Redis backend for in-memory caching

## Future Enhancements

Potential improvements:
1. **Redis Backend** - Faster in-memory caching
2. **Cache Warmup** - Pre-populate cache for common prompts
3. **Analytics Dashboard** - UI for cache statistics
4. **Partial Matching** - Fuzzy prompt matching
5. **Compression** - Compress large responses
6. **Distributed Caching** - Multi-node cache synchronization

## Security Considerations

- Cache entries may contain sensitive data
- Ensure proper access controls on cache API endpoints
- Consider encryption for sensitive prompt/response data
- Regular eviction reduces data retention risk

## Troubleshooting

### Cache not working
1. Check `ENABLE_PROMPT_CACHE=true` in config
2. Verify database migration ran successfully
3. Check logs for cache service errors

### High miss rate
1. Verify prompt normalization is working
2. Check if config parameters vary across requests
3. Review TTL settings (may be too short)

### Storage growing too large
1. Reduce `PROMPT_CACHE_TTL_HOURS`
2. Enable `PROMPT_CACHE_EVICTION_ENABLED`
3. Run manual eviction more frequently

## Support

For issues or questions:
- GitHub Issues: https://github.com/Skyvern-AI/skyvern/issues
- Documentation: https://docs.skyvern.com
