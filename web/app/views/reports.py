"""Report generation view routes."""
import csv
import io
import json

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from weasyprint import HTML

from app.api.deps import DbSession
from app.models import Asset, ScanJob
from app.reports import single_scan_report, asset_report, full_report

router = APIRouter(prefix="/reports", tags=["views"])


def _parse_date(value: str | None):
    """Parse YYYY-MM-DD string to datetime, or None."""
    if not value:
        return None
    from datetime import datetime
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def _get_report(db, scope, scan_id, asset_id, date_from, date_to):
    """Dispatch to the correct report function based on scope."""
    if scope == "scan" and scan_id:
        return single_scan_report(db, scan_id)
    elif scope == "asset" and asset_id:
        return asset_report(db, asset_id, _parse_date(date_from), _parse_date(date_to))
    else:
        return full_report(db, _parse_date(date_from), _parse_date(date_to))


@router.get("/", response_class=HTMLResponse)
def report_index(request: Request, db: DbSession):
    from app.main import templates
    assets = db.query(Asset).order_by(Asset.name).all()
    scans = db.query(ScanJob).filter(ScanJob.status == "completed").order_by(ScanJob.queued_at.desc()).limit(50).all()
    return templates.TemplateResponse(
        request, "reports/index.html", {"assets": assets, "scans": scans},
    )


@router.get("/view", response_class=HTMLResponse)
def report_html(
    request: Request,
    db: DbSession,
    scope: str = Query("all"),
    scan_id: str | None = Query(None),
    asset_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
):
    from app.main import templates
    data = _get_report(db, scope, scan_id, asset_id, date_from, date_to)
    if data is None:
        return HTMLResponse("Report not found", status_code=404)
    return templates.TemplateResponse(
        request, "reports/report.html",
        {"report": data, "scope": scope, "scan_id": scan_id, "asset_id": asset_id, "date_from": date_from, "date_to": date_to},
    )


@router.get("/pdf")
def report_pdf(
    request: Request,
    db: DbSession,
    scope: str = Query("all"),
    scan_id: str | None = Query(None),
    asset_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
):
    from app.main import templates
    data = _get_report(db, scope, scan_id, asset_id, date_from, date_to)
    if data is None:
        return HTMLResponse("Report not found", status_code=404)
    html_str = templates.get_template("reports/report.html").render(
        request=request, report=data, scope=scope, scan_id=scan_id,
        asset_id=asset_id, date_from=date_from, date_to=date_to,
    )
    pdf_bytes = HTML(string=html_str).write_pdf()
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report.pdf"'},
    )


@router.get("/csv")
def report_csv(
    db: DbSession,
    scope: str = Query("all"),
    scan_id: str | None = Query(None),
    asset_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
):
    data = _get_report(db, scope, scan_id, asset_id, date_from, date_to)
    if data is None:
        return HTMLResponse("Report not found", status_code=404)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["host", "port", "protocol", "state", "service", "version"])
    for r in data["results"]:
        writer.writerow([r.host, r.port, r.protocol, r.state, r.service or "", r.version or ""])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="report.csv"'},
    )


@router.get("/json")
def report_json(
    db: DbSession,
    scope: str = Query("all"),
    scan_id: str | None = Query(None),
    asset_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
):
    data = _get_report(db, scope, scan_id, asset_id, date_from, date_to)
    if data is None:
        return HTMLResponse("Report not found", status_code=404)
    rows = [
        {
            "host": r.host,
            "port": r.port,
            "protocol": r.protocol,
            "state": r.state,
            "service": r.service,
            "version": r.version,
        }
        for r in data["results"]
    ]
    output = json.dumps({"title": data["title"], "summary": data["summary"], "results": rows}, indent=2)
    return StreamingResponse(
        io.BytesIO(output.encode()),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="report.json"'},
    )
