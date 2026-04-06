"""Report data queries for different report scopes."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import ScanJob, ScanResult, Asset, ScanProfile, ScanStatus


def single_scan_report(db: Session, scan_id: str) -> dict | None:
    """Report data for a single scan."""
    scan = db.get(ScanJob, scan_id)
    if not scan:
        return None
    return {
        "title": f"Scan Report: {scan.asset.name} — {scan.profile.name}",
        "generated_at": datetime.now(timezone.utc),
        "scans": [scan],
        "results": scan.results,
        "summary": {
            "total_hosts": len(set(r.host for r in scan.results)),
            "total_ports": len(scan.results),
            "open_ports": sum(1 for r in scan.results if r.state == "open"),
        },
    }


def asset_report(db: Session, asset_id: int, date_from: datetime | None = None, date_to: datetime | None = None) -> dict | None:
    """Report data for all scans of a specific asset."""
    asset = db.get(Asset, asset_id)
    if not asset:
        return None
    query = db.query(ScanJob).filter(
        ScanJob.asset_id == asset_id,
        ScanJob.status == ScanStatus.completed,
    )
    if date_from:
        query = query.filter(ScanJob.completed_at >= date_from)
    if date_to:
        query = query.filter(ScanJob.completed_at <= date_to)
    scans = query.order_by(ScanJob.completed_at.desc()).all()

    all_results = []
    for scan in scans:
        all_results.extend(scan.results)

    return {
        "title": f"Asset Report: {asset.name} ({asset.address})",
        "generated_at": datetime.now(timezone.utc),
        "scans": scans,
        "results": all_results,
        "summary": {
            "total_scans": len(scans),
            "total_hosts": len(set(r.host for r in all_results)),
            "total_ports": len(all_results),
            "open_ports": sum(1 for r in all_results if r.state == "open"),
        },
    }


def full_report(db: Session, date_from: datetime | None = None, date_to: datetime | None = None) -> dict:
    """Report data for all completed scans in a date range."""
    query = db.query(ScanJob).filter(ScanJob.status == ScanStatus.completed)
    if date_from:
        query = query.filter(ScanJob.completed_at >= date_from)
    if date_to:
        query = query.filter(ScanJob.completed_at <= date_to)
    scans = query.order_by(ScanJob.completed_at.desc()).all()

    all_results = []
    for scan in scans:
        all_results.extend(scan.results)

    return {
        "title": "Full Scan Report",
        "generated_at": datetime.now(timezone.utc),
        "scans": scans,
        "results": all_results,
        "summary": {
            "total_scans": len(scans),
            "total_assets": len(set(s.asset_id for s in scans)),
            "total_hosts": len(set(r.host for r in all_results)),
            "total_ports": len(all_results),
            "open_ports": sum(1 for r in all_results if r.state == "open"),
        },
    }
