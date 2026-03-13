"""Custom SQLAlchemy type: JSONB on PostgreSQL, JSON everywhere else (e.g., SQLite in tests)."""
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class JSONBCompatible(TypeDecorator):
    """
    Stores as JSONB on PostgreSQL for indexing support;
    falls back to JSON on other databases (SQLite for tests).
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())
