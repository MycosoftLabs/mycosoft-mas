# PhysicsNeMo Integration - FEB09 2026

## Scope

This update integrates NVIDIA PhysicsNeMo as an on-demand local GPU service and wires MAS simulation modules and Earth2 workflows to call physics-backed endpoints instead of returning placeholder simulation outputs.

## Runtime Topology

- Local PhysicsNeMo service: `http://localhost:8400`
- Earth2 local inference service: `http://localhost:8220`
- MAS physics proxy endpoints: `http://192.168.0.188:8001/api/physics/*`
- Local GPU gateway: `http://localhost:8300`

## New and Updated Services

### New Files

- `scripts/physicsnemo_service.py` - FastAPI physics service intended to run inside the PhysicsNeMo container
- `scripts/start_physicsnemo.ps1` - Pull + start `nvcr.io/nvidia/physicsnemo/physicsnemo:25.06` on port `8400`
- `scripts/stop_physicsnemo.ps1` - Stop/remove `physicsnemo-service`
- `mycosoft_mas/agents/v2/physicsnemo_agent.py` - V2 agent for physics task dispatch
- `mycosoft_mas/core/routers/physicsnemo_api.py` - MAS API proxy for physics endpoints

### Updated Files

- `scripts/local_gpu_services.py` - now manages PhysicsNeMo (`8400`) in addition to Earth2/Moshi/Bridge
- `mycosoft_mas/simulation/physics.py` - now calls PhysicsNeMo endpoints with CPU fallback solvers
- `mycosoft_mas/agents/clusters/simulation/petri_dish_simulator_agent.py` - growth/environment updates use physics-backed methods
- `mycosoft_mas/agents/clusters/simulation/compound_simulator_agent.py` - chemical simulation + interaction analysis use physics service
- `mycosoft_mas/agents/clusters/simulation/growth_simulator_agent.py` - thermal factor now sourced from heat-transfer simulation
- `mycosoft_mas/simulation/mycelium.py` - nutrient and signal updates now physics-aware
- `mycosoft_mas/core/myca_main.py` - includes `physicsnemo_api` router when available
- `WEBSITE/website/services/earth2-inference/inference_server.py` - no mock fallback; includes `/physics-correction`
- `WEBSITE/website/components/crep/earth2/earth2-layer-control.tsx` - UI labels indicate PhysicsNeMo-backed weather workflows
- `WEBSITE/website/lib/earth2/client.ts` - disables generated mock weather/spore fallback for key runtime calls

## Physics API Surface

PhysicsNeMo local service:

- `GET /health`
- `GET /gpu/status`
- `GET /physics/models`
- `POST /physics/models/load`
- `POST /physics/models/unload`
- `POST /physics/diffusion`
- `POST /physics/heat-transfer`
- `POST /physics/fluid-flow`
- `POST /physics/reaction`
- `POST /physics/neural-operator`
- `POST /physics/pinn`

MAS proxy:

- `GET /api/physics/health`
- `GET /api/physics/gpu`
- `GET /api/physics/models`
- `POST /api/physics/simulate`
- `POST /api/physics/diffusion`
- `POST /api/physics/fluid`
- `POST /api/physics/heat`
- `POST /api/physics/reaction`

## Operational Notes

- Intended operating mode is PhysicsNeMo + Earth2 together; PersonaPlex voice should remain off in that mode if VRAM pressure rises.
- `scripts/local_gpu_services.py` can now proxy PhysicsNeMo via `/physics/{path}`.
- If PhysicsNeMo is unavailable, MAS simulation module uses deterministic CPU fallbacks (not mock generated scenario data).

## Validation Checklist

- Start container: `powershell -File scripts/start_physicsnemo.ps1`
- Health check: `curl http://localhost:8400/health`
- GPU status: `curl http://localhost:8400/gpu/status`
- MAS proxy check: `curl http://localhost:8001/api/physics/health`
- Earth2 correction check: `POST /physics-correction` on Earth2 inference server

