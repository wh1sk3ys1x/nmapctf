from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import DbSession
from app.models import AssetGroup, Asset
from app.org_scope import org_filter, get_org_id, can_edit

router = APIRouter(prefix="/groups", tags=["views"])


@router.get("/", response_class=HTMLResponse)
def list_groups(request: Request, db: DbSession):
    from app.main import templates
    groups = org_filter(db.query(AssetGroup), AssetGroup, request).order_by(AssetGroup.name).all()
    return templates.TemplateResponse(request, "groups/list.html", {"groups": groups})


@router.get("/new", response_class=HTMLResponse)
def new_group(request: Request):
    if not can_edit(request):
        return RedirectResponse("/groups", status_code=303)
    from app.main import templates
    return templates.TemplateResponse(request, "groups/form.html", {"group": None})


@router.get("/{group_id}", response_class=HTMLResponse)
def group_detail(group_id: int, request: Request, db: DbSession):
    from app.main import templates
    group = db.get(AssetGroup, group_id)
    if not group:
        return RedirectResponse("/groups", status_code=303)
    available_assets = (
        db.query(Asset)
        .filter(~Asset.id.in_([a.id for a in group.assets]))
        .order_by(Asset.name)
        .all()
    )
    return templates.TemplateResponse(
        request, "groups/detail.html",
        {"group": group, "available_assets": available_assets},
    )


@router.get("/{group_id}/edit", response_class=HTMLResponse)
def edit_group(group_id: int, request: Request, db: DbSession):
    if not can_edit(request):
        return RedirectResponse("/groups", status_code=303)
    from app.main import templates
    group = db.get(AssetGroup, group_id)
    if not group:
        return RedirectResponse("/groups", status_code=303)
    return templates.TemplateResponse(request, "groups/form.html", {"group": group})


@router.post("/", response_class=HTMLResponse)
def create_group(
    request: Request,
    db: DbSession,
    name: str = Form(...),
    description: str = Form(""),
):
    if not can_edit(request):
        return RedirectResponse("/groups", status_code=303)
    group = AssetGroup(name=name, description=description or None, org_id=get_org_id(request))
    db.add(group)
    db.commit()
    db.refresh(group)
    return RedirectResponse(f"/groups/{group.id}", status_code=303)


@router.post("/{group_id}", response_class=HTMLResponse)
def update_group(
    group_id: int,
    request: Request,
    db: DbSession,
    name: str = Form(...),
    description: str = Form(""),
):
    if not can_edit(request):
        return RedirectResponse("/groups", status_code=303)
    group = db.get(AssetGroup, group_id)
    if not group:
        return RedirectResponse("/groups", status_code=303)
    group.name = name
    group.description = description or None
    db.commit()
    return RedirectResponse(f"/groups/{group_id}", status_code=303)


@router.post("/{group_id}/members", response_class=HTMLResponse)
def add_member(
    group_id: int,
    request: Request,
    db: DbSession,
    asset_id: int = Form(...),
):
    if not can_edit(request):
        return RedirectResponse(f"/groups/{group_id}", status_code=303)
    group = db.get(AssetGroup, group_id)
    asset = db.get(Asset, asset_id)
    if group and asset and asset not in group.assets:
        group.assets.append(asset)
        db.commit()
    return RedirectResponse(f"/groups/{group_id}", status_code=303)


@router.delete("/{group_id}/members/{asset_id}")
def remove_member(group_id: int, asset_id: int, request: Request, db: DbSession):
    if not can_edit(request):
        return HTMLResponse("")
    group = db.get(AssetGroup, group_id)
    asset = db.get(Asset, asset_id)
    if group and asset and asset in group.assets:
        group.assets.remove(asset)
        db.commit()
    return HTMLResponse("")


@router.delete("/{group_id}")
def delete_group(group_id: int, request: Request, db: DbSession):
    if not can_edit(request):
        return HTMLResponse("")
    group = db.get(AssetGroup, group_id)
    if group:
        db.delete(group)
        db.commit()
    return HTMLResponse("")
