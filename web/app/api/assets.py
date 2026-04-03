from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.models import Asset
from app.schemas.asset import AssetCreate, AssetUpdate, AssetOut

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/", response_model=list[AssetOut])
def list_assets(db: DbSession):
    return db.query(Asset).order_by(Asset.name).all()


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: int, db: DbSession):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    return asset


@router.post("/", response_model=AssetOut, status_code=201)
def create_asset(body: AssetCreate, db: DbSession):
    asset = Asset(**body.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.patch("/{asset_id}", response_model=AssetOut)
def update_asset(asset_id: int, body: AssetUpdate, db: DbSession):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: int, db: DbSession):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    db.delete(asset)
    db.commit()
