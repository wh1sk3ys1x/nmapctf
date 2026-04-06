"""Organization management views (superadmin only)."""
import re

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import DbSession
from app.auth import hash_password
from app.models import Organization, User, OrgRole

router = APIRouter(prefix="/orgs", tags=["views"])


def _require_superadmin(request: Request):
    """Return RedirectResponse if not superadmin, else None."""
    if not request.session.get("is_superadmin"):
        return RedirectResponse("/", status_code=303)
    return None


def _slugify(name: str) -> str:
    """Convert name to URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


@router.get("/", response_class=HTMLResponse)
def list_orgs(request: Request, db: DbSession):
    if redirect := _require_superadmin(request):
        return redirect
    from app.main import templates
    orgs = db.query(Organization).order_by(Organization.name).all()
    return templates.TemplateResponse(request, "orgs/list.html", {"orgs": orgs})


@router.get("/new", response_class=HTMLResponse)
def new_org(request: Request):
    if redirect := _require_superadmin(request):
        return redirect
    from app.main import templates
    return templates.TemplateResponse(request, "orgs/form.html", {"org": None})


@router.get("/{org_id}", response_class=HTMLResponse)
def org_detail(org_id: int, request: Request, db: DbSession):
    if redirect := _require_superadmin(request):
        return redirect
    from app.main import templates
    org = db.get(Organization, org_id)
    if not org:
        return RedirectResponse("/orgs", status_code=303)
    members = db.query(User).filter(User.org_id == org_id).order_by(User.username).all()
    return templates.TemplateResponse(
        request, "orgs/detail.html", {"org": org, "members": members, "org_roles": [r.value for r in OrgRole]},
    )


@router.get("/{org_id}/edit", response_class=HTMLResponse)
def edit_org(org_id: int, request: Request, db: DbSession):
    if redirect := _require_superadmin(request):
        return redirect
    from app.main import templates
    org = db.get(Organization, org_id)
    if not org:
        return RedirectResponse("/orgs", status_code=303)
    return templates.TemplateResponse(request, "orgs/form.html", {"org": org})


@router.post("/", response_class=HTMLResponse)
def create_org(
    request: Request,
    db: DbSession,
    name: str = Form(...),
):
    if redirect := _require_superadmin(request):
        return redirect
    org = Organization(name=name, slug=_slugify(name))
    db.add(org)
    db.commit()
    db.refresh(org)
    return RedirectResponse(f"/orgs/{org.id}", status_code=303)


@router.post("/{org_id}", response_class=HTMLResponse)
def update_org(
    org_id: int,
    request: Request,
    db: DbSession,
    name: str = Form(...),
):
    if redirect := _require_superadmin(request):
        return redirect
    org = db.get(Organization, org_id)
    if not org:
        return RedirectResponse("/orgs", status_code=303)
    org.name = name
    org.slug = _slugify(name)
    db.commit()
    return RedirectResponse(f"/orgs/{org_id}", status_code=303)


@router.delete("/{org_id}")
def delete_org(org_id: int, request: Request, db: DbSession):
    if redirect := _require_superadmin(request):
        return redirect
    org = db.get(Organization, org_id)
    if org:
        db.delete(org)
        db.commit()
    return HTMLResponse("")


@router.post("/{org_id}/members", response_class=HTMLResponse)
def add_member(
    org_id: int,
    request: Request,
    db: DbSession,
    username: str = Form(...),
    password: str = Form(...),
    org_role: str = Form(...),
):
    if redirect := _require_superadmin(request):
        return redirect
    org = db.get(Organization, org_id)
    if not org:
        return RedirectResponse("/orgs", status_code=303)
    user = User(
        username=username,
        password_hash=hash_password(password),
        org_id=org_id,
        org_role=OrgRole(org_role),
    )
    db.add(user)
    db.commit()
    return RedirectResponse(f"/orgs/{org_id}", status_code=303)


@router.post("/{org_id}/members/{user_id}/role", response_class=HTMLResponse)
def update_member_role(
    org_id: int,
    user_id: int,
    request: Request,
    db: DbSession,
    org_role: str = Form(...),
):
    if redirect := _require_superadmin(request):
        return redirect
    user = db.get(User, user_id)
    if user and user.org_id == org_id:
        user.org_role = OrgRole(org_role)
        db.commit()
    return RedirectResponse(f"/orgs/{org_id}", status_code=303)


@router.delete("/{org_id}/members/{user_id}")
def remove_member(org_id: int, user_id: int, request: Request, db: DbSession):
    if redirect := _require_superadmin(request):
        return redirect
    user = db.get(User, user_id)
    if user and user.org_id == org_id and not user.is_superadmin:
        db.delete(user)
        db.commit()
    return HTMLResponse("")
