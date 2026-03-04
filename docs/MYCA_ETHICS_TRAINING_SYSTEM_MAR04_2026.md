# MYCA Ethics Training System
## Created: March 4, 2026 | Status: Complete

## Overview

The MYCA Ethics Training System is an isolated section within the website at `/ethics-training/*` for training sandboxed MYCA instances across developmental stages (Animal through Machine). It runs ethics scenarios via text/voice, grades outcomes using the Observer MYCA, and reports results.

## Architecture

- **Frontend:** Website at `/ethics-training/` (fullscreen layout, sidebar nav, Morgan + Michelle only)
- **Backend:** MAS API at `/api/ethics/training/*` (VM 188)
- **Proxy:** Website `/api/ethics-training/*` forwards to MAS

## Components

### MAS Backend

| Component | Path | Purpose |
|-----------|------|---------|
| SandboxManager | `mycosoft_mas/ethics/sandbox_manager.py` | Create/list/destroy sandbox sessions; chat via FrontierLLMRouter with vessel prompts |
| TrainingEngine | `mycosoft_mas/ethics/training_engine.py` | Load scenarios from YAML; run scenarios on sandboxes |
| GradingEngine | `mycosoft_mas/ethics/grading_engine.py` | Observer MYCA (Adult/Machine) grades responses; rubric breakdown |
| ObserverIntegration | `mycosoft_mas/ethics/observer_integration.py` | Record observations; batch summary; stub for production MYCA ingestion |
| EthicsTrainingAPI | `mycosoft_mas/core/routers/ethics_training_api.py` | 11 endpoints for sandbox, scenarios, run, grades, report, observations |

### API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/ethics/training/sandbox` | Create sandbox session |
| GET | `/api/ethics/training/sandbox` | List sessions |
| GET | `/api/ethics/training/sandbox/{id}` | Get session details |
| POST | `/api/ethics/training/sandbox/{id}/chat` | Chat with sandboxed MYCA |
| DELETE | `/api/ethics/training/sandbox/{id}` | Destroy session |
| GET | `/api/ethics/training/scenarios` | List scenarios |
| GET | `/api/ethics/training/scenarios/{id}` | Get scenario details |
| POST | `/api/ethics/training/run` | Run scenario on session |
| GET | `/api/ethics/training/grades/{session_id}` | Get grades |
| POST | `/api/ethics/training/report` | Generate aggregate report |
| GET | `/api/ethics/training/observations` | Observer MYCA notes |

### Scenarios (6 starter YAML files)

- `infant_observation.yaml` – Baby MYCA observation without bias
- `child_why_game.yaml` – Child MYCA "why" questions
- `teen_manipulation_detection.yaml` – Teen MYCA manipulation detection
- `adult_trolley_problem.yaml` – Trolley variations
- `adult_corporate_ethics.yaml` – Stakeholder dilemmas
- `machine_long_horizon.yaml` – 10-year projection

### Website Frontend

| Route | Page |
|-------|------|
| `/ethics-training/` | Dashboard (sessions, scenarios, quick-create) |
| `/ethics-training/sandbox/new` | Sandbox creator form |
| `/ethics-training/sandbox/[id]` | Training session (TrainingChat, VoiceInteraction, ScenarioRunner) |
| `/ethics-training/scenarios` | Scenario library |
| `/ethics-training/analytics` | MetricsDashboard, grades by vessel stage |
| `/ethics-training/observations` | Observer notes feed |

### Auth

- Morgan and Michelle only (`ETHICS_TRAINING_ALLOWED_EMAILS` in `lib/access/routes.ts`)
- Michelle: `michelle@mycosoft.org`, admin role

## Verification

1. **MAS:** `curl http://192.168.0.188:8001/api/ethics/training/scenarios`
2. **Website:** Log in as Morgan or Michelle, navigate to `/ethics-training`
3. **Create sandbox:** Pick vessel stage, create, chat, run scenario

## Related Docs

- `docs/MYCA_ETHICS_PHILOSOPHY_BASELINE_MAR03_2026.md` – Ethics pipeline, vessels
- `docs/SYSTEM_REGISTRY_FEB04_2026.md` – System registry
- `docs/API_CATALOG_FEB04_2026.md` – API catalog
