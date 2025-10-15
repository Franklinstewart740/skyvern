import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

import structlog
from litellm.utils import ModelResponse
from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from skyvern.config import settings
from skyvern.forge.sdk.db.models import PromptCacheModel

LOG = structlog.get_logger()


class PromptCacheService:
    """Service for managing LLM prompt caching and replay functionality."""

    @staticmethod
    def _serialize_response(response: ModelResponse | dict[str, Any]) -> dict[str, Any]:
        """
        Convert a ModelResponse or dict to a serializable dictionary.
        
        Args:
            response: The LLM response to serialize
        
        Returns:
            A JSON-serializable dictionary
        """
        if isinstance(response, ModelResponse):
            return response.model_dump(mode="json")
        return response

    @staticmethod
    def _normalize_model_config(model_config: dict[str, Any] | None) -> dict[str, Any] | None:
        """Normalize model configuration for hashing and storage."""
        if model_config is None:
            return None
        try:
            return json.loads(json.dumps(model_config, sort_keys=True, default=str))
        except (TypeError, ValueError):
            # Fallback: convert non-serializable values to strings
            normalized_config: dict[str, Any] = {}
            for key, value in model_config.items():
                if isinstance(value, (dict, list)):
                    try:
                        normalized_config[key] = json.loads(json.dumps(value, sort_keys=True, default=str))
                        continue
                    except (TypeError, ValueError):
                        pass
                normalized_config[key] = str(value)
            return normalized_config

    @staticmethod
    def _compute_prompt_hash(prompt: str | dict | list, llm_key: str, model_config: dict[str, Any] | None) -> str:
        """
        Compute a deterministic hash for a prompt + model configuration.
        
        Args:
            prompt: The prompt text or structured messages
            llm_key: The LLM model key identifier
            model_config: Optional model configuration parameters
        
        Returns:
            SHA256 hash of the normalized prompt + config
        """
        # Normalize prompt to string
        if isinstance(prompt, (dict, list)):
            prompt_str = json.dumps(prompt, sort_keys=True)
        else:
            prompt_str = str(prompt)
        
        # Include relevant config params in hash (excluding non-deterministic fields)
        config_for_hash = {}
        if model_config:
            # Only include parameters that affect output determinism
            relevant_keys = ["temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty"]
            config_for_hash = {k: v for k, v in model_config.items() if k in relevant_keys}
        
        # Combine all components
        hash_input = f"{llm_key}:{prompt_str}:{json.dumps(config_for_hash, sort_keys=True)}"
        
        return hashlib.sha256(hash_input.encode()).hexdigest()

    @staticmethod
    async def get_cached_response(
        session: AsyncSession,
        prompt: str | dict | list,
        llm_key: str,
        model_config: dict[str, Any] | None = None,
        organization_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Retrieve a cached response for the given prompt and model configuration.
        
        Args:
            session: Database session
            prompt: The prompt to look up
            llm_key: The LLM model key
            model_config: Optional model configuration
            organization_id: Optional organization ID for multi-tenant filtering
        
        Returns:
            Cached response payload if found and not expired, None otherwise
        """
        if not settings.ENABLE_PROMPT_CACHE:
            return None
        
        prompt_hash = PromptCacheService._compute_prompt_hash(prompt, llm_key, model_config)
        
        try:
            # Build query
            query = select(PromptCacheModel).where(
                and_(
                    PromptCacheModel.prompt_hash == prompt_hash,
                    PromptCacheModel.llm_key == llm_key,
                )
            )
            
            # Add organization filter if provided
            if organization_id:
                query = query.where(PromptCacheModel.organization_id == organization_id)
            
            # Filter out expired entries
            now = datetime.utcnow()
            query = query.where(
                or_(
                    PromptCacheModel.ttl_expires_at.is_(None),
                    PromptCacheModel.ttl_expires_at > now,
                )
            )
            
            result = await session.execute(query)
            cache_entry = result.scalar_one_or_none()
            
            if cache_entry:
                # Update access time and hit count
                await session.execute(
                    update(PromptCacheModel)
                    .where(PromptCacheModel.prompt_cache_id == cache_entry.prompt_cache_id)
                    .values(
                        accessed_at=now,
                        hit_count=PromptCacheModel.hit_count + 1,
                    )
                )
                await session.commit()
                
                LOG.info(
                    "Prompt cache hit",
                    prompt_cache_id=cache_entry.prompt_cache_id,
                    llm_key=llm_key,
                    hit_count=cache_entry.hit_count + 1,
                )
                
                return cache_entry.response_payload
            
            LOG.debug("Prompt cache miss", prompt_hash=prompt_hash, llm_key=llm_key)
            return None
            
        except Exception as e:
            LOG.error("Error retrieving cached response", error=str(e), llm_key=llm_key)
            return None

    @staticmethod
    async def save_cached_response(
        session: AsyncSession,
        prompt: str | dict | list,
        llm_key: str,
        response_payload: dict[str, Any],
        model_config: dict[str, Any] | None = None,
        organization_id: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        reasoning_tokens: int | None = None,
        cached_tokens: int | None = None,
        cache_cost: float | None = None,
    ) -> str | None:
        """
        Save a response to the cache.
        
        Args:
            session: Database session
            prompt: The prompt that generated this response
            llm_key: The LLM model key
            response_payload: The complete response from the LLM
            model_config: Optional model configuration
            organization_id: Optional organization ID
            input_tokens: Token count for input
            output_tokens: Token count for output
            reasoning_tokens: Token count for reasoning
            cached_tokens: Token count from cache
            cache_cost: Cost of this LLM call
        
        Returns:
            The prompt_cache_id if saved successfully, None otherwise
        """
        if not settings.ENABLE_PROMPT_CACHE:
            return None
        
        prompt_hash = PromptCacheService._compute_prompt_hash(prompt, llm_key, model_config)
        
        # Normalize prompt to string for storage
        if isinstance(prompt, (dict, list)):
            prompt_text = json.dumps(prompt, sort_keys=True)
        else:
            prompt_text = str(prompt)
        
        try:
            # Calculate TTL expiration
            ttl_expires_at = None
            if settings.PROMPT_CACHE_TTL_HOURS > 0:
                ttl_expires_at = datetime.utcnow() + timedelta(hours=settings.PROMPT_CACHE_TTL_HOURS)
            
            cache_entry = PromptCacheModel(
                organization_id=organization_id,
                prompt_hash=prompt_hash,
                llm_key=llm_key,
                model_config=model_config,
                prompt_text=prompt_text,
                response_payload=response_payload,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                reasoning_tokens=reasoning_tokens,
                cached_tokens=cached_tokens,
                cache_cost=cache_cost,
                ttl_expires_at=ttl_expires_at,
            )
            
            session.add(cache_entry)
            await session.commit()
            
            LOG.info(
                "Saved prompt to cache",
                prompt_cache_id=cache_entry.prompt_cache_id,
                llm_key=llm_key,
                ttl_expires_at=ttl_expires_at,
            )
            
            return cache_entry.prompt_cache_id
            
        except Exception as e:
            LOG.error("Error saving response to cache", error=str(e), llm_key=llm_key)
            await session.rollback()
            return None

    @staticmethod
    async def evict_expired_entries(session: AsyncSession) -> int:
        """
        Remove expired cache entries from the database.
        
        Args:
            session: Database session
        
        Returns:
            Number of entries evicted
        """
        if not settings.PROMPT_CACHE_EVICTION_ENABLED:
            return 0
        
        try:
            now = datetime.utcnow()
            
            # Delete expired entries
            result = await session.execute(
                delete(PromptCacheModel).where(
                    and_(
                        PromptCacheModel.ttl_expires_at.isnot(None),
                        PromptCacheModel.ttl_expires_at <= now,
                    )
                )
            )
            await session.commit()
            
            evicted_count = result.rowcount
            if evicted_count > 0:
                LOG.info("Evicted expired prompt cache entries", count=evicted_count)
            
            return evicted_count
            
        except Exception as e:
            LOG.error("Error evicting expired cache entries", error=str(e))
            await session.rollback()
            return 0

    @staticmethod
    async def get_cache_entry_by_id(
        session: AsyncSession,
        prompt_cache_id: str,
    ) -> PromptCacheModel | None:
        """
        Retrieve a specific cache entry by ID for replay purposes.
        
        Args:
            session: Database session
            prompt_cache_id: The cache entry ID
        
        Returns:
            The cache entry model if found, None otherwise
        """
        try:
            result = await session.execute(
                select(PromptCacheModel).where(PromptCacheModel.prompt_cache_id == prompt_cache_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            LOG.error("Error retrieving cache entry by ID", error=str(e), prompt_cache_id=prompt_cache_id)
            return None

    @staticmethod
    async def replay_cached_prompt(
        session: AsyncSession,
        prompt_cache_id: str,
    ) -> dict[str, Any] | None:
        """
        Replay a cached prompt response for debugging or benchmarking.
        
        Args:
            session: Database session
            prompt_cache_id: The cache entry ID to replay
        
        Returns:
            The cached response payload if found, None otherwise
        """
        if not settings.ENABLE_PROMPT_CACHE_REPLAY:
            LOG.warning("Prompt cache replay is disabled")
            return None
        
        cache_entry = await PromptCacheService.get_cache_entry_by_id(session, prompt_cache_id)
        
        if cache_entry:
            LOG.info(
                "Replaying cached prompt",
                prompt_cache_id=prompt_cache_id,
                llm_key=cache_entry.llm_key,
                original_created_at=cache_entry.created_at,
            )
            return cache_entry.response_payload
        
        LOG.warning("Cache entry not found for replay", prompt_cache_id=prompt_cache_id)
        return None
