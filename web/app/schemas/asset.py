from datetime import datetime

from pydantic import BaseModel

from app.models.asset import AssetType


class AssetCreate(BaseModel):
    name: str
    type: AssetType
    address: str
    notes: str | None = None


class AssetUpdate(BaseModel):
    name: str | None = None
    type: AssetType | None = None
    address: str | None = None
    notes: str | None = None


class AssetOut(BaseModel):
    id: int
    name: str
    type: AssetType
    address: str
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
