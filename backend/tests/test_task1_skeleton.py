"""
Task 1 TDD tests: Docker Compose stack, environment, and backend skeleton.
RED phase - these tests define expected behavior.
"""
import pytest
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestHealthEndpoint:
    """GET /healthz returns correct structure."""

    def test_healthz_responds(self, test_client):
        """Health endpoint responds (200 or 503, not 404)."""
        response = test_client.get("/healthz")
        assert response.status_code in (200, 503)

    def test_healthz_response_structure(self, test_client):
        """Health response has status, db, and redis fields."""
        response = test_client.get("/healthz")
        data = response.json()
        assert "status" in data
        assert "db" in data
        assert "redis" in data

    def test_healthz_status_field_is_string(self, test_client):
        """Health response status field is a string."""
        response = test_client.get("/healthz")
        data = response.json()
        assert isinstance(data["status"], str)


class TestSettings:
    """Settings class validates required environment variables."""

    def test_settings_has_database_url(self):
        """Settings class includes DATABASE_URL field."""
        from app.core.config import Settings
        fields = Settings.model_fields
        assert "DATABASE_URL" in fields or "database_url" in fields or hasattr(Settings(), "DATABASE_URL") or hasattr(Settings(), "database_url")

    def test_settings_has_jwt_secret(self):
        """Settings class includes JWT_SECRET_KEY field."""
        from app.core.config import Settings
        fields = Settings.model_fields
        assert "JWT_SECRET_KEY" in fields or "jwt_secret_key" in fields

    def test_settings_has_redis_url(self):
        """Settings class includes REDIS_URL field."""
        from app.core.config import Settings
        fields = Settings.model_fields
        assert "REDIS_URL" in fields or "redis_url" in fields

    def test_get_settings_returns_cached_instance(self):
        """get_settings() is cached via lru_cache."""
        from app.core.config import get_settings
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2


class TestModels:
    """Model table names match DB schema expectations."""

    def test_user_table_name(self):
        """User model maps to 'users' table."""
        from app.models.user import User
        assert User.__tablename__ == "users"

    def test_project_table_name(self):
        """Project model maps to 'projects' table."""
        from app.models.project import Project
        assert Project.__tablename__ == "projects"

    def test_run_table_name(self):
        """Run model maps to 'runs' table."""
        from app.models.run import Run
        assert Run.__tablename__ == "runs"

    def test_vnc_session_table_name(self):
        """VncSession model maps to 'vnc_sessions' table."""
        from app.models.vnc_session import VncSession
        assert VncSession.__tablename__ == "vnc_sessions"

    def test_run_has_separate_ppa_and_config_columns(self):
        """Run model has separate ppa and config JSONB columns."""
        from app.models.run import Run
        from sqlalchemy import inspect
        mapper = inspect(Run)
        column_names = [col.key for col in mapper.mapper.column_attrs]
        assert "ppa" in column_names
        assert "config" in column_names

    def test_run_ppa_and_config_are_separate(self):
        """ppa and config are distinct column attributes on Run."""
        from app.models.run import Run
        from sqlalchemy import inspect
        mapper = inspect(Run)
        cols = {col.key: col for col in mapper.mapper.column_attrs}
        assert "ppa" in cols
        assert "config" in cols
        # They should be different columns
        assert cols["ppa"] is not cols["config"]
