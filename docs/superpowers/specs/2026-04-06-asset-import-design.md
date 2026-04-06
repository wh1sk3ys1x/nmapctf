# Asset Import via File Upload Design Spec

## Overview

Add the ability to bulk-import assets from CSV, XLSX, or TXT files. Each IP/address becomes an individual asset, with optional assignment to an asset group during import. Duplicate addresses are skipped and reported.

## Upload Page

New page at `/assets/import`, accessible via an "Import" button on the assets list page (next to the existing "Add Asset" button).

### Form Fields

- **File** (required) — accepts `.csv`, `.xlsx`, `.txt`
- **Asset Group** (optional) — dropdown of existing groups; imported assets are added to this group
- **Default Asset Type** (optional) — dropdown (`ip`, `host`, `subnet`, `range`); defaults to `ip`. Overrides type for all entries unless the file provides a type column.

## File Format Parsing

### CSV

- First row is a header
- Required column: `address`
- Optional columns: `name`, `type`, `notes`
- Columns matched case-insensitively
- If `name` is missing or empty for a row, auto-generate from address (e.g., `asset-192.168.1.1`)
- If `type` is missing or empty for a row, use the form's default type selection

### XLSX

- Same column expectations as CSV
- Only the first sheet is read
- Requires `openpyxl` library

### TXT

- One address per line
- Blank lines and lines starting with `#` are ignored
- Name auto-generated from address
- Type uses the form's default type selection

## Processing Logic

1. Parse file based on extension
2. For each entry, validate: address is non-empty after stripping whitespace
3. Check if an asset with that address already exists in the database
4. If exists: skip, record as skipped with reason "already exists"
5. If new: create Asset with name, type, address
6. If asset group selected: add all newly created assets to the group
7. Render results page

## Results Page

After import, show a results summary on the same `/assets/import` page:

- **Created:** count and list of new asset names
- **Skipped:** count and list with address + reason
- Total rows processed

## Dependencies

- `openpyxl` added to `web/requirements.txt` for XLSX parsing
- CSV and TXT handled with Python stdlib (`csv`, `io`)

## Files

### Create
- `web/app/views/import_assets.py` — view routes for GET (form) and POST (process)
- `web/app/templates/assets/import.html` — upload form + results display

### Modify
- `web/app/templates/assets/list.html` — add "Import" button
- `web/app/main.py` — register import views router
- `web/requirements.txt` — add `openpyxl`

## What Does NOT Change

- Asset model unchanged — imports create standard Asset records
- Existing asset CRUD, groups, scans, schedules, reports all unaffected
- No new API endpoints — this is a web UI feature only
