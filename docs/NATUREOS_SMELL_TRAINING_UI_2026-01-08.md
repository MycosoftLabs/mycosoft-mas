# NatureOS Smell Training UI - January 8, 2026

## Overview

Created a comprehensive smell training interface in the NatureOS dashboard, including a Model Training apps section and a dedicated Smell Training page with wizard, blob manager, and session history tabs.

## Changes

### 1. Model Training Page Enhancement

Added a "Smell Training Applications" section to the Model Training page (`/natureos/model-training`), positioned between the NLM training strategy and Research Foundation widget.

**New Components:**
- **Smell Training Wizard**: Link to `/natureos/smell-training`
- **Blob Manager**: Link to `/natureos/smell-training?tab=blobs`
- **Smell Encyclopedia**: Link to `/natureos/mindex?tab=smells`
- **Training Status Summary**: Shows Smell Trainer Agent status (port 8042)

### 2. New Smell Training Page

Created a full-featured smell training page at `/natureos/smell-training` with three tabs:

#### Training Wizard Tab
- **Port Selection**: Dropdown to select COM port for MycoBrain device
- **Session Control**: Create/end training sessions
- **Specimen Recording**: 
  - Label input with common fungal species presets
  - Duration slider (10-300 seconds)
  - Optional description field
  - Start/stop recording controls
- **QA Status**: Visual indicator of sensor count and sample requirements
- **Live Sensor Data**: Real-time BME688 readings display
- **Export Controls**: CSV and ZIP export buttons

#### Blob Manager Tab
- **Upload Form**: 
  - File input for `.config` blob files
  - Name and class labels input
  - Upload progress indicator
- **Blob List**: 
  - All uploaded blobs with status badges
  - Status promotion buttons (testing → active → deprecated)
  - Download as C header button

#### Session History Tab
- List of all past training sessions
- Session metadata (ID, port, date, sample count)
- Direct CSV/ZIP download links

### 3. Device Network Topology Enhancement

Enhanced the Device Network page (`/natureos/devices/network`) with:

- **Back Navigation**: Buttons to return to NatureOS Dashboard and Device Manager
- **Network Topology Visualization**:
  - Central gateway/serial hub display
  - Three connection type branches:
    - Serial/USB devices (blue)
    - LoRa Mesh devices (amber)
    - WiFi/BLE devices (purple)
  - Visual connection lines and status indicators
  - Legend for online/offline status
- **Verified Device Filtering**: Only shows confirmed MycoBrain devices
- **Stats Update**: Shows filtered device count with "other ports filtered" indicator

## Files Modified

### MAS Repository
None (backend changes documented separately)

### Website Repository

| File | Action | Description |
|------|--------|-------------|
| `app/natureos/model-training/page.tsx` | MODIFIED | Added Smell Training Apps section |
| `app/natureos/smell-training/page.tsx` | CREATED | Full smell training page |
| `app/natureos/devices/network/page.tsx` | MODIFIED | Added topology visualization |

## UI Components Used

- Tabs, TabsList, TabsTrigger, TabsContent
- Card, CardHeader, CardContent, CardFooter
- Button, Badge, Progress, Slider
- Input, Label
- Alert, AlertTitle, AlertDescription
- ScrollArea, Separator

## API Integration

The Smell Training UI communicates with the Smell Trainer Agent at `http://localhost:8042`:

```typescript
const TRAINER_API = process.env.NEXT_PUBLIC_SMELL_TRAINER_URL || "http://localhost:8042"
```

Key API calls:
- `GET /health` - Check agent status
- `GET /ports` - List available ports
- `POST /sessions` - Create training session
- `POST /sessions/{id}/record` - Start recording
- `GET /sessions/{id}/status` - Poll recording status
- `GET /sessions/{id}/qa` - Check QA requirements
- `GET /sessions/{id}/export.csv` - Export data
- `POST /mindex/blobs` - Upload blob
- `GET /mindex/blobs` - List blobs

## Environment Variables

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_SMELL_TRAINER_URL` | URL of Smell Trainer Agent (default: `http://localhost:8042`) |

## Screenshot Descriptions

### Model Training Page
- New "Smell Training Applications" card with three app tiles
- Green-themed styling matching NatureOS design
- Status indicator showing agent availability

### Smell Training Wizard
- Three-column layout on desktop
- Left: Port selection and session control
- Center: Specimen recording form
- Right: Live sensor data and recorded specimens list

### Device Network Topology
- Visual tree diagram showing device connections
- Gateway at top, three branches for connection types
- Clickable device nodes linking to Device Manager
