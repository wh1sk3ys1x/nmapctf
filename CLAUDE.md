# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nmap Continuous Testing Framework (nmapctf) — a multi-tenant platform for running scheduled and ad-hoc nmap scans against network assets, tracking results, and generating reports. Three-container Docker stack: web (FastAPI), scanner (nmap worker), Redis (job queue).

## Architecture

- **Web app** (`web/`) — FastAPI with Jinja2/HTMX frontend, SQLite database, REST API
- **Scanner** (`scanner/`) — Stateless RQ worker executing nmap scans, posts results via internal API
- **Redis** — Job queue connecting web and scanner
- **Auth** — Session-based (web UI) + JWT (API). passlib/bcrypt for passwords.
- **Multi-tenancy** — Organization-scoped data. `org_scope.py` provides query filtering helpers.
- **Roles** — Superadmin (platform-wide), Owner/Admin/Member (per-org). `can_edit()` controls write access.

## Key Conventions

- Models use SQLAlchemy 2.0 `Mapped` type annotations in `web/app/models/`
- Schemas use Pydantic v2 in `web/app/schemas/`
- Views use lazy `from app.main import templates` inside handlers
- Templates extend `base.html`, use `can_edit` variable for permission-gated UI
- All data queries in views must use `org_filter()` from `web/app/org_scope.py`
- bcrypt must be pinned to 4.0.1 (passlib incompatibility with 5.x)
- Default scan profiles have `org_id=None` and are visible to all orgs

## Running Tests

```bash
cd web && .venv/bin/python -m pytest ../tests/web/ -v
```

## Deploy

```bash
./deploy.sh
```

## Workflow

- Commit all changes after each completed step. Do not batch multiple steps into one commit.
- Keep documentation (design spec, CLAUDE.md, README, etc.) updated as changes are made. Documentation updates should be part of the same commit as the related code changes.

## Git

- Do not add Claude/AI authorship or attribution anywhere (commits, PRs, code comments, docs, etc.).
