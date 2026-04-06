# Multi-Address Assets Design Spec

## Overview

Allow assets to have multiple IP addresses (e.g., primary + failover) via a separate AssetAddress table. Scans can target all addresses or specific ones. Results are grouped under the asset regardless of which address was scanned.

## Data Model

### AssetAddress (new)

| Column | Type | Constraints |
|--------|------|-------------|
| id | int | PK |
| asset_id | int | FK → assets.id, cascade delete |
| address | str(255) | required |
| label | str(100) | nullable (e.g., "primary", "failover", "mgmt") |
| is_primary | bool | default False |

One address per asset should have `is_primary=True`. The existing `Asset.address` column is kept and always reflects the primary address for backward compatibility and display.

### Asset Model Changes

- Add `addresses` relationship → list of AssetAddress (cascade delete)
- `Asset.address` remains as the primary address string field
- When creating an asset, the initial address is also inserted as an AssetAddress with `is_primary=True`
- When the primary AssetAddress changes, `Asset.address` syncs to match

## Asset UI

### Asset Form (create/edit)

- Primary address field stays as-is at the top
- New "Additional Addresses" section below:
  - List of existing additional addresses with label and remove button
  - "Add Address" row with address input + optional label input + add button
  - HTMX for add/remove without full page reload

### Asset List

- Primary address shown as before in the Address column
- If asset has additional addresses, show a badge like `+2` next to the primary address

### Group Detail

- Asset rows show all addresses (primary + additional)

## Scan Changes

### Run Scan Form

- When "Existing Asset" is selected and the chosen asset has multiple addresses:
  - Show address selection: radio for "All addresses" (default) or checkboxes for individual addresses
  - Dynamic — updates via HTMX or JS when the asset dropdown changes
- When "All addresses" is selected (or the asset has only one address): one ScanJob per address, all with the same `asset_id`
- Quick Target: unchanged, single address, auto-creates asset with one AssetAddress

### Scan Execution

- Each ScanJob targets one address (the `target` passed to the scanner worker)
- Multiple ScanJobs created for multi-address scans, all sharing the same `asset_id`
- ScanJob gets no schema change — `asset_id` already links to the asset

### Group Scans

- When scanning a group, scan all addresses for each asset in the group
- One ScanJob per address per asset

### Scheduled Scans

- When a schedule triggers for an asset with multiple addresses, create one ScanJob per address

## Report Changes

No changes needed. Reports already group/filter by `asset_id`. Multiple ScanJobs for the same asset from different addresses are naturally included.

## Import Changes

- If a row's name (or hostname/location/label column) matches an existing asset's name:
  - Instead of skipping, add the row's address as a new AssetAddress on the existing asset
  - Set `is_primary=False` on the new address
  - Track in results: count of "addresses added to existing assets"
- If the row is a new asset: create Asset + AssetAddress with `is_primary=True` as before

## Files

### Create
- `web/app/models/asset_address.py` — AssetAddress model
- `web/app/templates/assets/addresses_partial.html` — HTMX partial for address management

### Modify
- `web/app/models/__init__.py` — export AssetAddress
- `web/app/models/asset.py` — add `addresses` relationship
- `web/app/views/assets.py` — add/remove address endpoints, update create/edit
- `web/app/templates/assets/form.html` — additional addresses section
- `web/app/templates/assets/list.html` — show address count badge
- `web/app/views/scans.py` — handle multi-address scan creation
- `web/app/templates/scans/run.html` — address selection UI
- `web/app/views/schedules.py` — scan all addresses on schedule trigger
- `web/app/views/import_assets.py` — add addresses to existing assets on name match
- `web/app/templates/assets/import.html` — update results to show addresses added
- `web/app/templates/groups/detail.html` — show all addresses per asset

## What Does NOT Change

- Asset model keeps `address` column (primary address, backward compatible)
- ScanJob model unchanged — `asset_id` FK stays as-is
- ScanResult model unchanged
- Report queries unchanged — they filter by `asset_id`
- AssetGroup model unchanged
- Organization/multi-tenancy scoping unchanged — AssetAddress inherits org scope through its parent Asset
