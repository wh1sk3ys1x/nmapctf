from typing import List

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import DbSession
from app.models import Asset, AssetType, AssetGroup, AssetAddress
from app.org_scope import org_filter, get_org_id, can_edit

router = APIRouter(prefix="/assets", tags=["views"])


@router.get("/", response_class=HTMLResponse)
def list_assets(request: Request, db: DbSession):
    from app.main import templates
    query = org_filter(db.query(Asset), Asset, request)
    assets = query.order_by(Asset.name).all()
    groups = org_filter(db.query(AssetGroup), AssetGroup, request).order_by(AssetGroup.name).all()
    return templates.TemplateResponse(request, "assets/list.html", {"assets": assets, "groups": groups})


@router.get("/new", response_class=HTMLResponse)
def new_asset(request: Request):
    if not can_edit(request):
        return RedirectResponse("/assets", status_code=303)
    from app.main import templates
    return templates.TemplateResponse(
        request, "assets/form.html", {"asset": None, "asset_types": list(AssetType)},
    )


@router.post("/", response_class=HTMLResponse)
def create_asset(
    request: Request,
    db: DbSession,
    name: str = Form(...),
    type: str = Form(...),
    address: str = Form(...),
    notes: str = Form(""),
):
    if not can_edit(request):
        return RedirectResponse("/assets", status_code=303)
    asset = Asset(name=name, type=AssetType(type), address=address, notes=notes or None, org_id=get_org_id(request))
    db.add(asset)
    db.commit()
    db.refresh(asset)
    primary_addr = AssetAddress(asset_id=asset.id, address=address, is_primary=True)
    db.add(primary_addr)
    db.commit()
    return RedirectResponse("/assets", status_code=303)


@router.post("/bulk-delete", response_class=HTMLResponse)
def bulk_delete(request: Request, db: DbSession, asset_ids: List[str] = Form([])):
    if not can_edit(request):
        return RedirectResponse("/assets", status_code=303)
    for aid in asset_ids:
        if aid.strip():
            asset = db.get(Asset, int(aid))
            if asset:
                db.delete(asset)
    db.commit()
    return RedirectResponse("/assets", status_code=303)


@router.post("/bulk-add-to-group", response_class=HTMLResponse)
def bulk_add_to_group(
    request: Request,
    db: DbSession,
    asset_ids: List[str] = Form([]),
    group_id: str = Form(""),
):
    if not can_edit(request):
        return RedirectResponse("/assets", status_code=303)
    if not group_id.strip():
        return RedirectResponse("/assets", status_code=303)
    group = db.get(AssetGroup, int(group_id))
    if not group:
        return RedirectResponse("/assets", status_code=303)
    for aid in asset_ids:
        if aid.strip():
            asset = db.get(Asset, int(aid))
            if asset and asset not in group.assets:
                group.assets.append(asset)
    db.commit()
    return RedirectResponse("/assets", status_code=303)


@router.post("/{asset_id}/addresses", response_class=HTMLResponse)
def add_address(
    asset_id: int,
    request: Request,
    db: DbSession,
    address: str = Form(...),
    label: str = Form(""),
):
    if not can_edit(request):
        return HTMLResponse("")
    from app.main import templates
    asset = db.get(Asset, asset_id)
    if not asset:
        return HTMLResponse("")
    addr = AssetAddress(asset_id=asset_id, address=address, label=label or None, is_primary=False)
    db.add(addr)
    db.commit()
    db.refresh(asset)
    return templates.TemplateResponse(request, "assets/addresses_partial.html", {"asset": asset})


@router.delete("/{asset_id}/addresses/{address_id}", response_class=HTMLResponse)
def remove_address(asset_id: int, address_id: int, request: Request, db: DbSession):
    if not can_edit(request):
        return HTMLResponse("")
    from app.main import templates
    addr = db.get(AssetAddress, address_id)
    if addr and addr.asset_id == asset_id and not addr.is_primary:
        db.delete(addr)
        db.commit()
    asset = db.get(Asset, asset_id)
    return templates.TemplateResponse(request, "assets/addresses_partial.html", {"asset": asset})


@router.get("/{asset_id}/edit", response_class=HTMLResponse)
def edit_asset(asset_id: int, request: Request, db: DbSession):
    if not can_edit(request):
        return RedirectResponse("/assets", status_code=303)
    from app.main import templates
    asset = db.get(Asset, asset_id)
    if not asset:
        return RedirectResponse("/assets", status_code=303)
    return templates.TemplateResponse(
        request, "assets/form.html", {"asset": asset, "asset_types": list(AssetType)},
    )


@router.post("/{asset_id}", response_class=HTMLResponse)
def update_asset(
    asset_id: int,
    request: Request,
    db: DbSession,
    name: str = Form(...),
    type: str = Form(...),
    address: str = Form(...),
    notes: str = Form(""),
):
    if not can_edit(request):
        return RedirectResponse("/assets", status_code=303)
    asset = db.get(Asset, asset_id)
    if not asset:
        return RedirectResponse("/assets", status_code=303)
    asset.name = name
    asset.type = AssetType(type)
    asset.address = address
    asset.notes = notes or None
    # Sync primary AssetAddress
    primary = next((a for a in asset.addresses if a.is_primary), None)
    if primary:
        primary.address = address
    else:
        db.add(AssetAddress(asset_id=asset.id, address=address, is_primary=True))
    db.commit()
    return RedirectResponse("/assets", status_code=303)


@router.delete("/{asset_id}")
def delete_asset(asset_id: int, request: Request, db: DbSession):
    if not can_edit(request):
        return HTMLResponse("")
    asset = db.get(Asset, asset_id)
    if asset:
        db.delete(asset)
        db.commit()
    return HTMLResponse("")
