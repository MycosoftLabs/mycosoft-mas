# SporeBase Atmospheric Sampler

## Overview

The SporeBase Atmospheric Sampler is a next-generation spore collection and analysis device for environmental monitoring, species distribution mapping, and bioaerosol research.

## Technical Specifications

### Physical

| Specification | Value |
|---------------|-------|
| Dimensions | 200 × 150 × 100 mm |
| Weight | 850g (with battery) |
| Housing | IP65 weatherproof |
| Material | UV-resistant ABS |
| Mounting | Tripod, pole, or wall mount |
| Color | Forest green / Research white |

### Sampling System

| Component | Specification |
|-----------|---------------|
| Flow Rate | 2-20 L/min (adjustable) |
| Collection Method | Cyclone impaction + filter |
| Particle Size Range | 1-100 μm |
| Size Fractionation | 3 stages (1-5, 5-20, 20-100 μm) |
| Collection Surface | Adhesive slides / PTFE filters |
| Capacity | 7 days continuous |

### Optical Counter

| Feature | Value |
|---------|-------|
| Detection Range | 0.5-50 μm |
| Channels | 8 size bins |
| Sample Rate | 1 Hz |
| Light Source | 650nm laser diode |
| Accuracy | ±10% for 2-10 μm |

### Environmental Sensors

| Sensor | Range | Accuracy |
|--------|-------|----------|
| Temperature | -20 to +60°C | ±0.3°C |
| Humidity | 0-100% RH | ±2% |
| Pressure | 300-1100 hPa | ±1 hPa |
| UV Index | 0-15 | ±5% |
| Wind Speed | 0-30 m/s | ±0.5 m/s |
| Precipitation | 0-10 mm/hr | ±0.5 mm |

### Processor & Connectivity

| Component | Specification |
|-----------|---------------|
| MCU | ESP32-S3 (dual-core 240MHz) |
| RAM | 8 MB PSRAM |
| Flash | 16 MB |
| GPS | u-blox M10 (1m accuracy) |
| Cellular | 4G LTE Cat-M1/NB-IoT |
| WiFi | 802.11 b/g/n |
| Bluetooth | 5.0 LE |
| LoRa | Optional (915 MHz) |

### Power

| Specification | Value |
|---------------|-------|
| Battery | 18650 Li-ion × 4 (14,000 mAh) |
| Solar Panel | 5W integrated |
| Runtime (battery) | 3-7 days (depending on sampling) |
| Runtime (solar) | Indefinite (with sun) |
| Charging | USB-C 5V/3A |

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SporeBase Atmospheric Sampler                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Sampling System                          │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │ │
│  │  │  Inlet   │─▶│ Cyclone  │─▶│ Optical  │─▶│ Filter   │   │ │
│  │  │  (20μm)  │  │ (5μm)    │  │ Counter  │  │ Cassette │   │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │ │
│  │        │            │            │             │           │ │
│  │        ▼            ▼            ▼             ▼           │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │ │
│  │  │ Slide 1  │  │ Slide 2  │  │  Data    │  │  DNA     │   │ │
│  │  │ (Coarse) │  │ (Medium) │  │ Stream   │  │ Preserve │   │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Processing Unit                          │ │
│  │  ┌──────────────────┐  ┌──────────────────────────────────┐│ │
│  │  │    ESP32-S3      │  │       Sensor Array               ││ │
│  │  │  • Data logging  │  │  • BME688 (T/RH/P/VOC)           ││ │
│  │  │  • AI counting   │  │  • Wind speed/direction          ││ │
│  │  │  • Upload queue  │  │  • UV index                      ││ │
│  │  │  • GPS tracking  │  │  • Rain gauge                    ││ │
│  │  └──────────────────┘  └──────────────────────────────────┘│ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Communication                            │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │ │
│  │  │ Cellular │  │   WiFi   │  │   LoRa   │  │ Bluetooth│   │ │
│  │  │  4G LTE  │  │ 2.4 GHz  │  │ 915 MHz  │  │   5.0    │   │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│                         ┌──────────┐                            │
│                         │  MINDEX  │                            │
│                         │  Cloud   │                            │
│                         └──────────┘                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Sampling Modes

### Continuous Monitoring
- Low flow rate (2 L/min)
- Optical counting only
- 7+ day autonomous operation
- Hourly data upload

### Intensive Sampling
- High flow rate (20 L/min)
- Physical collection + counting
- 24-hour cassette capacity
- Real-time spore cloud alerts

### Event-Triggered
- Weather-based triggers
- Spore threshold alerts
- Automatic intensity increase
- Post-event DNA preservation

### Time-Lapse
- Programmable schedule
- Dawn/dusk focus
- Seasonal optimization
- Power conservation

## Data Products

### Real-time Telemetry
```json
{
  "timestamp": "2026-01-24T12:00:00Z",
  "location": {"lat": 40.7128, "lon": -74.0060},
  "environmental": {
    "temperature_c": 18.5,
    "humidity_pct": 72,
    "pressure_hpa": 1013.2,
    "wind_speed_ms": 2.4,
    "wind_direction": 225,
    "uv_index": 3.2,
    "precipitation_mm_hr": 0
  },
  "particles": {
    "total_count": 1523,
    "by_size": {
      "0.5-1um": 892,
      "1-2um": 341,
      "2-5um": 198,
      "5-10um": 67,
      "10-20um": 19,
      "20-50um": 5,
      "50-100um": 1
    },
    "concentration_per_m3": 15230
  },
  "spore_estimate": {
    "total_per_m3": 4500,
    "dominant_type": "basidiospore",
    "confidence": 0.72
  }
}
```

### Slide Images
- Microscopy-ready slides
- Automatic staining option
- QR code tracking
- MINDEX species matching

### DNA Samples
- RNAlater preservation
- 7-day stability at ambient
- Metabarcoding-ready
- Chain of custody

## MINDEX Integration

### Automatic Species Detection
1. Optical signature analysis
2. AI shape classification
3. Size distribution matching
4. Seasonal probability
5. Geographic likelihood
6. MINDEX species suggestion

### Data Flow
```
SporeBase → MINDEX Telemetry API → 
  → Time-series storage
  → Species prediction
  → Alert generation
  → Research dashboard
  → Public spore forecast
```

### Alert Types
- High spore count (customizable threshold)
- Rare species detection
- Unusual distribution
- Equipment malfunction
- Sample capacity

## Manufacturing

### Bill of Materials (BOM)

| Component | Qty | Unit Cost | Total |
|-----------|-----|-----------|-------|
| ESP32-S3 module | 1 | $8 | $8 |
| Optical sensor | 1 | $45 | $45 |
| Pump motor | 1 | $15 | $15 |
| Cyclone assembly | 1 | $25 | $25 |
| BME688 sensor | 1 | $12 | $12 |
| GPS module | 1 | $15 | $15 |
| LTE modem | 1 | $35 | $35 |
| Battery pack | 1 | $20 | $20 |
| Solar panel | 1 | $30 | $30 |
| Enclosure | 1 | $40 | $40 |
| PCB + assembly | 1 | $25 | $25 |
| Misc components | - | $30 | $30 |
| **Total BOM** | | | **$300** |

### Retail Pricing

| Version | Price | Features |
|---------|-------|----------|
| SporeBase Lite | $499 | Optical only, WiFi |
| SporeBase Pro | $799 | Full sampling, Cellular |
| SporeBase Research | $1,299 | DNA preservation, API |
| SporeBase Network | $599/unit (10+) | Bulk deployment |

## Research Applications

### Aerobiology Studies
- Seasonal spore patterns
- Diurnal variation
- Climate correlations
- Species phenology

### Agriculture
- Crop pathogen early warning
- Mycorrhizal inoculum monitoring
- Harvest timing optimization
- Biocontrol effectiveness

### Public Health
- Allergen forecasting
- Mold exposure assessment
- Indoor air quality
- Epidemiology support

### Conservation
- Rare species distribution
- Habitat quality assessment
- Restoration monitoring
- Climate change impacts

## Deployment Recommendations

### Site Selection
- Open area (avoid obstructions)
- Representative of target habitat
- Accessible for maintenance
- Secure from tampering
- Power source proximity

### Network Design
- 1 unit per 10-50 km² (regional)
- 1 unit per 1 km² (intensive)
- Minimum 3 units per study area
- Backup/calibration unit

### Maintenance Schedule
- Weekly: Check status, clear inlet
- Monthly: Replace filters, clean optics
- Quarterly: Full calibration
- Annual: Factory refurbishment

## Roadmap

### Version 1.0 (Q2 2026)
- Basic optical counting
- Environmental sensors
- Cellular upload
- MINDEX integration

### Version 1.5 (Q4 2026)
- On-device AI classification
- Slide imaging camera
- LoRa mesh networking
- Extended battery

### Version 2.0 (2027)
- DNA auto-sampler
- Real-time sequencing (MinION)
- Edge computing
- Solar-only operation

---

*Document Version: 1.0*
*Last Updated: 2026-01-24*
*Classification: Hardware Specification*
