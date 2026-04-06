# Asset Groups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add asset groups so users can organize assets into named collections and run scans, schedules, and reports against entire groups.

**Architecture:** New `AssetGroup` model with many-to-many junction table to `Asset`. Schedule and ScanJob get optional `asset_group_id` FK. Group scans create one ScanJob per member asset. New CRUD views/API at `/groups` and `/api/v1/asset-groups`.

**Tech Stack:** SQLAlchemy (models), Pydantic (schemas), FastAPI (API + views), Jinja2/HTMX (templates), pytest (tests)

---

### File Structure

**Create:**
- `web/app/models/asset_group.py` — AssetGroup model + junction table
- `web/app/schemas/asset_group.py` — Pydantic schemas for groups
- `web/app/api/asset_groups.py` — REST API endpoints
- `web/app/views/groups.py` — Web UI view routes
- `web/app/templates/groups/list.html` — Group list page
- `web/app/templates/groups/form.html` — Create/edit group form
- `web/app/templates/groups/detail.html` — Group detail with member management
- `tests/web/test_asset_groups.py` — Functional tests

**Modify:**
- `web/app/models/__init__.py` — Export AssetGroup
- `web/app/models/asset.py` — Add `groups` back-reference
- `web/app/models/schedule.py` — Add optional `asset_group_id` FK
- `web/app/models/scan_job.py` — Add optional `asset_group_id` FK
- `web/app/main.py` — Register new routers
- `web/app/templates/base.html` — Add Groups to navbar
- `web/app/views/scans.py` — Support group scan submission
- `web/app/templates/scans/run.html` — Add group dropdown
- `web/app/views/schedules.py` — Support group schedule creation
- `web/app/templates/schedules/form.html` — Add group dropdown
- `web/app/templates/schedules/list.html` — Show group name when applicable
- `web/app/reports.py` — Add group_report function
- `web/app/views/reports.py` — Add group scope
- `web/app/templates/reports/index.html` — Add group scope option

---

### Task 1: AssetGroup Model and Junction Table

**Files:**
- Create: `web/app/models/asset_group.py`
- Modify: `web/app/models/__init__.py`
- Modify: `web/app/models/asset.py`

- [ ] **Step 1: Create the AssetGroup model**

Create `web/app/models/asset_group.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import String, Text, Column, Table, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

asset_group_members = Table(
    "asset_group_members",
    Base.metadata,
    Column("asset_group_id", Integer, ForeignKey("asset_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("asset_id", Integer, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True),
)


class AssetGroup(Base):
    __tablename__ = "asset_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    assets: Mapped[list["Asset"]] = relationship(  # noqa: F821
        secondary=asset_group_members, back_populates="groups",
    )
    schedules: Mapped[list["Schedule"]] = relationship(back_populates="asset_group")  # noqa: F821
```

- [ ] **Step 2: Add groups back-reference to Asset model**

In `web/app/models/asset.py`, add import and relationship. After line 32 (`schedules` relationship), add:

```python
    groups: Mapped[list["AssetGroup"]] = relationship(  # noqa: F821
        secondary="asset_group_members", back_populates="assets",
    )
```

- [ ] **Step 3: Add optional asset_group_id to Schedule model**

In `web/app/models/schedule.py`, after line 14 (`asset_id` field), add:

```python
    asset_group_id: Mapped[int | None] = mapped_column(ForeignKey("asset_groups.id"), default=None)
```

After line 26 (`profile` relationship), add:

```python
    asset_group: Mapped["AssetGroup | None"] = relationship(back_populates="schedules")  # noqa: F821
```

Also make `asset_id` nullable — change line 14 from:
```python
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
```
to:
```python
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), default=None)
```

- [ ] **Step 4: Add optional asset_group_id to ScanJob model**

In `web/app/models/scan_job.py`, after line 33 (`schedule_id` field), add:

```python
    asset_group_id: Mapped[int | None] = mapped_column(ForeignKey("asset_groups.id"), default=None)
```

- [ ] **Step 5: Export AssetGroup from models __init__**

In `web/app/models/__init__.py`, add:

```python
from app.models.asset_group import AssetGroup, asset_group_members
```

And add `"AssetGroup"` and `"asset_group_members"` to `__all__`.

- [ ] **Step 6: Verify tables create correctly**

Run from `web/` directory:
```bash
.venv/bin/python -c "from app.database import Base, engine; from app.models import *; Base.metadata.create_all(bind=engine)"
```
Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add web/app/models/asset_group.py web/app/models/__init__.py web/app/models/asset.py web/app/models/schedule.py web/app/models/scan_job.py
git commit -m "Add AssetGroup model with junction table and FK relationships"
```

---

### Task 2: Schemas

**Files:**
- Create: `web/app/schemas/asset_group.py`

- [ ] **Step 1: Create asset group schemas**

Create `web/app/schemas/asset_group.py`:

```python
from datetime import datetime

from pydantic import BaseModel

from app.schemas.asset import AssetOut


class AssetGroupCreate(BaseModel):
    name: str
    description: str | None = None


class AssetGroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class AssetGroupOut(BaseModel):
    id: int
    name: str
    description: str | None
    member_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetGroupDetail(BaseModel):
    id: int
    name: str
    description: str | None
    assets: list[AssetOut]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GroupMemberAdd(BaseModel):
    asset_id: int
```

- [ ] **Step 2: Commit**

```bash
git add web/app/schemas/asset_group.py
git commit -m "Add Pydantic schemas for asset groups"
```

---

### Task 3: API Endpoints

**Files:**
- Create: `web/app/api/asset_groups.py`
- Modify: `web/app/main.py`

- [ ] **Step 1: Create the API router**

Create `web/app/api/asset_groups.py`:

```python
from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.models import AssetGroup, Asset
from app.models.asset_group import asset_group_members
from app.schemas.asset_group import (
    AssetGroupCreate, AssetGroupUpdate, AssetGroupOut, AssetGroupDetail, GroupMemberAdd,
)

router = APIRouter(prefix="/asset-groups", tags=["asset-groups"])


@router.get("/", response_model=list[AssetGroupOut])
def list_groups(db: DbSession):
    groups = db.query(AssetGroup).order_by(AssetGroup.name).all()
    return [
        AssetGroupOut(
            id=g.id, name=g.name, description=g.description,
            member_count=len(g.assets), created_at=g.created_at, updated_at=g.updated_at,
        )
        for g in groups
    ]


@router.get("/{group_id}", response_model=AssetGroupDetail)
def get_group(group_id: int, db: DbSession):
    group = db.get(AssetGroup, group_id)
    if not group:
        raise HTTPException(404, "Asset group not found")
    return group


@router.post("/", response_model=AssetGroupOut, status_code=201)
def create_group(body: AssetGroupCreate, db: DbSession):
    group = AssetGroup(name=body.name, description=body.description)
    db.add(group)
    db.commit()
    db.refresh(group)
    return AssetGroupOut(
        id=group.id, name=group.name, description=group.description,
        member_count=0, created_at=group.created_at, updated_at=group.updated_at,
    )


@router.patch("/{group_id}", response_model=AssetGroupOut)
def update_group(group_id: int, body: AssetGroupUpdate, db: DbSession):
    group = db.get(AssetGroup, group_id)
    if not group:
        raise HTTPException(404, "Asset group not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(group, field, value)
    db.commit()
    db.refresh(group)
    return AssetGroupOut(
        id=group.id, name=group.name, description=group.description,
        member_count=len(group.assets), created_at=group.created_at, updated_at=group.updated_at,
    )


@router.delete("/{group_id}", status_code=204)
def delete_group(group_id: int, db: DbSession):
    group = db.get(AssetGroup, group_id)
    if not group:
        raise HTTPException(404, "Asset group not found")
    db.delete(group)
    db.commit()


@router.post("/{group_id}/members", status_code=201)
def add_member(group_id: int, body: GroupMemberAdd, db: DbSession):
    group = db.get(AssetGroup, group_id)
    if not group:
        raise HTTPException(404, "Asset group not found")
    asset = db.get(Asset, body.asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    if asset in group.assets:
        raise HTTPException(409, "Asset already in group")
    group.assets.append(asset)
    db.commit()
    return {"status": "added"}


@router.delete("/{group_id}/members/{asset_id}", status_code=204)
def remove_member(group_id: int, asset_id: int, db: DbSession):
    group = db.get(AssetGroup, group_id)
    if not group:
        raise HTTPException(404, "Asset group not found")
    asset = db.get(Asset, asset_id)
    if not asset or asset not in group.assets:
        raise HTTPException(404, "Asset not in group")
    group.assets.remove(asset)
    db.commit()
```

- [ ] **Step 2: Register the API router in main.py**

In `web/app/main.py`, add import after line 13 (`from app.api import ...`):

```python
from app.api import asset_groups as api_asset_groups
```

After line 82 (`app.include_router(internal.router, ...)`), add:

```python
app.include_router(api_asset_groups.router, prefix="/api/v1")
```

- [ ] **Step 3: Commit**

```bash
git add web/app/api/asset_groups.py web/app/main.py
git commit -m "Add asset groups REST API endpoints"
```

---

### Task 4: Group Web UI — CRUD Views and Templates

**Files:**
- Create: `web/app/views/groups.py`
- Create: `web/app/templates/groups/list.html`
- Create: `web/app/templates/groups/form.html`
- Create: `web/app/templates/groups/detail.html`
- Modify: `web/app/main.py`
- Modify: `web/app/templates/base.html`

- [ ] **Step 1: Create the views router**

Create `web/app/views/groups.py`:

```python
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import DbSession
from app.models import AssetGroup, Asset

router = APIRouter(prefix="/groups", tags=["views"])


@router.get("/", response_class=HTMLResponse)
def list_groups(request: Request, db: DbSession):
    from app.main import templates
    groups = db.query(AssetGroup).order_by(AssetGroup.name).all()
    return templates.TemplateResponse(request, "groups/list.html", {"groups": groups})


@router.get("/new", response_class=HTMLResponse)
def new_group(request: Request):
    from app.main import templates
    return templates.TemplateResponse(request, "groups/form.html", {"group": None})


@router.get("/{group_id}", response_class=HTMLResponse)
def group_detail(group_id: int, request: Request, db: DbSession):
    from app.main import templates
    group = db.get(AssetGroup, group_id)
    if not group:
        return RedirectResponse("/groups", status_code=303)
    available_assets = (
        db.query(Asset)
        .filter(~Asset.id.in_([a.id for a in group.assets]))
        .order_by(Asset.name)
        .all()
    )
    return templates.TemplateResponse(
        request, "groups/detail.html",
        {"group": group, "available_assets": available_assets},
    )


@router.get("/{group_id}/edit", response_class=HTMLResponse)
def edit_group(group_id: int, request: Request, db: DbSession):
    from app.main import templates
    group = db.get(AssetGroup, group_id)
    if not group:
        return RedirectResponse("/groups", status_code=303)
    return templates.TemplateResponse(request, "groups/form.html", {"group": group})


@router.post("/", response_class=HTMLResponse)
def create_group(
    db: DbSession,
    name: str = Form(...),
    description: str = Form(""),
):
    group = AssetGroup(name=name, description=description or None)
    db.add(group)
    db.commit()
    db.refresh(group)
    return RedirectResponse(f"/groups/{group.id}", status_code=303)


@router.post("/{group_id}", response_class=HTMLResponse)
def update_group(
    group_id: int,
    db: DbSession,
    name: str = Form(...),
    description: str = Form(""),
):
    group = db.get(AssetGroup, group_id)
    if not group:
        return RedirectResponse("/groups", status_code=303)
    group.name = name
    group.description = description or None
    db.commit()
    return RedirectResponse(f"/groups/{group_id}", status_code=303)


@router.post("/{group_id}/members", response_class=HTMLResponse)
def add_member(
    group_id: int,
    request: Request,
    db: DbSession,
    asset_id: int = Form(...),
):
    group = db.get(AssetGroup, group_id)
    asset = db.get(Asset, asset_id)
    if group and asset and asset not in group.assets:
        group.assets.append(asset)
        db.commit()
    return RedirectResponse(f"/groups/{group_id}", status_code=303)


@router.delete("/{group_id}/members/{asset_id}")
def remove_member(group_id: int, asset_id: int, db: DbSession):
    group = db.get(AssetGroup, group_id)
    asset = db.get(Asset, asset_id)
    if group and asset and asset in group.assets:
        group.assets.remove(asset)
        db.commit()
    return HTMLResponse("")


@router.delete("/{group_id}")
def delete_group(group_id: int, db: DbSession):
    group = db.get(AssetGroup, group_id)
    if group:
        db.delete(group)
        db.commit()
    return HTMLResponse("")
```

- [ ] **Step 2: Create group list template**

Create `web/app/templates/groups/list.html`:

```html
{% extends "base.html" %}
{% block title %}Asset Groups — nmapctf{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
  <h1>Asset Groups</h1>
  <a href="/groups/new" class="btn btn-primary">New Group</a>
</div>

<table class="table table-hover">
  <thead>
    <tr>
      <th>Name</th>
      <th>Description</th>
      <th>Members</th>
      <th style="width: 180px;">Actions</th>
    </tr>
  </thead>
  <tbody>
    {% for group in groups %}
    <tr id="group-{{ group.id }}">
      <td><a href="/groups/{{ group.id }}">{{ group.name }}</a></td>
      <td>{{ group.description or '—' }}</td>
      <td><span class="badge bg-info">{{ group.assets | length }}</span></td>
      <td>
        <a href="/groups/{{ group.id }}/edit" class="btn btn-sm btn-outline-light">Edit</a>
        <button class="btn btn-sm btn-outline-danger"
                hx-delete="/groups/{{ group.id }}"
                hx-target="#group-{{ group.id }}"
                hx-swap="outerHTML"
                hx-confirm="Delete group '{{ group.name }}'?">Del</button>
      </td>
    </tr>
    {% else %}
    <tr><td colspan="4" class="text-muted text-center">No groups yet. <a href="/groups/new">Create one.</a></td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 3: Create group form template**

Create `web/app/templates/groups/form.html`:

```html
{% extends "base.html" %}
{% block title %}{{ 'Edit' if group else 'New' }} Group — nmapctf{% endblock %}
{% block content %}
<h1>{{ 'Edit' if group else 'New' }} Asset Group</h1>

<form method="post" action="{{ '/groups/' ~ group.id if group else '/groups/' }}" class="mt-3" style="max-width: 600px;">
  <div class="mb-3">
    <label for="name" class="form-label">Name</label>
    <input type="text" class="form-control" id="name" name="name" required
           value="{{ group.name if group else '' }}">
  </div>
  <div class="mb-3">
    <label for="description" class="form-label">Description</label>
    <textarea class="form-control" id="description" name="description" rows="3">{{ group.description if group and group.description else '' }}</textarea>
  </div>
  <button type="submit" class="btn btn-primary">{{ 'Update' if group else 'Create' }}</button>
  <a href="/groups" class="btn btn-outline-secondary">Cancel</a>
</form>
{% endblock %}
```

- [ ] **Step 4: Create group detail template**

Create `web/app/templates/groups/detail.html`:

```html
{% extends "base.html" %}
{% block title %}{{ group.name }} — nmapctf{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
  <div>
    <h1>{{ group.name }}</h1>
    {% if group.description %}<p class="text-muted">{{ group.description }}</p>{% endif %}
  </div>
  <a href="/groups/{{ group.id }}/edit" class="btn btn-outline-light">Edit Group</a>
</div>

<h3>Members <span class="badge bg-info">{{ group.assets | length }}</span></h3>

{% if available_assets %}
<form method="post" action="/groups/{{ group.id }}/members" class="mb-3 d-flex gap-2" style="max-width: 400px;">
  <select class="form-select" name="asset_id" required>
    <option value="">Add asset...</option>
    {% for asset in available_assets %}
    <option value="{{ asset.id }}">{{ asset.name }} ({{ asset.address }})</option>
    {% endfor %}
  </select>
  <button type="submit" class="btn btn-primary">Add</button>
</form>
{% endif %}

<table class="table table-hover">
  <thead>
    <tr>
      <th>Name</th>
      <th>Type</th>
      <th>Address</th>
      <th style="width: 100px;">Actions</th>
    </tr>
  </thead>
  <tbody>
    {% for asset in group.assets %}
    <tr id="member-{{ asset.id }}">
      <td>{{ asset.name }}</td>
      <td><span class="badge bg-secondary">{{ asset.type.value }}</span></td>
      <td><code>{{ asset.address }}</code></td>
      <td>
        <button class="btn btn-sm btn-outline-danger"
                hx-delete="/groups/{{ group.id }}/members/{{ asset.id }}"
                hx-target="#member-{{ asset.id }}"
                hx-swap="outerHTML"
                hx-confirm="Remove '{{ asset.name }}' from group?">Remove</button>
      </td>
    </tr>
    {% else %}
    <tr><td colspan="4" class="text-muted text-center">No members yet. Add assets above.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 5: Register views router and add navbar link**

In `web/app/main.py`, add import after the other view imports:

```python
from app.views import groups as group_views
```

After `app.include_router(report_views.router)`, add:

```python
app.include_router(group_views.router)
```

In `web/app/templates/base.html`, add after the Assets nav link (after line 21):

```html
          <li class="nav-item"><a class="nav-link" href="/groups">Groups</a></li>
```

- [ ] **Step 6: Commit**

```bash
git add web/app/views/groups.py web/app/templates/groups/ web/app/main.py web/app/templates/base.html
git commit -m "Add asset group web UI with list, create, edit, detail, and member management"
```

---

### Task 5: Integrate Groups into Scans

**Files:**
- Modify: `web/app/views/scans.py`
- Modify: `web/app/templates/scans/run.html`

- [ ] **Step 1: Update run scan form view to pass groups**

In `web/app/views/scans.py`, add `AssetGroup` to the import on line 8:

```python
from app.models import ScanJob, Asset, ScanProfile, ScanStatus, AssetGroup
```

In `run_scan_form` (line 50-56), add groups query:

```python
@router.get("/run", response_class=HTMLResponse)
def run_scan_form(request: Request, db: DbSession):
    from app.main import templates
    assets = db.query(Asset).order_by(Asset.name).all()
    profiles = db.query(ScanProfile).order_by(ScanProfile.name).all()
    groups = db.query(AssetGroup).order_by(AssetGroup.name).all()
    return templates.TemplateResponse(
        request, "scans/run.html", {"assets": assets, "profiles": profiles, "groups": groups},
    )
```

In `run_scan` (line 59-84), change `asset_id` to optional and add `asset_group_id`:

```python
@router.post("/run", response_class=HTMLResponse)
def run_scan(
    db: DbSession,
    asset_id: int | None = Form(None),
    asset_group_id: int | None = Form(None),
    profile_id: int = Form(...),
):
    profile = db.get(ScanProfile, profile_id)
    if not profile:
        return RedirectResponse("/scans/run", status_code=303)

    if asset_group_id:
        group = db.get(AssetGroup, asset_group_id)
        if not group or not group.assets:
            return RedirectResponse("/scans/run", status_code=303)
        last_job = None
        queue = _get_queue()
        for asset in group.assets:
            job = ScanJob(asset_id=asset.id, profile_id=profile_id, asset_group_id=group.id)
            db.add(job)
            db.commit()
            db.refresh(job)
            queue.enqueue(
                "tasks.run_scan",
                job_id=job.id,
                target=asset.address,
                nmap_args=profile.nmap_args,
                job_timeout="30m",
            )
            last_job = job
        return RedirectResponse(f"/scans", status_code=303)
    else:
        asset = db.get(Asset, asset_id)
        if not asset:
            return RedirectResponse("/scans/run", status_code=303)
        job = ScanJob(asset_id=asset_id, profile_id=profile_id)
        db.add(job)
        db.commit()
        db.refresh(job)
        queue = _get_queue()
        queue.enqueue(
            "tasks.run_scan",
            job_id=job.id,
            target=asset.address,
            nmap_args=profile.nmap_args,
            job_timeout="30m",
        )
        return RedirectResponse(f"/scans/{job.id}", status_code=303)
```

- [ ] **Step 2: Update run scan template**

Replace `web/app/templates/scans/run.html` entirely:

```html
{% extends "base.html" %}
{% block title %}Run Scan — nmapctf{% endblock %}
{% block content %}
<h1>Run Scan</h1>

<form method="post" action="/scans/run" class="mt-3" style="max-width: 600px;">
  <div class="mb-3">
    <label class="form-label">Target</label>
    <div class="form-check">
      <input class="form-check-input" type="radio" name="target_type" id="target_asset" value="asset" checked onchange="toggleTarget()">
      <label class="form-check-label" for="target_asset">Single Asset</label>
    </div>
    <div class="form-check">
      <input class="form-check-input" type="radio" name="target_type" id="target_group" value="group" onchange="toggleTarget()">
      <label class="form-check-label" for="target_group">Asset Group</label>
    </div>
  </div>
  <div class="mb-3" id="asset_field">
    <label for="asset_id" class="form-label">Asset</label>
    <select class="form-select" id="asset_id" name="asset_id">
      <option value="">Select asset...</option>
      {% for asset in assets %}
      <option value="{{ asset.id }}">{{ asset.name }} ({{ asset.address }})</option>
      {% endfor %}
    </select>
  </div>
  <div class="mb-3" id="group_field" style="display: none;">
    <label for="asset_group_id" class="form-label">Asset Group</label>
    <select class="form-select" id="asset_group_id" name="asset_group_id">
      <option value="">Select group...</option>
      {% for group in groups %}
      <option value="{{ group.id }}">{{ group.name }} ({{ group.assets | length }} assets)</option>
      {% endfor %}
    </select>
  </div>
  <div class="mb-3">
    <label for="profile_id" class="form-label">Scan Profile</label>
    <select class="form-select" id="profile_id" name="profile_id" required>
      <option value="">Select profile...</option>
      {% for profile in profiles %}
      <option value="{{ profile.id }}">{{ profile.name }} — {{ profile.nmap_args }}</option>
      {% endfor %}
    </select>
  </div>
  <button type="submit" class="btn btn-primary">Start Scan</button>
</form>

<script>
function toggleTarget() {
  const isGroup = document.getElementById('target_group').checked;
  document.getElementById('asset_field').style.display = isGroup ? 'none' : '';
  document.getElementById('group_field').style.display = isGroup ? '' : 'none';
  document.getElementById('asset_id').required = !isGroup;
  document.getElementById('asset_group_id').required = isGroup;
}
</script>
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add web/app/views/scans.py web/app/templates/scans/run.html
git commit -m "Add asset group support to run scan form"
```

---

### Task 6: Integrate Groups into Schedules

**Files:**
- Modify: `web/app/views/schedules.py`
- Modify: `web/app/templates/schedules/form.html`
- Modify: `web/app/templates/schedules/list.html`

- [ ] **Step 1: Update schedule views**

In `web/app/views/schedules.py`, add `AssetGroup` to import on line 5:

```python
from app.models import Schedule, Asset, ScanProfile, AssetGroup
```

In `new_schedule` (line 17-25), add groups query:

```python
@router.get("/new", response_class=HTMLResponse)
def new_schedule(request: Request, db: DbSession):
    from app.main import templates
    assets = db.query(Asset).order_by(Asset.name).all()
    profiles = db.query(ScanProfile).order_by(ScanProfile.name).all()
    groups = db.query(AssetGroup).order_by(AssetGroup.name).all()
    return templates.TemplateResponse(
        request, "schedules/form.html",
        {"schedule": None, "assets": assets, "profiles": profiles, "groups": groups},
    )
```

In `edit_schedule` (line 28-39), add groups query:

```python
@router.get("/{schedule_id}/edit", response_class=HTMLResponse)
def edit_schedule(schedule_id: int, request: Request, db: DbSession):
    from app.main import templates
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        return RedirectResponse("/schedules", status_code=303)
    assets = db.query(Asset).order_by(Asset.name).all()
    profiles = db.query(ScanProfile).order_by(ScanProfile.name).all()
    groups = db.query(AssetGroup).order_by(AssetGroup.name).all()
    return templates.TemplateResponse(
        request, "schedules/form.html",
        {"schedule": schedule, "assets": assets, "profiles": profiles, "groups": groups},
    )
```

In `create_schedule` (line 42-55), accept optional group:

```python
@router.post("/", response_class=HTMLResponse)
def create_schedule(
    db: DbSession,
    name: str = Form(...),
    asset_id: int | None = Form(None),
    asset_group_id: int | None = Form(None),
    profile_id: int = Form(...),
    cron_expression: str = Form(...),
):
    schedule = Schedule(
        name=name,
        asset_id=asset_id or None,
        asset_group_id=asset_group_id or None,
        profile_id=profile_id,
        cron_expression=cron_expression,
    )
    db.add(schedule)
    db.commit()
    return RedirectResponse("/schedules", status_code=303)
```

In `update_schedule` (line 58-75), accept optional group:

```python
@router.post("/{schedule_id}", response_class=HTMLResponse)
def update_schedule(
    schedule_id: int,
    db: DbSession,
    name: str = Form(...),
    asset_id: int | None = Form(None),
    asset_group_id: int | None = Form(None),
    profile_id: int = Form(...),
    cron_expression: str = Form(...),
):
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        return RedirectResponse("/schedules", status_code=303)
    schedule.name = name
    schedule.asset_id = asset_id or None
    schedule.asset_group_id = asset_group_id or None
    schedule.profile_id = profile_id
    schedule.cron_expression = cron_expression
    db.commit()
    return RedirectResponse("/schedules", status_code=303)
```

- [ ] **Step 2: Update schedule form template**

Replace `web/app/templates/schedules/form.html` entirely:

```html
{% extends "base.html" %}
{% block title %}{{ 'Edit' if schedule else 'New' }} Schedule — nmapctf{% endblock %}
{% block content %}
<h1>{{ 'Edit' if schedule else 'New' }} Schedule</h1>

<form method="post" action="{{ '/schedules/' ~ schedule.id if schedule else '/schedules/' }}" class="mt-3" style="max-width: 600px;">
  <div class="mb-3">
    <label for="name" class="form-label">Name</label>
    <input type="text" class="form-control" id="name" name="name" required
           value="{{ schedule.name if schedule else '' }}">
  </div>
  <div class="mb-3">
    <label class="form-label">Target</label>
    <div class="form-check">
      <input class="form-check-input" type="radio" name="target_type" id="target_asset" value="asset"
             {{ 'checked' if not schedule or not schedule.asset_group_id else '' }} onchange="toggleTarget()">
      <label class="form-check-label" for="target_asset">Single Asset</label>
    </div>
    <div class="form-check">
      <input class="form-check-input" type="radio" name="target_type" id="target_group" value="group"
             {{ 'checked' if schedule and schedule.asset_group_id else '' }} onchange="toggleTarget()">
      <label class="form-check-label" for="target_group">Asset Group</label>
    </div>
  </div>
  <div class="mb-3" id="asset_field">
    <label for="asset_id" class="form-label">Asset</label>
    <select class="form-select" id="asset_id" name="asset_id">
      <option value="">Select asset...</option>
      {% for asset in assets %}
      <option value="{{ asset.id }}" {{ 'selected' if schedule and schedule.asset_id == asset.id else '' }}>
        {{ asset.name }} ({{ asset.address }})
      </option>
      {% endfor %}
    </select>
  </div>
  <div class="mb-3" id="group_field" style="display: none;">
    <label for="asset_group_id" class="form-label">Asset Group</label>
    <select class="form-select" id="asset_group_id" name="asset_group_id">
      <option value="">Select group...</option>
      {% for group in groups %}
      <option value="{{ group.id }}" {{ 'selected' if schedule and schedule.asset_group_id == group.id else '' }}>
        {{ group.name }} ({{ group.assets | length }} assets)
      </option>
      {% endfor %}
    </select>
  </div>
  <div class="mb-3">
    <label for="profile_id" class="form-label">Scan Profile</label>
    <select class="form-select" id="profile_id" name="profile_id" required>
      <option value="">Select profile...</option>
      {% for profile in profiles %}
      <option value="{{ profile.id }}" {{ 'selected' if schedule and schedule.profile_id == profile.id else '' }}>
        {{ profile.name }}
      </option>
      {% endfor %}
    </select>
  </div>
  <div class="mb-3">
    <label for="cron_expression" class="form-label">Cron Expression</label>
    <input type="text" class="form-control" id="cron_expression" name="cron_expression" required
           placeholder="0 */6 * * *"
           value="{{ schedule.cron_expression if schedule else '' }}">
    <div class="form-text">Standard 5-field cron format. Example: <code>0 */6 * * *</code> = every 6 hours.</div>
  </div>
  <button type="submit" class="btn btn-primary">{{ 'Update' if schedule else 'Create' }}</button>
  <a href="/schedules" class="btn btn-outline-secondary">Cancel</a>
</form>

<script>
function toggleTarget() {
  const isGroup = document.getElementById('target_group').checked;
  document.getElementById('asset_field').style.display = isGroup ? 'none' : '';
  document.getElementById('group_field').style.display = isGroup ? '' : 'none';
}
document.addEventListener('DOMContentLoaded', toggleTarget);
</script>
{% endblock %}
```

- [ ] **Step 3: Update schedule list to show group name**

In `web/app/templates/schedules/list.html`, replace line 25 (`<td>{{ sched.asset.name }}</td>`) with:

```html
      <td>
        {% if sched.asset_group %}
        <span class="badge bg-info">{{ sched.asset_group.name }}</span> (group)
        {% elif sched.asset %}
        {{ sched.asset.name }}
        {% else %}
        —
        {% endif %}
      </td>
```

- [ ] **Step 4: Commit**

```bash
git add web/app/views/schedules.py web/app/templates/schedules/form.html web/app/templates/schedules/list.html
git commit -m "Add asset group support to schedules"
```

---

### Task 7: Integrate Groups into Reports

**Files:**
- Modify: `web/app/reports.py`
- Modify: `web/app/views/reports.py`
- Modify: `web/app/templates/reports/index.html`

- [ ] **Step 1: Add group_report function**

In `web/app/reports.py`, add `AssetGroup` to imports on line 6:

```python
from app.models import ScanJob, ScanResult, Asset, ScanProfile, ScanStatus, AssetGroup
```

Add this function at the end of the file:

```python
def group_report(db: Session, group_id: int, date_from: datetime | None = None, date_to: datetime | None = None) -> dict | None:
    """Report data for all scans of assets in a group."""
    group = db.get(AssetGroup, group_id)
    if not group:
        return None
    asset_ids = [a.id for a in group.assets]
    if not asset_ids:
        return {
            "title": f"Group Report: {group.name}",
            "generated_at": datetime.now(timezone.utc),
            "scans": [],
            "results": [],
            "summary": {"total_scans": 0, "total_assets": 0, "total_hosts": 0, "total_ports": 0, "open_ports": 0},
        }
    query = db.query(ScanJob).filter(
        ScanJob.asset_id.in_(asset_ids),
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
        "title": f"Group Report: {group.name}",
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
```

- [ ] **Step 2: Update report views to support group scope**

In `web/app/views/reports.py`, add imports. After line 10 (`from app.models import Asset, ScanJob`), add `AssetGroup`:

```python
from app.models import Asset, ScanJob, AssetGroup
```

After line 12 (`from app.reports import ...`), add `group_report`:

```python
from app.reports import single_scan_report, asset_report, full_report, group_report
```

Update `_get_report` function (lines 28-35) to handle group scope:

```python
def _get_report(db, scope, scan_id, asset_id, group_id, date_from, date_to):
    """Dispatch to the correct report function based on scope."""
    if scope == "scan" and scan_id:
        return single_scan_report(db, scan_id)
    elif scope == "asset" and asset_id:
        return asset_report(db, asset_id, _parse_date(date_from), _parse_date(date_to))
    elif scope == "group" and group_id:
        return group_report(db, group_id, _parse_date(date_from), _parse_date(date_to))
    else:
        return full_report(db, _parse_date(date_from), _parse_date(date_to))
```

Update `report_index` (line 38-45) to pass groups:

```python
@router.get("/", response_class=HTMLResponse)
def report_index(request: Request, db: DbSession):
    from app.main import templates
    assets = db.query(Asset).order_by(Asset.name).all()
    groups = db.query(AssetGroup).order_by(AssetGroup.name).all()
    scans = db.query(ScanJob).filter(ScanJob.status == "completed").order_by(ScanJob.queued_at.desc()).limit(50).all()
    return templates.TemplateResponse(
        request, "reports/index.html", {"assets": assets, "groups": groups, "scans": scans},
    )
```

Add `group_id: int | None = Query(None)` parameter to all four report endpoints (`report_html`, `report_pdf`, `report_csv`, `report_json`) and pass it to `_get_report`. For each endpoint, add the parameter and update the `_get_report` call:

```python
    group_id: int | None = Query(None),
```

Update each `_get_report(db, scope, scan_id, asset_id, date_from, date_to)` call to:

```python
    _get_report(db, scope, scan_id, asset_id, group_id, date_from, date_to)
```

Also pass `group_id=group_id` in the template context for `report_html`.

- [ ] **Step 3: Update report index template**

Replace `web/app/templates/reports/index.html` entirely:

```html
{% extends "base.html" %}
{% block title %}Reports — nmapctf{% endblock %}
{% block content %}
<h1>Reports</h1>

<form class="mt-3" style="max-width: 600px;" id="reportForm">
  <div class="mb-3">
    <label for="scope" class="form-label">Report Scope</label>
    <select class="form-select" id="scope" name="scope" onchange="toggleFields()">
      <option value="all">All Assets</option>
      <option value="group">Asset Group</option>
      <option value="asset">Single Asset</option>
      <option value="scan">Single Scan</option>
    </select>
  </div>
  <div class="mb-3" id="group_field" style="display: none;">
    <label for="group_id" class="form-label">Asset Group</label>
    <select class="form-select" id="group_id" name="group_id">
      <option value="">Select group...</option>
      {% for group in groups %}
      <option value="{{ group.id }}">{{ group.name }} ({{ group.assets | length }} assets)</option>
      {% endfor %}
    </select>
  </div>
  <div class="mb-3" id="asset_field" style="display: none;">
    <label for="asset_id" class="form-label">Asset</label>
    <select class="form-select" id="asset_id" name="asset_id">
      <option value="">Select asset...</option>
      {% for asset in assets %}
      <option value="{{ asset.id }}">{{ asset.name }} ({{ asset.address }})</option>
      {% endfor %}
    </select>
  </div>
  <div class="mb-3" id="scan_field" style="display: none;">
    <label for="scan_id" class="form-label">Scan</label>
    <select class="form-select" id="scan_id" name="scan_id">
      <option value="">Select scan...</option>
      {% for scan in scans %}
      <option value="{{ scan.id }}">{{ scan.asset.name }} — {{ scan.profile.name }} ({{ scan.completed_at.strftime('%Y-%m-%d %H:%M') if scan.completed_at else 'N/A' }})</option>
      {% endfor %}
    </select>
  </div>
  <div class="mb-3" id="date_fields">
    <div class="row">
      <div class="col">
        <label for="date_from" class="form-label">From</label>
        <input type="date" class="form-control" id="date_from" name="date_from">
      </div>
      <div class="col">
        <label for="date_to" class="form-label">To</label>
        <input type="date" class="form-control" id="date_to" name="date_to">
      </div>
    </div>
  </div>
  <div class="d-flex gap-2">
    <button type="button" class="btn btn-primary" onclick="go('/reports/view')">View Report</button>
    <button type="button" class="btn btn-outline-secondary" onclick="go('/reports/pdf')">Download PDF</button>
    <button type="button" class="btn btn-outline-secondary" onclick="go('/reports/csv')">Download CSV</button>
    <button type="button" class="btn btn-outline-secondary" onclick="go('/reports/json')">Download JSON</button>
  </div>
</form>

<script>
function toggleFields() {
  const scope = document.getElementById('scope').value;
  document.getElementById('asset_field').style.display = scope === 'asset' ? '' : 'none';
  document.getElementById('group_field').style.display = scope === 'group' ? '' : 'none';
  document.getElementById('scan_field').style.display = scope === 'scan' ? '' : 'none';
  document.getElementById('date_fields').style.display = scope === 'scan' ? 'none' : '';
}
function go(base) {
  const form = document.getElementById('reportForm');
  const params = new URLSearchParams(new FormData(form));
  window.location.href = base + '?' + params.toString();
}
</script>
{% endblock %}
```

- [ ] **Step 4: Commit**

```bash
git add web/app/reports.py web/app/views/reports.py web/app/templates/reports/index.html
git commit -m "Add asset group scope to report generation"
```

---

### Task 8: Tests

**Files:**
- Create: `tests/web/test_asset_groups.py`

- [ ] **Step 1: Create comprehensive test file**

Create `tests/web/test_asset_groups.py`:

```python
"""Functional tests for asset group views."""
import os

os.environ["DATABASE_URL"] = "sqlite:///test_nmapctf.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch
from datetime import datetime, timezone

from app.database import Base, get_db
from app.main import app
from app.models import (
    Asset, AssetType, AssetGroup, ScanProfile, ScanJob, ScanResult, ScanStatus, User,
)


@pytest.fixture
def _test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(_test_engine):
    Session = sessionmaker(bind=_test_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(_test_engine, db_session):
    TestSessionLocal = sessionmaker(bind=_test_engine)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with patch("app.main.engine", _test_engine), \
         patch("app.main.SessionLocal", TestSessionLocal):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session):
    from app.auth import hash_password
    user = User(username="admin", password_hash=hash_password("testpass123"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def authed_client(client, admin_user):
    client.post("/login", data={"username": "admin", "password": "testpass123"})
    return client


@pytest.fixture
def sample_assets(db_session):
    a1 = Asset(name="web-server", type=AssetType.ip, address="10.0.0.1")
    a2 = Asset(name="db-server", type=AssetType.ip, address="10.0.0.2")
    a3 = Asset(name="mail-server", type=AssetType.ip, address="10.0.0.3")
    db_session.add_all([a1, a2, a3])
    db_session.commit()
    for a in [a1, a2, a3]:
        db_session.refresh(a)
    return [a1, a2, a3]


@pytest.fixture
def sample_group(db_session, sample_assets):
    group = AssetGroup(name="Production", description="Prod servers")
    group.assets.append(sample_assets[0])
    group.assets.append(sample_assets[1])
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)
    return group


@pytest.fixture
def sample_group_with_scans(db_session, sample_group):
    profile = ScanProfile(name="Group Test Profile", nmap_args="-T4", is_default=False)
    db_session.add(profile)
    db_session.flush()
    scan = ScanJob(
        asset_id=sample_group.assets[0].id,
        profile_id=profile.id,
        status=ScanStatus.completed,
        asset_group_id=sample_group.id,
        completed_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    db_session.add(scan)
    db_session.flush()
    result = ScanResult(
        job_id=scan.id, host="10.0.0.1", port=80,
        protocol="tcp", state="open", service="http",
    )
    db_session.add(result)
    db_session.commit()
    return sample_group


class TestGroupCRUD:
    def test_list_groups_empty(self, authed_client):
        resp = authed_client.get("/groups")
        assert resp.status_code == 200
        assert "Asset Groups" in resp.text

    def test_create_group(self, authed_client):
        resp = authed_client.post(
            "/groups/",
            data={"name": "Test Group", "description": "A test group"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_list_groups_shows_group(self, authed_client, sample_group):
        resp = authed_client.get("/groups")
        assert resp.status_code == 200
        assert "Production" in resp.text

    def test_group_detail(self, authed_client, sample_group):
        resp = authed_client.get(f"/groups/{sample_group.id}")
        assert resp.status_code == 200
        assert "Production" in resp.text
        assert "web-server" in resp.text
        assert "db-server" in resp.text

    def test_edit_group(self, authed_client, sample_group):
        resp = authed_client.get(f"/groups/{sample_group.id}/edit")
        assert resp.status_code == 200
        assert "Production" in resp.text

    def test_update_group(self, authed_client, sample_group):
        resp = authed_client.post(
            f"/groups/{sample_group.id}",
            data={"name": "Staging", "description": "Staging servers"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_delete_group(self, authed_client, sample_group, db_session):
        resp = authed_client.delete(f"/groups/{sample_group.id}")
        assert resp.status_code == 200
        # Assets should still exist
        assert db_session.get(Asset, sample_group.assets[0].id) is not None


class TestGroupMembers:
    def test_add_member(self, authed_client, sample_group, sample_assets):
        resp = authed_client.post(
            f"/groups/{sample_group.id}/members",
            data={"asset_id": sample_assets[2].id},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_remove_member(self, authed_client, sample_group, sample_assets):
        resp = authed_client.delete(f"/groups/{sample_group.id}/members/{sample_assets[0].id}")
        assert resp.status_code == 200

    def test_detail_shows_available_assets(self, authed_client, sample_group):
        resp = authed_client.get(f"/groups/{sample_group.id}")
        assert resp.status_code == 200
        # mail-server is not in the group, should be in the add dropdown
        assert "mail-server" in resp.text


class TestGroupScans:
    def test_run_scan_form_shows_groups(self, authed_client, sample_group):
        resp = authed_client.get("/scans/run")
        assert resp.status_code == 200
        assert "Production" in resp.text
        assert "Asset Group" in resp.text


class TestGroupReports:
    def test_report_index_shows_groups(self, authed_client, sample_group):
        resp = authed_client.get("/reports/")
        assert resp.status_code == 200
        assert "Production" in resp.text

    def test_group_report_html(self, authed_client, sample_group_with_scans):
        group_id = sample_group_with_scans.id
        resp = authed_client.get(f"/reports/view?scope=group&group_id={group_id}")
        assert resp.status_code == 200
        assert "Group Report" in resp.text

    def test_group_report_json(self, authed_client, sample_group_with_scans):
        group_id = sample_group_with_scans.id
        resp = authed_client.get(f"/reports/json?scope=group&group_id={group_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "Group Report" in data["title"]
        assert len(data["results"]) == 1

    def test_group_report_csv(self, authed_client, sample_group_with_scans):
        group_id = sample_group_with_scans.id
        resp = authed_client.get(f"/reports/csv?scope=group&group_id={group_id}")
        assert resp.status_code == 200
        assert "http" in resp.text

    def test_nonexistent_group_returns_404(self, authed_client):
        resp = authed_client.get("/reports/view?scope=group&group_id=99999")
        assert resp.status_code == 404


class TestNavbar:
    def test_navbar_has_groups_link(self, authed_client):
        resp = authed_client.get("/")
        assert resp.status_code == 200
        assert 'href="/groups"' in resp.text
```

- [ ] **Step 2: Run all tests**

```bash
cd /home/whiskey/nmapctf/web && .venv/bin/python -m pytest ../tests/web/ -v
```

Expected: All tests pass (existing 42 + new ~18).

- [ ] **Step 3: Commit**

```bash
git add tests/web/test_asset_groups.py
git commit -m "Add functional tests for asset groups"
```

---

### Task 9: Final Verification and Docker Rebuild

- [ ] **Step 1: Run full test suite**

```bash
cd /home/whiskey/nmapctf/web && .venv/bin/python -m pytest ../tests/web/ -v
```

Expected: All tests pass.

- [ ] **Step 2: Rebuild and verify Docker**

```bash
docker compose build web && docker compose up -d
```

Wait 3 seconds, then:

```bash
curl -s http://localhost:8080/api/v1/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 3: Clean up**

```bash
docker compose down
```

- [ ] **Step 4: Commit any remaining changes**

If any fixes were needed, commit them.
