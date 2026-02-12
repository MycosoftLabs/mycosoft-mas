# Deprecated UniFi Dashboard Cleanup - Feb 12, 2026

## Summary

The deprecated `unifi-dashboard/` directory was permanently deleted from the MAS repo on Feb 12, 2026. This cleanup removed ~120 files of dead code that was causing confusion during development.

## What Was Deleted

| Category | Count | Description |
|----------|-------|-------------|
| React Components | 65+ | Old `.tsx` components (duplicate of website) |
| Pages | 8 | Old Next.js pages |
| Hooks | 5 | Custom React hooks |
| Lib files | 10+ | Utility functions |
| Config files | 6 | package.json, tailwind.config, next.config, etc. |
| **Total** | ~120 files | |

### Components That Were Deleted (all duplicates/superseded)

- `FCIMonitor.tsx` → Exists in `WEBSITE/website/components/fungi-compute/`
- `ElectrodeMap.tsx` → Superseded by `device-map.tsx`
- `SignalVisualizer.tsx` → Superseded by `oscilloscope.tsx`, `spectrum-analyzer.tsx`
- `MyceliumNetworkViz.tsx` → Exists in website
- `DeviceCard.tsx`, `DeviceGrid.tsx` → Exist in website
- `TelemetryChart.tsx` → Superseded by fungi-compute components
- `VoiceButton.tsx`, `VoiceOverlay.tsx` → Exist in website
- `PersonaPlexWidget.tsx` → Exists in website
- `ElevenLabsWidget.tsx` → Superseded by PersonaPlex (deprecated tech)
- `TalkToMYCA.tsx` → Superseded by test-voice page
- `ParticleGlobe.tsx` → Not needed
- UniFi network monitoring components → Feature not implemented

## What Remains (ALL Real Work Intact)

### MAS Backend (Python) - Unchanged

```
mycosoft_mas/
├── bio/fci.py                          # FCI core logic
├── devices/fci_driver.py               # FCI device driver
├── core/routers/fci_api.py             # FCI REST API
├── core/routers/fci_websocket.py       # FCI WebSocket
├── core/routers/memory_api.py          # Memory API
├── memory/                             # 15+ memory modules
│   ├── myca_memory.py
│   ├── graph_memory.py
│   ├── vector_memory.py
│   ├── session_memory.py
│   └── ... (12 more)
├── core/routers/                       # 50+ API routers
└── devices/                            # 11 device drivers
```

### Website Frontend (Next.js) - Unchanged

```
WEBSITE/website/
├── app/natureos/fungi-compute/page.tsx           # Main Fungi Compute page
├── components/fungi-compute/                      # 26 components
│   ├── oscilloscope.tsx
│   ├── spectrum-analyzer.tsx
│   ├── dashboard.tsx
│   ├── connection-status.tsx
│   ├── device-map.tsx
│   └── ... (21 more)
├── components/crep/fci/                          # FCI components
│   ├── fci-pattern-chart.tsx
│   └── fci-signal-widget.tsx
└── app/devices/mycobrain/integration/fci/page.tsx
```

## Why This Was Necessary

1. **Confusion**: The old dashboard was on ports 3001/3100, causing confusion with the real website on 3010
2. **Duplicate code**: All useful components had already been migrated to the website repo
3. **Wrong repo**: Frontend code should not live in the Python backend repo
4. **Dead code**: The dashboard was never connected to production systems

## Rules Created

A new rule was created at `.cursor/rules/deprecated-unifi-dashboard.mdc` to prevent future confusion:

- Website dev: `WEBSITE/website/` → `npm run dev:next-only` → `localhost:3010`
- MAS backend: `MAS/mycosoft-mas/` → Python/FastAPI only
- NEVER start a Next.js server from the MAS repo

## Related Updates

- `SYSTEM_STATUS_CURRENT.md` - Updated to remove deprecated port references
- `.cursor/rules/deprecated-unifi-dashboard.mdc` - New rule created
- `.cursor/rules/dev-server-3010.mdc` - Already enforced correct port

## Verification

After deletion, verified all real work intact:
- ✅ 50+ MAS core routers
- ✅ 15+ memory modules
- ✅ FCI driver, API, WebSocket
- ✅ 26 Fungi Compute website components
- ✅ 3 FCI website components
- ✅ All device drivers
