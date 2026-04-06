"""Functional tests for web UI view routes."""
import os

# Override settings before importing the app so the lifespan handler
# uses a temporary file-based database instead of the default /app/data path.
os.environ["DATABASE_URL"] = "sqlite:///test_nmapctf.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from app.database import Base, get_db
from app.main import app
from app.models import Asset, AssetType, ScanProfile, ScanJob, Schedule, User


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
    TestSessionLocal = sessionmaker(bind=_test_engine)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with patch("app.main.engine", _test_engine), \
         patch("app.main.SessionLocal", TestSessionLocal):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session):
    from app.auth import hash_password
    user = User(username="admin", password_hash=hash_password("testpass123"), is_superadmin=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def authed_client(client, admin_user):
    """A client that is logged in as admin."""
    client.post("/login", data={"username": "admin", "password": "testpass123"})
    return client


@pytest.fixture
def sample_asset(db_session):
    asset = Asset(name="test-server", type=AssetType.ip, address="192.168.1.1")
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


@pytest.fixture
def sample_profile(db_session):
    profile = ScanProfile(name="Test Quick Scan", nmap_args="-T4 -F", is_default=False)
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


class TestDashboard:
    def test_dashboard_loads(self, authed_client):
        resp = authed_client.get("/")
        assert resp.status_code == 200
        assert "Dashboard" in resp.text

    def test_dashboard_shows_stats(self, authed_client, sample_asset):
        resp = authed_client.get("/")
        assert resp.status_code == 200
        assert "Assets" in resp.text


class TestAssetViews:
    def test_list_assets(self, authed_client, sample_asset):
        resp = authed_client.get("/assets")
        assert resp.status_code == 200
        assert "test-server" in resp.text

    def test_new_asset_form(self, authed_client):
        resp = authed_client.get("/assets/new")
        assert resp.status_code == 200
        assert "New" in resp.text

    def test_create_asset(self, authed_client):
        resp = authed_client.post(
            "/assets/",
            data={"name": "web-host", "type": "host", "address": "example.com", "notes": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_edit_asset_form(self, authed_client, sample_asset):
        resp = authed_client.get(f"/assets/{sample_asset.id}/edit")
        assert resp.status_code == 200
        assert "192.168.1.1" in resp.text

    def test_delete_asset(self, authed_client, sample_asset):
        resp = authed_client.delete(f"/assets/{sample_asset.id}")
        assert resp.status_code == 200


class TestProfileViews:
    def test_list_profiles(self, authed_client, sample_profile):
        resp = authed_client.get("/profiles")
        assert resp.status_code == 200
        assert "Test Quick Scan" in resp.text

    def test_new_profile_form(self, authed_client):
        resp = authed_client.get("/profiles/new")
        assert resp.status_code == 200


class TestScheduleViews:
    def test_list_schedules(self, authed_client):
        resp = authed_client.get("/schedules")
        assert resp.status_code == 200
        assert "Schedules" in resp.text

    def test_new_schedule_form(self, authed_client):
        resp = authed_client.get("/schedules/new")
        assert resp.status_code == 200


class TestScanViews:
    def test_scan_history(self, authed_client):
        resp = authed_client.get("/scans")
        assert resp.status_code == 200
        assert "Scan History" in resp.text

    def test_run_scan_form(self, authed_client):
        resp = authed_client.get("/scans/run")
        assert resp.status_code == 200
        assert "Run Scan" in resp.text
