"""Tests for AssetAddress model and Asset relationship."""
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
from app.models import Asset, AssetType, AssetAddress, AssetGroup, User


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


class TestAssetAddressModel:
    def test_create_asset_address(self, db_session):
        asset = Asset(name="multi-server", type=AssetType.ip, address="10.0.0.1")
        db_session.add(asset)
        db_session.flush()

        addr = AssetAddress(asset_id=asset.id, address="10.0.0.1", label="primary", is_primary=True)
        db_session.add(addr)
        db_session.commit()
        db_session.refresh(addr)

        assert addr.id is not None
        assert addr.asset_id == asset.id
        assert addr.address == "10.0.0.1"
        assert addr.label == "primary"
        assert addr.is_primary is True

    def test_asset_addresses_relationship(self, db_session):
        asset = Asset(name="dual-nic", type=AssetType.ip, address="10.0.0.1")
        db_session.add(asset)
        db_session.flush()

        addr1 = AssetAddress(asset_id=asset.id, address="10.0.0.1", label="primary", is_primary=True)
        addr2 = AssetAddress(asset_id=asset.id, address="10.0.0.2", label="failover", is_primary=False)
        db_session.add_all([addr1, addr2])
        db_session.commit()
        db_session.refresh(asset)

        assert len(asset.addresses) == 2
        assert {a.address for a in asset.addresses} == {"10.0.0.1", "10.0.0.2"}

    def test_cascade_delete_asset_removes_addresses(self, db_session):
        asset = Asset(name="deleteme", type=AssetType.ip, address="10.0.0.1")
        db_session.add(asset)
        db_session.flush()

        addr = AssetAddress(asset_id=asset.id, address="10.0.0.1", is_primary=True)
        db_session.add(addr)
        db_session.commit()

        db_session.delete(asset)
        db_session.commit()

        assert db_session.query(AssetAddress).count() == 0


class TestAssetAddressSeeding:
    def test_create_asset_seeds_primary_address(self, authed_client, db_session):
        resp = authed_client.post("/assets/", data={
            "name": "new-server", "type": "ip", "address": "192.168.1.1", "notes": "",
        }, follow_redirects=False)
        assert resp.status_code == 303

        asset = db_session.query(Asset).filter_by(name="new-server").first()
        assert asset is not None
        assert len(asset.addresses) == 1
        assert asset.addresses[0].address == "192.168.1.1"
        assert asset.addresses[0].is_primary is True

    def test_update_asset_syncs_primary_address(self, authed_client, db_session):
        asset = Asset(name="edit-me", type=AssetType.ip, address="10.0.0.1")
        db_session.add(asset)
        db_session.flush()
        addr = AssetAddress(asset_id=asset.id, address="10.0.0.1", is_primary=True)
        db_session.add(addr)
        db_session.commit()

        resp = authed_client.post(f"/assets/{asset.id}", data={
            "name": "edit-me", "type": "ip", "address": "10.0.0.99", "notes": "",
        }, follow_redirects=False)
        assert resp.status_code == 303

        db_session.refresh(asset)
        assert asset.address == "10.0.0.99"
        primary = [a for a in asset.addresses if a.is_primary][0]
        assert primary.address == "10.0.0.99"


class TestAddRemoveAddresses:
    @pytest.fixture
    def asset_with_primary(self, db_session):
        asset = Asset(name="multi-nic", type=AssetType.ip, address="10.0.0.1")
        db_session.add(asset)
        db_session.flush()
        addr = AssetAddress(asset_id=asset.id, address="10.0.0.1", is_primary=True)
        db_session.add(addr)
        db_session.commit()
        db_session.refresh(asset)
        return asset

    def test_add_address(self, authed_client, db_session, asset_with_primary):
        asset = asset_with_primary
        resp = authed_client.post(f"/assets/{asset.id}/addresses", data={
            "address": "10.0.0.2", "label": "failover",
        })
        assert resp.status_code == 200

        db_session.refresh(asset)
        assert len(asset.addresses) == 2
        new_addr = [a for a in asset.addresses if not a.is_primary][0]
        assert new_addr.address == "10.0.0.2"
        assert new_addr.label == "failover"

    def test_remove_address(self, authed_client, db_session, asset_with_primary):
        asset = asset_with_primary
        extra = AssetAddress(asset_id=asset.id, address="10.0.0.2", label="failover", is_primary=False)
        db_session.add(extra)
        db_session.commit()
        db_session.refresh(extra)

        resp = authed_client.delete(f"/assets/{asset.id}/addresses/{extra.id}")
        assert resp.status_code == 200

        db_session.refresh(asset)
        assert len(asset.addresses) == 1
        assert asset.addresses[0].is_primary is True

    def test_cannot_remove_primary_address(self, authed_client, db_session, asset_with_primary):
        asset = asset_with_primary
        primary = asset.addresses[0]

        resp = authed_client.delete(f"/assets/{asset.id}/addresses/{primary.id}")
        assert resp.status_code == 200

        db_session.refresh(asset)
        assert len(asset.addresses) == 1  # primary still there


class TestAssetListBadge:
    def test_single_address_no_badge(self, authed_client, db_session):
        asset = Asset(name="single", type=AssetType.ip, address="10.0.0.1")
        db_session.add(asset)
        db_session.flush()
        db_session.add(AssetAddress(asset_id=asset.id, address="10.0.0.1", is_primary=True))
        db_session.commit()

        resp = authed_client.get("/assets")
        assert resp.status_code == 200
        assert "+1" not in resp.text  # no badge for single address

    def test_multi_address_shows_badge(self, authed_client, db_session):
        asset = Asset(name="multi", type=AssetType.ip, address="10.0.0.1")
        db_session.add(asset)
        db_session.flush()
        db_session.add(AssetAddress(asset_id=asset.id, address="10.0.0.1", is_primary=True))
        db_session.add(AssetAddress(asset_id=asset.id, address="10.0.0.2", is_primary=False))
        db_session.add(AssetAddress(asset_id=asset.id, address="10.0.0.3", is_primary=False))
        db_session.commit()

        resp = authed_client.get("/assets")
        assert resp.status_code == 200
        assert "+2" in resp.text


class TestGroupDetailAddresses:
    def test_group_detail_shows_all_addresses(self, authed_client, db_session):
        asset = Asset(name="grouped-server", type=AssetType.ip, address="10.0.0.1")
        db_session.add(asset)
        db_session.flush()
        db_session.add(AssetAddress(asset_id=asset.id, address="10.0.0.1", label="primary", is_primary=True))
        db_session.add(AssetAddress(asset_id=asset.id, address="10.0.0.2", label="failover", is_primary=False))
        db_session.commit()

        group = AssetGroup(name="test-group")
        db_session.add(group)
        db_session.flush()
        group.assets.append(asset)
        db_session.commit()

        resp = authed_client.get(f"/groups/{group.id}")
        assert resp.status_code == 200
        assert "10.0.0.1" in resp.text
        assert "10.0.0.2" in resp.text
