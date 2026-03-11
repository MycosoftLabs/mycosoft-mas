# Amazon Business Import Summary — March 7, 2026

## Report used
- **File:** orders_from_20241201_to_20260306_20260306_1012.csv
- **Date range:** Dec 2024 – Mar 2026 (from filename)
- **Raw rows:** 598
- **After excluding non-inventory:** 350 (248 excluded)
- **Unique components (by ASIN):** 291

## Filtering
- Excluded: cancelled orders, zero quantity
- Excluded non-inventory: aa , aaa , alkaline, apparel, artwork, bathroom, batteries, beverage, bookcase, candy, canvas, car phone holder, chair, coffee, deadbolt...
- Kept ambiguous items for manual review

## Outputs
- `mycoforge_components_import_ready.csv` — 291 rows, ready for Supabase
- `amazon_business_raw_export.csv` — raw copy

## Google Sheets
Paste `mycoforge_components_import_ready.csv` into:
https://docs.google.com/spreadsheets/d/1rhuGmyxZakCVet1zMK3_C2f3SCOzH_dr6HH6EKWGRmc/edit?gid=1289530278#gid=1289530278

## Next steps
1. Review excluded items; add back if needed
2. Set SUPABASE_SERVICE_ROLE_KEY and re-run for Supabase insert
3. Verify in MycoForge: https://mycoforge.tech619.com
