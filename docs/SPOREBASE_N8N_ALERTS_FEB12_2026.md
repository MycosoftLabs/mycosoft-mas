# SporeBase n8n Alert Workflows

**Created:** February 12, 2026

This document describes n8n workflows for SporeBase alerts. Import the workflow JSON into n8n (VM 188 or local) and activate.

## Workflows to Configure

| Workflow | Trigger | Action |
|----------|---------|--------|
| **High spore count** | Schedule or webhook from MAS/SporeBase API when `spore_count` exceeds threshold | Notify (email, Slack, or internal alert API) |
| **Device offline** | Schedule: check MAS `/api/sporebase/devices`, filter `status === "offline"` | Notify for each offline device |
| **Tape exhaustion** | Webhook or schedule: when tape position/segment near end (e.g. segment_number &gt; 2800) | Notify maintenance |
| **Calibration due** | Schedule: query MAS `/api/sporebase/calibration/{id}` or MINDEX; compare `performed_at` to policy (e.g. 90 days) | Notify for devices due for calibration |

## Implementation Notes

- **Trigger sources:** Use MAS API `GET /api/sporebase/devices` and `GET /api/sporebase/devices/{id}/telemetry` for device and telemetry checks. Use cron/schedule node for periodic checks.
- **Thresholds:** Configure in n8n static data or environment: e.g. `SPOREBASE_SPORE_ALERT_THRESHOLD`, `SPOREBASE_TAPE_WARNING_SEGMENT`, `SPOREBASE_CALIBRATION_DAYS`.
- **Notifications:** Use n8n Slack node, Send Email node, or HTTP Request to your internal alert/notification API.

## Importing the Workflow

1. Open n8n (http://192.168.0.188:5678 or local).
2. Create new workflow or use **Import from File**.
3. Use the JSON in `docs/sporebase_n8n_alert_workflow.json` (if present) as a starting template, or build manually from the table above.

## Related

- MAS SporeBase API: `mycosoft_mas/core/routers/sporebase_api.py`
- Website SporeBase dashboard: `components/dashboard/sporebase-dashboard.tsx`
- Device registry (SporeBase role): `mycosoft_mas/core/routers/device_registry_api.py`
