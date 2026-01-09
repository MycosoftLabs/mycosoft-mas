# Device Detection Fix - January 8, 2026

## Overview

Fixed an issue where COM ports without actual MycoBrain boards were being listed as MycoBrain devices in the NatureOS dashboard Overview tab. This was causing confusion when ports like COM1, COM2, and COM3 (which had no boards connected) were displayed as MycoBrain devices alongside the actual device on COM7.

## Problem Statement

The `minimal_mycobrain.py` service's `list_devices()` function was returning all connected devices without verifying they were actually MycoBrain boards. Additionally, the frontend hook `use-mycobrain.ts` had no filtering logic to exclude non-MycoBrain devices.

## Solution

### 1. Backend Verification (`minimal_mycobrain.py`)

Added a `verify_mycobrain_device()` function that:
- Sends a `status` command to the connected device
- Checks the JSON response for MycoBrain-specific fields:
  - `ok: true`
  - `side` (A or B)
  - `mdp_version`
  - `bme688_count`
  - `bme1` object
  - `uptime_ms`
- Falls back to text pattern matching for legacy firmware

Modified `connect_device()` endpoint to:
- Call `verify_mycobrain_device()` after opening serial connection
- Close the connection and return an error if verification fails
- Include `verified: true` and `device_info` in the response for verified devices

```python
def verify_mycobrain_device(ser) -> dict:
    """
    Verify that a serial device is actually a MycoBrain board
    """
    # ... verification logic
    return {
        "is_mycobrain": True/False,
        "device_info": {...},
        "error": None or "..."
    }
```

### 2. Frontend Filtering (`use-mycobrain.ts`)

Added filtering logic to `fetchDevices()`:
- Only includes devices with `verified: true` or `is_mycobrain: true`
- Also includes devices with MycoBrain-specific `device_info` fields
- Preserves existing connected devices for backward compatibility

```typescript
const rawDevices = (data.devices || []).filter((d: any) => {
  if (d.verified === true || d.is_mycobrain === true) return true
  if (d.device_info?.side || d.device_info?.mdp_version) return true
  // ... additional checks
  return false
})
```

### 3. Back Button Navigation (`mycobrain-device-manager.tsx`)

Added navigation header with:
- Back button to `/natureos/devices`
- Device count indicator when multiple devices are connected

## Files Modified

| File | Changes |
|------|---------|
| `minimal_mycobrain.py` | Added `verify_mycobrain_device()`, modified `connect_device()` |
| `hooks/use-mycobrain.ts` | Added device filtering in `fetchDevices()` |
| `components/mycobrain/mycobrain-device-manager.tsx` | Added back button navigation |

## Testing

After this fix:
- Only verified MycoBrain boards appear in the device list
- COM ports without boards are automatically filtered out
- Users can navigate back from device detail to device list
- Existing functionality remains unchanged

## Related Issues

- Device Manager defaulting to COM1 instead of COM7
- Overview tab showing incorrect device count
- No way to navigate back from device detail view
