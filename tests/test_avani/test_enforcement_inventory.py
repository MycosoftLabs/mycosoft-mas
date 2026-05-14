from __future__ import annotations

from mycosoft_mas.avani.enforcement import ACTION_ROUTE_POLICIES, get_action_policy


ACTION_CAPABLE_ROUTES = {
    "/api/deploy/trigger",
    "/api/deploy/autonomous-fix",
    "/tools/execute",
    "/tools/execute/batch",
    "/workflows/execute",
    "/workflows/create",
    "/workflows/{workflow_id}",
    "/workflows/{workflow_id}/activate",
    "/workflows/{workflow_id}/deactivate",
    "/workflows/{workflow_id}/archive",
    "/workflows/{workflow_id}/restore",
    "/workflows/sync",
    "/workflows/sync-both",
    "/workflows/export-all",
    "/workflows/{workflow_id}/export",
    "/workflows/{workflow_id}/clone",
    "/workflows/scheduler/start",
    "/workflows/scheduler/stop",
    "/api/devices/{device_id}/command",
    "/api/devices/{device_id}",
    "/api/devices/{device_id}/fci-summary",
    "/api/iot/fleet/bulk/commands",
    "/api/iot/fleet/firmware/deploy",
    "/api/iot/fleet/provisioning",
    "/api/earth2/forecast",
    "/api/earth2/nowcast",
    "/api/earth2/downscale",
    "/api/earth2/spore-dispersal",
    "/api/serving/profiles",
    "/api/serving/bundles",
    "/api/serving/bundles/{bundle_id}/eval",
    "/api/serving/bundles/{bundle_id}/promote",
    "/api/serving/calibrate",
    "/api/nlm/training/start",
    "/api/nlm/training/stop",
    "/api/nlm/training/pause",
    "/api/nlm/training/resume",
    "/api/nlm/training/checkpoint",
    "/api/nlm/training/load",
    "/api/nlm/training/mutate",
    "/api/nlm/training/export",
    "/api/gpu-node/deploy/container",
    "/api/gpu-node/deploy/service",
    "/api/gpu-node/deploy/personaplex-split",
    "/api/gpu-node/containers/{name}",
    "/api/omnichannel/send",
    "/api/omnichannel/forward",
    "/api/redteam/authorize",
    "/api/redteam/simulate",
    "/api/redteam/credential-test",
    "/api/redteam/phishing-sim",
    "/api/redteam/pivot-test",
    "/api/redteam/exfil-test",
    "/api/redteam/simulation/{sim_id}/cancel",
    "/api/n8n/sandbox/execute",
    "/api/n8n/safety/request-confirmation",
    "/api/n8n/safety/submit-confirmation",
    "/api/sporebase/devices/{device_id}/command",
    "/api/sporebase/calibration/{calibration_id}",
    "/api/sporebase/order",
}


READ_ONLY_EXCLUSIONS = {
    "/health",
    "/api/avani/health",
    "/api/myca/world",
    "/api/myca/world/summary",
    "/api/myca/world/sources",
    "/api/serving/health",
}


def test_action_route_inventory_covers_known_action_capable_surfaces():
    missing = sorted(route for route in ACTION_CAPABLE_ROUTES if route not in ACTION_ROUTE_POLICIES)

    assert missing == []


def test_action_route_policies_are_fail_closed_except_explicit_read_only_sim_outputs():
    for route in ACTION_CAPABLE_ROUTES:
        policy = get_action_policy(route)
        assert policy is not None
        if route not in {"/api/earth2/forecast", "/api/earth2/nowcast"}:
            assert policy.fail_closed is True
        assert policy.risk_tier in {"low", "medium", "high", "critical"}
        assert 0.0 <= policy.reversibility <= 1.0


def test_read_only_routes_are_not_accidentally_gated_as_action_routes():
    assert READ_ONLY_EXCLUSIONS.isdisjoint(ACTION_ROUTE_POLICIES)
