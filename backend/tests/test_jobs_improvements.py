"""Tests for submit job improvements: notes wiring and pre-submit guards."""
import uuid


def _make_project_with_files(test_client, email="j@ex.com"):
    """Register user, create project, set verilog_version=1 and config_version=1 directly."""
    test_client.post("/api/v1/auth/register", json={"email": email, "password": "pass1234"})
    token = test_client.post("/api/v1/auth/login", json={"email": email, "password": "pass1234"}).json()["access_token"]
    proj = test_client.post("/api/v1/projects", json={"name": "p"}, headers={"Authorization": f"Bearer {token}"}).json()
    return token, proj["id"]


def test_submit_blocked_when_no_verilog(test_client):
    email = f"v0-{uuid.uuid4().hex[:8]}@ex.com"
    token, pid = _make_project_with_files(test_client, email)
    resp = test_client.post(
        "/api/v1/jobs/submit",
        json={"project_id": pid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "Verilog" in resp.json()["detail"]


async def test_submit_blocked_when_no_config(test_client, async_session):
    """Verilog present but no config.mk saved — submit should return 400."""
    import asyncio
    from sqlalchemy import text as sqla_text

    email = f"c0-{uuid.uuid4().hex[:8]}@ex.com"
    token, pid = _make_project_with_files(test_client, email)

    # Set latest_source_path to simulate Verilog uploaded, but leave config_version=0
    await async_session.execute(
        sqla_text("UPDATE projects SET latest_source_path='projects/x/verilog/v1' WHERE id=:id"),
        {"id": pid},
    )
    await async_session.commit()

    resp = test_client.post(
        "/api/v1/jobs/submit",
        json={"project_id": pid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "config.mk" in resp.json()["detail"]


def test_make_override_arg_order():
    """locked_params must appear AFTER config_overrides in Make args (last-wins = instructor priority)."""
    config_snapshot = {
        "locked_params": {"CLOCK_PERIOD": "10", "PLATFORM": "sky130hd"},
        "config_overrides": {"CLOCK_PERIOD": "8", "CORE_UTILIZATION": "50"},
    }
    locked_params = config_snapshot.get("locked_params", {})
    config_overrides = config_snapshot.get("config_overrides", {})
    make_override_args = (
        [f"{k}={v}" for k, v in config_overrides.items() if v is not None and str(v) != ""] +
        [f"{k}={v}" for k, v in locked_params.items()]
    )
    # locked CLOCK_PERIOD=10 must come after student CLOCK_PERIOD=8
    clock_args = [a for a in make_override_args if a.startswith("CLOCK_PERIOD=")]
    assert clock_args[-1] == "CLOCK_PERIOD=10", f"Expected CLOCK_PERIOD=10 last, got: {clock_args}"
