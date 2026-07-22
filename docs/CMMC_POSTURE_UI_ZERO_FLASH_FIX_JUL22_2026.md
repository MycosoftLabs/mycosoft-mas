# CMMC Posture UI Zero-Flash Fix — July 22, 2026

**Date:** July 22, 2026  
**Status:** Implemented locally; MAS deployment pending restored VM access  
**Scope:** CMMC posture metadata only; no claim of CMMC certification or control completion.

## Incident

The Security compliance page periodically refreshed its control list. When MAS or its database was unavailable, the website API could return HTTP 200 with an empty controls array. The browser then appended its non-assessed reference catalog and painted a fabricated zero-Met / all-noncompliant posture before the next successful refresh.

## Never-again controls

1. The website Security API returns HTTP 503 and `posture_available: false` for an empty or failed live posture; it never represents that failure as zero compliance.
2. The compliance UI withholds all counts until it receives a validated posture or restores its session-scoped last-known-good snapshot. Failed refreshes retain that snapshot and show an unavailable/degraded banner.
3. The displayed CMMC percentage is the verified Met rate (`Met / 110`), not a weighted value that treats Partial as half complete.
4. MAS owns runtime detection. `mycosoft_mas/security/posture_integrity_monitor.py` runs with `mas-orchestrator`, normalizes NIST/CMMC mapping twins to 110 unique practices, detects an empty result, invalid total, or sudden non-zero-to-zero Met regression, logs at CRITICAL, and persists the last-known-good metadata snapshot in Redis 189 when configured.
5. MAS `/api/compliance/controls` and `/api/compliance/score` return the verified snapshot with `degraded: true` on a source anomaly, or HTTP 503 if no verified snapshot exists. `/api/security/posture-integrity` exposes the monitor health.

## MAS VM 188 deployment

1. Deploy these MAS repository files to the code checked out by `mas-orchestrator` on VM 188.
2. Pull the committed revision and restart `mas-orchestrator`; its FastAPI startup hook schedules the monitor at a 60-second cadence.
3. Verify `GET /api/security/posture-integrity`, `GET /api/compliance/controls`, and `GET /api/compliance/score`. A failed source must show `degraded: true` with a last-known-good snapshot, never a zero posture.

## Verification target

The authoritative CMMC count is 110 unique practices. Any UI score is `Met / 110`; Partial practices are reported separately and do not inflate the Met percentage.
