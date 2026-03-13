"""Wave 0 stub: job API tests — implemented in plan 01-03."""
import pytest


async def test_submit_job(test_client, async_session, mock_redis):
    """POST /api/v1/jobs/submit creates a run and queues the Celery task."""
    pass


async def test_get_job_status(test_client, async_session):
    """GET /api/v1/jobs/{id} returns current job status and metrics."""
    pass


async def test_cancel_job(test_client, async_session, mock_redis):
    """DELETE /api/v1/jobs/{id} cancels a running job."""
    pass


async def test_job_log_history(test_client, async_session):
    """GET /api/v1/jobs/{id}/logs returns paginated log history."""
    pass
