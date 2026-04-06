"""Functional tests for organization management and multi-tenancy."""
import os

os.environ["DATABASE_URL"] = "sqlite:///test_nmapctf.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from app.database import Base, get_db
from app.main import app
from app.models import Asset, AssetType, Organization, User, OrgRole


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
def superadmin(db_session):
    from app.auth import hash_password
    user = User(username="root", password_hash=hash_password("testpass123"), is_superadmin=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def superadmin_client(client, superadmin):
    client.post("/login", data={"username": "root", "password": "testpass123"})
    return client


@pytest.fixture
def sample_org(db_session):
    org = Organization(name="Acme Corp", slug="acme-corp")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def org_member(db_session, sample_org):
    from app.auth import hash_password
    user = User(
        username="member1", password_hash=hash_password("testpass123"),
        org_id=sample_org.id, org_role=OrgRole.member,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def member_client(client, org_member):
    client.post("/login", data={"username": "member1", "password": "testpass123"})
    return client


@pytest.fixture
def org_admin(db_session, sample_org):
    from app.auth import hash_password
    user = User(
        username="orgadmin", password_hash=hash_password("testpass123"),
        org_id=sample_org.id, org_role=OrgRole.admin,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def org_admin_client(client, org_admin):
    client.post("/login", data={"username": "orgadmin", "password": "testpass123"})
    return client


class TestOrgCRUD:
    def test_list_orgs_superadmin(self, superadmin_client):
        resp = superadmin_client.get("/orgs")
        assert resp.status_code == 200
        assert "Organizations" in resp.text

    def test_create_org(self, superadmin_client, db_session):
        resp = superadmin_client.post(
            "/orgs/", data={"name": "Test Corp"}, follow_redirects=False,
        )
        assert resp.status_code == 303
        org = db_session.query(Organization).filter_by(name="Test Corp").first()
        assert org is not None
        assert org.slug == "test-corp"

    def test_org_detail(self, superadmin_client, sample_org):
        resp = superadmin_client.get(f"/orgs/{sample_org.id}")
        assert resp.status_code == 200
        assert "Acme Corp" in resp.text

    def test_add_member(self, superadmin_client, sample_org, db_session):
        resp = superadmin_client.post(
            f"/orgs/{sample_org.id}/members",
            data={"username": "newuser", "password": "password123", "org_role": "member"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        user = db_session.query(User).filter_by(username="newuser").first()
        assert user is not None
        assert user.org_id == sample_org.id
        assert user.org_role == OrgRole.member

    def test_delete_org(self, superadmin_client, sample_org):
        resp = superadmin_client.delete(f"/orgs/{sample_org.id}")
        assert resp.status_code == 200


class TestOrgAccessControl:
    def test_non_superadmin_cannot_access_orgs(self, member_client):
        resp = member_client.get("/orgs/")
        # Should redirect away (not show org list)
        assert "Organizations" not in resp.text or resp.status_code != 200

    def test_non_superadmin_cannot_create_org(self, member_client):
        resp = member_client.post(
            "/orgs/", data={"name": "Sneaky Corp"}, follow_redirects=False,
        )
        assert resp.status_code == 303


class TestRolePermissions:
    def test_member_cannot_create_asset(self, member_client):
        resp = member_client.get("/assets/new", follow_redirects=False)
        assert resp.status_code == 303

    def test_member_cannot_run_scan(self, member_client):
        resp = member_client.get("/scans/run", follow_redirects=False)
        assert resp.status_code == 303

    def test_member_can_view_assets(self, member_client):
        resp = member_client.get("/assets")
        assert resp.status_code == 200

    def test_member_can_view_scans(self, member_client):
        resp = member_client.get("/scans")
        assert resp.status_code == 200

    def test_org_admin_can_create_asset(self, org_admin_client):
        resp = org_admin_client.get("/assets/new")
        assert resp.status_code == 200

    def test_org_admin_can_run_scan(self, org_admin_client):
        resp = org_admin_client.get("/scans/run")
        assert resp.status_code == 200


class TestDataIsolation:
    def test_member_sees_only_org_assets(self, member_client, db_session, sample_org):
        # Create asset in member's org
        org_asset = Asset(name="org-server", type=AssetType.ip, address="10.0.0.1", org_id=sample_org.id)
        # Create asset in another org
        other_org = Organization(name="Other Corp", slug="other-corp")
        db_session.add(other_org)
        db_session.flush()
        other_asset = Asset(name="other-server", type=AssetType.ip, address="10.0.0.2", org_id=other_org.id)
        db_session.add_all([org_asset, other_asset])
        db_session.commit()

        resp = member_client.get("/assets")
        assert resp.status_code == 200
        assert "org-server" in resp.text
        assert "other-server" not in resp.text

    def test_superadmin_sees_all_assets(self, superadmin_client, db_session, sample_org):
        a1 = Asset(name="asset-a", type=AssetType.ip, address="10.0.0.1", org_id=sample_org.id)
        a2 = Asset(name="asset-b", type=AssetType.ip, address="10.0.0.2", org_id=None)
        db_session.add_all([a1, a2])
        db_session.commit()

        resp = superadmin_client.get("/assets")
        assert resp.status_code == 200
        assert "asset-a" in resp.text
        assert "asset-b" in resp.text


class TestSetupCreatesSuperadmin:
    def test_setup_creates_superadmin(self, client, db_session):
        resp = client.post(
            "/setup",
            data={"username": "firstadmin", "password": "password123", "password_confirm": "password123"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        user = db_session.query(User).filter_by(username="firstadmin").first()
        assert user.is_superadmin is True
        assert user.org_id is None
