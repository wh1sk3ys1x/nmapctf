"""Asset import via file upload."""
import csv
import io

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse

from app.api.deps import DbSession
from app.models import Asset, AssetType, AssetGroup
from app.org_scope import get_org_id, org_filter, can_edit

router = APIRouter(prefix="/assets", tags=["views"])


def _parse_csv(content: str) -> list[dict]:
    """Parse CSV content into list of dicts with address, name, type, notes."""
    reader = csv.DictReader(io.StringIO(content))
    # Normalize header names to lowercase
    rows = []
    for row in reader:
        normalized = {k.strip().lower(): v.strip() if v else "" for k, v in row.items()}
        if normalized.get("address"):
            rows.append(normalized)
    return rows


def _parse_xlsx(content: bytes) -> list[dict]:
    """Parse XLSX content into list of dicts with address, name, type, notes."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(h).strip().lower() if h else "" for h in next(rows_iter, [])]
    if "address" not in headers:
        return []
    rows = []
    for row in rows_iter:
        entry = {}
        for i, val in enumerate(row):
            if i < len(headers) and headers[i]:
                entry[headers[i]] = str(val).strip() if val else ""
        if entry.get("address"):
            rows.append(entry)
    return rows


def _parse_txt(content: str) -> list[dict]:
    """Parse TXT content — one address per line."""
    rows = []
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            rows.append({"address": line})
    return rows


def _resolve_type(type_str: str | None, default_type: str) -> AssetType:
    """Convert a type string to AssetType enum, falling back to default."""
    if type_str:
        try:
            return AssetType(type_str.lower())
        except ValueError:
            pass
    return AssetType(default_type)


@router.get("/import", response_class=HTMLResponse)
def import_form(request: Request, db: DbSession):
    if not can_edit(request):
        return RedirectResponse("/assets", status_code=303)
    from app.main import templates
    groups = org_filter(db.query(AssetGroup), AssetGroup, request).order_by(AssetGroup.name).all()
    asset_types = [t.value for t in AssetType]
    return templates.TemplateResponse(
        request, "assets/import.html",
        {"groups": groups, "asset_types": asset_types, "results": None},
    )


@router.post("/import", response_class=HTMLResponse)
async def import_assets(
    request: Request,
    db: DbSession,
    file: UploadFile = File(...),
    asset_group_id: int | None = Form(None),
    default_type: str = Form("ip"),
):
    if not can_edit(request):
        return RedirectResponse("/assets", status_code=303)
    from app.main import templates

    content_bytes = await file.read()
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # Parse based on file type
    if ext == "xlsx":
        entries = _parse_xlsx(content_bytes)
    elif ext == "csv":
        entries = _parse_csv(content_bytes.decode("utf-8", errors="replace"))
    elif ext == "txt":
        entries = _parse_txt(content_bytes.decode("utf-8", errors="replace"))
    else:
        groups = org_filter(db.query(AssetGroup), AssetGroup, request).order_by(AssetGroup.name).all()
        asset_types = [t.value for t in AssetType]
        return templates.TemplateResponse(
            request, "assets/import.html",
            {
                "groups": groups, "asset_types": asset_types,
                "results": {"error": f"Unsupported file type: .{ext}. Use .csv, .xlsx, or .txt"},
            },
        )

    # Process entries
    created = []
    skipped = []
    existing_addresses = {a.address for a in org_filter(db.query(Asset.address), Asset, request).all()}

    for entry in entries:
        address = entry["address"]
        if address in existing_addresses:
            skipped.append({"address": address, "reason": "already exists"})
            continue

        name = entry.get("name") or f"asset-{address}"
        asset_type = _resolve_type(entry.get("type"), default_type)

        asset = Asset(
            name=name,
            type=asset_type,
            address=address,
            notes=entry.get("notes") or None,
            org_id=get_org_id(request),
        )
        db.add(asset)
        try:
            db.flush()
            existing_addresses.add(address)
            created.append(asset)
        except Exception:
            db.rollback()
            skipped.append({"address": address, "reason": "duplicate name or invalid data"})

    # Add to group if selected
    group = None
    if asset_group_id and created:
        group = db.get(AssetGroup, asset_group_id)
        if group:
            for asset in created:
                group.assets.append(asset)

    db.commit()

    groups = org_filter(db.query(AssetGroup), AssetGroup, request).order_by(AssetGroup.name).all()
    asset_types = [t.value for t in AssetType]
    return templates.TemplateResponse(
        request, "assets/import.html",
        {
            "groups": groups, "asset_types": asset_types,
            "results": {
                "created": [{"name": a.name, "address": a.address} for a in created],
                "skipped": skipped,
                "total": len(entries),
                "group_name": group.name if group else None,
            },
        },
    )
