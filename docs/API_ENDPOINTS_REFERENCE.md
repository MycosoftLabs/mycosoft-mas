# API Endpoints Reference

**Version**: 1.0  
**Date**: 2026-01-24  
**Base URLs**:
- Production: `https://mindex.mycosoft.com/api`
- Sandbox: `https://sandbox.mindex.mycosoft.com/api`
- Local MINDEX: `http://localhost:8000/api`
- Local Website: `http://localhost:3010`

---

## Table of Contents

1. [Compounds API](#compounds-api)
2. [Physics API](#physics-api)
3. [Taxon API](#taxon-api)
4. [Telemetry API](#telemetry-api)
5. [Authentication](#authentication)
6. [Error Handling](#error-handling)

---

## Compounds API

### List Compounds

```http
GET /compounds
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | integer | 100 | Max results (1-1000) |
| offset | integer | 0 | Pagination offset |
| search | string | - | Search by name or formula |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Psilocybin",
      "formula": "C12H17N2O4P",
      "molecular_weight": 284.25,
      "smiles": "CN(C)CCc1c[nH]c2cccc(OP(=O)(O)O)c12",
      "inchi": "InChI=1S/C12H17N2O4P/c...",
      "inchikey": "QZFMSOQMXGXQRX-UHFFFAOYSA-N",
      "chemspider_id": "10086",
      "pubchem_id": "10624",
      "source": "ChemSpider",
      "activities": [
        {"id": "uuid", "name": "Hallucinogenic", "category": "Psychoactive"}
      ],
      "created_at": "2026-01-24T00:00:00Z",
      "updated_at": "2026-01-24T00:00:00Z"
    }
  ],
  "meta": {
    "limit": 100,
    "offset": 0,
    "total": 500
  }
}
```

---

### Get Compound by ID

```http
GET /compounds/{compound_id}
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| compound_id | UUID | Compound identifier |

**Response:** Single compound object (see above)

---

### Get Compounds for Taxon

```http
GET /compounds/for-taxon/{taxon_id}
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| taxon_id | UUID | Taxon (species) identifier |

**Response:**
```json
{
  "compounds": [
    {
      "id": "uuid",
      "taxon_id": "uuid",
      "compound_id": "uuid",
      "evidence_level": "verified",
      "source": "MINDEX ETL",
      "compound": {
        "id": "uuid",
        "name": "Psilocybin",
        "formula": "C12H17N2O4P",
        ...
      }
    }
  ]
}
```

---

### Enrich Compound from ChemSpider

```http
POST /compounds/enrich
```

**Request Body:**
```json
{
  "compound_id": "uuid"
}
```

**Response:** Updated compound object with ChemSpider data

---

### Search ChemSpider

```http
GET /compounds/chemspider/search
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| query | string | Search term (name, formula, SMILES) |

**Response:**
```json
{
  "compounds": [
    {
      "id": "generated-uuid",
      "name": "Compound Name",
      "formula": "C10H12N2",
      "molecular_weight": 164.21,
      "chemspider_id": "12345",
      ...
    }
  ]
}
```

**Note:** Requires `CHEMSPIDER_API_KEY` environment variable.

---

## Physics API

### Molecular Simulation (QISE)

```http
POST /physics/molecular/simulate
```

**Request Body:**
```json
{
  "molecule": {
    "name": "Psilocybin",
    "atoms": ["C", "C", "C", "H", "N", ...],
    "bonds": [[0, 1], [1, 2], ...],
    "coordinates": [[0.0, 0.0, 0.0], ...]
  },
  "method": "qise",
  "parameters": {
    "max_iterations": 100,
    "convergence_threshold": 1e-6
  }
}
```

**Response:**
```json
{
  "ground_state_energy": -156.78,
  "homo_lumo_gap": 3.45,
  "dipole_moment": 2.34,
  "polarizability": 87.6,
  "message": "Simulation completed successfully"
}
```

---

### Molecular Dynamics

```http
POST /physics/molecular/dynamics
```

**Request Body:**
```json
{
  "system": {
    "atoms": [...],
    "initial_positions": [...],
    "initial_velocities": [...]
  },
  "parameters": {
    "steps": 1000,
    "timestep": 0.5,
    "force_field": "universal"
  }
}
```

**Response:**
```json
{
  "trajectory": [...],
  "final_positions": [...],
  "final_velocities": [...],
  "potential_energy": -45.67,
  "message": "MD simulation completed"
}
```

---

### Field Physics Conditions

```http
POST /physics/field/conditions
```

**Request Body:**
```json
{
  "location": {
    "latitude": 37.7749,
    "longitude": -122.4194,
    "altitude": 10
  },
  "timestamp": "2026-01-24T12:00:00Z"
}
```

**Response:**
```json
{
  "geomagnetic_field": {
    "bx": 22456.7,
    "by": -5678.9,
    "bz": 42345.6,
    "total": 48123.4,
    "inclination": 62.5,
    "declination": -14.2
  },
  "lunar_influence": {
    "gravitational_force": 3.3e-6,
    "tidal_potential": 1.2e-5,
    "phase": "Waxing Gibbous"
  },
  "atmospheric": {
    "temperature_celsius": 18.5,
    "pressure_hpa": 1013.25,
    "humidity_percent": 65.0,
    "wind_speed_mps": 5.2
  }
}
```

---

### Fruiting Prediction

```http
POST /physics/field/fruiting-prediction
```

**Request Body:**
```json
{
  "location": {
    "latitude": 37.7749,
    "longitude": -122.4194,
    "altitude": 10
  },
  "species_id": "uuid",
  "forecast_days": 7
}
```

**Response:**
```json
{
  "probability": 0.72,
  "optimal_date": "2026-01-28",
  "conditions_summary": "Good - high humidity expected",
  "recommendations": [
    "Monitor humidity levels",
    "Reduce light during pinning phase"
  ]
}
```

---

## Taxon API

### List Taxa

```http
GET /taxon
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | integer | 100 | Max results |
| offset | integer | 0 | Pagination offset |
| rank | string | - | Filter by rank (species, genus, family) |
| search | string | - | Search by name |

---

### Get Taxon by ID

```http
GET /taxon/{taxon_id}
```

**Response:**
```json
{
  "id": "uuid",
  "canonical_name": "Psilocybe cubensis",
  "common_name": "Golden Teacher",
  "rank": "species",
  "description": "...",
  "parent_id": "uuid",
  "ancestry": "Fungi > Basidiomycota > ...",
  "image_url": "https://...",
  "metadata": {...}
}
```

---

### Get Taxa with Compounds

```http
GET /taxon/with-compounds
```

Returns taxa that have associated compound data.

---

## Telemetry API

### Submit Telemetry

```http
POST /telemetry
```

**Request Body:**
```json
{
  "device_id": "MB-001",
  "timestamp": "2026-01-24T12:00:00Z",
  "readings": {
    "temperature": 22.5,
    "humidity": 85.0,
    "co2": 450,
    "light": 200,
    "ph": 6.5,
    "conductivity": 1.2
  },
  "location": {
    "latitude": 37.7749,
    "longitude": -122.4194
  }
}
```

---

### Get Device Telemetry

```http
GET /telemetry/device/{device_id}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| start | datetime | Start of time range |
| end | datetime | End of time range |
| limit | integer | Max results |

---

## Authentication

### API Key Authentication

Include your API key in the request header:

```http
Authorization: Bearer your_api_key_here
```

Or as a query parameter:

```http
GET /api/compounds?api_key=your_api_key_here
```

### Getting an API Key

1. Log in to NatureOS at `https://natureos.mycosoft.com`
2. Navigate to Settings > API Keys
3. Generate a new key
4. Store securely (key is shown only once)

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid compound_id format",
    "details": {
      "field": "compound_id",
      "expected": "UUID"
    }
  }
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid/missing API key |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limited |
| 500 | Internal Server Error |
| 503 | Service Unavailable - API down or missing config |

### Rate Limits

| Tier | Requests/minute | Requests/day |
|------|-----------------|--------------|
| Free | 60 | 1,000 |
| Pro | 300 | 10,000 |
| Enterprise | 1,000 | Unlimited |

---

## SDK Examples

### Python

```python
import httpx

MINDEX_URL = "https://mindex.mycosoft.com/api"
API_KEY = "your_key_here"

async def get_compounds():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MINDEX_URL}/compounds",
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        return response.json()
```

### TypeScript

```typescript
const MINDEX_URL = process.env.NEXT_PUBLIC_MINDEX_API_URL;

async function getCompounds() {
  const response = await fetch(`${MINDEX_URL}/compounds`, {
    headers: {
      'Authorization': `Bearer ${process.env.API_KEY}`
    }
  });
  return response.json();
}
```

### cURL

```bash
curl -X GET "https://mindex.mycosoft.com/api/compounds" \
  -H "Authorization: Bearer your_api_key_here" \
  -H "Content-Type: application/json"
```

---

## WebSocket Endpoints

### Live Telemetry Stream

```
wss://mindex.mycosoft.com/ws/telemetry/{device_id}
```

**Message Format:**
```json
{
  "type": "telemetry",
  "device_id": "MB-001",
  "timestamp": "2026-01-24T12:00:00Z",
  "data": {
    "temperature": 22.5,
    "humidity": 85.0,
    ...
  }
}
```

---

## Changelog

### v1.0.0 (2026-01-24)
- Initial release
- Compounds API with ChemSpider integration
- Physics API with QISE, MD, field physics
- Taxon API with compound associations
- Telemetry API for MycoBrain devices

---

*Document Version 1.0 | Last Updated: 2026-01-24*
