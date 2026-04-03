from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import DbSession
from app.models import Asset, AssetType

router = APIRouter(prefix="/assets", tags=["views"])


@router.get("/", response_class=HTMLResponse)
def list_assets(request: Request, db: DbSession):
    from app.main import templates
    assets = db.query(Asset).order_by(Asset.name).all()
    return templates.TemplateResponse(request, "assets/list.html", {"assets": assets})


@router.get("/new", response_class=HTMLResponse)
def new_asset(request: Request):
    from app.main import templates
    return templates.TemplateResponse(
        request, "assets/form.html", {"asset": None, "asset_types": list(AssetType)},
    )


@router.get("/{asset_id}/edit", response_class=HTMLResponse)
def edit_asset(asset_id: int, request: Request, db: DbSession):
    from app.main import templates
    asset = db.get(Asset, asset_id)
    if not asset:
        return RedirectResponse("/assets", status_code=303)
    return templates.TemplateResponse(
        request, "assets/form.html", {"asset": asset, "asset_types": list(AssetType)},
    )


@router.post("/", response_class=HTMLResponse)
def create_asset(
    db: DbSession,
    name: str = Form(...),
    type: str = Form(...),
    address: str = Form(...),
    notes: str = Form(""),
):
    asset = Asset(name=name, type=AssetType(type), address=address, notes=notes or None)
    db.add(asset)
    db.commit()
    return RedirectResponse("/assets", status_code=303)


@router.post("/{asset_id}", response_class=HTMLResponse)
def update_asset(
    asset_id: int,
    db: DbSession,
    name: str = Form(...),
    type: str = Form(...),
    address: str = Form(...),
    notes: str = Form(""),
):
    asset = db.get(Asset, asset_id)
    if not asset:
        return RedirectResponse("/assets", status_code=303)
    asset.name = name
    asset.type = AssetType(type)
    asset.address = address
    asset.notes = notes or None
    db.commit()
    return RedirectResponse("/assets", status_code=303)


@router.delete("/{asset_id}")
def delete_asset(asset_id: int, db: DbSession):
    asset = db.get(Asset, asset_id)
    if asset:
        db.delete(asset)
        db.commit()
    return HTMLResponse("")
