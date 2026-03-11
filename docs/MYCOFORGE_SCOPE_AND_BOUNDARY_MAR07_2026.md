# MycoForge Scope and Boundary

**Date:** March 7, 2026  
**Status:** Current  
**Purpose:** Define what belongs in MYCOFORGE (device manufacturing only) vs company operations.

---

## Rule of Thumb

**Purchasing something on Amazon does NOT mean it goes into MYCOFORGE.**  
MYCOFORGE = device manufacturing only. House items, office supplies, C-Suite tools, and general company purchases stay elsewhere.

---

## MYCOFORGE Scope (Device Manufacturing Only)

MYCOFORGE contains **only** items related to building the **5–6 Mycosoft devices**:

| Device      | Product IDs |
|-------------|-------------|
| Mushroom 1  | mushroom1-mini, mushroom1-standard, mushroom1-large, mushroom1-defense |
| SporeBase   | sporebase |
| ALARM       | alarm |
| MycoNODE    | myconode-white, myconode-black, etc. (9 colors) |
| Hypha 1     | hypha1-compact, hypha1-standard, hypha1-industrial |
| Soil Probe (FCI) | Component of Mushroom 1 |

### What Belongs in MYCOFORGE

- **Components** — Raw parts used in device BOMs: dev boards (ESP32, Jetson), sensors (BME688), antennas, batteries, chassis, cables, filament for device housings, etc.
- **Products** — Device variants (mushroom1-mini, sporebase, etc.)
- **BOM items** — Links between products and components
- **Builds** — Production runs for devices
- **Hardware network devices** — MycoBrain boards, field devices

### Supabase Tables (MYCOFORGE Only)

| Table                | Purpose |
|----------------------|---------|
| `products`           | Device variants |
| `components`         | BOM parts for devices |
| `bom_items`          | Product → component links |
| `builds`             | Build runs |
| `build_items`        | Components used per build |
| `production_runs`    | Device production (when device-specific) |
| `hardware_network_devices` | MycoBrain / network devices |

---

## NOT MYCOFORGE (Exclude)

These stay in company operations, house lists, or other tools. **Do not put them in MYCOFORGE.**

| Category           | Examples |
|--------------------|----------|
| **House items**    | Furniture, kitchen supplies, trash cans, bathroom, locks, vacuum, roomba |
| **Office supplies**| General office organizers, staplers, paper, non-device cables |
| **Tools (non-device)** | Hand tools for home repair, gym equipment, car accessories |
| **Personal purchases** | Apparel, snacks, beverages, subscriptions, wall art |
| **C-Suite / ops**  | Apps, vendors, commitments, liabilities, recruitment — company backbone, not device BOM |
| **Amazon random**  | Anything bought on Amazon that is not a device component |

### Master Spreadsheet Tabs by Scope

| Tab                  | Scope        | Description |
|----------------------|--------------|-------------|
| inventory            | **mycoforge** | Supabase `components` — device BOM parts only |
| hardware             | **mycoforge** | MycoBrain / network devices |
| production           | **mycoforge** | Device production runs |
| apps_and_services    | company_ops  | Company tools, dashboards |
| customer_vendors     | company_ops  | General vendors |
| commitments          | company_ops  | Company commitments |
| liabilities          | company_ops  | Company liabilities |
| recruitment          | company_ops  | HR / recruitment |
| singlogs             | company_ops  | Operational logs |

---

## Data Buses (Integration Points)

```
MYCOFORGE (device manufacturing)
├── device-products.ts  ←→  Supabase products (supabase_products_seed.py)
├── Supabase components ←→  Master Sheet "inventory" tab (sync_components_to_google_sheets.py)
├── mycoforge_components_import_ready.csv  →  Supabase components (supabase_components_import.py)
└── Amazon Business CSV (device parts only) →  amazon_business_import.py → mycoforge_components_import_ready.csv

Company backbone (operational)
├── Master Sheet tabs (inventory, hardware, apps_and_services, ...)
├── sync_master_spreadsheet.py  ←  Supabase + MAS API
└── n8n / POST /api/spreadsheet/sync
```

---

## Staff Process

1. **Before adding a component:** Ask: "Is this used in a BOM for Mushroom 1, SporeBase, ALARM, MycoNODE, or Hypha 1?"
2. **If NO** — Do not add to MYCOFORGE. Use company ops, house list, or other tracking.
3. **If YES** — Add via `mycoforge_components_import_ready.csv` or direct Supabase, following `COMPONENT_NAMES_STAFF_GUIDE_MAR07_2026.md`.

---

## Related

- `docs/DEVICE_PRODUCTS_AND_MYCOFORGE_SYNC_MAR07_2026.md`
- `docs/COMPONENT_NAMES_STAFF_GUIDE_MAR07_2026.md`
- `config/master_spreadsheet_automation.yaml` (scope per tab)
