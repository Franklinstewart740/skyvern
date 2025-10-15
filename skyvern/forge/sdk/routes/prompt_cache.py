from typing import Any

import structlog
from fastapi import HTTPException
from pydantic import BaseModel

from skyvern.config import settings
from skyvern.forge.app import DATABASE
from skyvern.forge.sdk.api.llm.prompt_cache import PromptCacheService
from skyvern.forge.sdk.routes.routers import base_router

LOG = structlog.get_logger()


class PromptCacheInfoResponse(BaseModel):
    enabled: bool
    backend: str
    ttl_hours: int
    replay_enabled: bool
    eviction_enabled: bool
    eviction_interval_hours: int


class EvictResponse(BaseModel):
    evicted_count: int
    message: str


class ReplayResponse(BaseModel):
    prompt_cache_id: str
    llm_key: str
    response_payload: dict[str, Any]
    created_at: str
    hit_count: int


@base_router.get("/prompt-cache/info", response_model=PromptCacheInfoResponse)
async def get_cache_info() -> PromptCacheInfoResponse:
    """Get prompt cache configuration information."""
    return PromptCacheInfoResponse(
        enabled=settings.ENABLE_PROMPT_CACHE,
        backend=settings.PROMPT_CACHE_BACKEND,
        ttl_hours=settings.PROMPT_CACHE_TTL_HOURS,
        replay_enabled=settings.ENABLE_PROMPT_CACHE_REPLAY,
        eviction_enabled=settings.PROMPT_CACHE_EVICTION_ENABLED,
        eviction_interval_hours=settings.PROMPT_CACHE_EVICTION_INTERVAL_HOURS,
    )


@base_router.post("/prompt-cache/evict", response_model=EvictResponse)
async def evict_expired_entries() -> EvictResponse:
    """Manually evict expired cache entries."""
    if not settings.ENABLE_PROMPT_CACHE:
        raise HTTPException(status_code=400, detail="Prompt cache is disabled")
    
    try:
        async with DATABASE.Session() as session:
            count = await PromptCacheService.evict_expired_entries(session)
            return EvictResponse(
                evicted_count=count,
                message=f"Evicted {count} expired cache entries" if count > 0 else "No expired entries found",
            )
    except Exception as e:
        LOG.error("Error evicting cache entries", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to evict cache entries: {str(e)}")


@base_router.get("/prompt-cache/replay/{prompt_cache_id}", response_model=ReplayResponse)
async def replay_cached_prompt(prompt_cache_id: str) -> ReplayResponse:
    """Replay a cached prompt response by ID."""
    if not settings.ENABLE_PROMPT_CACHE:
        raise HTTPException(status_code=400, detail="Prompt cache is disabled")
    
    if not settings.ENABLE_PROMPT_CACHE_REPLAY:
        raise HTTPException(status_code=400, detail="Prompt cache replay is disabled")
    
    try:
        async with DATABASE.Session() as session:
            cache_entry = await PromptCacheService.get_cache_entry_by_id(session, prompt_cache_id)
            
            if not cache_entry:
                raise HTTPException(status_code=404, detail=f"Cache entry not found: {prompt_cache_id}")
            
            return ReplayResponse(
                prompt_cache_id=cache_entry.prompt_cache_id,
                llm_key=cache_entry.llm_key,
                response_payload=cache_entry.response_payload,
                created_at=cache_entry.created_at.isoformat(),
                hit_count=cache_entry.hit_count,
            )
    except HTTPException:
        raise
    except Exception as e:
        LOG.error("Error replaying cached prompt", error=str(e), prompt_cache_id=prompt_cache_id)
        raise HTTPException(status_code=500, detail=f"Failed to replay cached prompt: {str(e)}")
