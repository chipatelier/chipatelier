"""
Wave 0 pytest fixtures for Phase 3 AI tests.

Provides: mock_llm_client, sample_run_context.
"""
import pytest
from unittest.mock import AsyncMock


@pytest.fixture
def mock_llm_client():
    """Mocked OllamaClient that returns canned AI responses."""
    client = AsyncMock()
    client.generate = AsyncMock(return_value="This is a mock AI explanation.")
    client.warm_up = AsyncMock(return_value=None)

    # chat_stream returns an async iterator of chunks
    async def _mock_stream(*args, **kwargs):
        chunks = [
            {"message": {"content": "Hello"}},
            {"message": {"content": " world"}},
        ]
        for c in chunks:
            yield c

    client.chat_stream = AsyncMock(side_effect=_mock_stream)
    return client


@pytest.fixture
def sample_run_context():
    """Sample context dict matching build_run_context() output shape."""
    return {
        "run_id": "00000000-0000-0000-0000-000000000001",
        "status": "complete",
        "stage_completed": "route",
        "target_stage": "finish",
        "ppa": {
            "worst_negative_slack": -2.3,
            "total_negative_slack": -15.7,
            "drc_routing_errors": 0,
            "core_area": 1070.65,
            "total_power": 0.00073,
        },
        "config": {
            "DESIGN_NAME": "gcd",
            "PLATFORM": "sky130hd",
            "CLOCK_PERIOD": "10",
            "CORE_UTILIZATION": "40",
        },
        "log_tail": [
            "[INFO FLW-0012] Running stage route",
            "[WARNING DRT-0001] 3 DRC violations found",
            "[INFO FLW-0036] Elapsed time: 0:02:15",
        ],
        "design_name": "gcd",
    }
