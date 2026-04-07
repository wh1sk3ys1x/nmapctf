# UI Redesign Design Spec

## Overview

Replace the Bootstrap navbar + generic styling with a persistent sidebar navigation, custom dark theme, and terminal-inspired data display. The goal is a professional hacker tool aesthetic — dense, readable, no wasted space.

## Design Decisions

- **Navigation**: Persistent 200px sidebar with grouped sections, replacing top navbar
- **Tables**: Hybrid terminal style — monospace, alternating rows, pill-shaped status badges
- **Forms**: Clean minimal — stacked fields, no panels or sections
- **Dashboard**: Lean restyle — same content (stats, recent scans, schedules), new theme
- **Typography**: JetBrains Mono for all data/labels/nav, Outfit for headings and brand
- **Color palette**: Deep backgrounds, cyan accent, muted text hierarchy

## Color System

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-deep` | `#0a0e14` | Page background |
| `--bg-surface` | `#111820` | Cards, inputs, elevated surfaces |
| `--bg-sidebar` | `#0d1117` | Sidebar background |
| `--bg-row-alt` | `#0c1118` | Alternating table rows |
| `--bg-hover` | `#131b25` | Row/item hover state |
| `--bg-active` | `#1a2332` | Active sidebar item |
| `--border` | `#1e2a38` | All borders |
| `--accent` | `#38bdf8` | Primary accent (links, active items, addresses, services) |
| `--accent-hover` | `#5ccefb` | Accent hover state |
| `--text-primary` | `#e2e8f0` | Primary text (names, values) |
| `--text-secondary` | `#8899aa` | Secondary text (table data, nav items) |
| `--text-muted` | `#556677` | Labels, headers, timestamps |
| `--status-open` | `#22c55e` on `#16432a` | Open ports, completed scans |
| `--status-filtered` | `#eab308` on `#3b2e10` | Filtered ports, running scans |
| `--status-closed` | `#ef4444` on `#3b1515` | Closed ports, failed scans |
| `--status-pending` | `#8899aa` on `#1e2a38` | Pending scans |

## Navigation — Sidebar

### Structure

200px fixed sidebar on the left. All page content shifts right with `margin-left: 200px`.

```
nmapctf              (brand, Outfit bold, cyan)

Dashboard            (standalone item)

TARGETS              (section header)
  Assets
  Groups
  Import

SCANNING             (section header)
  Run Scan
  History
  Schedules
  Profiles

ANALYSIS             (section header)
  Reports

(spacer)

admin · Acme Corp    (user info at bottom, above border)
```

### Styling

- Section headers: 9px uppercase, letter-spacing 1.5px, `--text-muted`
- Items: 11px, `--text-secondary`, padding 8px 16px
- Active item: `--accent` text, `--bg-active` background, 2px left border in `--accent`, padding-left reduced by 2px
- Hover: `--text-primary` text, `--bg-surface` background
- User info: bottom of sidebar, above 1px top border, `--text-muted`

### Template Implementation

Extract sidebar into `web/app/templates/partials/sidebar.html`. Base template includes it. Active state set via a `nav_active` template variable passed from each view.

### URL Mapping

| Sidebar Item | URL | nav_active value |
|-------------|-----|-----------------|
| Dashboard | `/` | `dashboard` |
| Assets | `/assets` | `assets` |
| Groups | `/groups` | `groups` |
| Import | `/assets/import` | `import` |
| Run Scan | `/scans/run` | `run_scan` |
| History | `/scans` | `history` |
| Schedules | `/schedules` | `schedules` |
| Profiles | `/profiles` | `profiles` |
| Reports | `/reports` | `reports` |

## Tables — Hybrid Style

All data tables use a consistent style across the app.

### Structure

- Full-width, border-collapse
- Uppercase monospace column headers (10px, letter-spacing 1px, `--text-muted`), bottom border
- Alternating row backgrounds: odd rows `--bg-row-alt`, even rows transparent
- Hover: `--bg-hover`
- Cell padding: 6px 8px
- No vertical borders, only header bottom border

### Text Classes

- `.primary` — `--text-primary` for main identifiers (names, hosts)
- `.accent` — `--accent` for addresses, services, links
- `.muted` — `--text-muted` for timestamps, secondary data

### Status Badges

Pill-shaped: `padding: 1px 7px; border-radius: 3px; font-size: 10px`. Each status has a text color and tinted background:

- `completed` / `open`: green on dark green
- `running` / `filtered`: yellow on dark yellow
- `failed` / `closed`: red on dark red
- `pending`: secondary on border color

## Forms — Clean Minimal

### Input Styling

- Labels: `--text-secondary`, 10px, above field
- Inputs: `--bg-surface` background, 1px `--border`, 4px border-radius, 8px 10px padding, `--text-secondary` text
- Focus: border color changes to `--accent`, subtle glow (`0 0 0 2px rgba(56,189,248,0.15)`)
- Select dropdowns: same styling as inputs

### Buttons

- Primary: `--accent` background, `--bg-deep` text, bold
- Outline: transparent background, 1px `--border`, `--text-secondary` text
- Danger (small): transparent, 1px dark red border, red text
- All buttons: 4px border-radius, 11px JetBrains Mono

### Layout

- `max-width: 480px` for simple forms (asset, profile, schedule)
- `max-width: 600px` for complex forms (run scan, import)
- Page title in `--text-primary`, 13px, above form

## Pages

### Dashboard

- Page header: "DASHBOARD" in uppercase muted
- 4 stat cards in a row (grid, 4 columns): Assets, Total Scans, Active (green value), Schedules
- Stat cards: `--bg-surface`, 1px border, 6px radius, label above value
- Label: 9px uppercase `--text-muted`; Value: 24px Outfit bold `--text-primary`
- Two-column layout below stats:
  - Left: Recent Scans table (Asset, Profile, Status badge, Time)
  - Right: Active Schedules list (name + cron expression, alternating rows)
- Section headers: 9px uppercase `--text-muted`, letter-spacing 1.5px

### Assets List

- Page header: "ASSETS" + action buttons (Add Asset primary, Import outline)
- Bulk action bar (shown when items selected): `--bg-surface` with border, count in `--accent`, delete button, group dropdown + add button
- Table columns: checkbox, Name (.primary), Type (badge), Address (.accent + multi-address badge), Notes (.muted), Actions
- Type badge: `--border` background, `--text-secondary` text
- Multi-address badge: `--bg-active` background, `--accent` text (e.g., "+2")
- Action buttons: Edit (outline-sm), Del (danger-sm)

### Asset Form

- Clean minimal layout
- Fields: Name, Type (select), Address, Additional Addresses (HTMX partial — unchanged behavior), Notes (textarea)
- Buttons: Create/Update (primary), Cancel (outline)

### Groups List

- Table: Name (.primary, linked), Description, Members (count badge), Actions

### Group Detail

- Header: group name + description + Edit button
- Add member dropdown form
- Members table: Name, Type, Address (with additional addresses shown below primary in muted), Actions

### Scan History

- Filter bar: Status select + Asset select + Filter button (all inline)
- Table columns: Asset (.primary), Profile, Status (badge), Trigger, Queued (.muted), Completed (.muted), Results (count or —)
- Rows link to scan detail
- Cancel button for pending/running scans

### Scan Detail

- Breadcrumb: History > Scan Detail
- Page title: "SCAN · {asset_name}"
- Info grid (4-column, 2 rows): Asset (.accent), Address (.accent), Profile, Status (badge), Trigger, Queued, Completed, Duration
- Info items: `--bg-surface` cards with label and value
- Results table: Host (.primary), Port, State (badge), Service (.accent), Version (.muted)
- Collapsible raw XML section with syntax highlighting (tags=cyan, attrs=yellow, values=green)

### Run Scan Form

- Radio target selection (Quick Target / Existing Asset / Asset Group)
- Conditional field display (unchanged JS behavior)
- Asset dropdown shows "+N" for multi-address assets
- Address selection info section for multi-address assets
- Profile dropdown
- Styled with clean minimal form rules

### Schedules List

- Table: Name (.primary), Asset/Group, Profile, Cron (.muted, monospace), Status (enable/disable badge), Last Run (.muted), Actions
- Toggle button via HTMX (unchanged behavior)

### Schedule Form

- Clean minimal, radio for target type, conditional asset/group dropdowns

### Profiles List

- Table: Name (.primary, with default badge), Arguments (.muted, monospace), Description, Actions

### Profile Form

- Clean minimal: Name, Nmap Arguments, Description

### Import

- File upload, group dropdown, default type select
- Results: stat cards (Created/Skipped/Addresses Added/Total) + detail tables
- Styled with clean minimal form rules, stat cards match dashboard style

### Reports

- Scope selector (radio), conditional dropdowns, date range
- Action buttons: View Report, Download PDF/CSV/JSON
- Report viewer: standalone page (not base template), print-friendly — minimal restyle needed

### Auth Pages (Login, Setup, Account)

- Centered card on deep background
- Clean minimal form inside
- Brand "nmapctf" above form

### Org Pages (List, Form, Detail)

- Same patterns as other list/form/detail pages
- Member table with role select, add member form

## CSS Architecture

### Remove

- Bootstrap 5.3.3 CSS (CDN link in base.html)
- Bootstrap JS (CDN link in base.html)
- Existing `style.css` (550 lines) — complete replacement

### Keep

- HTMX 2.0.4 (no styling dependency)
- Google Fonts (JetBrains Mono + Outfit — already loaded)

### New Files

- `web/app/static/style.css` — complete rewrite with CSS custom properties
- `web/app/templates/partials/sidebar.html` — sidebar navigation partial

### Modify

- `web/app/templates/base.html` — remove Bootstrap, add sidebar include, restructure layout
- All ~20 page templates — remove Bootstrap classes, apply new CSS classes

### CSS Organization

Single `style.css` organized by section:

1. **Reset & custom properties** — CSS variables for colors, typography
2. **Layout** — sidebar, main content area, page headers
3. **Typography** — headings, labels, text utilities
4. **Tables** — data-table, alternating rows, text classes
5. **Badges** — status badges, type badges, count badges
6. **Forms** — inputs, selects, textareas, buttons
7. **Cards** — stat cards, info grid items
8. **Components** — bulk action bar, breadcrumbs, filter bar
9. **Utilities** — spacing, display helpers
10. **Auth** — centered login/setup layout

### Bootstrap Removal

Bootstrap classes used across templates that need replacement:

| Bootstrap Class | Replacement |
|----------------|-------------|
| `container` | `.main` (from sidebar layout) |
| `table`, `table-hover` | `.data-table` |
| `btn btn-primary` | `.btn .btn-primary` |
| `btn btn-outline-*` | `.btn .btn-outline` or `.btn-outline-sm` |
| `btn-sm` | size built into `.btn-outline-sm`, `.btn-danger-sm` |
| `form-control` | `input, select, textarea` (styled globally) |
| `form-select` | `select` (styled globally) |
| `form-label` | `label` (styled globally) |
| `form-check-input` | `.checkbox` |
| `badge bg-*` | `.badge .badge-*` |
| `alert alert-*` | `.alert .alert-*` |
| `d-flex`, `gap-*` | flex utilities or inline styles |
| `d-none` | `.hidden` utility |
| `mb-3`, `mt-3`, etc. | margin built into component styles |
| `row`, `col-*` | CSS grid on parent elements |

### Responsive

- Sidebar remains fixed at 200px (no collapse on small screens — this is a desktop admin tool)
- Stat cards: 4 columns on wide, 2 columns below 900px
- Dashboard two-column: stacks to single column below 900px

## What Does NOT Change

- HTMX behavior (all hx-* attributes remain)
- JavaScript logic (toggleTarget, bulk selection, etc.)
- View handlers (no Python changes)
- URL structure
- Template variable names
- Flash message system (just restyled)
- Report viewer (standalone page, minimal changes)

## Mockups

Reference mockups saved in `.superpowers/brainstorm/` directory:
- `show-dashboard.html` — Dashboard page
- `show-assets.html` — Assets list page
- `show-scan-detail.html` — Scan detail page
