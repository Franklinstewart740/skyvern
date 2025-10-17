"""Utility functions for LLM telemetry."""

from typing import Any


def extract_provider_from_llm_key(llm_key: str) -> str:
    """Extract provider name from LLM key.
    
    Examples:
        openai/gpt-4 -> openai
        anthropic/claude-3-5-sonnet-20241022 -> anthropic
        gemini/gemini-2.0-flash-exp -> gemini
        gpt-4o -> openai (default)
    """
    if "/" in llm_key:
        return llm_key.split("/")[0]
    
    # Common patterns for extracting provider from model name
    if llm_key.startswith("gpt-") or llm_key.startswith("o1-") or llm_key.startswith("o3-"):
        return "openai"
    elif llm_key.startswith("claude-"):
        return "anthropic"
    elif llm_key.startswith("gemini-"):
        return "gemini"
    elif llm_key.startswith("bedrock"):
        return "bedrock"
    
    # If no pattern matches, return the first part before any special character
    for sep in ["-", "_", ":"]:
        if sep in llm_key:
            return llm_key.split(sep)[0]
    
    return llm_key


def extract_model_name_from_llm_key(llm_key: str, llm_config: Any) -> str | None:
    """Extract model name from LLM key or config."""
    if hasattr(llm_config, "model_name") and llm_config.model_name:
        return llm_config.model_name
    
    # If llm_key contains /, use the part after /
    if "/" in llm_key:
        return llm_key.split("/", 1)[1]
    
    return llm_key
