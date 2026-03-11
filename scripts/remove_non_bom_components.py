#!/usr/bin/env python3
"""
Remove non-BOM components from Supabase components table.
Keeps ONLY items that are BOM for the 5 Mycosoft devices (MycoBrain, Mushroom1, SporeBase, etc.).
Removes: house, furniture, shop tools, office equipment, personal, lab consumables.

Usage:
  python scripts/remove_non_bom_components.py [--dry-run]
  Writes docs/COMPONENTS_REMOVED_MAR07_2026.md with removal list for restoration.

Env: NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (or NEXT_PUBLIC_SUPABASE_ANON_KEY)
"""

import argparse
import json
import os
import re
from pathlib import Path

# BOM: Must match at least one of these (device BOM for MycoBrain, Mushroom1, SporeBase, etc.)
BOM_INCLUDE = {
    "esp32", "arduino", "raspberry pi", "jetson", "lora", "sx1262", "sx1278",
    "bme680", "bme688", "bme690", "meshtastic", "lilygo", "ttgo",
    "ov5647", "ov2640", "gc2145", "ov5647", "foriot", "arducam",
    "filament", "pla", "petg", "abs", "asa",
    "18650", "lipo", "tp4056", "tp4057", "battery charger",
    "jst", "dupont", "heat shrink", "chassis", "junction box", "qilipsu",
    "mycobrain", "mushroom one", "mycobot", "flipper zero",
    "sensecap", "myoware", "solar controller",
    "915mhz", "915 mhz", "gnss", "antenna",
    "micro sd", "microsd", "sd card",
    "cn3065", "solar lipo", "aceirmc",
    "ws2812b", "led pixel",  # for device indicators
    "ttgo t-", "t-beam", "t-echo", "t-deck", "t-sim7000", "t-a7670",
    "wire 22awg", "22 gauge wire", "silicone wire", "bare copper wire",
    "keystone", "rj45", "cat8", "ethernet",  # for device networking
    "rubber grommet", "threaded insert", "m3", "m4", "m5", "screw", "bolt",
    "solder", "rework", "heat gun", "tip tinner",
    "potentiometer", "trimmer", "resistor", "diode", "schottky",
    "ina333", "ina128", "ad620", "amplifier module",
    "obstacle avoidance", "tcrt5000", "ttp223", "touch switch",
    "lidar", "tf-luna", "as3935",
    "sma ", "ipex", "u.fl", "coaxial",
}

# REMOVE: If name matches any of these → delete (house, furniture, shop, office, personal)
REMOVE_KEYWORDS = {
    "toilet paper", "spray bottle", "trash", "trash can", "hair mister",
    "chair", "stool", "ottoman", "tv mount", "tv wall mount", "shelf", "bookcase",
    "organizer", "furniture", "household", "storage bin", "storage box",
    "utility cart", "workbench", "step stool", "garage", "home decor",
    "ceiling tile", "ceiling fan", "throw pillow", "cord concealer", "sleek socket",
    "govee", "linkind", "smart bulb", "smart light", "smart plug", "smart switch",
    "smart outlet", "usb wall outlet", "usb charger wall",
    "nest ", "furrion", "thermostat", "rv roof", "rv air",
    "tile leveling", "tile spacer", "tile clip", "baumfeuer", "dgsl",
    "ladder", "drill bit", "pegboard", "screwdriver rack", "garage organizer",
    "flexi rods", "wire spool rack", "drawer cabinet", "arteza",
    "keyboard tray", "laptop stand", "headphone stand", "vivo mount", "upergo",
    "apple pencil", "minecraft", "beanie", "antifungal", "clotrimazole",
    "car registration", "car truck boat", "directional car",
    "solar pathway", "pathway light", "jofios solar",
    "petri dish", "agar plate", "scalpel", "inoculating loop", "centrifuge tube",
    "microscope", "trinocular", "copper sulfate", "beaker", "flask", "bunsen",
    "soxhlet", "lab glassware", "soil moisture", "plant meter", "gardening",
    "earthwise", "chipper", "tiller", "cultivator", "rototiller",
    "prime membership", "business prime",
    "bitcoin miner", "btc miner", "nerdqaxe",
    "shrooly", "mushroom growing",
    "irobot", "roomba", "cleaning solution",
    "samsung tv", "samsung 32", "power cord for samsung", "bn44-00837",
    "speaker cable", "amazon basics speaker",
    "logitech", "lenovo legion", "hp laptop", "hp 15.6",
    "samsung monitor", "viewfinity", "ls32d",
    "caldigit", "thunderbolt dock",
    "ac infinity", "airframe", "ventilation grille",
    "incubator", "scientific incubator", "25l",
    "magnetic tool holder", "tool organizer", "tool rack",
    "14 gauge wire", "600 ft", "auto wire", "low voltage 14 gauge",
    "displayport to hdmi", "8k displayport", "hdmi splitter", "orei",
    "thandble", "displayport", "usb c to 3 hdmi",
    "10g ethernet switch", "10g nas", "wifi7 router",
    "anker prime thunderbolt", "anker thunderbolt", "anker usb-c hub",
    "cat8 flat", "invisable", "home/office", "indoor & outdoor",
    "mouse pad", "digital calendar", "apolosign",
    "microfiber", "cleaning cloth",
    "scissors", "sharpie", "permanent marker",
    "cob led strip", "wood slat wall", "under cabinet", "acoustic panel",
    "elegrp smart", "elegrp usb",
    "ghome smart",
    "candelabra", "e12 bulb", "chandelier",
    "copper wire 20 gauge", "310ft", "1lb spool",  # bulk house wire - remove
    "landscape", "path light", "sunvie",
    "submersible pump", "superior pump",
    "asus pro ws", "wrx90", "threadripper",
    "be quiet", "dark power pro", "1600w",
    "corsair vengeance", "ddr4 3200",
    "nzxt kraken", "liquid cooler",
    "msi gaming", "rtx 5090", "suprim",
    "hyte y70", "dual chamber",
    "wd_black", "sn850x", "wd red pro", "26tb", "8tb",
    "nemix ram", "ecc rdimm",
    "beelink mini", "acemagician", "mini pc", "mini gaming pc",
    "creality k2 plus combo", "3d printer", "creality k2 plus build plate",
    "creality cfs", "filament system",
    "google pixel", "pixel 9a",
    "myq smart garage", "garage door",
    "bysameyee", "wireless digital microscope",
    "fanttik", "electric screwdriver",
    "stream controller", "soomfon", "obs twitch",
    "xbox", "gaming controller",
    "video conference", "zoom lighting", "ring light",
    "speed rail", "liquor rack", "bottle holder",
    "curtain track", "replacement belt",
    "laptop holder", "vertical laptop",
    "studless tv mount", "perlegear", "mounting dream",
}

# Explicit IDs to always KEEP (device BOM by ID)
KEEP_IDS = {
    "c1772753572559",  # Mycobrain V1
    "c1772756665580",  # Mushroom One Big Body
    "c1772757984324",  # BME680
    "c1772757965488",  # BME688
    "c1772754630521",  # BME690
    "c1772767020653",  # ESP32-S3
    "c1772765873359",  # Jetson Orin Nano
    "c1772756532326",  # Medium grey box chassis
    "c1772756572006",  # Small grey box chassis
    "c1772756491478",  # White box chassis
    "c1772756414292",  # Solar controller
    "b0fq5xwxmg",     # Yahboom Jetson Orin NX Super 157TOPS
}


def is_bom_component(row: dict) -> bool:
    """True if component is device BOM for Mycosoft devices."""
    cid = (row.get("id") or "").strip().lower()
    name = (row.get("name") or "").lower()
    cat = (row.get("category") or "").lower()

    if cid in KEEP_IDS:
        return True

    # Check BOM include FIRST (device components override broad REMOVE)
    for kw in BOM_INCLUDE:
        if kw in name or kw in cat:
            return True

    # Filament / PLA / PETG / ABS consumables (enclosure printing)
    if any(x in name for x in ("filament", " pla ", "petg", " abs ", " asa ")) and "1.75mm" in name:
        return True

    # Antennas category
    if cat == "antennas":
        return True

    # Device enclosures: electrical outdoor junction box
    if "junction box" in name and "electrical" in name and "outdoor" in name:
        return True

    # Check REMOVE - house, furniture, shop, office, personal
    for kw in REMOVE_KEYWORDS:
        if kw in name:
            return False

    # Default: when in doubt, REMOVE (user can add back from list)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Do not delete, only report")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    for p in [root.parent.parent / "WEBSITE" / "website" / ".env.local", root / ".env"]:
        if p.exists():
            for L in p.read_text(encoding="utf-8").splitlines():
                if L and not L.startswith("#") and "=" in L:
                    k, _, v = L.partition("=")
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

    url = (os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        or ""
    )
    if not url or not key:
        print("ERROR: Set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or ANON_KEY)")
        return 1

    import requests
    r = requests.get(
        f"{url}/rest/v1/components",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        params={"select": "id,name,sku,category", "order": "name.asc"},
        timeout=30,
    )
    if not r.ok:
        print(f"ERROR {r.status_code}: {r.text[:500]}")
        return 1

    rows = r.json()
    to_keep = []
    to_remove = []

    for row in rows:
        if is_bom_component(row):
            to_keep.append(row)
        else:
            to_remove.append(row)

    # Write removal list (for restoration)
    docs_dir = root / "docs"
    docs_dir.mkdir(exist_ok=True)
    report_path = docs_dir / "COMPONENTS_REMOVED_MAR07_2026.md"

    lines = [
        "# Components Removed (Non-Device BOM) — March 7, 2026",
        "",
        "These items were removed from the Supabase `components` table because they are **not** BOM for the 5 Mycosoft devices (MycoBrain, Mushroom1, SporeBase, etc.).",
        "",
        "Categories removed: house, furniture, shop tools, office equipment, personal, lab consumables.",
        "",
        "**To restore any item:** Re-add it manually or re-import from Amazon CSV with updated filters.",
        "",
        "## Removed Components",
        "",
        "| ID | Name | SKU | Category |",
        "|----|------|-----|----------|",
    ]
    for row in to_remove:
        sid = (row.get("id") or "").replace("|", "\\|")
        sname = (row.get("name") or "")[:80].replace("|", "\\|")
        ssku = (row.get("sku") or "").replace("|", "\\|")
        scat = (row.get("category") or "").replace("|", "\\|")
        lines.append(f"| {sid} | {sname} | {ssku} | {scat} |")

    lines.extend([
        "",
        f"## Summary",
        "",
        f"- **Kept:** {len(to_keep)} components (device BOM)",
        f"- **Removed:** {len(to_remove)} components",
        "",
    ])

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote removal list to {report_path}")

    if args.dry_run:
        print(f"[DRY-RUN] Would delete {len(to_remove)} rows, keep {len(to_keep)}")
        return 0

    # Delete in batches (PostgREST: id=in.(val1,val2) with quoted strings)
    ids_to_delete = [r["id"] for r in to_remove]
    if not ids_to_delete:
        print("Nothing to remove.")
        return 0

    batch_size = 30
    deleted = 0
    for i in range(0, len(ids_to_delete), batch_size):
        batch = ids_to_delete[i : i + batch_size]
        # PostgREST in filter: id=in.("id1","id2")
        in_val = ",".join(f'"{str(x).replace(chr(34), "")}"' for x in batch)
        del_r = requests.delete(
            f"{url}/rest/v1/components",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            params={"id": f"in.({in_val})"},
            timeout=30,
        )
        if del_r.ok:
            deleted += len(batch)
            print(f"Deleted batch {i // batch_size + 1} ({len(batch)} rows)")
        else:
            # Fallback: delete one by one
            for mid in batch:
                dr = requests.delete(
                    f"{url}/rest/v1/components",
                    headers={"apikey": key, "Authorization": f"Bearer {key}"},
                    params={"id": f"eq.{mid}"},
                    timeout=10,
                )
                if dr.ok:
                    deleted += 1
            print(f"Deleted via single-row fallback for batch {i // batch_size + 1}")

    print(f"Done. Kept {len(to_keep)}, removed {deleted} components.")
    return 0


if __name__ == "__main__":
    exit(main())
