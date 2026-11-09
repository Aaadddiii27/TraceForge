"""
Model Provider Abstraction.

Defines the interface all providers must implement, and provides:
- MockProvider: deterministic, no API key, works offline
- OpenAIProvider: optional, gated by OPENAI_API_KEY env var
- GeminiProvider: optional, gated by GEMINI_API_KEY env var
"""
from __future__ import annotations

import abc
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class ProviderError(Exception):
    """Raised when a provider call fails."""
    def __init__(self, message: str, retriable: bool = False) -> None:
        super().__init__(message)
        self.retriable = retriable


class ModelResponse:
    """Structured response from a model provider."""
    def __init__(
        self,
        content: str,
        model: str,
        provider: str,
        token_usage_input: int = 0,
        token_usage_output: int = 0,
        estimated_cost_usd: float | None = None,
        raw_response: dict[str, Any] | None = None,
    ) -> None:
        self.content = content
        self.model = model
        self.provider = provider
        self.token_usage_input = token_usage_input
        self.token_usage_output = token_usage_output
        self.estimated_cost_usd = estimated_cost_usd
        self.raw_response = raw_response or {}


class BaseProvider(abc.ABC):
    """Abstract base for model providers."""

    name: str

    @abc.abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> ModelResponse:
        """Send a completion request and return a structured response."""
        ...

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider is configured and available."""
        ...


# ─── Mock Provider ────────────────────────────────────────────────────────────

class MockProvider(BaseProvider):
    """
    Deterministic mock provider. No API key required.

    Returns predictable responses based on the prompt content,
    useful for local development, testing, and CI.
    """
    name = "mock"

    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> ModelResponse:
        # Produce a deterministic, prompt-length-proportional response
        words = prompt.strip().split()
        word_count = len(words)

        response_content = (
            f"[MockProvider] Received prompt with {word_count} words. "
            f"System: '{system_prompt[:50]}...' " if system_prompt else
            f"[MockProvider] Received prompt with {word_count} words. "
        )
        response_content += "This is a deterministic mock response. No external API was called."

        return ModelResponse(
            content=response_content,
            model="mock-v1",
            provider="mock",
            token_usage_input=word_count,
            token_usage_output=len(response_content.split()),
            estimated_cost_usd=0.0,
        )

    def is_available(self) -> bool:
        return True


# ─── OpenAI Provider ─────────────────────────────────────────────────────────

class OpenAIProvider(BaseProvider):
    """Optional OpenAI provider. Requires OPENAI_API_KEY environment variable."""
    name = "openai"

    def __init__(self) -> None:
        self._client: Any = None
        self._model: str = "gpt-4o-mini"
        self._max_tokens: int = 1000

    def _ensure_client(self) -> None:
        from app.core.config import settings
        if not settings.openai_api_key:
            raise ProviderError(
                "OpenAI provider is not configured. Set OPENAI_API_KEY in your .env file.",
                retriable=False,
            )
        if self._client is None:
            try:
                import openai
                self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
                self._model = settings.openai_default_model
                self._max_tokens = settings.openai_max_tokens
            except ImportError:
                raise ProviderError(
                    "openai package not installed. Run: pip install 'ai-runtime-backend[openai]'",
                    retriable=False,
                )

    def is_available(self) -> bool:
        from app.core.config import settings
        return bool(settings.openai_api_key)

    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> ModelResponse:
        self._ensure_client()
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            content = resp.choices[0].message.content or ""
            usage = resp.usage
            return ModelResponse(
                content=content,
                model=self._model,
                provider="openai",
                token_usage_input=usage.prompt_tokens if usage else 0,
                token_usage_output=usage.completion_tokens if usage else 0,
            )
        except Exception as exc:
            raise ProviderError(f"OpenAI API error: {exc}", retriable=True) from exc


# ─── Gemini Provider ─────────────────────────────────────────────────────────

class GeminiProvider(BaseProvider):
    """Optional Google Gemini provider. Requires GEMINI_API_KEY environment variable."""
    name = "gemini"

    def __init__(self) -> None:
        self._client: Any = None
        self._model_name: str = "gemini-1.5-flash"
        self._max_tokens: int = 1000

    def _ensure_client(self) -> None:
        from app.core.config import settings
        if not settings.gemini_api_key:
            raise ProviderError(
                "Gemini provider is not configured. Set GEMINI_API_KEY in your .env file.",
                retriable=False,
            )
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.gemini_api_key)
                self._model_name = settings.gemini_default_model
                self._max_tokens = settings.gemini_max_tokens
                self._client = genai.GenerativeModel(self._model_name)
            except ImportError:
                raise ProviderError(
                    "google-generativeai package not installed. "
                    "Run: pip install 'ai-runtime-backend[gemini]'",
                    retriable=False,
                )

    def is_available(self) -> bool:
        from app.core.config import settings
        return bool(settings.gemini_api_key)

    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> ModelResponse:
        self._ensure_client()
        full_prompt = f"{system_prompt}\n\n{prompt}".strip() if system_prompt else prompt
        try:
            resp = await self._client.generate_content_async(
                full_prompt,
                generation_config={"max_output_tokens": max_tokens, "temperature": temperature},
            )
            content = resp.text or ""
            return ModelResponse(
                content=content,
                model=self._model_name,
                provider="gemini",
                token_usage_input=0,  # Gemini doesn't always return token counts
                token_usage_output=0,
            )
        except Exception as exc:
            raise ProviderError(f"Gemini API error: {exc}", retriable=True) from exc


# ─── Provider Registry ────────────────────────────────────────────────────────

class ProviderRegistry:
    """Registry of available model providers."""

    def __init__(self) -> None:
        self._providers: dict[str, BaseProvider] = {}

    def register(self, provider: BaseProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> BaseProvider | None:
        return self._providers.get(name)

    def get_or_raise(self, name: str) -> BaseProvider:
        provider = self._providers.get(name)
        if provider is None:
            available = list(self._providers.keys())
            raise ProviderError(
                f"Provider '{name}' is not registered. Available: {available}",
                retriable=False,
            )
        if not provider.is_available():
            raise ProviderError(
                f"Provider '{name}' is registered but not configured. "
                "Check environment variables.",
                retriable=False,
            )
        return provider

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())


# Module-level singleton
provider_registry = ProviderRegistry()


def register_providers() -> None:
    """Register all provider adapters."""
    provider_registry.register(MockProvider())
    provider_registry.register(OpenAIProvider())
    provider_registry.register(GeminiProvider())
