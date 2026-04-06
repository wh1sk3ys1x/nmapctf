# nmapctf

Nmap Continuous Testing Framework — a platform for running scheduled and ad-hoc nmap scans against network assets, tracking results, and generating reports. Multi-tenant with organization-based isolation and role-based access control.

## Features

- **Asset Management** — Define scan targets (IPs, hostnames, subnets, ranges). Bulk import from CSV, XLSX, or TXT files.
- **Asset Groups** — Organize assets into named collections. Scan or schedule entire groups at once.
- **Scan Profiles** — Reusable nmap argument presets (Quick Scan, Full TCP, UDP, etc.). Includes sensible defaults.
- **On-Demand Scans** — Run any scan profile against any asset or group with one click.
- **Scheduled Scans** — Cron-based recurring scans against assets or groups.
- **Scan Results** — Track all scan history with host/port/service/version data per scan.
- **Reports** — Generate reports scoped by single scan, asset, asset group, or date range. Export as HTML, PDF, CSV, or JSON.
- **Multi-Tenancy** — Organizations isolate data between teams. Users belong to one org.
- **Role-Based Access** — Three-tier permissions: Owner, Admin (full CRUD), Member (read-only).
- **Root Superadmin** — Platform-wide administrator created during first-run setup. Manages organizations and users.

## Architecture

Three-container stack:

| Service | Role | Image |
|---------|------|-------|
| **web** | FastAPI app — API, web UI, reports, auth | `nmapctf-web` |
| **scanner** | Stateless nmap worker, pulls jobs from Redis | `nmapctf-scanner` |
| **redis** | Job queue (internal only) | `redis:7-alpine` |

- Web app owns the SQLite database and serves the UI on port 8080
- Scanner worker executes nmap with `NET_RAW` capability, posts results back via internal API
- Redis connects the two via an RQ job queue

## Quick Start

```bash
git clone https://github.com/wh1sk3ys1x/nmapctf.git
cd nmapctf
./deploy.sh
```

This builds all images, starts the stack, and verifies the health endpoint. Open http://localhost:8080 to complete first-time setup.

## Manual Deploy

```bash
docker compose build
docker compose up -d
```

To reset the database (fresh start):

```bash
docker compose down -v
docker compose up -d
```

## Configuration

Environment variables (set in `.env` or `docker-compose.yml`):

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `changeme-in-production` | Session encryption key |
| `SCANNER_API_TOKEN` | `changeme` | Shared token for scanner worker auth |
| `DATABASE_URL` | `sqlite:////app/data/nmapctf.db` | Database connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection for job queue |

See `.env.example` for a template.

## First-Time Setup

1. Run `./deploy.sh`
2. Open http://localhost:8080 — you'll be redirected to `/setup`
3. Create the root superadmin account
4. As superadmin, go to **Organizations** to create orgs and add users

## User Roles

| Role | Scope | Permissions |
|------|-------|-------------|
| **Superadmin** | Platform-wide | All actions, manage orgs and users |
| **Owner** | Organization | Manage org settings and members, full CRUD |
| **Admin** | Organization | Full CRUD on assets, scans, schedules, reports |
| **Member** | Organization | Read-only access to all org data |

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic
- **Frontend:** Jinja2 templates, Bootstrap 5, HTMX
- **Worker:** RQ (Redis Queue), python-nmap
- **Auth:** passlib/bcrypt (passwords), python-jose (JWT), Starlette sessions
- **Reports:** WeasyPrint (PDF), stdlib csv/json
- **Database:** SQLite (file-based, mounted volume)
- **Container:** Docker, Docker Compose

## Project Structure

```
nmapctf/
├── web/                        # FastAPI web application
│   ├── app/
│   │   ├── api/                # REST API endpoints
│   │   ├── models/             # SQLAlchemy models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── views/              # Web UI view routes
│   │   ├── templates/          # Jinja2 templates
│   │   ├── static/             # CSS, JS
│   │   ├── main.py             # App setup, middleware, routers
│   │   ├── auth.py             # Password hashing, JWT
│   │   ├── config.py           # Settings from env vars
│   │   ├── database.py         # SQLAlchemy engine/session
│   │   ├── org_scope.py        # Multi-tenancy query helpers
│   │   └── reports.py          # Report data queries
│   ├── Dockerfile
│   └── requirements.txt
├── scanner/                    # Nmap scanner worker
│   ├── worker.py               # RQ worker entry point
│   ├── tasks.py                # Scan execution and result posting
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── deploy.sh                   # One-command deploy script
├── .env.example                # Environment variable template
└── docs/superpowers/specs/     # Design specifications
```

## API

REST API available at `/api/v1/`. Authenticated via JWT bearer token.

```bash
# Get a token
curl -X POST http://localhost:8080/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "yourpass"}'

# List assets
curl http://localhost:8080/api/v1/assets \
  -H "Authorization: Bearer <token>"
```

### Endpoints

| Prefix | Resource |
|--------|----------|
| `/api/v1/assets` | Assets CRUD |
| `/api/v1/asset-groups` | Asset groups CRUD + membership |
| `/api/v1/scans` | Scan jobs |
| `/api/v1/schedules` | Scan schedules |
| `/api/v1/profiles` | Scan profiles |
| `/api/v1/auth/token` | JWT token login |
| `/api/v1/health` | Health check |

## Testing

Tests run against an in-memory SQLite database (no Docker required):

```bash
cd web
.venv/bin/python -m pytest ../tests/web/ -v
```

85 tests covering auth, assets, groups, scans, schedules, reports, import, org management, multi-tenancy isolation, and role-based permissions.
