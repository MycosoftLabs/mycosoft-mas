#!/usr/bin/env python3
"""Reduce MycoForge component names to 4-6 word common names.

Implements the Name Reduction Process from docs/COMPONENT_NAMES_STAFF_GUIDE_MAR07_2026.md:
1. Strip marketing fluff (parentheticals, "for X", "Pack of N", etc.)
2. Extract product type from category
3. Extract model numbers and key specs
4. Build common name: [Model/Type] [Product] [Key Spec] — max 6 words
5. Store original in description for ordering/search

Run: python scripts/update_component_names_for_staff.py [--dry-run]
Requires: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY)
"""
import argparse
import os
import re

try:
    from supabase import create_client
except ImportError:
    print("pip install supabase")
    raise SystemExit(1)

PROJECT_REF = "hnevnsxnhfibhbsipqvz"
MAX_WORDS = 5  # Stricter: 4-5 words for cleaner lists

def _trim(s: str, max_w: int = MAX_WORDS) -> str:
    """Enforce max word count on any result."""
    words = s.split()
    if len(words) <= max_w:
        return s
    return " ".join(words[:max_w])

# Explicit overrides: component_id -> short name (use when reduction process misses)
STAFF_NAME_OVERRIDES = {
    "c1772753572559": "Mycobrain V1",
    "c1772767020653": "ESP32-S3",
    "c1772757965488": "BME688",
    "c1772757984324": "BME680",
    "c1772754630521": "BME690",
    "c1772756414292": "Solar Controller",
    "c1772756665580": "Mushroom 1 Big Body",
    "c1772756491478": "White Box Chassis",
    "c1772756532326": "Medium Grey Box",
    "c1772756572006": "Small Grey Box",
    "c1772765873359": "Jetson Orin Nano 8GB",
    "B01FV1DD9C": "LoRa Antenna 13dBi",
    "B0DB5MH38T": "LoRa Antenna 10dBi",
    "B0CTXL61LY": "LoRa Antenna 3dBi",
    "B0BZ4WV4PQ": "BME688 Sensor",
    "B0C9H7Y66W": "ESP32-S3 Dev Kit",
    "B0D3LP1G3F": "Li-Po 6600mAh",
    "B0DP634VQ5": "Li-Po 10000mAh",
    "B01FVWCKKE": "SMA to N Cable 15m",
    "B099RQ7BSR": "LILYGO T-SIM7000G",
    "B0D9JWT4P1": "E-Ink E290 Dev Board",
    "B0DNZ3ZD36": "OV2640 ESP32-CAM",
    "B0D56GV4X1": "AMD Mini PC Ryzen",
    "B08TJRVWV1": "256GB Micro SD Card",
    "B01EV70C78": "Dupont Wire 40pin",
    "B0D8T53CQ5": "ESP32 Dev Board",
    "B0B9W96SD6": "myCobot 280 Robotic Arm",
    "B0CRNPBGNB": "Beelink Mini PC",
    "B0CLLNMRX7": "LILYGO T-A7670G 4G",
    "B0DGGFFY8K": "GPS Galileo Tracker",
    "B0CQT9J4K8": "GPS Galileo Tracker",
    "B0FQ5XWXMG": "Jetson Orin NX",
    "B0DF4TB93J": "Soil Moisture Meter",
    "B0CGR8ZLTZ": "Bare Copper Wire 20ga",
    "B08FM9334M": "Centrifuge Tubes 15mL",
    "B0CS69N2Z6": "Anker USB-C Hub",
    "B08VNB7MVQ": "Storage Cabinet 16 Drawer",
    "B0CNH8H6NG": "5\" Round LCD 1080p",
    "B072PCQ2LW": "Heat Shrink Tubing",
    "B0CQXMPXKC": "8 Port 10G Switch",
    "B0DDQDG6GF": "Anker TB4 Cable 3.3ft",
    "B0CDH4FGZY": "Anker TB4 Cable",
    "B0BM26L46T": "Wire Spool Rack",
    "B098QH631G": "SMA to IPX Cable",
    "B0BZ4WV4PQ": "BME688 Sensor",
    "B0CNSSS6T4": "18650 Shield Board",
    "B083XMGSVP": "Pi Zero Camera 5MP",
    "B0DKSS4K6N": "LoRa Antenna 915MHz",
    "B0DMK4QPPD": "LoRa Antenna Magnetic",
    "B0CJM767KB": "T-SIM7000G ESP32",
    "B0CJ9C4FFH": "ESP32 Case 5-in-1",
    "B0DWPKQ3LH": "HP 15.6 Laptop",
    "B0DJ7GNDL8": "Digital Calendar",
    "B0BY3GTG48": "NZXT Kraken 360 AIO",
    "B0DLKLY669": "Mini Speaker 8 Ohm",
}

# Model/spec patterns (order matters: more specific first)
MODEL_PATTERNS = [
    r"ESP32-S3(?:-DevKitC|-DevKit)?",
    r"ESP32-WROVER-B",
    r"ESP32-S3",
    r"ESP32",
    r"BME69[08]",
    r"BME688",
    r"BME680",
    r"NEO-6M",
    r"OV2640",
    r"OV5647",
    r"TP4056",
    r"TP4057",
    r"Jetson Orin Nano",
    r"Jetson Nano",
    r"SX1278",
    r"SX1262",
    r"SIM7600G-H",
    r"T-SIM7000G",
    r"T-BeamSUPREME",
    r"T-Echo",
    r"T-Deck Plus",
    r"T-A7670G",
    r"SenseCAP T1000-E",
    r"AS3935",
    r"INA333",
    r"INA128",
    r"AD620",
    r"GC2145",
    r"TF-Luna",
    r"MyoWare 2\.0",
    r"WS2812B",
    r"TCRT5000",
    r"TTP223",
]

# Spec patterns: 10dBi, 6600mAh, 15m, 915MHz, 1.75mm, etc.
SPEC_PATTERNS = [
    (r"\b(\d+(?:\.\d+)?)\s*dBi\b", r"\1dBi"),
    (r"\b(\d+)\s*mAh\b", r"\1mAh"),
    (r"\b(\d+)\s*[mM](?:\s|$|eter)", r"\1m"),
    (r"\b(\d+)\s*[fF]t\b", r"\1ft"),
    (r"\b915\s*MHz\b", "915MHz"),
    (r"\b(\d+)\s*[gG]B\b", r"\1GB"),
    (r"\b1\.75\s*mm\b", "1.75mm"),
    (r"\b(\d+)\s*[pP]ack\b", r"\1-Pack"),
    (r"\bCat\s*8\b", "Cat8"),
    (r"\bIP67\b", "IP67"),
    (r"\bUHS-I\s*U3\b", "U3"),
]

# Strip patterns (remove from title)
STRIP_PATTERNS = [
    r"\s*\([^)]*\)\s*",
    r"\bfor\s+(?:Arduino|Raspberry Pi|Helium|Meshtastic|Heltec)[^,]*",
    r"\bCompatible\s+with[^,]*",
    r"\b(?:Excellent|Ideal|Perfect)\s+for[^,]*",
    r"\b(?:2|3|4|5|6|8|10|12|100)\s*(?:Pcs?|Pack|Pack of|pcs?)\b",
    r"\bDesigned\s+from[^,]*",
    r"\bReplacement\s+for[^,]*",
    r"\bwith\s+Full\s+Size\s+Adapter\b",
    r"\bRechargeable\b",
    r"\bOpens\s+to\s+\d+mm\b",
    r",\s*[^,]*(?:Drone|Camera|Action Camera)[^,]*",
    r"\bw\s*$",  # trailing "w" from truncated titles
]

CATEGORY_TYPE_MAP = {
    "antennas": "Antenna",
    "dev-boards": "Board",
    "chassis-housing": "Enclosure",
    "power": None,  # infer from content
    "sensors": "Sensor",
    "cameras": "Camera",
    "misc": None,
}


def _strip_fluff(text: str) -> str:
    """Step 1: Remove marketing fluff."""
    t = text
    for pat in STRIP_PATTERNS:
        t = re.sub(pat, " ", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _extract_model(text: str) -> str | None:
    """Extract first matching model/identifier."""
    for pat in MODEL_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(0)
    return None


def _extract_specs(text: str) -> list[str]:
    """Extract key specs (dBi, mAh, length, etc.)."""
    specs = []
    if re.search(r"\d+\s*dBi", text, re.I):
        m = re.search(r"(\d+(?:\.\d+)?)\s*dBi", text, re.I)
        if m:
            specs.append(f"{m.group(1)}dBi")
    if re.search(r"\d+\s*mAh", text, re.I):
        m = re.search(r"(\d+)\s*mAh", text, re.I)
        if m:
            specs.append(f"{m.group(1)}mAh")
    if re.search(r"\d+\s*[mM](?:\s|$|eter)", text):
        m = re.search(r"(\d+)\s*[mM](?:\s|$|eter)", text)
        if m:
            specs.append(f"{m.group(1)}m")
    if re.search(r"1\.75\s*mm", text):
        specs.append("1.75mm")
    if re.search(r"Cat\s*8", text, re.I):
        specs.append("Cat8")
    if re.search(r"(\d+)\s*[pP]ack", text):
        m = re.search(r"(\d+)\s*[pP]ack", text)
        if m:
            specs.append(f"{m.group(1)}-Pack")
    # Filament type
    if re.search(r"\bPLA\b", text):
        specs.append("PLA")
    elif re.search(r"\bABS\b", text):
        specs.append("ABS")
    elif re.search(r"\bPETG\b", text):
        specs.append("PETG")
    elif re.search(r"\bASA\b", text):
        specs.append("ASA")
    return specs[:2]  # max 2 specs


def _extract_product_type(text: str, category: str) -> str:
    """Infer product type from text and category."""
    t = text.lower()
    c = (category or "").lower()
    if "antenna" in t or c == "antennas":
        return "Antenna"
    if "battery" in t or "lipo" in t or "lipolymer" in t:
        return "Li-Po"
    if "cable" in t or "ethernet" in t:
        return "Cable"
    if "filament" in t:
        return "Filament"
    if "sensor" in t or c == "sensors":
        return "Sensor"
    if "enclosure" in t or "junction box" in t or "chassis" in t:
        return "Enclosure"
    if "esp32" in t:
        return "ESP32"
    if "bme68" in t or "bme69" in t:
        return "BME"
    if "connector" in t or "keystone" in t:
        return "Connector"
    if "screen" in t or "display" in t or "lcd" in t:
        return "Display"
    if "charger" in t or "charging" in t:
        return "Charger"
    if c == "dev-boards":
        return "Board"
    if c == "chassis-housing":
        return "Enclosure"
    if c == "power":
        return "Power"
    return ""


def reduce_to_common_name(title: str, category: str = "") -> str:
    """Reduce any Amazon/vendor title to 4-6 word common name."""
    if not title or not title.strip():
        return title
    original = title.strip()
    t = _strip_fluff(original)

    model = _extract_model(t)
    specs = _extract_specs(t)
    ptype = _extract_product_type(t, category)

    parts = []

    # Antennas: LoRa Antenna XdBi, GNSS Antenna, etc. (skip when dev-boards - e.g. LILYGO has "antenna" in desc)
    if category == "antennas" or ("antenna" in t.lower() and category != "dev-boards"):
        if "lora" in t.lower() or "915" in t.lower():
            parts.append("LoRa")
        elif "gnss" in t.lower() or "gps" in t.lower():
            parts.append("GNSS")
        elif "4g" in t.lower() or "lte" in t.lower():
            parts.append("4G LTE")
        elif "wifi" in t.lower():
            parts.append("WiFi")
        parts.append("Antenna")
        for s in specs:
            if "dBi" in s and s not in parts:
                parts.append(s)
                break
        if not any("dBi" in str(p) for p in parts) and "cable" in t.lower():
            if "sma" in t.lower() and "n " in t.lower():
                parts = ["SMA to N", "Cable"]
            for s in specs:
                if "m" in s and s not in parts:
                    parts.append(s)
                    break
        if parts:
            return _trim(" ".join(str(p) for p in parts))

    # Batteries: Li-Po XmAh
    if "lipo" in t.lower() or "lipolymer" in t.lower() or "lithium polymer" in t.lower():
        parts = ["Li-Po"]
        for s in specs:
            if "mAh" in s:
                parts.append(s)
                break
        if parts:
            return _trim(" ".join(parts))

    # Boards: ESP32-S3, BME688, Jetson, etc.
    if model:
        if "ESP32" in model:
            parts.append("ESP32-S3" if "S3" in model else "ESP32")
            if "dev" in t.lower() or "development" in t.lower():
                parts.append("Dev Board")
            else:
                parts.append("Board")
        elif "BME" in model:
            parts.append(model)
            parts.append("Sensor")
        elif "Jetson" in model:
            parts.append(model)
        elif "TP405" in model:
            parts.extend([model, "Charger"])
        else:
            parts.append(model)
        if parts:
            return _trim(" ".join(str(p) for p in parts))

    # Filaments: PLA/ABS/PETG Filament 1.75mm Color
    if "filament" in t.lower():
        for mat in ["PLA", "ABS", "PETG", "ASA", "PLA+"]:
            if mat.lower() in t.lower():
                parts.append(mat)
                break
        parts.append("Filament")
        if "1.75" in t or "1.75mm" in t:
            parts.append("1.75mm")
        for c in ["Black", "White"]:
            if c.lower() in t.lower():
                parts.append(c)
                break
        if parts:
            return _trim(" ".join(parts))

    # Cables: Type + length
    if "cable" in t.lower() or "ethernet" in t.lower():
        if "cat8" in t.lower() or "cat 8" in t.lower():
            parts.append("Cat8")
        if "ethernet" in t.lower():
            parts.append("Ethernet")
        parts.append("Cable")
        for s in specs:
            if "m" in s or "ft" in s:
                parts.append(s)
                break
        if parts:
            return _trim(" ".join(parts))

    # Connectors, enclosures, misc
    if "rj45" in t.lower() or "keystone" in t.lower():
        parts = ["Cat8 RJ45 Connector"] if "cat" in t.lower() else ["RJ45 Connector"]
        for s in specs:
            if "Pack" in s:
                parts.append(s)
                break
        return _trim(" ".join(parts))

    if "junction box" in t.lower() or "enclosure" in t.lower() or "chassis" in t.lower() or ("box" in t.lower() and category == "chassis-housing"):
        size = ""
        if "large" in t.lower() or "medium" in t.lower():
            size = "Medium" if "medium" in t.lower() else "Large"
        elif "small" in t.lower():
            size = "Small"
        wb = "White" if "white" in t.lower() else "Grey" if "grey" in t.lower() or "gray" in t.lower() else ""
        label = "Junction Box" if "junction" in t.lower() else ("Box Chassis" if "chassis" in t.lower() else "Box")
        parts = [p for p in [size, wb, label] if p]
        return _trim(" ".join(parts)) if parts else "Box"

    # Sensors
    if ptype == "Sensor":
        parts.append(model or "Sensor")
        if model:
            parts.append("Sensor")
        return _trim(" ".join(parts)) if parts else "Sensor"

    # Fallback: first meaningful words, max 5
    skip = {"the", "a", "an", "with", "for", "and", "or", "pack", "pcs", "pc", "replacement", "compatible", "excellent", "ideal"}
    words = []
    for w in t.split():
        if w.lower() not in skip and len(words) < MAX_WORDS:
            words.append(w)
    return _trim(" ".join(words)) if words else _trim(original[:60])


def get_supabase():
    url = os.environ.get("SUPABASE_URL") or f"https://{PROJECT_REF}.supabase.co"
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not key:
        raise SystemExit("Set SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY")
    return create_client(url, key)


def main():
    ap = argparse.ArgumentParser(
        description="Reduce all MycoForge component names to 4-6 word common names"
    )
    ap.add_argument("--dry-run", action="store_true", help="Print changes only, no DB update")
    ap.add_argument(
        "--from-dump",
        action="store_true",
        help="Read from scripts/_components_output.txt instead of Supabase (for testing)",
    )
    ap.add_argument(
        "--output-sql",
        action="store_true",
        help="Print SQL UPDATE statements instead of applying (use with --from-dump)",
    )
    args = ap.parse_args()

    if args.from_dump:
        dump_path = os.path.join(os.path.dirname(__file__), "_components_output.txt")
        rows = []
        with open(dump_path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip().replace("\ufeff", "")
                if not line or line.startswith("---"):
                    continue
                parts = line.split("|", 2)
                if len(parts) >= 3:
                    rows.append({"id": parts[0], "name": parts[1], "category": parts[2], "description": ""})
    else:
        sb = get_supabase()
        r = sb.table("components").select("id, name, category, description").execute()
        rows = r.data or []

    updates = []
    for row in rows:
        cid = row.get("id")
        name = (row.get("name") or "").strip()
        category = row.get("category") or ""
        desc = row.get("description") or ""

        # Use override if defined
        if cid in STAFF_NAME_OVERRIDES:
            short = STAFF_NAME_OVERRIDES[cid]
        else:
            short = reduce_to_common_name(name, category)

        # Skip if already short enough and unchanged
        words = short.split()
        if len(words) <= MAX_WORDS and short != name:
            updates.append((cid, name, short, desc))

    if args.dry_run or args.from_dump:
        mode = "FROM DUMP" if args.from_dump else "DRY RUN"
        if args.output_sql:
            def esc(s):
                return (s or "").replace("\\", "\\\\").replace("'", "''")
            print("-- MycoForge component name reduction")
            for cid, old_name, short_name, _ in updates:
                print(f"UPDATE components SET name = '{esc(short_name)}', description = '{esc(old_name)}' WHERE id = '{esc(cid)}';")
            print(f"-- {len(updates)} rows")
            return
        print(f"{mode} - no database updates\n")
        print(f"{'ID':<20} {'CURRENT':<55} -> {'SHORT':<30}")
        print("-" * 120)
        for cid, old, new, _ in updates[:80]:
            old_d = old[:52] + ".." if len(old) > 54 else old
            try:
                print(f"{cid:<20} {old_d:<55} -> {new:<30}")
            except UnicodeEncodeError:
                print(f"{cid:<20} {old_d.encode('ascii','replace').decode():<55} -> {new.encode('ascii','replace').decode():<30}")
        if len(updates) > 80:
            print(f"... and {len(updates) - 80} more")
        print(f"\nWould update {len(updates)} components.")
        return

    updated = 0
    errors = []
    for cid, old_name, short_name, desc in updates:
        try:
            payload = {"name": short_name}
            if not desc or len(desc) < len(old_name):
                payload["description"] = old_name
            sb.table("components").update(payload).eq("id", cid).execute()
            updated += 1
            print(f"  {cid} -> {short_name}")
        except Exception as e:
            errors.append((cid, str(e)))

    print(f"\nUpdated {updated} components.")
    if errors:
        print("Errors:")
        for cid, msg in errors:
            print(f"  {cid}: {msg}")


if __name__ == "__main__":
    main()
