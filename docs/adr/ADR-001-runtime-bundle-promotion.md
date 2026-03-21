# ADR-001: Runtime Bundle Promotion

**Date:** 2026-03-21
**Status:** Accepted
**Authors:** MYCA Engineering

## Decision

The promotion unit in Plasticity Forge is a **deployment bundle**, not a bare model candidate.

A deployment bundle is:

```
deployment_bundle = {
    model_build_id,
    adapter_set_id,       # optional LoRA/adapter set
    serving_profile_id,   # cache_mode, target_stack, offload/transport policy
    kvtc_artifact_id,     # optional KVTC calibration artifact
    cache_policy,         # hot window, sink tokens, eviction rules
    target_alias,         # myca_core, myca_edge, avani_core, fallback_local
    target_runtime,       # vllm, lmcache, megatron, custom
}
```

## Context

Phase 1 adds serving optimization (KVTC KV-cache compression) as a first-class concern. Promoting only `model_build_id` ignores:

- **Serving profile:** cache mode, offload/transport policies, target stack
- **KVTC artifact:** PCA matrices, bitplans, compression target
- **Cache policy:** hot window size, sink tokens, eviction rules

This means production regressions from serving config drift are invisible to the promotion system. A model that passes eval with `kvtc16x` can silently run with `baseline` cache mode if serving config is managed separately.

## Consequences

1. All promotion decisions reference a `deployment_bundle_id`
2. The rollout state machine (`shadow` → `canary` → `active` → `rollback` → `retired`) operates on bundles
3. Rollback reverts to a prior bundle (model + serving config + cache policy), not just a prior model
4. Serving evals run against the full bundle, not just the model
5. `backend_selection.py` alias resolution consults the active bundle for a target alias
6. The existing `CandidateLifecycle` in `plasticity_contracts.py` remains valid — bundle promotion wraps it

## Alternatives Considered

- **Promote model only, configure serving separately:** Rejected — creates config drift and invisible regressions
- **Promote model + serving profile without cache policy:** Rejected — cache policy affects latency and memory, must be part of the promotion unit
