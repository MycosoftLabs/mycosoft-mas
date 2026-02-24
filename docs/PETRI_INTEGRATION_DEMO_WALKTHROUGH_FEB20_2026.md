# Petri Full Integration Demonstration Walkthrough

**Date:** Feb 20, 2026  
**Status:** Complete  
**Related Plan:** petri-full-integration

## Overview

This document provides a step-by-step verification that the Petri Dish Simulator is fully integrated: domain model, UI, API, MINDEX/NLM, MYCA agent control, and scale batch engine.

---

## 1. Legacy Features Integrated

### From Advanced Virtual PetriDish (BETA-Incompleted).html

- **Agar types:** charcoal, blood, maltExtract, sabouraud, etc. (in `petridishsim/data/agar_types.json`)
- **Species/contaminant schemas:** domain model in `petridishsim/src/domain/`
- **Environmental variables:** temperature, humidity, pH, speed
- **Contamination interactions:** bacteria/virus/mold competition in `interaction.py`

### From myceliumsimv19.html

- **Growth logic:** agar, pH, temperature, humidity influence growth
- **Chemical diffusion:** reaction/diffusion in petridishsim chemical module

---

## 2. New Controls and Live Simulation Flow

### Website UI (`/apps/petri-dish-sim`)

1. **ChemicalParamsPanel** – species, agar, contamination, temperature, humidity, pH, speed
2. **SimulationMetricsDashboard** – metrics from sim state
3. **MyceliumSimulator** – canvas + stepping with `onMetricsUpdate` / `onCompoundsUpdate` callbacks

### Backend-Driven State

- Website proxy: `app/api/simulation/petri/[[...path]]/route.ts` → MAS
- MAS petri API: `/api/simulation/petri/*` → petridishsim when `PETRIDISHSIM_URL` is set

### Verification

1. Start website dev: `npm run dev:next-only` (port 3010)
2. Open http://localhost:3010/apps/petri-dish-sim
3. Adjust chemical params and observe metrics updating
4. Ensure no mock data; empty states when backend unavailable

---

## 3. API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/simulation/petri/chemical/init` | POST | Initialize chemical fields |
| `/api/simulation/petri/chemical/step` | POST | Step simulation |
| `/api/simulation/petri/metrics` | GET | Get current metrics |
| `/api/simulation/petri/calibrate` | POST | Calibration job |
| `/api/simulation/petri/session/create` | POST | Create session |
| `/api/simulation/petri/session/{id}` | GET | Get session |
| `/api/simulation/petri/session/{id}/reset` | POST | Reset session |
| `/api/simulation/petri/status` | GET | MAS + petridishsim status |
| `/api/simulation/petri/batch` | POST | Batch run (≤10k iterations) |
| `/api/simulation/petri/batch/scale` | POST | Scale batch (up to 1M iterations) |
| `/api/simulation/petri/batch/scale/{job_id}` | GET | Scale batch job status |
| `/api/simulation/petri/batch/scale/{job_id}/cancel` | POST | Cancel scale batch |
| `/api/simulation/petri/agent/control` | POST | MYCA agent control |
| `/api/simulation/petri/agent/audit` | GET | Audit trail |

---

## 4. MINDEX / NLM Interaction Path

- **MINDEX schema:** `migrations/0015_petri_simulation.sql` – sessions, metrics, calibration, outcomes
- **Persistence:** `data/petri_simulations.json` (agent state); optional MINDEX when endpoint exists
- **NLM hooks:** `petri_outcome`, `simulation_outcome` → `petri_outcome_ingest` workflow
- **Notifications:** Simulation complete, calibration complete, batch complete trigger NLM workflow

---

## 5. MYCA Agent Control

### Voice Commands (via command_registry)

- `petri.monitor` – get Petri status
- `petri.adjust_env` – adjust temperature, humidity, pH
- `petri.contamination_response` – trigger strategy (isolate, reduce_speed, adjust_ph)
- `petri.multi_run` – run N iterations

### Agent Control API

```bash
# Monitor
curl -X POST http://localhost:8001/api/simulation/petri/agent/control \
  -H "Content-Type: application/json" \
  -d '{"action":"monitor","source":"agent"}'

# Adjust environment
curl -X POST http://localhost:8001/api/simulation/petri/agent/control \
  -H "Content-Type: application/json" \
  -d '{"action":"adjust_env","source":"agent","params":{"temperature":26,"humidity":85}}'

# Multi-run
curl -X POST http://localhost:8001/api/simulation/petri/agent/control \
  -H "Content-Type: application/json" \
  -d '{"action":"multi_run","source":"agent","params":{"iterations":100}}'
```

### Audit Trail

- All agent actions logged via `log_petri_agent_action`
- `GET /api/simulation/petri/agent/audit?limit=50` returns recent entries

---

## 6. Batch Autonomy Demonstration

### Small Run (Synchronous)

```bash
# 100 iterations, immediate response
curl -X POST http://localhost:8001/api/simulation/petri/batch \
  -H "Content-Type: application/json" \
  -d '{"iterations":100,"dt":0.1}'
```

### Large Run (Queued)

```bash
# 50,000 iterations – returns job_id, poll for status
curl -X POST http://localhost:8001/api/simulation/petri/batch/scale \
  -H "Content-Type: application/json" \
  -d '{"iterations":50000,"dt":0.1,"summary_only":true}'

# Poll status
curl http://localhost:8001/api/simulation/petri/batch/scale/{job_id}

# Cancel if needed
curl -X POST http://localhost:8001/api/simulation/petri/batch/scale/{job_id}/cancel
```

---

## 7. Checklist

- [ ] Website UI loads without errors
- [ ] Chemical params and metrics panels display
- [ ] API proxy routes to MAS (check network tab)
- [ ] MAS petri status returns `petridishsim_configured` and `petridishsim_reachable` when petridishsim is running
- [ ] Session create/load/reset works
- [ ] Batch run completes for small iterations
- [ ] Scale batch returns job_id for large iterations; poll returns progress
- [ ] Agent control adjust_env, contamination_response, multi_run respond
- [ ] Agent audit trail returns entries after agent actions
- [ ] NLM workflow trigger (if n8n `petri_outcome_ingest` exists) receives outcomes

---

## 8. Prerequisites

- **PETRIDISHSIM_URL** – URL of petridishsim API (e.g. `http://localhost:8004`)
- **MAS_API_URL** – MAS orchestrator (e.g. `http://192.168.0.188:8001`)
- Website `.env.local`: `MAS_API_URL`, `MINDEX_API_URL` (optional)

---

## 9. File Reference

| Component | Path |
|-----------|------|
| Domain model | `petridishsim/src/domain/` |
| Website UI | `website/components/apps/petri-dish-sim-content.tsx`, `chemical-params-panel.tsx`, `simulation-metrics-dashboard.tsx` |
| Website proxy | `website/app/api/simulation/petri/[[...path]]/route.ts` |
| MAS petri API | `mycosoft_mas/core/routers/petri_sim_api.py` |
| Persistence | `mycosoft_mas/simulation/petri_persistence.py` |
| Batch engine | `mycosoft_mas/simulation/petri_batch_engine.py` |
| Petri agent | `mycosoft_mas/agents/clusters/simulation/petri_dish_simulator_agent.py` |
| Voice commands | `mycosoft_mas/voice/command_registry.py` |
| MINDEX migration | `mindex/migrations/0015_petri_simulation.sql` |
