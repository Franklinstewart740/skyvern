"""
Integration tests for prompt cache that simulate repetitive task prompts.
These tests verify cache hit/miss behavior and eviction.
"""
import hashlib
import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select

from skyvern.config import settings
from skyvern.forge.sdk.api.llm.prompt_cache import PromptCacheService
from skyvern.forge.sdk.db.models import PromptCacheModel


class TestPromptCacheIntegration:
    """Integration tests for prompt cache with repetitive prompts."""

    @pytest.mark.asyncio
    async def test_repetitive_prompts_caching(self, test_db_session) -> None:
        """Test that repetitive prompts are cached and reused."""
        with patch.object(settings, "ENABLE_PROMPT_CACHE", True):
            with patch.object(settings, "PROMPT_CACHE_TTL_HOURS", 24):
                # Simulate a task that uses the same prompt multiple times
                prompt = "Extract the product name from this page"
                llm_key = "OPENAI_GPT4O"
                model_config = {"temperature": 0, "max_tokens": 100}
                
                # First call - should be a cache miss, so we save it
                response1 = {"choices": [{"message": {"content": "Product A"}}]}
                cache_id = await PromptCacheService.save_cached_response(
                    test_db_session,
                    prompt,
                    llm_key,
                    response1,
                    model_config=model_config,
                    input_tokens=10,
                    output_tokens=5,
                )
                
                assert cache_id is not None
                
                # Second call with same prompt - should be a cache hit
                cached_response = await PromptCacheService.get_cached_response(
                    test_db_session,
                    prompt,
                    llm_key,
                    model_config=model_config,
                )
                
                assert cached_response is not None
                assert cached_response == response1
                
                # Verify hit count increased
                result = await test_db_session.execute(
                    select(PromptCacheModel).where(PromptCacheModel.prompt_cache_id == cache_id)
                )
                entry = result.scalar_one()
                assert entry.hit_count == 1  # Hit count incremented

    @pytest.mark.asyncio
    async def test_different_prompts_no_collision(self, test_db_session) -> None:
        """Test that different prompts don't collide."""
        with patch.object(settings, "ENABLE_PROMPT_CACHE", True):
            with patch.object(settings, "PROMPT_CACHE_TTL_HOURS", 24):
                llm_key = "OPENAI_GPT4O"
                model_config = {"temperature": 0}
                
                # Save first prompt
                prompt1 = "What is 2+2?"
                response1 = {"choices": [{"message": {"content": "4"}}]}
                await PromptCacheService.save_cached_response(
                    test_db_session, prompt1, llm_key, response1, model_config=model_config
                )
                
                # Save second prompt
                prompt2 = "What is 3+3?"
                response2 = {"choices": [{"message": {"content": "6"}}]}
                await PromptCacheService.save_cached_response(
                    test_db_session, prompt2, llm_key, response2, model_config=model_config
                )
                
                # Retrieve each prompt and verify no collision
                cached1 = await PromptCacheService.get_cached_response(
                    test_db_session, prompt1, llm_key, model_config=model_config
                )
                cached2 = await PromptCacheService.get_cached_response(
                    test_db_session, prompt2, llm_key, model_config=model_config
                )
                
                assert cached1 == response1
                assert cached2 == response2
                assert cached1 != cached2

    @pytest.mark.asyncio
    async def test_config_variation_creates_new_cache(self, test_db_session) -> None:
        """Test that different configs create separate cache entries."""
        with patch.object(settings, "ENABLE_PROMPT_CACHE", True):
            with patch.object(settings, "PROMPT_CACHE_TTL_HOURS", 24):
                prompt = "What is the weather?"
                llm_key = "OPENAI_GPT4O"
                
                # Save with temperature 0
                config1 = {"temperature": 0}
                response1 = {"choices": [{"message": {"content": "Sunny"}}]}
                await PromptCacheService.save_cached_response(
                    test_db_session, prompt, llm_key, response1, model_config=config1
                )
                
                # Save with temperature 0.7 (should create new entry)
                config2 = {"temperature": 0.7}
                response2 = {"choices": [{"message": {"content": "Cloudy"}}]}
                await PromptCacheService.save_cached_response(
                    test_db_session, prompt, llm_key, response2, model_config=config2
                )
                
                # Verify both configs retrieve their own responses
                cached1 = await PromptCacheService.get_cached_response(
                    test_db_session, prompt, llm_key, model_config=config1
                )
                cached2 = await PromptCacheService.get_cached_response(
                    test_db_session, prompt, llm_key, model_config=config2
                )
                
                assert cached1 == response1
                assert cached2 == response2

    @pytest.mark.asyncio
    async def test_expired_cache_not_returned(self, test_db_session) -> None:
        """Test that expired cache entries are not returned."""
        with patch.object(settings, "ENABLE_PROMPT_CACHE", True):
            with patch.object(settings, "PROMPT_CACHE_TTL_HOURS", -1):  # Expire immediately
                prompt = "Test prompt"
                llm_key = "OPENAI_GPT4O"
                response = {"choices": [{"message": {"content": "Test"}}]}
                
                # Save with negative TTL (already expired)
                await PromptCacheService.save_cached_response(
                    test_db_session, prompt, llm_key, response
                )
                
                # Try to retrieve - should not find expired entry
                cached = await PromptCacheService.get_cached_response(
                    test_db_session, prompt, llm_key
                )
                
                assert cached is None

    @pytest.mark.asyncio
    async def test_eviction_removes_expired_entries(self, test_db_session) -> None:
        """Test that eviction removes expired cache entries."""
        with patch.object(settings, "ENABLE_PROMPT_CACHE", True):
            with patch.object(settings, "PROMPT_CACHE_EVICTION_ENABLED", True):
                # Create an expired entry manually
                expired_entry = PromptCacheModel(
                    organization_id="org_test",
                    prompt_hash=hashlib.sha256("expired".encode()).hexdigest(),
                    llm_key="OPENAI_GPT4O",
                    model_config={},
                    prompt_text="Expired prompt",
                    response_payload={"expired": True},
                    ttl_expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
                )
                test_db_session.add(expired_entry)
                await test_db_session.commit()
                
                # Create a non-expired entry
                active_entry = PromptCacheModel(
                    organization_id="org_test",
                    prompt_hash=hashlib.sha256("active".encode()).hexdigest(),
                    llm_key="OPENAI_GPT4O",
                    model_config={},
                    prompt_text="Active prompt",
                    response_payload={"active": True},
                    ttl_expires_at=datetime.utcnow() + timedelta(hours=24),  # Expires in 24 hours
                )
                test_db_session.add(active_entry)
                await test_db_session.commit()
                
                # Run eviction
                evicted_count = await PromptCacheService.evict_expired_entries(test_db_session)
                
                # Should have evicted the expired entry
                assert evicted_count == 1
                
                # Verify expired entry is gone
                result = await test_db_session.execute(
                    select(PromptCacheModel).where(
                        PromptCacheModel.prompt_cache_id == expired_entry.prompt_cache_id
                    )
                )
                assert result.scalar_one_or_none() is None
                
                # Verify active entry still exists
                result = await test_db_session.execute(
                    select(PromptCacheModel).where(
                        PromptCacheModel.prompt_cache_id == active_entry.prompt_cache_id
                    )
                )
                assert result.scalar_one_or_none() is not None


# Fixture for database session (simplified - actual implementation would use proper fixtures)
@pytest.fixture
async def test_db_session():
    """
    Simplified fixture for testing. In real implementation, this would:
    - Set up a test database
    - Create tables
    - Provide a session
    - Clean up after tests
    """
    from unittest.mock import AsyncMock
    
    # This is a simplified mock for demonstration
    # Real implementation would use an actual test database
    mock_session = AsyncMock()
    
    # Mock execute to return appropriate results
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    yield mock_session
