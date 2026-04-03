from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.models import ScanProfile
from app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileOut

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/", response_model=list[ProfileOut])
def list_profiles(db: DbSession):
    return db.query(ScanProfile).order_by(ScanProfile.name).all()


@router.get("/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: int, db: DbSession):
    profile = db.get(ScanProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    return profile


@router.post("/", response_model=ProfileOut, status_code=201)
def create_profile(body: ProfileCreate, db: DbSession):
    profile = ScanProfile(**body.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/{profile_id}", response_model=ProfileOut)
def update_profile(profile_id: int, body: ProfileUpdate, db: DbSession):
    profile = db.get(ScanProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    if profile.is_default:
        raise HTTPException(400, "Cannot modify default profiles")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int, db: DbSession):
    profile = db.get(ScanProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    if profile.is_default:
        raise HTTPException(400, "Cannot delete default profiles")
    db.delete(profile)
    db.commit()
