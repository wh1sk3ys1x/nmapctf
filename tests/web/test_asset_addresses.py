"""Tests for AssetAddress model and Asset relationship."""
import os

os.environ["DATABASE_URL"] = "sqlite:///test_nmapctf.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"

import pytest
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.models import Asset, AssetType, AssetAddress


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
