"""Shared pytest fixtures.

Tests run against the real Postgres from docker-compose (not sqlite/mocks):
several models use Postgres-native types (JSONB, ARRAY, native ENUM) that
don't exist on other backends, and the whole point of the tenancy test is
to prove real row-level filtering works — a mock session would prove
nothing.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)
