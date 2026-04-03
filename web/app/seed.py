"""Seed the database with default scan profiles."""

from sqlalchemy.orm import Session

from app.models import ScanProfile


DEFAULT_PROFILES = [
    {
        "name": "Quick Scan",
        "nmap_args": "-T4 -F",
        "description": "Fast scan of the 100 most common ports.",
        "is_default": True,
    },
    {
        "name": "Full Port Scan",
        "nmap_args": "-p 1-65535 -T4",
        "description": "Scan all 65535 TCP ports.",
        "is_default": True,
    },
    {
        "name": "Service/Version Detection",
        "nmap_args": "-sV -sC",
        "description": "Detect service versions and run default scripts.",
        "is_default": True,
    },
    {
        "name": "OS Detection",
        "nmap_args": "-O --osscan-guess",
        "description": "Attempt to identify the operating system.",
        "is_default": True,
    },
]


def seed_default_profiles(db: Session) -> None:
    existing = {p.name for p in db.query(ScanProfile).filter_by(is_default=True).all()}
    for profile_data in DEFAULT_PROFILES:
        if profile_data["name"] not in existing:
            db.add(ScanProfile(**profile_data))
    db.commit()
