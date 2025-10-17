import hashlib
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skyvern.config import settings
from skyvern.forge.sdk.api.llm.prompt_cache import PromptCacheService
from skyvern.forge.sdk.db.models import PromptCacheModel


class TestPromptCacheService:
    """Unit tests for PromptCacheService."""

    def test_compute_prompt_hash_string(self) -> None:
        """Test hash computation for string prompts."""
        prompt = "What is the capital of France?"
        llm_key = "OPENAI_GPT4O"
        config = {"temperature": 0, "max_tokens": 100}
        
        hash1 = PromptCacheService._compute_prompt_hash(prompt, llm_key, config)
        hash2 = PromptCacheService._compute_prompt_hash(prompt, llm_key, config)
        
        # Same input should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 hex characters

    def test_compute_prompt_hash_dict(self) -> None:
        """Test hash computation for structured prompts."""
        prompt = {"role": "user", "content": "Hello"}
        llm_key = "OPENAI_GPT4O"
        
        hash1 = PromptCacheService._compute_prompt_hash(prompt, llm_key, None)
        
        # Same dict with different order should produce same hash (sorted)
        prompt2 = {"content": "Hello", "role": "user"}
        hash2 = PromptCacheService._compute_prompt_hash(prompt2, llm_key, None)
        
        assert hash1 == hash2

    def test_compute_prompt_hash_different_llm_keys(self) -> None:
        """Test that different LLM keys produce different hashes."""
        prompt = "What is 2+2?"
        config = {"temperature": 0}
        
        hash1 = PromptCacheService._compute_prompt_hash(prompt, "OPENAI_GPT4O", config)
        hash2 = PromptCacheService._compute_prompt_hash(prompt, "ANTHROPIC_CLAUDE3", config)
        
        assert hash1 != hash2

    def test_compute_prompt_hash_ignores_irrelevant_config(self) -> None:
        """Test that irrelevant config params don't affect hash."""
        prompt = "Test prompt"
        llm_key = "OPENAI_GPT4O"
        
        config1 = {"temperature": 0, "timeout": 60, "retry": 3}
        config2 = {"temperature": 0, "timeout": 120, "retry": 5}
        
        hash1 = PromptCacheService._compute_prompt_hash(prompt, llm_key, config1)
        hash2 = PromptCacheService._compute_prompt_hash(prompt, llm_key, config2)
        
        # Should be same since timeout and retry are not relevant for determinism
        assert hash1 == hash2

    def test_compute_prompt_hash_temperature_affects_hash(self) -> None:
        """Test that temperature changes affect hash."""
        prompt = "Test prompt"
        llm_key = "OPENAI_GPT4O"
        
        config1 = {"temperature": 0}
        config2 = {"temperature": 0.7}
        
        hash1 = PromptCacheService._compute_prompt_hash(prompt, llm_key, config1)
        hash2 = PromptCacheService._compute_prompt_hash(prompt, llm_key, config2)
        
        # Different temperatures should produce different hashes
        assert hash1 != hash2

    @pytest.mark.asyncio
    async def test_get_cached_response_disabled(self) -> None:
        """Test that caching returns None when disabled."""
        with patch.object(settings, "ENABLE_PROMPT_CACHE", False):
            session = AsyncMock(spec=AsyncSession)
            result = await PromptCacheService.get_cached_response(
                session, "test", "OPENAI_GPT4O"
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_get_cached_response_not_found(self) -> None:
        """Test cache miss scenario."""
        with patch.object(settings, "ENABLE_PROMPT_CACHE", True):
            session = AsyncMock(spec=AsyncSession)
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None
            session.execute.return_value = mock_result
            
            result = await PromptCacheService.get_cached_response(
                session, "test", "OPENAI_GPT4O"
            )
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_cached_response_hit(self) -> None:
        """Test cache hit scenario."""
        with patch.object(settings, "ENABLE_PROMPT_CACHE", True):
            session = AsyncMock(spec=AsyncSession)
            
            # Mock cache entry
            cache_entry = Mock(spec=PromptCacheModel)
            cache_entry.prompt_cache_id = "pcache_123"
            cache_entry.response_payload = {"result": "cached response"}
            cache_entry.hit_count = 5
            
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = cache_entry
            session.execute.return_value = mock_result
            
            result = await PromptCacheService.get_cached_response(
                session, "test", "OPENAI_GPT4O"
            )
            
            assert result == {"result": "cached response"}
            session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_cached_response_disabled(self) -> None:
        """Test that saving does nothing when disabled."""
        with patch.object(settings, "ENABLE_PROMPT_CACHE", False):
            session = AsyncMock(spec=AsyncSession)
            result = await PromptCacheService.save_cached_response(
                session, "test", "OPENAI_GPT4O", {"response": "data"}
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_save_cached_response_success(self) -> None:
        """Test successful cache save."""
        with patch.object(settings, "ENABLE_PROMPT_CACHE", True):
            with patch.object(settings, "PROMPT_CACHE_TTL_HOURS", 24):
                session = AsyncMock(spec=AsyncSession)
                
                result = await PromptCacheService.save_cached_response(
                    session,
                    "test prompt",
                    "OPENAI_GPT4O",
                    {"response": "data"},
                    model_config={"temperature": 0},
                    organization_id="org_123",
                    input_tokens=100,
                    output_tokens=50,
                )
                
                # Should add entry and commit
                session.add.assert_called_once()
                session.commit.assert_called_once()
                assert result is not None

    @pytest.mark.asyncio
    async def test_evict_expired_entries_disabled(self) -> None:
        """Test eviction does nothing when disabled."""
        with patch.object(settings, "PROMPT_CACHE_EVICTION_ENABLED", False):
            session = AsyncMock(spec=AsyncSession)
            result = await PromptCacheService.evict_expired_entries(session)
            assert result == 0

    @pytest.mark.asyncio
    async def test_evict_expired_entries_success(self) -> None:
        """Test successful eviction."""
        with patch.object(settings, "PROMPT_CACHE_EVICTION_ENABLED", True):
            session = AsyncMock(spec=AsyncSession)
            
            mock_result = Mock()
            mock_result.rowcount = 5
            session.execute.return_value = mock_result
            
            result = await PromptCacheService.evict_expired_entries(session)
            
            assert result == 5
            session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_replay_cached_prompt_disabled(self) -> None:
        """Test replay returns None when disabled."""
        with patch.object(settings, "ENABLE_PROMPT_CACHE_REPLAY", False):
            session = AsyncMock(spec=AsyncSession)
            result = await PromptCacheService.replay_cached_prompt(session, "pcache_123")
            assert result is None

    @pytest.mark.asyncio
    async def test_replay_cached_prompt_not_found(self) -> None:
        """Test replay when cache entry doesn't exist."""
        with patch.object(settings, "ENABLE_PROMPT_CACHE_REPLAY", True):
            session = AsyncMock(spec=AsyncSession)
            
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None
            session.execute.return_value = mock_result
            
            result = await PromptCacheService.replay_cached_prompt(session, "pcache_123")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_replay_cached_prompt_success(self) -> None:
        """Test successful replay."""
        with patch.object(settings, "ENABLE_PROMPT_CACHE_REPLAY", True):
            session = AsyncMock(spec=AsyncSession)
            
            cache_entry = Mock(spec=PromptCacheModel)
            cache_entry.prompt_cache_id = "pcache_123"
            cache_entry.llm_key = "OPENAI_GPT4O"
            cache_entry.response_payload = {"result": "replayed response"}
            cache_entry.created_at = datetime.utcnow()
            
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = cache_entry
            session.execute.return_value = mock_result
            
            result = await PromptCacheService.replay_cached_prompt(session, "pcache_123")
            
            assert result == {"result": "replayed response"}
