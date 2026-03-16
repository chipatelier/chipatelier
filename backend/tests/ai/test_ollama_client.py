"""
Unit tests for OllamaClient — all tests mock the underlying ollama.AsyncClient
to avoid requiring a real Ollama instance.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.llm_client import OllamaClient


def _make_client(base_url: str = "http://localhost:11434", model: str = "deepseek-r1:7b"):
    """Create an OllamaClient and replace its internal _client with a mock."""
    client = OllamaClient(base_url=base_url, model=model)
    client._client = AsyncMock()
    return client


async def test_generate_returns_stripped_response():
    """OllamaClient.generate() strips <think> tags from the response."""
    client = _make_client()
    client._client.generate = AsyncMock(
        return_value={"response": "<think>reasoning block</think>\nThe answer is 42"}
    )
    result = await client.generate("test prompt")
    assert result == "The answer is 42"
    assert "<think>" not in result


async def test_generate_strips_multiline_think_tags():
    """OllamaClient.generate() strips multi-line <think> blocks."""
    client = _make_client()
    client._client.generate = AsyncMock(
        return_value={
            "response": (
                "<think>\n"
                "Let me analyze this step by step...\n"
                "Considering the timing violations...\n"
                "</think>\n\n"
                "Your WNS is too negative. Try increasing CLOCK_PERIOD."
            )
        }
    )
    result = await client.generate("explain timing")
    assert "think" not in result.lower()
    assert "WNS is too negative" in result


async def test_generate_no_think_tags_passes_through():
    """OllamaClient.generate() passes through responses with no <think> tags."""
    client = _make_client()
    client._client.generate = AsyncMock(
        return_value={"response": "  The placement density is too high.  "}
    )
    result = await client.generate("test")
    # Result should be stripped of surrounding whitespace
    assert result == "The placement density is too high."
    assert "<think>" not in result


async def test_warm_up_succeeds():
    """OllamaClient.warm_up() completes without error when Ollama responds."""
    client = _make_client()
    client._client.generate = AsyncMock(return_value={"response": ""})
    # Should not raise
    await client.warm_up()
    client._client.generate.assert_called_once()


async def test_warm_up_retries_on_failure():
    """OllamaClient.warm_up() retries 3 times when Ollama fails then succeeds."""
    client = _make_client()
    # Fail twice, then succeed on third attempt
    client._client.generate = AsyncMock(
        side_effect=[
            Exception("Connection refused"),
            Exception("Connection refused"),
            {"response": ""},
        ]
    )

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await client.warm_up()

    assert client._client.generate.call_count == 3
    # Should have slept between attempts 1→2 and 2→3
    assert mock_sleep.call_count == 2


async def test_warm_up_handles_total_failure():
    """OllamaClient.warm_up() swallows all exceptions after 3 failed attempts."""
    client = _make_client()
    client._client.generate = AsyncMock(
        side_effect=Exception("Ollama not running")
    )

    with patch("asyncio.sleep", new_callable=AsyncMock):
        # Should NOT raise — warm_up failure is non-fatal
        await client.warm_up()

    assert client._client.generate.call_count == 3
