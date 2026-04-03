# Nmap Continuous Testing Framework (nmapctf) — Design Spec

## Overview

A platform for running scheduled and ad-hoc nmap scans against network assets, tracking results over time, and generating reports. Accessed through a web UI and backed by a REST API.

## Architecture

Three Docker containers orchestrated via `docker-compose`:

1. **Web App** — FastAPI + Jinja2/HTMX/Bootstrap 5. Owns the REST API, web UI, report generation, and SQLite database.
2. **Scanner Worker** — Picks nmap scan jobs off a Redis queue, executes them via `python-nmap`, posts results back to the web app API.
3. **Redis** — Job queue between web app and scanner worker.

### Data Flow

```
User -> Web UI -> FastAPI API -> Redis queue -> Scanner Worker -> nmap
                                                       |
                                               Results -> API -> SQLite
```

The web app is the single source of truth. The scanner worker is stateless — it only reads jobs from Redis and writes results back via the API.

### Security Boundary

The scanner container runs with `NET_RAW` capabilities (required by nmap). The web app container does not need elevated privileges. This isolation is a key reason for the two-container split.

## Tech Stack

- **Language:** Python 3.12+
- **Web framework:** FastAPI
- **Templating:** Jinja2 + HTMX + Bootstrap 5
- **Database:** SQLite via SQLAlchemy (ORM)
- **Job queue:** Redis (via `rq` or `redis-py`)
- **Nmap integration:** `python-nmap`
- **PDF generation:** `weasyprint`
- **Scheduling:** APScheduler (runs in the web app, enqueues jobs to Redis)
- **Auth:** Session-based for web UI, token-based for API
- **Containerization:** Docker + docker-compose

## Data Models

### Assets
- `id` (primary key)
- `name` (string, unique)
- `type` (enum: host, ip, subnet, range)
- `address` (string — hostname, IP, CIDR, or range)
- `notes` (text, optional)
- `created_at`, `updated_at` (timestamps)

### Scan Profiles
- `id` (primary key)
- `name` (string, unique)
- `nmap_args` (string — raw nmap arguments, e.g., `-sV -sC -p 1-1000`)
- `description` (text, optional)
- `is_default` (boolean — marks predefined profiles)
- `created_at`, `updated_at` (timestamps)

Predefined defaults included at setup: Quick Scan, Full Port Scan, Service/Version Detection, OS Detection.

### Scan Jobs
- `id` (primary key, UUID)
- `asset_id` (foreign key -> Assets)
- `profile_id` (foreign key -> Scan Profiles)
- `status` (enum: pending, running, completed, failed)
- `trigger` (enum: manual, scheduled)
- `schedule_id` (foreign key -> Schedules, nullable)
- `queued_at`, `started_at`, `completed_at` (timestamps)
- `error_message` (text, nullable — populated on failure)
- `raw_xml` (text, nullable — full nmap XML output)

### Scan Results
- `id` (primary key)
- `job_id` (foreign key -> Scan Jobs)
- `host` (string)
- `port` (integer)
- `protocol` (string — tcp/udp)
- `state` (string — open/closed/filtered)
- `service` (string, nullable)
- `version` (string, nullable)

One row per discovered port/service, for structured querying. The full raw nmap XML output is stored on the Scan Jobs model (`raw_xml` text field) so nothing is lost.

### Schedules
- `id` (primary key)
- `name` (string)
- `asset_id` (foreign key -> Assets)
- `profile_id` (foreign key -> Scan Profiles)
- `cron_expression` (string — standard cron format)
- `enabled` (boolean, default true)
- `created_at`, `updated_at` (timestamps)
- `last_run_at` (timestamp, nullable)

### Users
- `id` (primary key)
- `username` (string, unique)
- `password_hash` (string)
- `role` (enum: admin — extensible to viewer/operator later)
- `created_at` (timestamp)

## API Design

RESTful JSON API under `/api/v1/`. All endpoints require authentication.

### Endpoint Groups

| Group | Path | Description |
|-------|------|-------------|
| Assets | `/api/v1/assets/` | CRUD + bulk import (CSV upload) |
| Profiles | `/api/v1/profiles/` | CRUD for scan profiles |
| Scans | `/api/v1/scans/` | Trigger scans, list history, get results |
| Schedules | `/api/v1/schedules/` | CRUD + enable/disable toggle |
| Reports | `/api/v1/reports/` | Generate reports (HTML/PDF/CSV/JSON) |
| Auth | `/api/v1/auth/` | Login, token refresh |
| Users | `/api/v1/users/` | User management (admin only) |

### Scanner Worker Authentication

The scanner worker uses an internal API token (configured via environment variable) to authenticate when posting results back to the web app.

## Web UI Pages

| Page | Purpose |
|------|---------|
| Dashboard | Recent scans, upcoming scheduled scans, quick stats |
| Assets | List, add, edit, delete, bulk import targets |
| Scan Profiles | Manage reusable nmap configurations |
| Schedules | Create/edit recurring scans, enable/disable |
| Run Scan | Pick asset + profile, kick off a one-off scan |
| Scan History | Filterable list of all past scans with status |
| Scan Detail | Full results for a single scan (parsed table + raw output) |
| Reports | Generate/view reports: in-browser, PDF, CSV/JSON |
| Settings | User account, password change |

HTMX handles dynamic interactions: live scan status updates, inline filtering, form submissions without full page reloads.

## Report Generation

Three output formats, all generated server-side:

- **In-browser HTML** — rendered pages showing scan results, filterable by asset/date range/profile
- **PDF** — generated via `weasyprint` from the same HTML templates
- **CSV/JSON** — raw data exports, downloadable via API

Report scopes:
- Single scan
- Asset over time (trending/comparison)
- All assets for a date range

## Authentication

Starting with single admin user (username + password, created on first run). Session-based auth for the web UI, token-based for API consumers and the scanner worker.

Designed for future extension to multi-user with roles (admin, operator, viewer) without schema changes — the `role` field on the Users model supports this.

## Docker Setup

`docker-compose.yml` defines three services:

- **web** — FastAPI app, exposes port 8080, mounts SQLite volume
- **scanner** — Worker process, has `NET_RAW` capability, no exposed ports
- **redis** — Standard Redis image, no exposed ports (internal network only)

A shared Docker network connects all three. Only the web container exposes a port to the host.

SQLite database and any generated report files are persisted via Docker volumes.
