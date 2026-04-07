"""One-time backfill: create AssetAddress rows for existing assets that lack them."""
from app.database import SessionLocal
from app.models import Asset, AssetAddress


def backfill():
    db = SessionLocal()
    try:
        assets = db.query(Asset).all()
        count = 0
        for asset in assets:
            if not asset.addresses:
                db.add(AssetAddress(asset_id=asset.id, address=asset.address, is_primary=True))
                count += 1
        db.commit()
        print(f"Backfilled {count} asset(s) with primary AssetAddress rows.")
    finally:
        db.close()


if __name__ == "__main__":
    backfill()
