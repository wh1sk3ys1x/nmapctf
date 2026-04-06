# Asset Groups Design Spec

## Overview

Add asset groups to nmapctf so users can organize assets into named collections (e.g., "Production Servers", "DMZ") and run scans, schedules, and reports against entire groups.

## Data Model

### AssetGroup

| Column | Type | Constraints |
|--------|------|-------------|
| id | int | PK |
| name | str(255) | unique, indexed |
| description | text | nullable |
| created_at | datetime | UTC default |
| updated_at | datetime | UTC default |

### asset_group_members (junction table)

| Column | Type | Constraints |
|--------|------|-------------|
| asset_group_id | int | FK → asset_groups.id, PK |
| asset_id | int | FK → assets.id, PK |

Composite primary key on (asset_group_id, asset_id). Cascade delete on both FKs — deleting a group or asset removes the membership row.

### Relationships

- AssetGroup has `assets` (many-to-many via junction table)
- Asset has `groups` (many-to-many back-reference)
- Schedule gets optional `asset_group_id` (FK, nullable) — mutually exclusive with `asset_id` (one must be set, not both)
- ScanJob gets optional `asset_group_id` (FK, nullable) — tracks which group triggered the scan, if any. `asset_id` remains required (each job still targets one asset).

## API Endpoints

### Group CRUD — `/api/v1/asset-groups`

| Method | Endpoint | Action |
|--------|----------|--------|
| GET | `/` | List all groups (with member count) |
| GET | `/{group_id}` | Get group with member assets |
| POST | `/` | Create group (name, description) |
| PATCH | `/{group_id}` | Update group name/description |
| DELETE | `/{group_id}` | Delete group (removes memberships, not assets) |

### Membership — `/api/v1/asset-groups/{group_id}/members`

| Method | Endpoint | Action |
|--------|----------|--------|
| POST | `/` | Add asset to group (body: `{asset_id}`) |
| DELETE | `/{asset_id}` | Remove asset from group |

### Scan Changes — `/api/v1/scans`

ScanCreate accepts either `asset_id` or `asset_group_id` (not both). When `asset_group_id` is provided, the endpoint creates one ScanJob per member asset, all sharing the same profile. Returns the list of created jobs.

### Schedule Changes — `/api/v1/schedules`

ScheduleCreate accepts either `asset_id` or `asset_group_id` (not both). When the schedule triggers, it creates one ScanJob per member asset in the group at that time (membership evaluated at trigger time, not schedule creation time).

## Web UI

### Groups Pages — `/groups`

| Route | Method | Description |
|-------|--------|-------------|
| `/groups` | GET | List groups with member count, edit/delete buttons |
| `/groups/new` | GET | Create group form (name, description) |
| `/groups/{id}` | GET | Group detail — lists member assets with remove button, add-asset dropdown |
| `/groups/{id}/edit` | GET | Edit group name/description |
| `/groups` | POST | Create group |
| `/groups/{id}` | POST | Update group |
| `/groups/{id}` | DELETE | Delete group (HTMX) |
| `/groups/{id}/members` | POST | Add asset to group (HTMX) |
| `/groups/{id}/members/{asset_id}` | DELETE | Remove asset from group (HTMX) |

### Changes to Existing Pages

- **Navbar:** Add "Groups" link between "Assets" and "Profiles"
- **Asset list (`/assets`):** Show group badges next to each asset
- **Run Scan (`/scans/run`):** Add "Asset Group" dropdown as alternative to single asset. JavaScript toggles between asset and group selection.
- **New Schedule (`/schedules/new`):** Same toggle — pick either a single asset or a group.
- **Reports (`/reports`):** Add "Asset Group" scope option. When selected, show group dropdown. Report aggregates all scans for all assets in the group.

## Schemas

### AssetGroupCreate
- `name` (str, required)
- `description` (str, optional)

### AssetGroupUpdate
- `name` (str, optional)
- `description` (str, optional)

### AssetGroupOut
- All fields + `member_count` (int) + timestamps

### AssetGroupDetail
- All fields + `assets` (list of AssetOut) + timestamps

### Modified: ScanCreate
- `asset_id` (int, optional) — now optional
- `asset_group_id` (int, optional) — new
- Validation: exactly one of asset_id or asset_group_id must be provided

### Modified: ScheduleCreate
- `asset_id` (int, optional) — now optional
- `asset_group_id` (int, optional) — new
- Validation: exactly one of asset_id or asset_group_id must be provided

## Reports

New report scope `group`:
- `group_report(db, group_id, date_from, date_to)` — queries all completed ScanJobs where `asset_id` is in the group's membership, within date range
- Title: "Group Report: {group.name}"
- Summary: total_scans, total_assets, total_hosts, total_ports, open_ports

Report index form gets a group dropdown, shown when scope is "group".

## Testing

Tests follow existing patterns in `tests/web/`:

- **test_asset_groups.py:** Group CRUD via web UI, membership add/remove, group detail page, asset list shows badges
- **API tests** (if separate test file exists): Group API CRUD, membership API, scan creation with group, schedule creation with group
- **Report tests:** Group-scoped report generation

## What Does NOT Change

- Asset model gets no new columns (groups are purely relational via junction table)
- Existing single-asset scans and schedules continue to work unchanged
- ScanJob always has a required `asset_id` — group scans just create multiple jobs
- Deleting a group never deletes assets
