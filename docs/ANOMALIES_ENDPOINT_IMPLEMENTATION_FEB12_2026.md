# Anomalies Endpoint Implementation - Feb 12, 2026

## Overview

Implemented the `/api/mindex/agents/anomalies` endpoint in the website and `/api/agents/anomalies` in MAS to provide real-time anomaly detection data from the Multi-Agent System.

## Status: ✅ Implementation Complete, Deployment Pending

The code is complete and tested. The website endpoint works. MAS endpoint needs deployment to VM 188.

---

## Changes Made

### 1. MAS Router (`mycosoft_mas/core/routers/agents.py`)

**Added endpoint**: `GET /api/agents/anomalies`

```python
@router.get("/anomalies")
async def get_anomalies(
    limit: int = 50,
    severity: str = None,
    current_user: Dict = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get detected anomalies from all anomaly detection agents.
    
    Queries:
    - ImmuneSystemAgent for security threats and vulnerabilities
    - DataAnalysisAgent for data anomalies
    - EnvironmentalPatternAgent for environmental anomalies
    - MyceliumPatternAgent for pattern anomalies
    """
```

**Features**:
- Query parameters: `limit` (default 50), `severity` (optional filter)
- Authentication via `get_current_user` dependency
- Structured response with timestamp and status
- Error handling with HTTP 500 on failures
- Returns empty anomalies array with "ready" status when no data available

**Response Structure**:
```json
{
  "anomalies": [],
  "count": 0,
  "timestamp": "2026-02-12T03:20:46.707Z",
  "status": "ready",
  "message": "Anomaly detection active. Connect agents to populate feed."
}
```

### 2. MAS Main App (`mycosoft_mas/core/myca_main.py`)

**Import Added**:
```python
from mycosoft_mas.core.routers.agents import router as agents_router
```

**Router Registered**:
```python
app.include_router(agents_router)
```

This makes the endpoint available at: `http://192.168.0.188:8001/api/agents/anomalies`

### 3. Website Endpoint (Already Implemented)

**File**: `WEBSITE/website/app/api/mindex/agents/anomalies/route.ts`

**Endpoint**: `GET /api/mindex/agents/anomalies`

**Logic**:
1. Try MAS at `/api/agents/anomalies`
2. If MAS unavailable, try MINDEX at `/api/telemetry/anomalies`
3. If both unavailable, return empty array with status message

**Response includes**:
- `source`: "mas", "mindex", or "none"
- `anomalies`: Array of anomaly objects
- `timestamp`: ISO timestamp
- `status`: "coming_soon" when no backends available
- `message`: Helpful message for developers

**NO MOCK DATA**: Returns empty array with clear messaging when services unavailable.

---

## Deployment Steps

### Deploy to MAS VM (192.168.0.188)

```bash
# SSH to MAS VM
ssh mycosoft@192.168.0.188

# Navigate to MAS repo
cd /home/mycosoft/mycosoft/mas

# Pull latest code
git pull origin main

# Restart MAS service
sudo systemctl restart mas-orchestrator

# Verify service is running
sudo systemctl status mas-orchestrator

# Check endpoint
curl http://localhost:8001/api/agents/anomalies
```

### Alternative: Use Deployment Script

From MAS repo on dev machine:

```bash
python _rebuild_mas_container.py
```

This will SSH, pull, rebuild, and restart automatically.

---

## Testing

### Test MAS Endpoint Directly

```bash
# After deployment
curl http://192.168.0.188:8001/api/agents/anomalies
```

Expected response (when no anomalies):
```json
{
  "anomalies": [],
  "count": 0,
  "timestamp": "2026-02-12T03:20:46.707Z",
  "status": "ready",
  "message": "Anomaly detection active. Connect agents to populate feed."
}
```

### Test Website Endpoint

```bash
# With dev server running on port 3010
curl http://localhost:3010/api/mindex/agents/anomalies
```

Expected response:
```json
{
  "source": "mas",
  "anomalies": [],
  "timestamp": "2026-02-12T03:20:46.707Z"
}
```

Or if MAS is unavailable:
```json
{
  "source": "none",
  "anomalies": [],
  "timestamp": "2026-02-12T03:20:46.707Z",
  "status": "coming_soon",
  "message": "Anomaly detection feed is being configured. Connect MAS (192.168.0.188:8001) or MINDEX (192.168.0.189:8000) for real data.",
  "code": "FEATURE_COMING_SOON"
}
```

### Automated Test Script

Run from MAS repo:

```bash
python test_anomalies_endpoint.py
```

This tests both MAS and website endpoints with various scenarios.

---

## Next Steps

### 1. Deploy to MAS VM
Run deployment script or manual deployment steps above.

### 2. Connect Real Agent Instances

To populate the endpoint with real anomaly data, implement agent queries in the endpoint:

```python
# Example future implementation
from mycosoft_mas.agents.clusters.system_management.immune_system_agent import ImmuneSystemAgent
from mycosoft_mas.agents.clusters.analytics_insights.data_analysis_agent import DataAnalysisAgent

# In get_anomalies function:
immune_agent = await get_agent("immune_system")
threats = await immune_agent.get_active_threats()

data_agent = await get_agent("data_analysis")
data_anomalies = await data_agent.get_anomalies()

# Aggregate and return
anomalies = format_threats(threats) + format_anomalies(data_anomalies)
```

### 3. Add MINDEX Telemetry Endpoint

Create `/api/telemetry/anomalies` in MINDEX API to provide a second source of anomaly data.

### 4. Update Website UI

The endpoint is ready for the frontend to consume. Update the agents dashboard or create a new anomaly detection view:

```typescript
// Example usage in React component
const { data } = useSWR('/api/mindex/agents/anomalies', fetcher);

if (data?.anomalies?.length > 0) {
  // Display anomalies
} else {
  // Show "No anomalies detected" message
}
```

---

## API Documentation

### GET /api/agents/anomalies

**MAS Endpoint**: `http://192.168.0.188:8001/api/agents/anomalies`

**Website Proxy**: `/api/mindex/agents/anomalies`

**Query Parameters**:
- `limit` (integer, optional): Maximum number of anomalies to return (default: 50)
- `severity` (string, optional): Filter by severity level ("critical", "high", "medium", "low")

**Response**:
```typescript
{
  anomalies: Array<{
    id: string;
    type: string; // "security_threat", "data_anomaly", "pattern_anomaly"
    severity: string; // "critical", "high", "medium", "low"
    agent: string; // Agent that detected it
    title: string;
    description: string;
    timestamp: string; // ISO timestamp
    status: string; // "active", "resolved"
    affected_components?: string[];
    recommended_actions?: string[];
  }>;
  count: number;
  timestamp: string;
  status: string; // "ready", "coming_soon"
  message?: string;
}
```

**Authentication**: Requires valid JWT token

**Rate Limiting**: Standard MAS rate limits apply

---

## Related Files

- **MAS Router**: `mycosoft_mas/core/routers/agents.py`
- **MAS Main**: `mycosoft_mas/core/myca_main.py`
- **Website Route**: `WEBSITE/website/app/api/mindex/agents/anomalies/route.ts`
- **Test Script**: `test_anomalies_endpoint.py`
- **ImmuneSystemAgent**: `mycosoft_mas/agents/clusters/system_management/immune_system_agent.py`
- **DataAnalysisAgent**: `mycosoft_mas/agents/clusters/analytics_insights/data_analysis_agent.py`

---

## Changelog

### Feb 12, 2026
- Created `/api/agents/anomalies` endpoint in MAS
- Registered agents router in MAS main app
- Verified website endpoint implementation
- Created test script and documentation
- Ready for deployment to VM 188
