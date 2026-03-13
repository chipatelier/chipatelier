"""Wave 0 stub: metrics parsing and storage tests — implemented in plan 01-03."""
import pytest


async def test_ppa_metrics_stored_in_jsonb(async_session):
    """PPA metrics are stored in the ppa JSONB column of the runs table."""
    pass


async def test_config_snapshot_stored_separately(async_session):
    """config.mk snapshot is stored in the config JSONB column, separate from ppa."""
    pass


async def test_stage_metrics_tracked(async_session):
    """Per-stage runtimes and cell counts are stored in stage_metrics."""
    pass
