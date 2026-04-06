# Multi-Tenancy with Organizations Design Spec

## Overview

Add organization-based multi-tenancy so users within the same org share assets, scans, and reports, while being isolated from other orgs. A root superadmin manages all orgs.

## Phase 1: Org and User Models, Superadmin, Org CRUD

### Organization Model

| Column | Type | Constraints |
|--------|------|-------------|
| id | int | PK |
| name | str(255) | unique |
| slug | str(255) | unique, indexed |
| created_at | datetime | UTC default |
| updated_at | datetime | UTC default |

### User Model Changes

Add to existing User model:
- `org_id` (FK → organizations.id, nullable) — null for superadmin
- `org_role` (Enum: `owner`, `admin`, `member`, nullable) — null for superadmin
- `is_superadmin` (bool, default False)

### Setup Flow

`/setup` creates the root superadmin with `is_superadmin=True`, `org_id=None`, `org_role=None`. No org is created during setup.

### Org Management (Superadmin Only)

- `GET /orgs` — list all orgs
- `GET /orgs/new` — create org form
- `POST /orgs/` — create org
- `GET /orgs/{id}` — org detail with member list
- `GET /orgs/{id}/edit` — edit org form
- `POST /orgs/{id}` — update org
- `DELETE /orgs/{id}` — delete org

### User Management

- Superadmin can create users and assign them to orgs via `/orgs/{id}/members`
- `POST /orgs/{id}/members` — add user to org (creates user with org_id + org_role)
- `POST /orgs/{id}/members/{user_id}` — update user's role
- `DELETE /orgs/{id}/members/{user_id}` — remove user from org (deletes user)

### Auth Changes

- Login returns user with org context
- Session stores `org_id` alongside `user_id` and `username`
- Superadmin session has `org_id=None`

## Phase 2: Scope All Data to Orgs

### Model Changes

Add `org_id` (FK → organizations.id) to:
- `Asset`
- `AssetGroup`
- `ScanProfile` (org-specific profiles, default profiles have `org_id=None`)
- `Schedule`
- `ScanJob`

`ScanResult` inherits org scope through its ScanJob parent.

### Query Filtering

Every query that reads assets, groups, profiles, schedules, or scans must filter by the current user's `org_id`. This is enforced at the view/API layer.

Superadmin bypasses the filter and sees all data (or can filter by org).

### Default Profiles

Seeded default scan profiles have `org_id=None` and are visible to all orgs. Org-created profiles are only visible within that org.

## Phase 3: Role-Based Permissions and UI

### Permission Enforcement

Middleware or dependency that checks:
1. Is the user a superadmin? → allow everything
2. Does the resource belong to the user's org? → check role permissions
3. Otherwise → 403

### Role Permissions

| Action | Owner | Admin | Member |
|--------|-------|-------|--------|
| Manage org settings | Yes | No | No |
| Invite/remove members | Yes | No | No |
| CRUD assets, groups, profiles, schedules | Yes | Yes | No |
| Run scans, import assets | Yes | Yes | No |
| View assets, scans, reports | Yes | Yes | Yes |

### UI Changes

- Navbar shows org name (or "Superadmin" for root user)
- Superadmin sees "Organizations" link in navbar
- Org owner sees "Members" link
- Member users see read-only views (no edit/delete/create buttons)
- Asset/scan/schedule pages only show org-scoped data

### Migration of Existing Data

On first run after upgrade:
- If the database has existing assets/scans but no orgs, create a "Default" org
- Assign all existing non-superadmin users and all data to the Default org
- The superadmin (from setup) remains org-less

## Files Overview

### Create
- `web/app/models/organization.py` — Organization model
- `web/app/schemas/organization.py` — Org schemas
- `web/app/views/orgs.py` — Org management views
- `web/app/templates/orgs/list.html` — Org list
- `web/app/templates/orgs/form.html` — Create/edit org
- `web/app/templates/orgs/detail.html` — Org detail with members
- `web/app/templates/orgs/add_member.html` — Add member form
- `tests/web/test_orgs.py` — Org management tests
- `tests/web/test_multitenancy.py` — Data isolation tests

### Modify
- `web/app/models/user.py` — Add org_id, org_role, is_superadmin
- `web/app/models/__init__.py` — Export Organization, OrgRole
- `web/app/models/asset.py` — Add org_id FK
- `web/app/models/asset_group.py` — Add org_id FK
- `web/app/models/scan_profile.py` — Add org_id FK (nullable for defaults)
- `web/app/models/schedule.py` — Add org_id FK
- `web/app/models/scan_job.py` — Add org_id FK
- `web/app/views/auth.py` — Setup creates superadmin, login stores org_id in session
- `web/app/views/assets.py` — Filter by org_id
- `web/app/views/groups.py` — Filter by org_id
- `web/app/views/scans.py` — Filter by org_id
- `web/app/views/schedules.py` — Filter by org_id
- `web/app/views/reports.py` — Filter by org_id
- `web/app/views/import_assets.py` — Set org_id on created assets
- `web/app/views/dashboard.py` — Filter stats by org_id
- `web/app/api/assets.py` — Filter by org_id
- `web/app/api/scans.py` — Filter by org_id
- `web/app/api/schedules.py` — Filter by org_id
- `web/app/api/asset_groups.py` — Filter by org_id
- `web/app/main.py` — Register org views, update middleware
- `web/app/templates/base.html` — Show org name, conditional nav links
- Various templates — Hide edit/create/delete for member role
