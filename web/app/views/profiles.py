from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import DbSession
from app.models import ScanProfile

router = APIRouter(prefix="/profiles", tags=["views"])


@router.get("/", response_class=HTMLResponse)
def list_profiles(request: Request, db: DbSession):
    from app.main import templates
    profiles = db.query(ScanProfile).order_by(ScanProfile.name).all()
    return templates.TemplateResponse("profiles/list.html", {"request": request, "profiles": profiles})


@router.get("/new", response_class=HTMLResponse)
def new_profile(request: Request):
    from app.main import templates
    return templates.TemplateResponse("profiles/form.html", {"request": request, "profile": None})


@router.get("/{profile_id}/edit", response_class=HTMLResponse)
def edit_profile(profile_id: int, request: Request, db: DbSession):
    from app.main import templates
    profile = db.get(ScanProfile, profile_id)
    if not profile:
        return RedirectResponse("/profiles", status_code=303)
    return templates.TemplateResponse("profiles/form.html", {"request": request, "profile": profile})


@router.post("/", response_class=HTMLResponse)
def create_profile(
    db: DbSession,
    name: str = Form(...),
    nmap_args: str = Form(...),
    description: str = Form(""),
):
    profile = ScanProfile(name=name, nmap_args=nmap_args, description=description or None)
    db.add(profile)
    db.commit()
    return RedirectResponse("/profiles", status_code=303)


@router.post("/{profile_id}", response_class=HTMLResponse)
def update_profile(
    profile_id: int,
    db: DbSession,
    name: str = Form(...),
    nmap_args: str = Form(...),
    description: str = Form(""),
):
    profile = db.get(ScanProfile, profile_id)
    if not profile or profile.is_default:
        return RedirectResponse("/profiles", status_code=303)
    profile.name = name
    profile.nmap_args = nmap_args
    profile.description = description or None
    db.commit()
    return RedirectResponse("/profiles", status_code=303)


@router.delete("/{profile_id}")
def delete_profile(profile_id: int, db: DbSession):
    profile = db.get(ScanProfile, profile_id)
    if profile and not profile.is_default:
        db.delete(profile)
        db.commit()
    return HTMLResponse("")
