from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func

from app.api.deps import DbSession
from app.models import ScanJob, Asset, Schedule, ScanStatus

router = APIRouter(tags=["views"])


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: DbSession):
    from app.main import templates

    total_assets = db.query(func.count(Asset.id)).scalar()
    total_scans = db.query(func.count(ScanJob.id)).scalar()
    running_scans = db.query(func.count(ScanJob.id)).filter(
        ScanJob.status.in_([ScanStatus.pending, ScanStatus.running])
    ).scalar()
    active_schedules = db.query(func.count(Schedule.id)).filter(
        Schedule.enabled == True
    ).scalar()

    recent_scans = (
        db.query(ScanJob)
        .order_by(ScanJob.queued_at.desc())
        .limit(10)
        .all()
    )

    upcoming_schedules = (
        db.query(Schedule)
        .filter(Schedule.enabled == True)
        .order_by(Schedule.name)
        .limit(5)
        .all()
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "total_assets": total_assets,
            "total_scans": total_scans,
            "running_scans": running_scans,
            "active_schedules": active_schedules,
            "recent_scans": recent_scans,
            "upcoming_schedules": upcoming_schedules,
        },
    )
