# Inventory → Master Google Sheet Sync — March 7, 2026

**Status:** Implemented  
**Purpose:** Keep the master inventory tab in sync with Supabase `components`.

---

## Master Sheet

| Property | Value |
|----------|-------|
| **URL** | https://docs.google.com/spreadsheets/d/1rhuGmyxZakCVet1zMK3_C2f3SCOzH_dr6HH6EKWGRmc/edit?gid=1289530278#gid=1289530278 |
| **Spreadsheet ID** | `1rhuGmyxZakCVet1zMK3_C2f3SCOzH_dr6HH6EKWGRmc` |
| **Tab GID** | `1289530278` |

---

## Sync Script

| Script | Purpose |
|--------|---------|
| `scripts/sync_components_to_google_sheets.py` | Fetches Supabase components → CSV + optional push to master sheet |

**Usage:**
```bash
# 1. Export CSV only (always works if Supabase env is set)
python scripts/sync_components_to_google_sheets.py

# 2. Push to Google Sheets (requires gspread + credentials)
python scripts/sync_components_to_google_sheets.py --push
```

**Output CSV:** `data/amazon_import/master_sheet_inventory.csv`  
**Columns:** `id`, `name`, `sku`, `category`, `quantity`, `unit_cost`, `supplier_name`, `location`, `reorder_threshold`, `supplier_lead_time_days`

---

## Env Vars

| Purpose | Env Vars |
|---------|----------|
| **Supabase** | `NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` |
| **Google Sheets push** | `GOOGLE_APPLICATION_CREDENTIALS` (path to service account JSON) or `GOOGLE_SERVICE_ACCOUNT_PATH` or `GOOGLE_SERVICE_ACCOUNT_KEY` or `GOOGLE_SHEETS_CREDENTIALS_JSON` |

---

## When to Sync

**After any inventory change**, run the sync so the master sheet stays current:

1. After importing components from Amazon or other sources
2. After name updates (`update_component_names_for_staff.py`)
3. After BOM edits that affect `components`
4. After manual edits in Supabase

---

## Manual Paste (no credentials)

If you don't have a Google service account JSON locally:

1. Run: `python scripts/sync_components_to_google_sheets.py`
2. Open the master sheet tab (URL above)
3. Select cell A1, paste the contents of `data/amazon_import/master_sheet_inventory.csv` (File > Import or paste from clipboard)

---

## Automated Push

1. Create a Google Cloud service account with Sheets API access
2. Download the JSON key
3. Share the spreadsheet with the service account email (Editor)
4. Set `GOOGLE_APPLICATION_CREDENTIALS` to the JSON path
5. Run: `python scripts/sync_components_to_google_sheets.py --push`

The script **replaces** the entire tab content (clear + update). It does not append.

---

## Related

- `docs/AMAZON_IMPORT_SUPABASE_COMPLETE_MAR07_2026.md` — Import workflow
- `docs/COMPONENT_NAMES_STAFF_GUIDE_MAR07_2026.md` — Staff names, naming rules
- `docs/COMPONENTS_REMOVED_MAR07_2026.md` — Non-BOM removal list
