# CREP Dashboard - Aircraft/Vessel/Satellite Marker Fixes

**Date:** January 16, 2026  
**Author:** Cursor AI Assistant  
**Status:** ✅ RESOLVED

---

## Executive Summary

Fixed critical crashes that occurred when clicking on aircraft, vessel, and satellite markers on the CREP dashboard. The crashes were caused by unguarded `.toFixed()` calls on undefined values.

---

## Issue Description

**Symptoms:**
- Clicking on an aircraft marker crashed the CREP website with "Something went wrong!"
- Clicking on a vessel marker crashed the CREP website
- Clicking on a satellite marker potentially crashed the website
- Error message: `Cannot read properties of undefined (reading 'toFixed')`

**Impact:**
- Users could not view aircraft, vessel, or satellite details
- Entire CREP dashboard became unusable after clicking these markers

---

## Root Cause Analysis

The crashes were caused by calling `.toFixed()` on properties that could be `undefined`:

### Affected Files:

| File | Issue |
|------|-------|
| `components/crep/panels/entity-detail-panel.tsx` | Multiple unguarded `.toFixed()` calls for latitude, longitude, altitude, velocity, inclination |
| `components/crep/vessel-tracker-widget.tsx` | Unguarded `.toFixed()` call for `properties.sog` |

---

## Fixes Applied

### 1. `entity-detail-panel.tsx` - FungalDetail Component

**Before:**
```typescript
{observation.latitude.toFixed(3)}°, {observation.longitude.toFixed(3)}°
```

**After:**
```typescript
{typeof observation.latitude === 'number' ? observation.latitude.toFixed(3) : '—'}°, {typeof observation.longitude === 'number' ? observation.longitude.toFixed(3) : '—'}°
```

### 2. `entity-detail-panel.tsx` - AircraftDetail Component

**Before:**
```typescript
<span className="text-cyan-400 font-mono">{aircraft.latitude.toFixed(3)}°, {aircraft.longitude.toFixed(3)}°</span>
```

**After:**
```typescript
<span className="text-cyan-400 font-mono">{typeof aircraft.latitude === 'number' ? aircraft.latitude.toFixed(3) : '—'}°, {typeof aircraft.longitude === 'number' ? aircraft.longitude.toFixed(3) : '—'}°</span>
```

### 3. `entity-detail-panel.tsx` - VesselDetail Component

**Before:**
```typescript
{vessel.latitude.toFixed(4)}°, {vessel.longitude.toFixed(4)}°
```

**After:**
```typescript
{typeof vessel.latitude === 'number' ? vessel.latitude.toFixed(4) : '—'}°, {typeof vessel.longitude === 'number' ? vessel.longitude.toFixed(4) : '—'}°
```

### 4. `entity-detail-panel.tsx` - SatelliteDetail Component

**Before:**
```typescript
{satellite.inclination && (
  <>
    <span className="text-gray-500">Inclination</span>
    <span className="text-white">{satellite.inclination.toFixed(1)}°</span>
  </>
)}
```

**After:**
```typescript
{typeof satellite.inclination === 'number' && (
  <>
    <span className="text-gray-500">Inclination</span>
    <span className="text-white">{satellite.inclination.toFixed(1)}°</span>
  </>
)}
```

Also fixed satellite coordinates:
```typescript
{typeof satellite.latitude === 'number' ? satellite.latitude.toFixed(2) : '—'}°, {typeof satellite.longitude === 'number' ? satellite.longitude.toFixed(2) : '—'}°
```

### 5. `vessel-tracker-widget.tsx`

**Before:**
```typescript
const speedKnots = properties?.sog != null ? properties.sog.toFixed(1) : "0.0"
```

**After:**
```typescript
const speedKnots = typeof properties?.sog === 'number' ? properties.sog.toFixed(1) : "0.0"
```

---

## Testing Results

After applying fixes and rebuilding Docker container:

| Marker Type | Click Test | Popup Display | No Crash |
|-------------|------------|---------------|----------|
| ✅ Aircraft | Working | Shows callsign, altitude, speed, heading, LAT/LON coordinates | Yes |
| ✅ Vessel | Working | Shows name, MMSI, SOG, COG, heading, LAT/LON coordinates | Yes |
| ✅ Satellite | Working | Shows NORAD ID, altitude (424 km ✓), position, period, inclination | Yes |
| ✅ Fungal | Working | Shows species, location, photo | Yes |
| ✅ Event | Working | Shows event type, severity, location | Yes |

### Specific Verification - Satellite Altitude Fix

**Before Fix:**
- ISS (ZARYA) displayed: `ALTITUDE: 423,863 km` ❌

**After Fix:**
- ISS (ZARYA) displays: `ALTITUDE: 424 km` ✅

---

## Best Practices Applied

### Defensive Coding Pattern for `.toFixed()`:

```typescript
// ❌ Bad - crashes if value is undefined
{value.toFixed(2)}

// ✅ Good - safe with fallback
{typeof value === 'number' ? value.toFixed(2) : '—'}
```

### Alternative Patterns:

```typescript
// Using optional chaining (may still fail on undefined)
{value?.toFixed?.(2) ?? '—'}

// Using nullish coalescing with fallback
{(value ?? 0).toFixed(2)}
```

---

## Additional Fixes Applied (Session 2)

### 6. `aircraft-marker.tsx` - Added Coordinates and Detailed Data to Popup

Added comprehensive position and flight data display:
- **LAT/LON coordinates** with 5 decimal precision
- **Altitude** in feet
- **Speed** in knots
- **Heading** in degrees
- **Registration number**
- **Squawk code**

### 7. `vessel-marker.tsx` - Added Coordinates and Detailed Data to Popup

Added comprehensive position and navigation data display:
- **LAT/LON coordinates** with 5 decimal precision
- **MMSI** identification
- **SOG (Speed Over Ground)** in knots
- **COG (Course Over Ground)** in degrees
- **Heading** in degrees
- **Draught** in meters

### 8. `satellite-marker.tsx` - Fixed Altitude Unit Conversion

**Issue:** Satellite altitude was showing 423,863 km instead of ~423 km

**Root Cause:** The `estimatedPosition.altitude` from the connector was in meters (multiplied by 1000), but the UI was displaying it as-is with "km" label.

**Fix:**
```typescript
// Before - wrong units
const alt = satellite?.estimatedPosition?.altitude ?? satellite?.orbitalParams?.apogee ?? 0;

// After - proper conversion
const rawAlt = satellite?.estimatedPosition?.altitude ?? null;
const altKm = rawAlt !== null ? rawAlt / 1000 : (satellite?.orbitalParams?.apogee ?? 0);
```

### 9. `entity-detail-panel.tsx` - Fixed Satellite Altitude in Detail Panel

**Issue:** Same altitude unit conversion issue in the EntityDetailPanel's SatelliteDetail component.

**Fix:**
```typescript
// Before - raw altitude (in meters) was being used directly
const altitude = satellite.estimatedPosition?.altitude ?? satellite.orbitalParams?.apogee ?? 0;

// After - proper conversion from meters to km
const rawAltitude = satellite.estimatedPosition?.altitude ?? null;
const altitude = rawAltitude !== null ? rawAltitude / 1000 : (satellite.orbitalParams?.apogee ?? 0);
```

Also simplified the display logic:
```typescript
// Before - confusing conditional
{typeof altitude === 'number' ? (altitude > 1000 ? altitude.toFixed(0) : Math.round(altitude / 1000)) : 0} km

// After - clean display
{typeof altitude === 'number' ? Math.round(altitude) : 0} km
```

---

## Files Modified

1. `website/components/crep/panels/entity-detail-panel.tsx` - 6 fixes (including satellite altitude conversion)
2. `website/components/crep/vessel-tracker-widget.tsx` - 1 fix
3. `website/components/crep/markers/aircraft-marker.tsx` - Added coordinates and detailed flight data
4. `website/components/crep/markers/vessel-marker.tsx` - Added coordinates and detailed navigation data
5. `website/components/crep/markers/satellite-marker.tsx` - Fixed altitude unit conversion (meters to km)

---

## Deployment

Docker container rebuilt with `--no-cache` and restarted:

```bash
docker-compose build --no-cache website
docker-compose up -d website
```

---

## Related Documentation

- `docs/CREP_MARKER_CLICK_FIX_AUDIT.md` - Previous fixes for marker click issues
