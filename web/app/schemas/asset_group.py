from datetime import datetime

from pydantic import BaseModel

from app.schemas.asset import AssetOut


class AssetGroupCreate(BaseModel):
    name: str
    description: str | None = None


class AssetGroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class AssetGroupOut(BaseModel):
    id: int
    name: str
    description: str | None
    member_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetGroupDetail(BaseModel):
    id: int
    name: str
    description: str | None
    assets: list[AssetOut]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GroupMemberAdd(BaseModel):
    asset_id: int
