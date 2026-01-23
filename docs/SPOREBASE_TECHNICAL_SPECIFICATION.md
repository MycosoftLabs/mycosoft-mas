# SporeBase™ Technical Specification

**Version:** 3.0 (V3/V4)  
**Last Updated:** January 22, 2026  
**Status:** Official Technical Reference

---

## Document Purpose

This document serves as the **single source of truth** for SporeBase technical specifications across all Mycosoft projects:

- **Website** (`mycosoft.com`)
- **MINDEX** (data indexing and chain-of-custody)
- **NatureOS** (visualization and fleet operations)
- **MycoBrain** (embedded controller firmware)
- **Firmware** (ESP32-S3 device firmware)

All teams working with SporeBase—via MycoNode, Hyphae1, Mushroom1, or direct integration—must reference this document.

---

## Overview

**SporeBase™ is a time-indexed bioaerosol collection instrument** built to make airborne biology measurable at scale—spores, pollen, dust/particulates, and other microscopic material—while simultaneously logging environmental context (air chemistry, humidity, temperature, and location metadata) so samples can be interpreted correctly.

Unlike "snapshot" sampling that loses temporal context, SporeBase advances a **sealed adhesive-tape sampling cassette** on a fixed schedule (default **every 15 minutes for 30 days**) to create a chronological, lab-ready record that can be processed by microscopy, qPCR, or sequencing.

SporeBase is designed to operate as a stand-alone field unit or as a networked node in Mycosoft's broader Environmental Intelligence stack—using **Mycorrhizae Protocol + MINDEX** for secure data formatting, timestamping, and chain-of-custody, with visualization and fleet operations through **NatureOS**.

---

## ⚠️ IMPORTANT: Inaccurate Claims to Remove

### These claims are INCORRECT for the current system:

| Incorrect Claim | Why It's Wrong |
|----------------|----------------|
| "100 LPM precision pump" | Current system uses fan-based deposition, not a pump |
| "Multi-stage filtration" | No multi-stage filter stack in current design |
| "99.7% to 0.3 µm efficiency" | This spec is for HEPA filters, not tape deposition |
| "24 time-indexed slots" | Actual: 2,880 intervals per cassette (30 days × 24 hrs × 4/hr) |
| "20cm × 15cm × 40cm" | Actual: ~194 × 149 × 53 mm from V3 CAD |

### Replace with accurate statements:

- **Active, fan-driven sampling:** SporeBase uses a controlled fan to pull ambient air across a protected sampling path where particles deposit onto adhesive tape (not a multi-stage filter stack).
- **Time-indexed samples (true chronological tape record):** A single cassette creates **2,880 timestamped collection intervals** (30 days × 24 hours/day × 4 per hour) at the default 15-minute cadence.
- **Lab-ready cassette workflow:** The cassette is sealed for transport, and the tape is designed for downstream lab workflows (microscopy, qPCR, sequencing, and archive storage).

---

## System Architecture

### Role in the Mycosoft Stack

SporeBase is positioned as an **airborne biological collector** within the Nature Compute / OEI system, alongside:

- **MycoNode** - Underground fungal network monitoring
- **ALARM** - Environmental alerting system  
- **Mushroom1** - Cultivation monitoring
- **Hyphae1** - Mycelium growth tracking

### Core Value Proposition

SporeBase produces:

1. **(A) Physical, time-indexed biological samples** - Sealed tape cassettes
2. **(B) Synchronized environmental telemetry** - Sensor data normalized via Mycorrhizae Protocol

Sample metadata is stored with **MINDEX** for tamper-evident recordkeeping and chain-of-custody, then visualized via **NatureOS**.

---

## How SporeBase Works

### Sampling Cycle (Default Configuration)

**Default schedule:** every **15 minutes** for **30 days**

Each cycle performs:

1. **Wake / power-up**
2. **Record telemetry** (environment + device status + optional GNSS)
3. **Active intake** (fan-driven airflow across sampling head)
4. **Tape advance** to expose fresh collection surface
5. **Seal/park** tape segment inside cassette
6. **Log sample index** locally and (if connected) transmit a compact record

**Total intervals per cassette:**

```
30 days × 24 hours/day × 4 intervals/hour = 2,880 time-indexed deposits
```

### Time Indexing Model

SporeBase creates a **continuous timeline**, like a ruler:

- Each interval corresponds to a fixed tape advance distance (ΔL)
- Hour/day markers can be printed onto tape or encoded as periodic "marker advances"
- Sample metadata includes:
  - Cassette ID
  - Tape index (0–2879)
  - Start/end timestamp
  - Telemetry snapshot (or reference hash to telemetry block)

### Dual-Lane "A/B" Tape (Recommended Design)

To support **simultaneous lab analysis + archival preservation**, SporeBase should produce two equivalent sample lanes:

- **Lane A:** sent to lab
- **Lane B:** sealed and archived (cold storage or long-term)

Implementation options:

1. **Single wide tape split into two lanes** via internal slitter + parallel take-up
2. **Two narrow tapes** advanced in lockstep from a dual-supply cassette

---

## Mechanical Architecture

### Enclosure Dimensions (V3 CAD-Derived)

From the **SporeBase_V3 STEP** file, the *Body_V3* bounding dimensions are:

```
~194 mm (W) × 149 mm (H) × 53 mm (D)
```

### Internal Layout (Functional Zones)

| Zone | Description |
|------|-------------|
| **Air Intake & Sampling Head** | Inlet guard + sampling channel + tape exposure window |
| **Tape Cassette Module** | Supply, take-up, seal path, desiccant bay |
| **Drive System** | Stepper/DC motor + gear train + tension control |
| **Electronics Bay** | MycoBrain + sensor daughterboards + storage + power |

### Outdoor Hardening (IP65 Design Targets)

- Continuous perimeter **gasket** with defined compression
- **Hydrophobic vent membrane** for pressure equalization (no open vents)
- Sealed fastener strategy (bosses + screws + washers)
- Conformal coating on electronics (field version)
- Strain relief / sealed cable glands for external leads

---

## Electronics & Compute

### MycoBrain Controller

The MycoBrain schematic provides:

| Component | Description |
|-----------|-------------|
| **Compute** | Dual ESP32-S3 modules (ESP32-S3-WROOM-1U variants) |
| **Radio** | LoRa module (CORE1262-868M) |
| **Power** | MPPT Li-ion solar charger (CN3903) + battery/solar terminals |
| **Outputs** | OUT_1, OUT_2, OUT_3... for driving actuators |
| **Analog Inputs** | AIN_1–AIN_4 for sensing/diagnostics |
| **Connectivity** | USB-C ports for power/programming/service |
| **Expansion** | I2C connectors for sensor daughterboards |

### Actuators

SporeBase requires two actuator channels:

| Channel | Purpose |
|---------|---------|
| **Fan Control** | PWM + tach recommended for repeatability |
| **Tape Advance Motor** | Stepper preferred for deterministic indexing |

Optional: heater or dehumidifier for tape preservation

### Sensor Payload

**Baseline (Recommended):**

- Temperature / humidity / barometric pressure
- VOC / gas sensing (**Bosch BME69x family** - BME688/BME690)
- Particulate proxy (**Bosch BMV080**) for PM correlation
- Device health: battery voltage, internal temp, fan tach, motor current

**Optional Add-ons:**

- GNSS (location + time discipline)
- CO₂ (indoor air quality and ecology correlation)
- IMU (movement/shock logging for mobile deployments)
- External sensor port (I2C/UART) for add-on probes

### Data Storage

- **microSD storage** (user-selectable; 32–256 GB typical)
- Stores:
  - Telemetry time series
  - Sample index ledger (cassette ID + interval index + hashes)

---

## Connectivity & Networking

### Current Capabilities

| Technology | Status |
|------------|--------|
| **LoRa** | Core - DTN/store-and-forward |
| **Wi-Fi Mesh** | Fallback networking |
| **Cellular (LTE/CAT-M1/NB-IoT)** | Optional by SKU |

### Range Statement

> **DO NOT hardcode specific range claims (e.g., "5 miles")**

Safe website language:

> "Long-range LoRa connectivity with mesh / store-and-forward networking; range depends on terrain, antenna placement, and gateway density."

### Data Format & Integrity

- **Mycorrhizae Protocol** normalizes sensor records into compact binary payloads
- **MINDEX** provides tamper-evident records and chain-of-custody

---

## Tape & Adhesive System

### Engineering Requirements

| Requirement | Description |
|-------------|-------------|
| **Capture efficiency** | Broad particle size distribution (spores/pollen/dust) |
| **Low outgassing** | Doesn't affect VOC readings or downstream sequencing |
| **Stable adhesion** | Temperature swings + humidity over 30 days |
| **Preservation behavior** | Discourage growth without destroying DNA/RNA targets |
| **Extraction compatibility** | Swabbing, solvent elution, or direct tape-to-slide transfer |
| **Manufacturability** | Consistent width/thickness, roll stability, no adhesive creep |

### Candidate Tape Categories

- Acrylic adhesive films (stable, strong capture)
- Silicone adhesives (cleaner release)
- Microstructured collection surfaces (textured films)
- Hybrid "capture + preservation" laminates

### Validation Protocol

1. **Capture bench test** in controlled chamber
2. **Aging test**: 30-day exposure with thermal/humidity cycling
3. **Downstream compatibility**: microscopy clarity, qPCR inhibition, extraction yield
4. **Preservation test**: viability/growth vs inertness
5. **Field correlation**: compare tape signal vs BMV080 PM + humidity + wind

---

## Official Specification Sheet

### SporeBase™ Technical Details (V3/V4)

| Specification | Value |
|---------------|-------|
| **Sampling Method** | Fan-driven active deposition onto adhesive tape |
| **Time Indexing** | 15-minute intervals (configurable), 30-day cassette (default) |
| **Intervals Per Cassette** | **2,880** (30×24×4) |
| **Sample Format** | Sealed tape cassette; optional dual-lane A/B for lab + archive |
| **Environmental Sensors** | Modular: gas/VOC + T/RH/pressure baseline; PM + CO₂ + GNSS optional |
| **Compute** | MycoBrain (ESP32-S3 + LoRa; actuator outputs; I2C expansion; MPPT solar) |
| **Connectivity** | LoRa DTN/store-and-forward; Wi-Fi mesh fallback; cellular optional |
| **Storage** | microSD (32–256 GB typical) |
| **Weather Rating** | IP65 design target |
| **Operating Temperature** | −10°C to +50°C |
| **Dimensions** | ~194 × 149 × 53 mm |
| **Weight** | TBD (target < 1 kg) |

---

## Product SKUs

### SporeBase Indoor/Lab ($299–$399 MSRP Target)

- No solar kit, minimal sealing
- Wi-Fi provisioning + optional LoRa
- Smaller battery (multi-week duty cycle)
- Core environmental sensors + tape cassette

### SporeBase Field/Rugged ($499–$799 MSRP Target)

- Full gasket + vent membrane + UV-stable enclosure
- LoRa DTN standard, optional cellular add-on
- Larger battery + solar-ready MPPT
- Expanded sensor payload (PM + GNSS + CO₂ optional)

---

## Integration Points

### With MycoNode

- Shared MycoBrain controller platform
- Mycorrhizae Protocol for data normalization
- Combined underground (MycoNode) + atmospheric (SporeBase) monitoring

### With Hyphae1

- Correlate spore dispersal with mycelium growth patterns
- Time-synchronized data via MINDEX

### With Mushroom1

- Link airborne spore counts to cultivation conditions
- Environmental telemetry comparison

### With MINDEX

- Chain-of-custody for sample metadata
- Tamper-evident record hashing
- Query interface for sample lookup

### With NatureOS

- Fleet visualization (map view of deployed SporeBase units)
- Telemetry dashboards
- Alert configuration
- Sample status tracking

### With MycoBrain Firmware

- Shared codebase where possible
- OTA update infrastructure
- Provisioning workflow

---

## Website Copy (Approved for Use)

### Header

> **SporeBase™ — Bioaerosol Collection, Time-Indexed for the Real World**
> *Capturing the invisible. Making it measurable.*

### Why SporeBase Exists

> The air around us carries billions of microscopic particles—spores, pollen, and other biological material. SporeBase creates **time-indexed physical samples** for lab analysis while logging the environmental context needed to interpret those samples accurately. It can be deployed on buildings, vehicles, and research stations to help map airborne biology across space and time.

### How SporeBase Works

> SporeBase uses **fan-driven active sampling** to deposit airborne particles onto an adhesive tape inside a sealed cassette. The cassette advances on a schedule (default **every 15 minutes**) to produce a chronological sample record spanning **30 days** (2,880 intervals). Each tape segment can be matched to sensor telemetry (humidity, temperature, VOCs, particulates, and optional location).

### Built for Networks (But Works Standalone)

> SporeBase can operate independently with onboard storage, or as part of Mycosoft's Environmental Intelligence network using **LoRa + Wi-Fi mesh** transport and standardized data encoding via **Mycorrhizae Protocol + MINDEX**, surfaced through **NatureOS** dashboards.

---

## Remaining Unknowns (Measure Before Publishing)

1. **True airflow through the sampling head** (CFM/LPM measurement)
2. **Verified 30-day power budget** for chosen battery configuration
3. **Tape/adhesive performance metrics** (capture + preservation + extraction)

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-22 | 3.0 | Major update: corrected inaccurate claims, aligned with V3/V4 CAD, added integration points |

---

## Related Documents

- `docs/DEVICE_MEDIA_ASSETS_PIPELINE.md` - Media asset management
- `docs/NATUREOS_OEI_INTEGRATION_PLAN.md` - NatureOS integration
- `firmware/mycobrain/` - MycoBrain firmware source
- `services/mindex/` - MINDEX service documentation
