"""Internal API endpoints used by the scanner worker."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Header

from app.api.deps import DbSession
from app.config import settings
from app.models import ScanJob, ScanResult, ScanStatus
from app.schemas.scan import ScanResultOut

from pydantic import BaseModel

router = APIRouter(prefix="/internal", tags=["internal"])


class ScanUpdatePayload(BaseModel):
    status: str
    raw_xml: str | None = None
    error_message: str | None = None
    results: list[dict] | None = None


def _verify_scanner_token(authorization: str = Header(...)) -> None:
    expected = f"Bearer {settings.scanner_api_token}"
    if authorization != expected:
        raise HTTPException(401, "Invalid scanner token")


@router.put("/scans/{scan_id}/results")
def update_scan_results(
    scan_id: str,
    body: ScanUpdatePayload,
    db: DbSession,
    authorization: str = Header(...),
):
    _verify_scanner_token(authorization)

    job = db.get(ScanJob, scan_id)
    if not job:
        raise HTTPException(404, "Scan job not found")

    now = datetime.now(timezone.utc)

    if body.status == "running":
        job.status = ScanStatus.running
        job.started_at = now

    elif body.status == "completed":
        job.status = ScanStatus.completed
        job.completed_at = now
        job.raw_xml = body.raw_xml

        if body.results:
            # Clear partial results and replace with full results (includes service/version)
            for r in job.results:
                db.delete(r)
            db.flush()
            for r in body.results:
                db.add(ScanResult(
                    job_id=scan_id,
                    host=r["host"],
                    port=r["port"],
                    protocol=r["protocol"],
                    state=r["state"],
                    service=r.get("service"),
                    version=r.get("version"),
                ))

    elif body.status == "failed":
        job.status = ScanStatus.failed
        job.completed_at = now
        job.error_message = body.error_message

    db.commit()
    return {"status": "ok"}


class ProgressPayload(BaseModel):
    progress: int
    phase: str | None = None


@router.post("/scans/{scan_id}/progress")
def update_scan_progress(
    scan_id: str,
    body: ProgressPayload,
    db: DbSession,
    authorization: str = Header(...),
):
    """Accept progress updates from the scanner."""
    _verify_scanner_token(authorization)

    job = db.get(ScanJob, scan_id)
    if not job:
        raise HTTPException(404, "Scan job not found")

    job.progress = body.progress
    if body.phase:
        job.progress_phase = body.phase
    db.commit()
    return {"status": "ok"}


class PartialResultsPayload(BaseModel):
    results: list[dict]


@router.post("/scans/{scan_id}/partial")
def push_partial_results(
    scan_id: str,
    body: PartialResultsPayload,
    db: DbSession,
    authorization: str = Header(...),
):
    """Accept partial results (discovered ports) while scan is still running."""
    _verify_scanner_token(authorization)

    job = db.get(ScanJob, scan_id)
    if not job:
        raise HTTPException(404, "Scan job not found")

    # Build set of existing (host, port, protocol) to avoid duplicates
    existing = {
        (r.host, r.port, r.protocol) for r in job.results
    }

    for r in body.results:
        key = (r["host"], r["port"], r["protocol"])
        if key not in existing:
            db.add(ScanResult(
                job_id=scan_id,
                host=r["host"],
                port=r["port"],
                protocol=r["protocol"],
                state=r.get("state", "open"),
                service=r.get("service"),
                version=r.get("version"),
            ))
            existing.add(key)

    db.commit()
    return {"status": "ok"}
