from fastapi import APIRouter, HTTPException
from redis import Redis
from rq import Queue

from app.api.deps import DbSession
from app.config import settings
from app.models import ScanJob, Asset, ScanProfile
from app.schemas.scan import ScanCreate, ScanOut, ScanDetailOut

router = APIRouter(prefix="/scans", tags=["scans"])


def _get_queue() -> Queue:
    conn = Redis.from_url(settings.redis_url)
    return Queue("scans", connection=conn)


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
    asset = db.get(Asset, body.asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    profile = db.get(ScanProfile, body.profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")

    job = ScanJob(asset_id=body.asset_id, profile_id=body.profile_id)
    db.add(job)
    db.commit()
    db.refresh(job)

    # Enqueue the scan job for the scanner worker
    queue = _get_queue()
    queue.enqueue(
        "tasks.run_scan",
        job_id=job.id,
        target=asset.address,
        nmap_args=profile.nmap_args,
        job_timeout="30m",
    )

    return job
