# Device Products and MycoForge Sync

**Date:** March 7, 2026  
**Status:** Current  
**Related:** `WEBSITE/website/lib/device-products.ts`, Supabase `products`, `components`, `bom_items`, `builds`

## Overview

MycoForge is the internal system for hardware products, BOMs, components, and build tracking. The **canonical product registry** lives in `WEBSITE/website/lib/device-products.ts`. Supabase `products` must stay in sync with this registry for pre-orders, builds, and BOMs.

## Canonical Source

- **File:** `WEBSITE/website/lib/device-products.ts`
- **Exports:** `DEVICE_PRODUCTS`, `getAllProductIds()`, `DEVICE_ROLE_DISPLAY`
- **Product IDs:** e.g. `mushroom1-mini`, `myconode-white`, `hypha1-compact`

## Supabase Schema

| Table       | Purpose                    | Key Columns                    |
|------------|----------------------------|--------------------------------|
| `products` | Device variants            | id (text PK), name, description, image_url |
| `components` | Raw parts/boards         | id, name, sku, category        |
| `bom_items` | Product → Component links | product_id, component_id, quantity_needed |
| `builds`   | Build runs                 | product_id, quantity, status   |
| `build_items` | Components used per build | build_id, component_id, quantity_used |

## Sync Scripts

### 1. Products seed (device variants)

**Script:** `scripts/supabase_products_seed.py`

Upserts all device variants from `getAllProductIds()` into Supabase `products` with canonical IDs.

```bash
# From MAS repo root; requires NEXT_PUBLIC_SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY
python scripts/supabase_products_seed.py
```

**Product IDs synced:** mushroom1-mini, mushroom1-standard, mushroom1-large, mushroom1-defense, sporebase, alarm, myconode-white, myconode-black, myconode-purple, myconode-blue, myconode-orange, myconode-red, myconode-yellow, myconode-camo-green, hypha1-compact, hypha1-standard, hypha1-industrial.

### 2. Components import

**Script:** `scripts/supabase_components_import.py`  
**Data:** `data/amazon_import/mycoforge_components_import_ready.csv`

Imports raw components into Supabase `components`. Run when BOM source data changes.

### 3. Amazon Business import

**Script:** `scripts/amazon_business_import.py`

Generates/updates the CSV used by the components import.

## Website Integration

### PreOrderModal

- **File:** `components/devices/pre-order-modal.tsx`
- **Props:** `productName`, `productId` (canonical ID for MycoForge/Supabase)
- **Usage:** Mushroom 1 details page passes `productId={mushroom1-${selectedVariant}}`

### Device pages

- **Mushroom 1:** Uses `PreOrderModal` with `productName` and `productId` from selected variant.
- **MycoNODE, Hyphae 1:** No pre-order modal yet; add when ready.

## Legacy Product

- **ID:** `p1772752271359`
- **Name:** "Mushroom One (big/internal testing)"
- **Note:** Old ID scheme. Can remain as legacy/internal product or be migrated to canonical `mushroom1-*` if BOM links are updated.

## Maintenance

1. **Add new product variant:** Update `DEVICE_PRODUCTS` in `device-products.ts`, then run `supabase_products_seed.py`.
2. **Add BOM items:** Link new `products.id` to `components.id` in `bom_items`.
3. **Pre-order flow:** When "Complete Pre-Order" is implemented, use `productId` to create `orders` or pre-order records in Supabase.
