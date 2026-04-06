# tests/web/test_auth.py
"""Tests for authentication: login, logout, setup, route protection."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.auth import hash_password


@pytest.fixture
def _test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(_test_engine):
    Session = sessionmaker(bind=_test_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(_test_engine, db_session):
    # Session factory bound to same in-memory engine so middleware and lifespan see test data
    TestSessionLocal = sessionmaker(bind=_test_engine)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # Patch engine (used by lifespan) and SessionLocal (used by middleware)
    with patch("app.main.engine", _test_engine), \
         patch("app.main.SessionLocal", TestSessionLocal):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session):
    user = User(username="admin", password_hash=hash_password("testpass123"), is_superadmin=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestSetup:
    def test_redirects_to_setup_when_no_users(self, client):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 303
        assert "/setup" in resp.headers["location"]

    def test_setup_page_renders(self, client):
        resp = client.get("/setup")
        assert resp.status_code == 200
        assert "setup" in resp.text.lower()

    def test_setup_creates_user_and_logs_in(self, client):
        resp = client.post(
            "/setup",
            data={"username": "admin", "password": "securepass1", "password_confirm": "securepass1"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"

    def test_setup_rejects_short_password(self, client):
        resp = client.post(
            "/setup",
            data={"username": "admin", "password": "short", "password_confirm": "short"},
        )
        assert resp.status_code == 400
        assert "at least 8 characters" in resp.text

    def test_setup_rejects_mismatched_passwords(self, client):
        resp = client.post(
            "/setup",
            data={"username": "admin", "password": "securepass1", "password_confirm": "different1"},
        )
        assert resp.status_code == 400
        assert "do not match" in resp.text

    def test_setup_blocked_when_user_exists(self, client, admin_user):
        resp = client.get("/setup", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]


class TestLogin:
    def test_login_page_renders(self, client, admin_user):
        resp = client.get("/login")
        assert resp.status_code == 200
        assert "Login" in resp.text

    def test_login_success_redirects(self, client, admin_user):
        resp = client.post(
            "/login",
            data={"username": "admin", "password": "testpass123"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"

    def test_login_invalid_password(self, client, admin_user):
        resp = client.post(
            "/login",
            data={"username": "admin", "password": "wrongpassword"},
        )
        assert resp.status_code == 401
        assert "Invalid" in resp.text

    def test_login_nonexistent_user(self, client, admin_user):
        resp = client.post(
            "/login",
            data={"username": "nobody", "password": "testpass123"},
        )
        assert resp.status_code == 401


class TestRouteProtection:
    def test_unauthenticated_redirects_to_login(self, client, admin_user):
        resp = client.get("/assets", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]

    def test_health_endpoint_is_public(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_authenticated_user_can_access_pages(self, client, admin_user):
        client.post("/login", data={"username": "admin", "password": "testpass123"})
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Dashboard" in resp.text


class TestLogout:
    def test_logout_clears_session(self, client, admin_user):
        client.post("/login", data={"username": "admin", "password": "testpass123"})
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 200
        resp = client.get("/logout", follow_redirects=False)
        assert resp.status_code == 303
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]


class TestAPIAuth:
    def test_api_token_login(self, client, admin_user):
        resp = client.post(
            "/api/v1/auth/token",
            json={"username": "admin", "password": "testpass123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_api_token_invalid_credentials(self, client, admin_user):
        resp = client.post(
            "/api/v1/auth/token",
            json={"username": "admin", "password": "wrong"},
        )
        assert resp.status_code == 401
