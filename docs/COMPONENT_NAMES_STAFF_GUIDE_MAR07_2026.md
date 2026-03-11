# Component Names — Staff Guide

**Date:** March 7, 2026  
**Purpose:** Short, clear names for components staff need to know. No long Amazon-style titles.

---

## Name Reduction Process

**Use this process** to reduce any Amazon, vendor, or scraped title into a common name for the MycoForge inventory list. Output: 4–6 words max. Extra detail → description field.

### Step 1: Strip marketing fluff

Remove (case-insensitive):

- Parentheticals: `(Opens to 90mm)`, `(500/Pack)`, `2 Pcs`
- Compatibility clauses: `for Arduino`, `for Raspberry Pi`, `Compatible with X`
- Pack/quantity at start: `12 Packs`, `2 Pack`, `100pcs`, `5 PCS`
- Vendor SEO: `Excellent for Helium Hotspot Mining`, `Replacement for X`
- Redundant descriptors: `Rechargeable`, `with Full Size Adapter`, `Designed from Elephant Robotics`

### Step 2: Extract product type

From the title or category:

- **antennas** → Antenna (add key spec: 10dBi, 915MHz, etc.)
- **dev-boards** → Board, Module, Sensor, Kit (use model if present: ESP32-S3, BME688)
- **chassis-housing** → Box, Enclosure, Junction Box
- **power** → Cable, Battery, Charger, Adapter
- **sensors** → Sensor, Module
- **misc** → Use first meaningful noun (Filament, Cable, Screws, etc.)

### Step 3: Extract key identifiers

Keep (in order):

1. **Model numbers**: ESP32-S3, BME688, BME690, NEO-6M, OV2640, TP4056, Jetson Orin Nano
2. **Key specs**: 10dBi, 6600mAh, 15m, 915MHz, 4GB, Cat8, 1.75mm
3. **Product type** if not obvious: Antenna, Sensor, Cable, Board, Filament

### Step 4: Build common name

Format: `[Model or Type] [Product] [Key Spec]` — max 6 words.

Examples:

| Original (scraped) | Common name |
|--------------------|-------------|
| 915MHz Antenna 10dBi Gain for Meshtastic LoRa Long Range Soft Whip Antenna, 17cm | LoRa Antenna 10dBi |
| MakerHawk 3.7V 6000mAh LiPo Battery Rechargeable 1S 3C Lithium Polymer Battery w | Li-Po 6600mAh |
| 3PCS ESP32 ESP32-S3 Development Board Type-C WiFi+Bluetooth Internet of Things D | ESP32-S3 Dev Board |
| Creality ABS Filament 1.75mm Black 3D Printer Filaments, 1kg(2.2lbs) Neatly-Woun | PLA Filament 1.75mm Black |
| Cable Matters 20-Pack 23-24AWG Shielded Cat8 RJ45 Pass Through Connector with Lo | Cat8 RJ45 Connector 20-Pack |

### Step 5: Store full title in description

The original scraped/vendor title goes in `description` for ordering and search. The `name` field is the short common name only.

---

## 4–6 Words Max

**All component names: 4–6 words maximum.** Anything else → description.

---

## Soil Probe = FCI

**Soil Probe** is the staff alias. **FCI** = Fungal Computer Interface — the formal name. Same component: 2m depth sensor array (moisture, temp, pH) for Mushroom 1.

---

## Mushroom 1 — Components Staff Need

| Staff Name       | What It Is                            | Qty    | Notes                  |
|------------------|----------------------------------------|--------|------------------------|
| Solar Panels     | Monocrystalline solar cells            | 4      | 2x2 config, ~5W peak   |
| Cap Housing      | UV-resistant polycarbonate dome        | 1      | Protects sensors       |
| Status LEDs      | RGB indicators (power, network, alert) | 1 set  |                        |
| LoRa Antenna     | 915MHz mesh antenna                    | 1      | ~5km line-of-sight     |
| BME688 Sensors   | Environmental sensors (temp, humidity, gas) | 2  | Ambient + ENV          |
| ESP32-S3 Brain   | Main processor, 16MB flash             | 1      | Dual-core 240MHz       |
| Li-Po Battery    | 3.7V 6600mAh                           | 1      | Rechargeable           |
| Stem Housing     | IP67 weatherproof enclosure            | 1      | Electronics protection |
| Quadruped Legs   | 4 articulated walking legs             | 1 set  | Carbon fiber           |
| Soil Probe (FCI) | 2m depth sensor array                  | 1      | Moisture, temp, pH     |

**Pre-order “What You Get” (customer-facing):** 1x unit, 2m soil probe (FCI) array, 4x solar panels, 6600mAh Li-Po battery, quadruped walking system.

---

## SporeBase — Components Staff Need

| Staff Name         | What It Is                            | Notes                           |
|--------------------|----------------------------------------|---------------------------------|
| Air Intake         | Protected sampling inlet               | Fan-driven particle collection  |
| Tape Cassette      | Sealed time-indexed collection         | 15-min intervals, 30-day tape   |
| Sampling Fan       | Fan-driven active sampling             | PWM + tachometer feedback       |
| Tape Drive         | Stepper motor tape advance             | Precise ΔL per advance          |
| Environmental Sensors | BME688/BME690 + optional BMV080    | Temp, humidity, pressure, VOC   |
| MycoBrain Controller | Dual ESP32-S3 + LoRa                  | MPPT solar, I2C expansion       |
| Solar + Battery    | MPPT solar charging                    | 30-day autonomous operation     |
| Universal Mount    | IP65 weatherproof enclosure            | Buildings, poles, vehicles      |

---

## ALARM — Components Staff Need

| Staff Name     | What It Is                      | Notes                               |
|----------------|----------------------------------|-------------------------------------|
| Dual Smoke Sensors | Ionization + Photoelectric    | Fast + smoldering fire detection    |
| VOC Sensor     | Volatile organic compound detection | Formaldehyde, benzene, etc.     |
| Particulate Sensor | PM1.0 / PM2.5 / PM10           | Laser-scattering, AQI               |
| Mold Spore Detector | Bioaerosol density estimation | Early mold warning                  |
| Climate Sensors | BME688 temp, humidity, pressure | ±0.5°C, ±3% RH                     |
| CO₂ Sensor     | NDIR carbon dioxide 400–5000 ppm | Ventilation alerts                 |
| ESP32-S3 + TinyML | Edge AI for pattern recognition | Reduces false alarms               |
| Alert System   | 85dB siren + RGB LED ring        | Voice alerts, status colors         |

---

## MycoNODE — Components Staff Need

| Staff Name      | What It Is                      | Notes                           |
|-----------------|----------------------------------|---------------------------------|
| Bioelectric Electrodes | Platinum-iridium array     | 0.1μV resolution               |
| Soil Moisture Sensor | Capacitive multi-depth     | FDR, salinity immune           |
| Temperature Array | Platinum RTD sensors       | ±0.1°C, surface to 50cm        |
| EC Sensor       | Electrical conductivity         | 0–20 dS/m, temp compensated    |
| pH Probe        | Solid-state ISFET              | Maintenance-free, buried use   |
| ESP32-S3 Core   | Edge processing with ML         | TinyML pattern recognition     |
| LoRa Radio      | Long-range mesh                 | ~10km, AES-256                 |
| Battery System  | 90+ day rechargeable            | Solar option, -40°C to 85°C    |

---

## Hypha 1 — Components Staff Need

| Staff Name   | What It Is                        | Notes                            |
|--------------|------------------------------------|----------------------------------|
| IP66 Enclosure | Fiberglass-reinforced polymer   | UV-stable, white or grey         |
| Terminal Block | Modular connection 4–16 channels | 2A/terminal, 22–12 AWG          |
| Control Module | ESP32-S3 + RS-485               | Modbus RTU/TCP, SCADA/BMS       |
| Power Supply | 24V DC / 120–240V AC              | Optional battery backup          |
| I/O Expansion | Analog + digital cards          | 4–20mA, 0–10V, relays            |
| Communications | Ethernet, LoRa, WiFi, LTE       | Hardwired or wireless            |
| DIN Rail Mount | 35mm standard                    | Panel, wall, pole kits           |
| Status Display | LED indicators + optional LCD   | Power, network, alarms           |

---

## Supabase ID → Simplified Name (Mycosoft Parts)

| Component ID     | Simplified Name        | Device(s)   | Category   |
|------------------|------------------------|-------------|------------|
| c1772753572559   | Mycobrain V1           | Mushroom 1  | dev-boards |
| c1772767020653   | ESP32-S3               | Mushroom 1  | dev-boards |
| c1772757965488   | BME688                 | Mushroom 1  | sensors    |
| c1772757984324   | BME680                 | Various     | sensors    |
| c1772754630521   | BME690                 | Mushroom 1  | sensors    |
| c1772756414292   | Solar Controller       | Mushroom 1  | power      |
| c1772756665580   | Mushroom 1 Big Body    | Mushroom 1  | chassis    |
| c1772756491478   | White Box Chassis      | Various     | chassis    |
| c1772756532326   | Medium Grey Box        | Various     | chassis    |
| c1772756572006   | Small Grey Box         | Various     | chassis    |
| c1772765873359   | Jetson Orin Nano 8GB   | Mushroom 1 (big) | dev-boards |

---

## Amazon/Third-Party Parts — Simplified Names

Use these when talking to staff or in build docs. Original SKU/ID kept for ordering.

| Simplified Name   | Original (truncated)                  | Category   | Used In     |
|-------------------|--------------------------------------|------------|-------------|
| LoRa Antenna 13dBi| 915MHz Yagi LoRa Antenna…            | antennas   | Mushroom 1  |
| LoRa Antenna 10dBi| 915MHz 10dBi Soft Whip…              | antennas   | Mushroom 1  |
| LoRa Antenna 3dBi | 915MHz LoRa Indoor 3dBi Omni…        | antennas   | Mushroom 1  |
| BME688 Sensor     | BME688 Environmental Sensor…         | dev-boards | Mushroom 1  |
| ESP32-S3 Dev Kit  | ESP32-S3 Development Board…          | dev-boards | Mushroom 1  |
| Li-Po 6600mAh     | MakerHawk 3.7V 6000mAh LiPo…         | dev-boards | Mushroom 1  |
| Li-Po 10000mAh    | MakerHawk 3.7V 10000mAh LiPo…        | dev-boards | Extended    |
| SMA to N Cable    | SMA to N Cable 15m RG58…             | antennas   | Antenna run |

---

## Devices Enforced (Canonical Registry)

All 5 devices live in `WEBSITE/website/lib/device-products.ts` and sync to Supabase:

| Device    | Product IDs (examples) |
|-----------|------------------------|
| Mushroom 1 | mushroom1-mini, mushroom1-standard, mushroom1-large, mushroom1-defense |
| SporeBase | sporebase |
| ALARM     | alarm |
| MycoNODE  | myconode-white, myconode-black, etc. (9 colors) |
| Hypha 1   | hypha1-compact, hypha1-standard, hypha1-industrial |

**Soil Probe (FCI)** — Component of Mushroom 1; add to Supabase `components` when BOM is finalized.

---

## What’s Missing / Unclear

1. **BOM for canonical products** — Supabase `bom_items` only links legacy product `p1772752271359`. No links for `mushroom1-mini`, `mushroom1-standard`, etc.
2. **SporeBase, ALARM, MycoNODE, Hypha 1** — Component lists from website device pages. Supabase BOM/component links may be missing; **hardware team to work on components**.
3. **Long Amazon titles in DB** — 185 components; many vendor marketing text. Use `scripts/update_component_names_for_staff.py` to apply staff names (4–6 words max).
4. **Soil Probe (FCI)** — Not in Supabase components. Add when BOM finalized; alias: FCI = Fungal Computer Interface.

---

## Source Files (Website)

| Device    | File                                      |
|-----------|-------------------------------------------|
| Mushroom 1| `components/devices/mushroom1-details.tsx` |
| SporeBase | `components/devices/sporebase-details.tsx` |
| ALARM     | `components/devices/alarm-details.tsx`     |
| MycoNODE  | `components/devices/myconode-details.tsx`  |
| Hypha 1   | `components/devices/hyphae1-details.tsx`   |

---

## Quick Reference — Staff Naming Rules

- **4–6 words max.** Anything else → description.
- **Short:** “LoRa Antenna 10dBi” not “915MHz Antenna 10dBi Gain for Meshtastic LoRa Long Range…”
- **Accurate:** Include key spec if needed (e.g. 6600mAh, 4x, 2m).
- **Consistent:** Same part = same name across devices and docs.
- **Device prefix when helpful:** “Mushroom 1 Cap” vs “MycoNODE Cap” if both exist.
---

## Sync to Master Google Sheet (Required)

After **any** inventory or name change, sync the master sheet:

`ash
python scripts/sync_components_to_google_sheets.py
# Then either --push (if you have credentials) or paste the CSV manually
`

**Master sheet tab:** https://docs.google.com/spreadsheets/d/1rhuGmyxZakCVet1zMK3_C2f3SCOzH_dr6HH6EKWGRmc/edit?gid=1289530278#gid=1289530278

See `docs/INVENTORY_GOOGLE_SHEETS_SYNC_MAR07_2026.md` for full instructions.
