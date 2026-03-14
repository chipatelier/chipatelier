"""
Pluggable LLM client supporting Ollama (default), Anthropic, and OpenAI.

Phase 3 implements the actual generate() method bodies.
Phase 1 scaffolds the interface and warm-on-startup hook.

Selection via LLM_BACKEND env var: "ollama" | "anthropic" | "openai"

Privacy constraint (CLAUDE.md):
  Design data NEVER leaves the server via this client.
  context_builder.py enforces this by only including log_tail, ppa, and config.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.config import get_settings


class LLMClient(ABC):
    """Abstract base class for LLM backends."""

    @abstractmethod
    async def generate(self, prompt: str, max_tokens: int = 1024) -> str:
        """Generate a completion for the given prompt."""
        ...

    async def warm_up(self) -> None:
        """Pre-load the model to avoid first-request hang. Called on service startup."""
        pass


class OllamaClient(LLMClient):
    """Ollama local LLM client (default — keeps design data on-premise).

    Phase 3 implementation: POST {base_url}/api/generate, stream response.
    """

    def __init__(self, base_url: str, model: str = "llama3.2:3b"):
        self._base_url = base_url
        self._model = model

    async def warm_up(self) -> None:
        """Send a trivial generation request to load the model into memory.

        Phase 3 implementation: POST {base_url}/api/generate with empty prompt.
        MVP stub — no-op (model loads on first real request).
        """
        pass

    async def generate(self, prompt: str, max_tokens: int = 1024) -> str:
        """Generate a completion via Ollama API.

        Phase 3 implementation: POST {base_url}/api/generate, stream response.
        """
        raise NotImplementedError("Ollama AI features available in Phase 3")


class AnthropicClient(LLMClient):
    """Anthropic Claude client (optional cloud LLM — requires ANTHROPIC_API_KEY).

    Only use for non-sensitive prompts (log explanations, not design files).
    """

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def generate(self, prompt: str, max_tokens: int = 1024) -> str:
        raise NotImplementedError("Anthropic AI features available in Phase 3")


class OpenAIClient(LLMClient):
    """OpenAI client (optional cloud LLM — requires OPENAI_API_KEY)."""

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def generate(self, prompt: str, max_tokens: int = 1024) -> str:
        raise NotImplementedError("OpenAI AI features available in Phase 3")


def get_llm_client() -> LLMClient:
    """Return the configured LLM client based on LLM_BACKEND env var.

    Default: OllamaClient (local, on-premise — design data stays on server).
    """
    settings = get_settings()
    if settings.LLM_BACKEND == "anthropic":
        return AnthropicClient(api_key=settings.ANTHROPIC_API_KEY)
    if settings.LLM_BACKEND == "openai":
        return OpenAIClient(api_key=settings.ANTHROPIC_API_KEY)  # placeholder
    # Default: Ollama (local inference)
    return OllamaClient(base_url=settings.OLLAMA_BASE_URL)
