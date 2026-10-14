import os

# Must be set before the app is imported, because settings are read at import time.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ["REDIS_URL"] = ""  # tests must never talk to a real Redis

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cache import cache
from app.database import Base, get_db
from app.main import app
from app.models import UserDB


@pytest.fixture(autouse=True)
def clean_cache():
    """Cache entries and rate-limit counters must not leak from one test to the next."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture()
def client():
    """A test client backed by a fresh in-memory SQLite database for every test."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.session_factory = TestingSession
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def login(client):
    """login('alice') registers the user if needed and returns auth headers."""

    def _login(username, password="password123"):
        client.post("/register", json={"username": username, "password": password})
        response = client.post("/login", data={"username": username, "password": password})
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    return _login


@pytest.fixture()
def make_admin(client):
    def _make_admin(username):
        db = client.session_factory()
        user = db.query(UserDB).filter(UserDB.username == username).first()
        user.role = "admin"
        db.commit()
        db.close()

    return _make_admin
