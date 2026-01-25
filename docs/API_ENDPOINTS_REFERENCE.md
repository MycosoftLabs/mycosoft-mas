# API Endpoints Reference

> Complete API documentation for all MYCOSOFT systems

**Version**: 2.0.0  
**Base URL**: `https://api.mycosoft.io` (Production) | `http://localhost:3010` (Development)  
**Last Updated**: 2026-01-24

---

## Table of Contents

1. [Authentication](#authentication)
2. [Innovation Apps API](#innovation-apps-api)
3. [MINDEX Core API](#mindex-core-api)
4. [Compounds API](#compounds-api)
5. [User Data API](#user-data-api)
6. [Error Handling](#error-handling)

---

## Authentication

All API endpoints require authentication via JWT token or API key.

### Headers

```http
Authorization: Bearer <jwt_token>
X-API-Key: <api_key>
Content-Type: application/json
```

### Get Token

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

## Innovation Apps API

### Physics Simulator

#### Run Simulation

```http
POST /api/mindex/innovation/physics
```

**Request Body**:
```json
{
  "action": "simulate",
  "molecule": {
    "name": "Psilocybin",
    "smiles": "CN(C)CCc1c[nH]c2cccc(OP(=O)(O)O)c12",
    "formula": "C12H17N2O4P"
  },
  "parameters": {
    "steps": 100,
    "timestep": 1.0,
    "method": "qise",
    "force_field": "universal"
  }
}
```

**Response** (200 OK):
```json
{
  "simulation_id": "sim_abc123",
  "status": "completed",
  "trajectory": [
    {"step": 0, "energy": -42.5, "positions": [...]},
    {"step": 1, "energy": -42.3, "positions": [...]}
  ],
  "final_energy": -41.8,
  "quantum_properties": {
    "homo_lumo_gap": 3.24,
    "dipole_moment": 1.52,
    "polarizability": 18.7
  },
  "execution_time_ms": 1250
}
```

#### Get Simulation Status

```http
GET /api/mindex/innovation/physics/{simulation_id}
```

---

### Digital Twin Mycelium

#### Get Digital Twin State

```http
GET /api/mindex/innovation/digital-twin?species={species_id}
```

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| species | string | No | Species identifier |

**Response** (200 OK):
```json
{
  "twin_id": "dtm_xyz789",
  "species": "psilocybe_cubensis",
  "state": {
    "biomass_grams": 5.2,
    "network_density": 0.35,
    "health": 100,
    "temperature": 24.0,
    "humidity": 85.0
  },
  "nodes": [
    {"id": "node_0", "x": 400, "y": 300, "type": "junction"},
    {"id": "node_1", "x": 450, "y": 280, "type": "tip"}
  ],
  "edges": [
    {"source": "node_0", "target": "node_1", "strength": 0.9}
  ],
  "last_update": "2026-01-24T10:30:00Z"
}
```

#### Update Digital Twin

```http
POST /api/mindex/innovation/digital-twin
```

**Request Body**:
```json
{
  "action": "update",
  "sensor_data": {
    "temperature_celsius": 24.5,
    "humidity_percent": 87,
    "co2_ppm": 850
  }
}
```

#### Predict Growth

```http
POST /api/mindex/innovation/digital-twin
```

**Request Body**:
```json
{
  "action": "predict",
  "duration_hours": 24
}
```

**Response**:
```json
{
  "current_biomass_grams": 5.2,
  "predicted_biomass_grams": 6.8,
  "predicted_network_density": 0.42,
  "fruiting_probability": 0.15,
  "growth_rate_per_hour": 0.012,
  "recommendations": [
    "Conditions are optimal, maintain current parameters"
  ]
}
```

---

### Lifecycle Simulator

#### Advance Lifecycle

```http
POST /api/mindex/innovation/lifecycle
```

**Request Body**:
```json
{
  "action": "advance",
  "species": "psilocybe_cubensis",
  "hours": 24,
  "environment": {
    "temperature": 24,
    "humidity": 90,
    "co2": 800,
    "light_hours": 12
  }
}
```

**Response**:
```json
{
  "stage": "hyphal_growth",
  "stage_index": 2,
  "stage_progress": 0.45,
  "day_count": 5.0,
  "biomass_grams": 2.5,
  "health": 95.0,
  "environment": {
    "temperature": 24,
    "humidity": 90
  },
  "recommendations": [
    "Conditions are optimal. Maintain current parameters."
  ],
  "predicted_harvest_date": "2026-02-15T12:00:00Z"
}
```

#### Available Species Profiles

| Species Key | Common Name | Germination Days | Colonization Days |
|-------------|-------------|------------------|-------------------|
| psilocybe_cubensis | Golden Teacher | 2 | 14 |
| hericium_erinaceus | Lion's Mane | 5 | 21 |
| pleurotus_ostreatus | Oyster | 2 | 10 |
| ganoderma_lucidum | Reishi | 7 | 30 |
| cordyceps_militaris | Cordyceps | 5 | 28 |

---

### Genetic Circuit Designer

#### Get Available Circuits

```http
GET /api/mindex/innovation/genetic-circuit
```

**Response**:
```json
{
  "circuits": [
    {
      "id": "psilocybin_pathway",
      "name": "Psilocybin Biosynthesis",
      "species": "Psilocybe cubensis",
      "product": "Psilocybin",
      "genes": ["psiD", "psiK", "psiM", "psiH"]
    }
  ]
}
```

#### Run Circuit Simulation

```http
POST /api/mindex/innovation/genetic-circuit
```

**Request Body**:
```json
{
  "action": "simulate",
  "circuit_id": "psilocybin_pathway",
  "steps": 100,
  "timestep": 0.1,
  "modifications": {
    "psiD": 20,
    "psiM": -10
  },
  "conditions": {
    "stress_level": 0,
    "nutrient_level": 50
  }
}
```

**Response**:
```json
{
  "circuit_name": "Psilocybin Biosynthesis",
  "trajectory": [
    {"psiD": 60, "psiK": 45, "psiM": 55, "psiH": 40},
    {"psiD": 61, "psiK": 46, "psiM": 54, "psiH": 41}
  ],
  "final_state": {
    "psiD": 72.5,
    "psiK": 58.2,
    "psiM": 48.1,
    "psiH": 52.0
  },
  "final_metabolite": 15.8,
  "bottleneck_gene": "psiM",
  "average_expression": 57.7,
  "flux_rate": 0.158,
  "execution_time_ms": 45
}
```

---

### Symbiosis Mapper

#### Get Network

```http
GET /api/mindex/innovation/symbiosis
```

**Response**:
```json
{
  "organisms": [
    {"id": "org_1", "name": "P. cubensis", "type": "fungus", "x": 400, "y": 300}
  ],
  "relationships": [
    {"source": "org_1", "target": "org_2", "type": "mycorrhizal", "strength": 0.8}
  ]
}
```

#### Analyze Network

```http
POST /api/mindex/innovation/symbiosis
```

**Request Body**:
```json
{
  "action": "analyze"
}
```

**Response**:
```json
{
  "num_organisms": 30,
  "num_relationships": 45,
  "average_degree": 3.0,
  "density": 0.103,
  "keystone_species": [
    {"id": "org_5", "name": "Fungus 5", "type": "fungus", "degree": 12, "betweenness": 26.7}
  ],
  "relationship_breakdown": {
    "mycorrhizal": 15,
    "parasitic": 8,
    "saprotrophic": 12,
    "endophytic": 10
  },
  "communities": [
    {"id": 1, "organism_type": "fungus", "size": 12, "dominant_relationship": "mycorrhizal"}
  ]
}
```

---

### Retrosynthesis Viewer

#### Analyze Pathway

```http
GET /api/mindex/innovation/retrosynthesis?compound={compound_name}
```

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| compound | string | Yes | Compound name or SMILES |
| max_steps | integer | No | Maximum pathway depth (default: 6) |

**Response**:
```json
{
  "target": {
    "name": "Psilocybin",
    "formula": "C12H17N2O4P"
  },
  "starting_material": "L-Tryptophan",
  "total_steps": 5,
  "steps": [
    {
      "step_number": 1,
      "precursor": {"name": "L-Tryptophan"},
      "product": {"name": "Tryptamine"},
      "reaction_type": "decarboxylation",
      "enzyme": "PsiD (Tryptophan decarboxylase)",
      "confidence": 0.95,
      "description": "Removal of carboxyl group as CO2"
    }
  ],
  "pathway_confidence": 0.85,
  "pathway_type": "known"
}
```

---

### Alchemy Lab

#### Design Compound

```http
POST /api/mindex/innovation/alchemy
```

**Request Body**:
```json
{
  "action": "design",
  "scaffold": "tryptamine",
  "modifications": ["hydroxyl", "methyl"],
  "target_activities": ["psychedelic", "neurotrophic"],
  "mw_range": [200, 400]
}
```

**Response**:
```json
{
  "id": "MYCO-54321",
  "name": "Tryptamine Derivative MYCO-54321",
  "formula": "C11H14N2O",
  "molecular_weight": 190.24,
  "smiles": "CN(C)CCc1c[nH]c2ccc(O)cc12",
  "scaffold": "tryptamine",
  "modifications": [
    {"name": "hydroxyl", "effect": "hydrophilicity"},
    {"name": "methyl", "effect": "lipophilicity"}
  ],
  "predicted_properties": {
    "molecular_weight": 190.24,
    "logP": 1.85,
    "h_bond_donors": 2,
    "h_bond_acceptors": 3,
    "tpsa": 45.2,
    "rotatable_bonds": 3,
    "ro5_violations": 0,
    "drug_likeness": "Good"
  },
  "predicted_activities": [
    {"activity_name": "Psychedelic", "activity_id": "psychedelic", "confidence": 0.82},
    {"activity_name": "Neurotrophic", "activity_id": "neurotrophic", "confidence": 0.65}
  ],
  "optimization_score": 0.735
}
```

#### Virtual Screening

```http
POST /api/mindex/innovation/alchemy
```

**Request Body**:
```json
{
  "action": "screen",
  "target_activity": "anticancer",
  "num_compounds": 10
}
```

---

## MINDEX Core API

### Taxon Endpoints

```http
GET /api/mindex/v1/taxa
GET /api/mindex/v1/taxa/{taxon_id}
GET /api/mindex/v1/taxa/search?q={query}
```

### Compound Endpoints

```http
GET /api/mindex/compounds
GET /api/mindex/compounds/{compound_id}
GET /api/mindex/compounds/for-taxon/{taxon_id}
GET /api/mindex/compounds/chemspider/search?query={query}
POST /api/mindex/compounds/enrich
```

---

## Compounds API

### List Compounds

```http
GET /api/mindex/compounds?limit=100&offset=0&search={query}
```

**Response**:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Psilocybin",
      "formula": "C12H17N2O4P",
      "molecular_weight": 284.25,
      "smiles": "...",
      "inchi": "...",
      "chemspider_id": "10254679",
      "activities": [
        {"id": "uuid", "name": "Psychedelic", "category": "Neuroactive"}
      ]
    }
  ],
  "meta": {
    "limit": 100,
    "offset": 0,
    "total": 250
  }
}
```

### ChemSpider Search

```http
GET /api/mindex/compounds/chemspider/search?query=psilocybin
```

### Enrich Compound

```http
POST /api/mindex/compounds/enrich
Content-Type: application/json

{
  "compound_id": "uuid-of-compound"
}
```

---

## User Data API

### Get User Sessions

```http
GET /api/user/sessions?app_name={app_name}
```

### Log Simulation

```http
POST /api/user/simulations
Content-Type: application/json

{
  "app_name": "physics-sim",
  "simulation_type": "molecular_dynamics",
  "input_data": {...},
  "output_data": {...}
}
```

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": {
      "field": "steps",
      "issue": "Must be between 1 and 10000"
    }
  },
  "request_id": "req_abc123"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTH_REQUIRED` | 401 | Authentication needed |
| `AUTH_EXPIRED` | 401 | Token expired |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 400 | Invalid input |
| `RATE_LIMITED` | 429 | Too many requests |
| `MINDEX_UNAVAILABLE` | 503 | Database unavailable |
| `CHEMSPIDER_ERROR` | 502 | External API error |
| `INTERNAL_ERROR` | 500 | Server error |

### Rate Limits

| Endpoint | Limit |
|----------|-------|
| Innovation APIs | 100 req/min |
| Compounds API | 60 req/min |
| ChemSpider Search | 10 req/min |
| Auth | 10 req/min |

---

## SDK Examples

### JavaScript/TypeScript

```typescript
// Using fetch
async function runPhysicsSimulation(molecule: string) {
  const response = await fetch('/api/mindex/innovation/physics', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      action: 'simulate',
      molecule: { name: molecule },
      parameters: { steps: 100 }
    })
  });
  return response.json();
}
```

### Python

```python
import requests

def run_physics_simulation(molecule: str, steps: int = 100):
    response = requests.post(
        'http://localhost:3010/api/mindex/innovation/physics',
        json={
            'action': 'simulate',
            'molecule': {'name': molecule},
            'parameters': {'steps': steps}
        },
        headers={'Authorization': f'Bearer {token}'}
    )
    return response.json()
```

### cURL

```bash
curl -X POST http://localhost:3010/api/mindex/innovation/physics \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"action":"simulate","molecule":{"name":"Psilocybin"},"parameters":{"steps":100}}'
```

---

*API Reference v2.0 - Generated 2026-01-24*
