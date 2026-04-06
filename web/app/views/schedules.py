from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import DbSession
from app.models import Schedule, Asset, ScanProfile, AssetGroup
from app.org_scope import org_filter, get_org_id, can_edit

router = APIRouter(prefix="/schedules", tags=["views"])


@router.get("/", response_class=HTMLResponse)
def list_schedules(request: Request, db: DbSession):
    from app.main import templates
    schedules = org_filter(db.query(Schedule), Schedule, request).order_by(Schedule.name).all()
    return templates.TemplateResponse(request, "schedules/list.html", {"schedules": schedules})


@router.get("/new", response_class=HTMLResponse)
def new_schedule(request: Request, db: DbSession):
    if not can_edit(request):
        return RedirectResponse("/schedules", status_code=303)
    from app.main import templates
    assets = org_filter(db.query(Asset), Asset, request).order_by(Asset.name).all()
    profiles = db.query(ScanProfile).order_by(ScanProfile.name).all()
    groups = org_filter(db.query(AssetGroup), AssetGroup, request).order_by(AssetGroup.name).all()
    return templates.TemplateResponse(
        request, "schedules/form.html",
        {"schedule": None, "assets": assets, "profiles": profiles, "groups": groups},
    )


@router.get("/{schedule_id}/edit", response_class=HTMLResponse)
def edit_schedule(schedule_id: int, request: Request, db: DbSession):
    if not can_edit(request):
        return RedirectResponse("/schedules", status_code=303)
    from app.main import templates
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        return RedirectResponse("/schedules", status_code=303)
    assets = org_filter(db.query(Asset), Asset, request).order_by(Asset.name).all()
    profiles = db.query(ScanProfile).order_by(ScanProfile.name).all()
    groups = org_filter(db.query(AssetGroup), AssetGroup, request).order_by(AssetGroup.name).all()
    return templates.TemplateResponse(
        request, "schedules/form.html",
        {"schedule": schedule, "assets": assets, "profiles": profiles, "groups": groups},
    )


@router.post("/", response_class=HTMLResponse)
def create_schedule(
    request: Request,
    db: DbSession,
    name: str = Form(...),
    asset_id: int | None = Form(None),
    asset_group_id: int | None = Form(None),
    profile_id: int = Form(...),
    cron_expression: str = Form(...),
):
    if not can_edit(request):
        return RedirectResponse("/schedules", status_code=303)
    schedule = Schedule(
        name=name,
        asset_id=asset_id or None,
        asset_group_id=asset_group_id or None,
        profile_id=profile_id,
        cron_expression=cron_expression,
        org_id=get_org_id(request),
    )
    db.add(schedule)
    db.commit()
    return RedirectResponse("/schedules", status_code=303)


@router.post("/{schedule_id}", response_class=HTMLResponse)
def update_schedule(
    schedule_id: int,
    request: Request,
    db: DbSession,
    name: str = Form(...),
    asset_id: int | None = Form(None),
    asset_group_id: int | None = Form(None),
    profile_id: int = Form(...),
    cron_expression: str = Form(...),
):
    if not can_edit(request):
        return RedirectResponse("/schedules", status_code=303)
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        return RedirectResponse("/schedules", status_code=303)
    schedule.name = name
    schedule.asset_id = asset_id or None
    schedule.asset_group_id = asset_group_id or None
    schedule.profile_id = profile_id
    schedule.cron_expression = cron_expression
    db.commit()
    return RedirectResponse("/schedules", status_code=303)


@router.post("/{schedule_id}/toggle")
def toggle_schedule(schedule_id: int, request: Request, db: DbSession):
    if not can_edit(request):
        return HTMLResponse("")
    schedule = db.get(Schedule, schedule_id)
    if schedule:
        schedule.enabled = not schedule.enabled
        db.commit()
        state = "Disable" if schedule.enabled else "Enable"
        btn_class = "btn-outline-warning" if schedule.enabled else "btn-outline-success"
        return HTMLResponse(
            f'<button class="btn btn-sm {btn_class}" '
            f'hx-post="/schedules/{schedule_id}/toggle" '
            f'hx-swap="outerHTML">{state}</button>'
        )
    return HTMLResponse("")


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, request: Request, db: DbSession):
    if not can_edit(request):
        return HTMLResponse("")
    schedule = db.get(Schedule, schedule_id)
    if schedule:
        db.delete(schedule)
        db.commit()
    return HTMLResponse("")
