"""Functional tests for asset group views."""
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
    Asset, AssetType, AssetGroup, ScanProfile, ScanJob, ScanResult, ScanStatus, User,
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
    user = User(username="admin", password_hash=hash_password("testpass123"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def authed_client(client, admin_user):
    client.post("/login", data={"username": "admin", "password": "testpass123"})
    return client


@pytest.fixture
def sample_assets(db_session):
    a1 = Asset(name="web-server", type=AssetType.ip, address="10.0.0.1")
    a2 = Asset(name="db-server", type=AssetType.ip, address="10.0.0.2")
    a3 = Asset(name="mail-server", type=AssetType.ip, address="10.0.0.3")
    db_session.add_all([a1, a2, a3])
    db_session.commit()
    for a in [a1, a2, a3]:
        db_session.refresh(a)
    return [a1, a2, a3]


@pytest.fixture
def sample_group(db_session, sample_assets):
    group = AssetGroup(name="Production", description="Prod servers")
    group.assets.append(sample_assets[0])
    group.assets.append(sample_assets[1])
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)
    return group


@pytest.fixture
def sample_group_with_scans(db_session, sample_group):
    profile = ScanProfile(name="Group Test Profile", nmap_args="-T4", is_default=False)
    db_session.add(profile)
    db_session.flush()
    scan = ScanJob(
        asset_id=sample_group.assets[0].id,
        profile_id=profile.id,
        status=ScanStatus.completed,
        asset_group_id=sample_group.id,
        completed_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    db_session.add(scan)
    db_session.flush()
    result = ScanResult(
        job_id=scan.id, host="10.0.0.1", port=80,
        protocol="tcp", state="open", service="http",
    )
    db_session.add(result)
    db_session.commit()
    return sample_group


class TestGroupCRUD:
    def test_list_groups_empty(self, authed_client):
        resp = authed_client.get("/groups")
        assert resp.status_code == 200
        assert "Asset Groups" in resp.text

    def test_create_group(self, authed_client):
        resp = authed_client.post(
            "/groups/",
            data={"name": "Test Group", "description": "A test group"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_list_groups_shows_group(self, authed_client, sample_group):
        resp = authed_client.get("/groups")
        assert resp.status_code == 200
        assert "Production" in resp.text

    def test_group_detail(self, authed_client, sample_group):
        resp = authed_client.get(f"/groups/{sample_group.id}")
        assert resp.status_code == 200
        assert "Production" in resp.text
        assert "web-server" in resp.text
        assert "db-server" in resp.text

    def test_edit_group(self, authed_client, sample_group):
        resp = authed_client.get(f"/groups/{sample_group.id}/edit")
        assert resp.status_code == 200
        assert "Production" in resp.text

    def test_update_group(self, authed_client, sample_group):
        resp = authed_client.post(
            f"/groups/{sample_group.id}",
            data={"name": "Staging", "description": "Staging servers"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_delete_group(self, authed_client, sample_group, db_session):
        resp = authed_client.delete(f"/groups/{sample_group.id}")
        assert resp.status_code == 200
        # Assets should still exist
        assert db_session.get(Asset, sample_group.assets[0].id) is not None


class TestGroupMembers:
    def test_add_member(self, authed_client, sample_group, sample_assets):
        resp = authed_client.post(
            f"/groups/{sample_group.id}/members",
            data={"asset_id": sample_assets[2].id},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_remove_member(self, authed_client, sample_group, sample_assets):
        resp = authed_client.delete(f"/groups/{sample_group.id}/members/{sample_assets[0].id}")
        assert resp.status_code == 200

    def test_detail_shows_available_assets(self, authed_client, sample_group):
        resp = authed_client.get(f"/groups/{sample_group.id}")
        assert resp.status_code == 200
        # mail-server is not in the group, should be in the add dropdown
        assert "mail-server" in resp.text


class TestGroupScans:
    def test_run_scan_form_shows_groups(self, authed_client, sample_group):
        resp = authed_client.get("/scans/run")
        assert resp.status_code == 200
        assert "Production" in resp.text
        assert "Asset Group" in resp.text


class TestGroupReports:
    def test_report_index_shows_groups(self, authed_client, sample_group):
        resp = authed_client.get("/reports/")
        assert resp.status_code == 200
        assert "Production" in resp.text

    def test_group_report_html(self, authed_client, sample_group_with_scans):
        group_id = sample_group_with_scans.id
        resp = authed_client.get(f"/reports/view?scope=group&group_id={group_id}")
        assert resp.status_code == 200
        assert "Group Report" in resp.text

    def test_group_report_json(self, authed_client, sample_group_with_scans):
        group_id = sample_group_with_scans.id
        resp = authed_client.get(f"/reports/json?scope=group&group_id={group_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "Group Report" in data["title"]
        assert len(data["results"]) == 1

    def test_group_report_csv(self, authed_client, sample_group_with_scans):
        group_id = sample_group_with_scans.id
        resp = authed_client.get(f"/reports/csv?scope=group&group_id={group_id}")
        assert resp.status_code == 200
        assert "http" in resp.text

    def test_nonexistent_group_returns_404(self, authed_client):
        resp = authed_client.get("/reports/view?scope=group&group_id=99999")
        assert resp.status_code == 404


class TestNavbar:
    def test_navbar_has_groups_link(self, authed_client):
        resp = authed_client.get("/")
        assert resp.status_code == 200
        assert 'href="/groups"' in resp.text
