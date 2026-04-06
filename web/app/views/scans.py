from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from redis import Redis
from rq import Queue

from app.api.deps import DbSession
from app.config import settings
from app.models import ScanJob, Asset, AssetType, ScanProfile, ScanStatus, AssetGroup
from app.org_scope import org_filter, get_org_id, can_edit

router = APIRouter(prefix="/scans", tags=["views"])


def _get_queue() -> Queue:
    conn = Redis.from_url(settings.redis_url)
    return Queue("scans", connection=conn)


@router.get("/", response_class=HTMLResponse)
def scan_history(
    request: Request,
    db: DbSession,
    status: str | None = None,
    asset_id: int | None = None,
):
    from app.main import templates

    query = org_filter(db.query(ScanJob), ScanJob, request)
    if status:
        query = query.filter(ScanJob.status == status)
    if asset_id:
        query = query.filter(ScanJob.asset_id == asset_id)
    scans = query.order_by(ScanJob.queued_at.desc()).limit(100).all()

    assets = org_filter(db.query(Asset), Asset, request).order_by(Asset.name).all()
    statuses = [s.value for s in ScanStatus]

    return templates.TemplateResponse(
        request, "scans/history.html",
        {
            "scans": scans,
            "assets": assets,
            "statuses": statuses,
            "filter_status": status,
            "filter_asset_id": asset_id,
        },
    )


@router.get("/run", response_class=HTMLResponse)
def run_scan_form(request: Request, db: DbSession):
    if not can_edit(request):
        return RedirectResponse("/scans", status_code=303)
    from app.main import templates
    assets = org_filter(db.query(Asset), Asset, request).order_by(Asset.name).all()
    profiles = db.query(ScanProfile).order_by(ScanProfile.name).all()
    groups = org_filter(db.query(AssetGroup), AssetGroup, request).order_by(AssetGroup.name).all()
    return templates.TemplateResponse(
        request, "scans/run.html", {"assets": assets, "profiles": profiles, "groups": groups},
    )


@router.post("/run", response_class=HTMLResponse)
def run_scan(
    request: Request,
    db: DbSession,
    asset_id: int | None = Form(None),
    asset_group_id: int | None = Form(None),
    quick_target: str | None = Form(None),
    profile_id: int = Form(...),
):
    if not can_edit(request):
        return RedirectResponse("/scans", status_code=303)
    profile = db.get(ScanProfile, profile_id)
    if not profile:
        return RedirectResponse("/scans/run", status_code=303)

    # Quick target: auto-create asset from typed address
    if quick_target and quick_target.strip():
        address = quick_target.strip()
        org_id = get_org_id(request)
        # Reuse existing asset if address matches within this org
        existing = db.query(Asset).filter(Asset.address == address, Asset.org_id == org_id).first()
        if existing:
            asset_id = existing.id
        else:
            asset = Asset(name=f"asset-{address}", type=AssetType.ip, address=address, org_id=org_id)
            db.add(asset)
            db.commit()
            db.refresh(asset)
            asset_id = asset.id

    if asset_group_id:
        group = db.get(AssetGroup, asset_group_id)
        if not group or not group.assets:
            return RedirectResponse("/scans/run", status_code=303)
        queue = _get_queue()
        for asset in group.assets:
            job = ScanJob(asset_id=asset.id, profile_id=profile_id, asset_group_id=group.id, org_id=get_org_id(request))
            db.add(job)
            db.commit()
            db.refresh(job)
            queue.enqueue(
                "tasks.run_scan",
                job_id=job.id,
                target=asset.address,
                nmap_args=profile.nmap_args,
                job_timeout="30m",
            )
        return RedirectResponse("/scans", status_code=303)
    else:
        asset = db.get(Asset, asset_id)
        if not asset:
            return RedirectResponse("/scans/run", status_code=303)
        job = ScanJob(asset_id=asset_id, profile_id=profile_id, org_id=get_org_id(request))
        db.add(job)
        db.commit()
        db.refresh(job)
        queue = _get_queue()
        queue.enqueue(
            "tasks.run_scan",
            job_id=job.id,
            target=asset.address,
            nmap_args=profile.nmap_args,
            job_timeout="30m",
        )
        return RedirectResponse(f"/scans/{job.id}", status_code=303)


@router.get("/{scan_id}", response_class=HTMLResponse)
def scan_detail(scan_id: str, request: Request, db: DbSession):
    from app.main import templates
    scan = db.get(ScanJob, scan_id)
    if not scan:
        return RedirectResponse("/scans", status_code=303)
    return templates.TemplateResponse(
        request, "scans/detail.html", {"scan": scan},
    )


@router.get("/{scan_id}/status", response_class=HTMLResponse)
def scan_status_partial(scan_id: str, db: DbSession, request: Request):
    """HTMX endpoint for polling scan status."""
    from app.main import templates
    scan = db.get(ScanJob, scan_id)
    if not scan:
        return HTMLResponse("")
    return templates.TemplateResponse(
        request, "partials/scan_status.html", {"scan": scan},
    )
