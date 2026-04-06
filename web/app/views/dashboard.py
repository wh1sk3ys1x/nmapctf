from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func

from app.api.deps import DbSession
from app.models import ScanJob, Asset, Schedule, ScanStatus
from app.org_scope import org_filter, is_superadmin

router = APIRouter(tags=["views"])


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: DbSession):
    from app.main import templates

    total_assets = org_filter(db.query(func.count(Asset.id)), Asset, request).scalar()
    total_scans = org_filter(db.query(func.count(ScanJob.id)), ScanJob, request).scalar()
    running_scans = org_filter(db.query(func.count(ScanJob.id)), ScanJob, request).filter(
        ScanJob.status.in_([ScanStatus.pending, ScanStatus.running])
    ).scalar()
    active_schedules = org_filter(db.query(func.count(Schedule.id)), Schedule, request).filter(
        Schedule.enabled == True
    ).scalar()

    recent_scans = (
        org_filter(db.query(ScanJob), ScanJob, request)
        .order_by(ScanJob.queued_at.desc())
        .limit(10)
        .all()
    )

    upcoming_schedules = (
        org_filter(db.query(Schedule), Schedule, request)
        .filter(Schedule.enabled == True)
        .order_by(Schedule.name)
        .limit(5)
        .all()
    )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "total_assets": total_assets,
            "total_scans": total_scans,
            "running_scans": running_scans,
            "active_schedules": active_schedules,
            "recent_scans": recent_scans,
            "upcoming_schedules": upcoming_schedules,
        },
    )
