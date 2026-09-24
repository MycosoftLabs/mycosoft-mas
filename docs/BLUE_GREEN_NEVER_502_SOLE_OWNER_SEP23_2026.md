# Blue-Green Never 502 — Sole Owner Lock — September 23, 2026

**Date:** September 23, 2026  
**Status:** Active — hard policy (Morgan)  
**Owner:** Morgan Rockcoons  
**Applies to:** Sandbox website `192.168.0.187` (`sandbox.mycosoft.com`, `mycosoft.com`)  
**Related:** `CODE/docs/BLUE_GREEN_NO_DOWNTIME_RULE_JUL15_2026.md`, `.cursor/rules/blue-green-no-downtime-deploy.mdc`

---

## Prime directive

**During deploys, HTTP 502 Bad Gateway is NEVER allowed.** That is why we use blue-green. Nothing is allowed to walk on anything else — no racing restore vs cutover, no two agents flipping nginx, no swapping upstream until the new origin is proven **HTTP 200** while the old primary keeps serving.

---

## Sole owner

| Rule | Required behavior |
|------|-------------------|
| **One deploy owner** | Only **one** agent/session may mutate nginx, active-slot, or website containers for cutover at a time. |
| **Abort if contested** | If another deploy, restore, or `CUTOVER_FROZEN` / `deploy.lock` is present → **ABORT**. Do **not** touch nginx, do **not** reload proxy, do **not** stop the live upstream. |
| **Concurrent agents** | Parallel agents (build, docs, FormSpace, NLM scrub waiters) must **not** both mutate the proxy. Build may continue; cutover may not. |

Freeze file on VM (when set by ops): `/opt/mycosoft/state/CUTOVER_FROZEN`  
Active slot: `/opt/mycosoft/state/active-slot`  
Deploy lock: `/opt/mycosoft/state/deploy.lock`

---

## Cutover gates (no 502 path)

1. **Old primary keeps serving** until cutover is intentional and verified.
2. Probe the **candidate on its own container IP** (e.g. `http://<candidate-ip>:3000/` and `/api/health`). Require **HTTP 200**. Do **not** use a flapping public origin as the only health signal for a candidate you already pointed nginx at.
3. **Never** point nginx at unhealthy, `health: starting`, missing, or placeholder upstreams (`blue`, `green` aliases without a live container name, empty names).
4. Cut nginx **once**, only after candidate probe is 200 (prefer a short streak of 200s).
5. Keep the previous healthy container available for rollback until the new origin is proven through the proxy.

---

## Emergency restore

| Allowed | Forbidden |
|---------|-----------|
| Roll nginx only to an **already-proven** healthy container (direct IP probe = 200) | Race a Docker build or start a brand-new unproven image as the restore target |
| Start a **known-good image tag** (e.g. `mkt2-*`, `lp327-*`) with NAS mount, wait until IP probe 200, **then** point nginx | Point nginx first and “hope” the container becomes healthy |
| Stop non-sole candidates after sole upstream is proven | Delete the last-good container while restoring |

NAS mount required on any recreate:  
`-v /opt/mycosoft/media/website/assets:/app/public/assets:ro`

---

## What caused the Sep 23 502 flap (lesson)

NLM scrub blue-green build/cutover waiters raced emergency restore. Upstream was flipped while the live slot was unhealthy/restarting and under memory pressure from `next build`. A later freeze incorrectly treated slot name `blue` as a container and pointed nginx at a non-existent upstream → sustained 502. **Fix:** only freeze/cut to a container whose **own IP** returns 200; never trust slot labels alone.

---

## Agent checklist before any nginx edit

- [ ] Read `/opt/mycosoft/state/CUTOVER_FROZEN` — if `FROZEN=1`, stop.
- [ ] Read `/opt/mycosoft/state/deploy.lock` — if another owner, abort.
- [ ] Confirm current origin `http://127.0.0.1:3000/` is 200 **or** you are in restore-only with a proven healthy target IP.
- [ ] Candidate (if cutover): IP probe 200 before sed/reload.
- [ ] After reload: origin + public URLs 200 before claiming success.

---

## Cross-references

- Website rule: `WEBSITE/website/.cursor/rules/blue-green-no-downtime-deploy.mdc`
- MAS rule: `MAS/mycosoft-mas/.cursor/rules/blue-green-no-downtime-deploy.mdc`
- Deploy agent: `MAS/mycosoft-mas/.cursor/agents/deploy-pipeline.md`
