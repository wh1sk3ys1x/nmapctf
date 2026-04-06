"""Functional tests for asset import via file upload."""
import os

os.environ["DATABASE_URL"] = "sqlite:///test_nmapctf.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from app.database import Base, get_db
from app.main import app
from app.models import Asset, AssetType, AssetGroup, User


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
def sample_group(db_session):
    group = AssetGroup(name="Import Group")
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)
    return group


class TestImportForm:
    def test_import_page_loads(self, authed_client):
        resp = authed_client.get("/assets/import")
        assert resp.status_code == 200
        assert "Import Assets" in resp.text

    def test_import_page_shows_groups(self, authed_client, sample_group):
        resp = authed_client.get("/assets/import")
        assert resp.status_code == 200
        assert "Import Group" in resp.text


class TestCSVImport:
    def test_import_csv(self, authed_client, db_session):
        csv_content = "address,name,type\n10.0.0.1,web-server,ip\n10.0.0.2,db-server,host\n"
        resp = authed_client.post(
            "/assets/import",
            files={"file": ("assets.csv", csv_content.encode(), "text/csv")},
            data={"default_type": "ip"},
        )
        assert resp.status_code == 200
        assert "web-server" in resp.text
        assert "db-server" in resp.text
        assets = db_session.query(Asset).all()
        assert len(assets) == 2

    def test_import_csv_skips_duplicates(self, authed_client, db_session):
        existing = Asset(name="existing", type=AssetType.ip, address="10.0.0.1")
        db_session.add(existing)
        db_session.commit()

        csv_content = "address,name\n10.0.0.1,dup\n10.0.0.2,new-one\n"
        resp = authed_client.post(
            "/assets/import",
            files={"file": ("assets.csv", csv_content.encode(), "text/csv")},
            data={"default_type": "ip"},
        )
        assert resp.status_code == 200
        assert "already exists" in resp.text
        assert "new-one" in resp.text
        assets = db_session.query(Asset).count()
        assert assets == 2  # existing + new-one

    def test_import_csv_auto_generates_name(self, authed_client, db_session):
        csv_content = "address\n192.168.1.100\n"
        resp = authed_client.post(
            "/assets/import",
            files={"file": ("assets.csv", csv_content.encode(), "text/csv")},
            data={"default_type": "ip"},
        )
        assert resp.status_code == 200
        asset = db_session.query(Asset).first()
        assert asset.name == "asset-192.168.1.100"

    def test_import_csv_with_group(self, authed_client, db_session, sample_group):
        csv_content = "address\n10.0.0.5\n10.0.0.6\n"
        resp = authed_client.post(
            "/assets/import",
            files={"file": ("assets.csv", csv_content.encode(), "text/csv")},
            data={"default_type": "ip", "asset_group_id": str(sample_group.id)},
        )
        assert resp.status_code == 200
        assert "Import Group" in resp.text
        db_session.refresh(sample_group)
        assert len(sample_group.assets) == 2


class TestTXTImport:
    def test_import_txt(self, authed_client, db_session):
        txt_content = "10.0.0.1\n10.0.0.2\n# comment\n\n10.0.0.3\n"
        resp = authed_client.post(
            "/assets/import",
            files={"file": ("hosts.txt", txt_content.encode(), "text/plain")},
            data={"default_type": "ip"},
        )
        assert resp.status_code == 200
        assets = db_session.query(Asset).count()
        assert assets == 3

    def test_import_txt_default_type(self, authed_client, db_session):
        txt_content = "192.168.1.1\n"
        resp = authed_client.post(
            "/assets/import",
            files={"file": ("hosts.txt", txt_content.encode(), "text/plain")},
            data={"default_type": "subnet"},
        )
        assert resp.status_code == 200
        asset = db_session.query(Asset).first()
        assert asset.type == AssetType.subnet


class TestUnsupportedFormat:
    def test_reject_unsupported_file(self, authed_client):
        resp = authed_client.post(
            "/assets/import",
            files={"file": ("data.json", b"{}", "application/json")},
            data={"default_type": "ip"},
        )
        assert resp.status_code == 200
        assert "Unsupported file type" in resp.text


class TestAssetListImportButton:
    def test_assets_page_has_import_button(self, authed_client):
        resp = authed_client.get("/assets")
        assert resp.status_code == 200
        assert 'href="/assets/import"' in resp.text
