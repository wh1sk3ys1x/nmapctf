from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.models import AssetGroup, Asset
from app.models.asset_group import asset_group_members
from app.schemas.asset_group import (
    AssetGroupCreate, AssetGroupUpdate, AssetGroupOut, AssetGroupDetail, GroupMemberAdd,
)

router = APIRouter(prefix="/asset-groups", tags=["asset-groups"])


@router.get("/", response_model=list[AssetGroupOut])
def list_groups(db: DbSession):
    groups = db.query(AssetGroup).order_by(AssetGroup.name).all()
    return [
        AssetGroupOut(
            id=g.id, name=g.name, description=g.description,
            member_count=len(g.assets), created_at=g.created_at, updated_at=g.updated_at,
        )
        for g in groups
    ]


@router.get("/{group_id}", response_model=AssetGroupDetail)
def get_group(group_id: int, db: DbSession):
    group = db.get(AssetGroup, group_id)
    if not group:
        raise HTTPException(404, "Asset group not found")
    return group


@router.post("/", response_model=AssetGroupOut, status_code=201)
def create_group(body: AssetGroupCreate, db: DbSession):
    group = AssetGroup(name=body.name, description=body.description)
    db.add(group)
    db.commit()
    db.refresh(group)
    return AssetGroupOut(
        id=group.id, name=group.name, description=group.description,
        member_count=0, created_at=group.created_at, updated_at=group.updated_at,
    )


@router.patch("/{group_id}", response_model=AssetGroupOut)
def update_group(group_id: int, body: AssetGroupUpdate, db: DbSession):
    group = db.get(AssetGroup, group_id)
    if not group:
        raise HTTPException(404, "Asset group not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(group, field, value)
    db.commit()
    db.refresh(group)
    return AssetGroupOut(
        id=group.id, name=group.name, description=group.description,
        member_count=len(group.assets), created_at=group.created_at, updated_at=group.updated_at,
    )


@router.delete("/{group_id}", status_code=204)
def delete_group(group_id: int, db: DbSession):
    group = db.get(AssetGroup, group_id)
    if not group:
        raise HTTPException(404, "Asset group not found")
    db.delete(group)
    db.commit()


@router.post("/{group_id}/members", status_code=201)
def add_member(group_id: int, body: GroupMemberAdd, db: DbSession):
    group = db.get(AssetGroup, group_id)
    if not group:
        raise HTTPException(404, "Asset group not found")
    asset = db.get(Asset, body.asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    if asset in group.assets:
        raise HTTPException(409, "Asset already in group")
    group.assets.append(asset)
    db.commit()
    return {"status": "added"}


@router.delete("/{group_id}/members/{asset_id}", status_code=204)
def remove_member(group_id: int, asset_id: int, db: DbSession):
    group = db.get(AssetGroup, group_id)
    if not group:
        raise HTTPException(404, "Asset group not found")
    asset = db.get(Asset, asset_id)
    if not asset or asset not in group.assets:
        raise HTTPException(404, "Asset not in group")
    group.assets.remove(asset)
    db.commit()
