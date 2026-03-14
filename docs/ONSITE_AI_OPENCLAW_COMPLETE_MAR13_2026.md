# On-Site AI (OpenClaw) Integration Complete

**Date:** Mar 13, 2026  
**Status:** Complete  
**Related:** `docs/JETSON_MYCOBRAIN_PRODUCTION_DEPLOY_MAR13_2026.md`, `docs/MYCOBRAIN_GATEWAY_NODE_RECOGNITION_MAR13_2026.md`

---

## Summary

On-Site AI is now integrated into the Device Manager. Users can run OpenClaw on a Jetson or gateway, manage MycoBrain devices via MYCA and the Device Manager, and access OpenClaw (shell + GUI) directly from mycosoft.com.

---

## What Was Delivered

### 1. Network API: `openclaw_url` per device
- **File:** `WEBSITE/website/app/api/devices/network/route.ts`
- Each device from the MAS registry gets `openclaw_url: http://${device.host}:18789` when `device.host` is set.
- OpenClaw Control UI runs on port 18789 on the same host as the gateway.

### 2. Device Subnav: On-Site AI link
- **File:** `WEBSITE/website/components/natureos/device-subnav.tsx`
- Added **"On-Site AI"** next to Fleet in `NAV_ITEMS`.
- Route: `/natureos/devices/onsite-ai`

### 3. On-Site AI page
- **File:** `WEBSITE/website/app/natureos/devices/onsite-ai/page.tsx`
- Uses `DevicePageShell` with heading "On-Site AI" and descriptive text.
- Renders `OnSiteAIPanel` inside a Suspense boundary.

### 4. On-Site AI panel (client component)
- **File:** `WEBSITE/website/components/iot/onsite-ai-panel.tsx`
- Fetches `/api/devices/network?include_offline=true` via SWR (15s refresh).
- Groups devices by host; shows only hosts with `openclaw_url`.
- Per-host cards show:
  - Host IP
  - Device list (names/roles)
  - **"Open OpenClaw"** button → opens `http://<host>:18789` in a new tab
  - SSH shell instructions: `ssh mycosoft@<host>`
- Handles loading, error, and empty states (no OpenClaw hosts).
- Empty state message: run `install_openclaw.sh` on the Jetson.

---

## How to Verify

1. **OpenClaw running on Jetson:** Ensure OpenClaw is installed and running on port 18789 (see `deploy/jetson/install_openclaw.sh`).
2. **Device with host:** Devices must have a `host` field (gateway/Jetson IP) in the MAS device registry.
3. **Navigate:** Device Manager → **On-Site AI**.
4. **Expect:** Cards for each gateway host with devices; "Open OpenClaw" opens the Control UI in a new tab.
5. **Network:** User must be on the same LAN or VPN as the Jetson to reach `http://<host>:18789`.

---

## File Reference

| Purpose | Path |
|---------|------|
| On-Site AI page | `WEBSITE/website/app/natureos/devices/onsite-ai/page.tsx` |
| On-Site AI panel | `WEBSITE/website/components/iot/onsite-ai-panel.tsx` |
| Device subnav | `WEBSITE/website/components/natureos/device-subnav.tsx` |
| Network devices API | `WEBSITE/website/app/api/devices/network/route.ts` |
| OpenClaw install script | `MAS/mycosoft-mas/deploy/jetson/install_openclaw.sh` |

---

## Known Gaps / Follow-Up

- **Iframe embed:** OpenClaw UI opens in a new tab. An optional embedded iframe view could be added later.
- **SSH terminal:** Shell access is documented as `ssh mycosoft@<host>`; no in-browser terminal yet.
- **Tunnel/VPN:** For remote access, user must use VPN or Cloudflare Tunnel; not wired into On-Site AI UI.
