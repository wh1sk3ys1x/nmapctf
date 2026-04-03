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

from app.database import Base, get_db
from app.main import app
from app.models import Asset, AssetType, ScanProfile, ScanJob, Schedule


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_asset(db_session):
    asset = Asset(name="test-server", type=AssetType.ip, address="192.168.1.1")
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


@pytest.fixture
def sample_profile(db_session):
    profile = ScanProfile(name="Quick Scan", nmap_args="-T4 -F", is_default=True)
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


class TestDashboard:
    def test_dashboard_loads(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Dashboard" in resp.text

    def test_dashboard_shows_stats(self, client, sample_asset):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Assets" in resp.text


class TestAssetViews:
    def test_list_assets(self, client, sample_asset):
        resp = client.get("/assets")
        assert resp.status_code == 200
        assert "test-server" in resp.text

    def test_new_asset_form(self, client):
        resp = client.get("/assets/new")
        assert resp.status_code == 200
        assert "New" in resp.text

    def test_create_asset(self, client):
        resp = client.post(
            "/assets/",
            data={"name": "web-host", "type": "host", "address": "example.com", "notes": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_edit_asset_form(self, client, sample_asset):
        resp = client.get(f"/assets/{sample_asset.id}/edit")
        assert resp.status_code == 200
        assert "192.168.1.1" in resp.text

    def test_delete_asset(self, client, sample_asset):
        resp = client.delete(f"/assets/{sample_asset.id}")
        assert resp.status_code == 200


class TestProfileViews:
    def test_list_profiles(self, client, sample_profile):
        resp = client.get("/profiles")
        assert resp.status_code == 200
        assert "Quick Scan" in resp.text

    def test_new_profile_form(self, client):
        resp = client.get("/profiles/new")
        assert resp.status_code == 200


class TestScheduleViews:
    def test_list_schedules(self, client):
        resp = client.get("/schedules")
        assert resp.status_code == 200
        assert "Schedules" in resp.text

    def test_new_schedule_form(self, client):
        resp = client.get("/schedules/new")
        assert resp.status_code == 200


class TestScanViews:
    def test_scan_history(self, client):
        resp = client.get("/scans")
        assert resp.status_code == 200
        assert "Scan History" in resp.text

    def test_run_scan_form(self, client):
        resp = client.get("/scans/run")
        assert resp.status_code == 200
        assert "Run Scan" in resp.text
