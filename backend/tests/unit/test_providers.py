"""
Unit tests for model providers and registry.
"""
from __future__ import annotations

import pytest

from app.providers import (
    GeminiProvider,
    MockProvider,
    OpenAIProvider,
    ProviderError,
    provider_registry,
)


@pytest.mark.asyncio
async def test_mock_provider_deterministic_response():
    provider = MockProvider()
    assert provider.is_available() is True

    resp = await provider.complete(prompt="Calculate the sum of two integers")
    assert resp.provider == "mock"
    assert "MockProvider" in resp.content
    assert resp.token_usage_input > 0


@pytest.mark.asyncio
async def test_provider_registry():
    assert provider_registry.get("mock") is not None
    assert provider_registry.get("openai") is not None
    assert provider_registry.get("gemini") is not None

    mock = provider_registry.get_or_raise("mock")
    assert mock.name == "mock"

    with pytest.raises(ProviderError, match="not registered"):
        provider_registry.get_or_raise("non_existent_provider")


@pytest.mark.asyncio
async def test_unconfigured_providers_raise_on_complete():
    # OpenAI and Gemini should raise ProviderError if no API key is provided
    openai_prov = OpenAIProvider()
    assert openai_prov.is_available() is False

    with pytest.raises(ProviderError, match="not configured"):
        await openai_prov.complete(prompt="Hello")

    gemini_prov = GeminiProvider()
    assert gemini_prov.is_available() is False

    with pytest.raises(ProviderError, match="not configured"):
        await gemini_prov.complete(prompt="Hello")
