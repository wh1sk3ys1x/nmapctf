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
    {
        "name": "Aggressive Scan",
        "nmap_args": "-A -T4",
        "description": "OS detection, version detection, script scanning, and traceroute.",
        "is_default": True,
    },
    {
        "name": "Stealth SYN Scan",
        "nmap_args": "-sS -T2",
        "description": "Half-open SYN scan at polite timing. Less likely to trigger IDS.",
        "is_default": True,
    },
    {
        "name": "UDP Scan (Top 100)",
        "nmap_args": "-sU -F -T4",
        "description": "Scan the 100 most common UDP ports.",
        "is_default": True,
    },
    {
        "name": "Vulnerability Scan",
        "nmap_args": "-sV --script vuln",
        "description": "Run vulnerability detection scripts against discovered services.",
        "is_default": True,
    },
    {
        "name": "Web Server Scan",
        "nmap_args": "-p 80,443,8080,8443 -sV --script http-title,http-headers,ssl-cert",
        "description": "Target common web ports with HTTP and SSL scripts.",
        "is_default": True,
    },
    {
        "name": "Ping Sweep",
        "nmap_args": "-sn",
        "description": "Host discovery only — no port scan. Find live hosts on a network.",
        "is_default": True,
    },
    {
        "name": "Top 1000 Ports",
        "nmap_args": "-T4 --top-ports 1000",
        "description": "Scan the 1000 most common ports. Good balance of speed and coverage.",
        "is_default": True,
    },
]


def seed_default_profiles(db: Session) -> None:
    existing = {p.name for p in db.query(ScanProfile).filter_by(is_default=True).all()}
    for profile_data in DEFAULT_PROFILES:
        if profile_data["name"] not in existing:
            db.add(ScanProfile(**profile_data))
    db.commit()
