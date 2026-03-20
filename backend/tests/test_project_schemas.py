"""Schema field tests for ProjectResponse and SubmitRequest."""
import uuid
from datetime import datetime, timezone

from app.schemas.jobs import SubmitRequest
from app.schemas.projects import ProjectResponse


def test_project_response_has_new_fields():
    now = datetime.now(timezone.utc)
    proj = ProjectResponse(
        id=uuid.uuid4(), name="test", pdk="sky130hd",
        storage_bytes=0, created_at=now, run_count=0,
    )
    assert proj.config_version == 0
    assert proj.verilog_version == 0
    assert proj.latest_source_path is None


def test_submit_request_accepts_notes():
    req = SubmitRequest(project_id=uuid.uuid4(), notes="my note")
    assert req.notes == "my note"


def test_submit_request_notes_defaults_none():
    req = SubmitRequest(project_id=uuid.uuid4())
    assert req.notes is None


def test_config_overrides_str_values():
    req = SubmitRequest(
        project_id=uuid.uuid4(),
        config_overrides={"CLOCK_PERIOD": "8", "CORE_UTILIZATION": "40"},
    )
    assert req.config_overrides == {"CLOCK_PERIOD": "8", "CORE_UTILIZATION": "40"}
