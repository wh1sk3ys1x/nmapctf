from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import DbSession
from app.models import Schedule, Asset, ScanProfile

router = APIRouter(prefix="/schedules", tags=["views"])


@router.get("/", response_class=HTMLResponse)
def list_schedules(request: Request, db: DbSession):
    from app.main import templates
    schedules = db.query(Schedule).order_by(Schedule.name).all()
    return templates.TemplateResponse("schedules/list.html", {"request": request, "schedules": schedules})


@router.get("/new", response_class=HTMLResponse)
def new_schedule(request: Request, db: DbSession):
    from app.main import templates
    assets = db.query(Asset).order_by(Asset.name).all()
    profiles = db.query(ScanProfile).order_by(ScanProfile.name).all()
    return templates.TemplateResponse(
        "schedules/form.html",
        {"request": request, "schedule": None, "assets": assets, "profiles": profiles},
    )


@router.get("/{schedule_id}/edit", response_class=HTMLResponse)
def edit_schedule(schedule_id: int, request: Request, db: DbSession):
    from app.main import templates
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        return RedirectResponse("/schedules", status_code=303)
    assets = db.query(Asset).order_by(Asset.name).all()
    profiles = db.query(ScanProfile).order_by(ScanProfile.name).all()
    return templates.TemplateResponse(
        "schedules/form.html",
        {"request": request, "schedule": schedule, "assets": assets, "profiles": profiles},
    )


@router.post("/", response_class=HTMLResponse)
def create_schedule(
    db: DbSession,
    name: str = Form(...),
    asset_id: int = Form(...),
    profile_id: int = Form(...),
    cron_expression: str = Form(...),
):
    schedule = Schedule(
        name=name, asset_id=asset_id, profile_id=profile_id, cron_expression=cron_expression
    )
    db.add(schedule)
    db.commit()
    return RedirectResponse("/schedules", status_code=303)


@router.post("/{schedule_id}", response_class=HTMLResponse)
def update_schedule(
    schedule_id: int,
    db: DbSession,
    name: str = Form(...),
    asset_id: int = Form(...),
    profile_id: int = Form(...),
    cron_expression: str = Form(...),
):
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        return RedirectResponse("/schedules", status_code=303)
    schedule.name = name
    schedule.asset_id = asset_id
    schedule.profile_id = profile_id
    schedule.cron_expression = cron_expression
    db.commit()
    return RedirectResponse("/schedules", status_code=303)


@router.post("/{schedule_id}/toggle")
def toggle_schedule(schedule_id: int, db: DbSession):
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
def delete_schedule(schedule_id: int, db: DbSession):
    schedule = db.get(Schedule, schedule_id)
    if schedule:
        db.delete(schedule)
        db.commit()
    return HTMLResponse("")
