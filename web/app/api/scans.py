from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.models import ScanJob, Asset, ScanProfile
from app.schemas.scan import ScanCreate, ScanOut, ScanDetailOut

router = APIRouter(prefix="/scans", tags=["scans"])


@router.get("/", response_model=list[ScanOut])
def list_scans(db: DbSession, status: str | None = None, asset_id: int | None = None):
    query = db.query(ScanJob)
    if status:
        query = query.filter(ScanJob.status == status)
    if asset_id:
        query = query.filter(ScanJob.asset_id == asset_id)
    return query.order_by(ScanJob.queued_at.desc()).all()


@router.get("/{scan_id}", response_model=ScanDetailOut)
def get_scan(scan_id: str, db: DbSession):
    scan = db.get(ScanJob, scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    return scan


@router.post("/", response_model=ScanOut, status_code=201)
def create_scan(body: ScanCreate, db: DbSession):
    if not db.get(Asset, body.asset_id):
        raise HTTPException(404, "Asset not found")
    if not db.get(ScanProfile, body.profile_id):
        raise HTTPException(404, "Profile not found")

    job = ScanJob(asset_id=body.asset_id, profile_id=body.profile_id)
    db.add(job)
    db.commit()
    db.refresh(job)

    # TODO: enqueue job to Redis once scanner integration is wired up

    return job
