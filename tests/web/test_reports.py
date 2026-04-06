"""Functional tests for report generation views."""
import os

os.environ["DATABASE_URL"] = "sqlite:///test_nmapctf.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch
from datetime import datetime, timezone

from app.database import Base, get_db
from app.main import app
from app.models import (
    Asset, AssetType, ScanProfile, ScanJob, ScanResult, ScanStatus, User,
)


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
    client.post("/login", data={"username": "admin", "password": "testpass123"})
    return client


@pytest.fixture
def sample_data(db_session):
    """Create an asset, profile, completed scan, and scan results."""
    asset = Asset(name="test-server", type=AssetType.ip, address="192.168.1.1")
    db_session.add(asset)
    db_session.flush()

    profile = ScanProfile(name="Report Test Scan", nmap_args="-T4 -F", is_default=False)
    db_session.add(profile)
    db_session.flush()

    scan = ScanJob(
        asset_id=asset.id,
        profile_id=profile.id,
        status=ScanStatus.completed,
        completed_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    db_session.add(scan)
    db_session.flush()

    results = [
        ScanResult(job_id=scan.id, host="192.168.1.1", port=22, protocol="tcp", state="open", service="ssh", version="OpenSSH 8.9"),
        ScanResult(job_id=scan.id, host="192.168.1.1", port=80, protocol="tcp", state="open", service="http", version="nginx 1.24"),
        ScanResult(job_id=scan.id, host="192.168.1.1", port=443, protocol="tcp", state="filtered", service="https"),
    ]
    db_session.add_all(results)
    db_session.commit()
    db_session.refresh(asset)
    db_session.refresh(scan)
    return {"asset": asset, "profile": profile, "scan": scan, "results": results}


class TestReportIndex:
    def test_report_index_loads(self, authed_client):
        resp = authed_client.get("/reports/")
        assert resp.status_code == 200
        assert "Report" in resp.text

    def test_report_index_shows_assets(self, authed_client, sample_data):
        resp = authed_client.get("/reports/")
        assert resp.status_code == 200
        assert "test-server" in resp.text

    def test_report_index_shows_scans(self, authed_client, sample_data):
        resp = authed_client.get("/reports/")
        assert resp.status_code == 200
        assert sample_data["scan"].id in resp.text


class TestReportHTML:
    def test_full_report(self, authed_client, sample_data):
        resp = authed_client.get("/reports/view?scope=all")
        assert resp.status_code == 200
        assert "Full Scan Report" in resp.text
        assert "192.168.1.1" in resp.text

    def test_single_scan_report(self, authed_client, sample_data):
        scan_id = sample_data["scan"].id
        resp = authed_client.get(f"/reports/view?scope=scan&scan_id={scan_id}")
        assert resp.status_code == 200
        assert "test-server" in resp.text
        assert "ssh" in resp.text

    def test_asset_report(self, authed_client, sample_data):
        asset_id = sample_data["asset"].id
        resp = authed_client.get(f"/reports/view?scope=asset&asset_id={asset_id}")
        assert resp.status_code == 200
        assert "Asset Report" in resp.text

    def test_asset_report_with_dates(self, authed_client, sample_data):
        asset_id = sample_data["asset"].id
        resp = authed_client.get(
            f"/reports/view?scope=asset&asset_id={asset_id}&date_from=2026-03-01&date_to=2026-05-01"
        )
        assert resp.status_code == 200
        assert "192.168.1.1" in resp.text

    def test_nonexistent_scan_returns_404(self, authed_client):
        resp = authed_client.get("/reports/view?scope=scan&scan_id=nonexistent-id")
        assert resp.status_code == 404

    def test_nonexistent_asset_returns_404(self, authed_client):
        resp = authed_client.get("/reports/view?scope=asset&asset_id=99999")
        assert resp.status_code == 404


class TestReportCSV:
    def test_csv_download(self, authed_client, sample_data):
        resp = authed_client.get("/reports/csv?scope=all")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"
        lines = resp.text.strip().splitlines()
        assert lines[0].strip() == "host,port,protocol,state,service,version"
        assert len(lines) == 4  # header + 3 results

    def test_csv_single_scan(self, authed_client, sample_data):
        scan_id = sample_data["scan"].id
        resp = authed_client.get(f"/reports/csv?scope=scan&scan_id={scan_id}")
        assert resp.status_code == 200
        assert "ssh" in resp.text
        assert "OpenSSH 8.9" in resp.text


class TestReportJSON:
    def test_json_download(self, authed_client, sample_data):
        resp = authed_client.get("/reports/json?scope=all")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Full Scan Report"
        assert "summary" in data
        assert len(data["results"]) == 3

    def test_json_single_scan(self, authed_client, sample_data):
        scan_id = sample_data["scan"].id
        resp = authed_client.get(f"/reports/json?scope=scan&scan_id={scan_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "test-server" in data["title"]
        assert any(r["service"] == "ssh" for r in data["results"])
