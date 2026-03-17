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

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from typing import AsyncIterator

from ollama import AsyncClient as OllamaAsyncClient

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

    Uses the ollama Python AsyncClient (0.6.1) for async inference.
    Strips <think>...</think> reasoning tags from deepseek-r1 responses.
    """

    def __init__(self, base_url: str, model: str = "deepseek-r1:7b"):
        self._client = OllamaAsyncClient(host=base_url)
        self._model = model

    async def generate(self, prompt: str, max_tokens: int = 1024) -> str:
        """Generate a completion via Ollama API (non-streaming).

        Strips <think>...</think> reasoning traces emitted by deepseek-r1 models.
        """
        response = await self._client.generate(
            model=self._model,
            prompt=prompt,
            options={"num_predict": max_tokens, "num_ctx": 8192},
            stream=False,
            keep_alive=-1,
        )
        raw = response["response"]
        return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    async def chat_stream(self, messages: list[dict]) -> AsyncIterator:
        """Stream a multi-turn chat response via Ollama API.

        Returns an async iterator of chunk dicts with shape:
            {"message": {"content": "<token>"}}
        """
        return await self._client.chat(
            model=self._model,
            messages=messages,
            stream=True,
            options={"num_ctx": 8192, "num_predict": 512},
            keep_alive=-1,
        )

    async def warm_up(self) -> None:
        """Pre-load model into memory with keep_alive=-1 to pin it.

        Retries 3 times with 5-second backoff to handle Ollama container
        startup race conditions. Non-fatal if all attempts fail — model
        loads on first real request (with cold-start delay).
        """
        log = logging.getLogger("chipatelier.ai")
        for attempt in range(1, 4):
            try:
                await self._client.generate(model=self._model, prompt="", keep_alive=-1)
                log.info("Ollama model %s warmed up successfully", self._model)
                return
            except Exception as exc:
                log.warning("Ollama warm-up attempt %d/3 failed: %s", attempt, exc)
                if attempt < 3:
                    await asyncio.sleep(5)
        log.warning("Ollama warm-up failed after 3 attempts — model loads on first request")


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
        return OpenAIClient(api_key=getattr(settings, "OPENAI_API_KEY", ""))
    # Default: Ollama (local inference)
    return OllamaClient(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)
