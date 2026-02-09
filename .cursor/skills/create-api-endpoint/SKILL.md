---
name: create-api-endpoint
description: Create a new FastAPI router and endpoints for the MAS system. Use when adding new API endpoints, creating new routers, or extending the MAS API surface.
---

# Create a New FastAPI API Endpoint

## Pattern

All API routers use FastAPI's `APIRouter` with prefix and tags, and are registered in `myca_main.py`.

## Steps

```
API Endpoint Creation Progress:
- [ ] Step 1: Create router file
- [ ] Step 2: Register in myca_main.py
- [ ] Step 3: Update API catalog
- [ ] Step 4: Test endpoints
```

### Step 1: Create the router file

Create `mycosoft_mas/core/routers/your_api.py`:

```python
"""Your API - Brief description of these endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Any, Dict, List, Optional


router = APIRouter(prefix="/api/your-domain", tags=["your-domain"])


class YourRequest(BaseModel):
    """Request model."""
    field: str
    optional_field: Optional[str] = None


class YourResponse(BaseModel):
    """Response model."""
    status: str
    data: Dict[str, Any]


@router.get("/health")
async def health():
    """Health check for this API domain."""
    return {"status": "healthy", "service": "your-domain"}


@router.post("/action", response_model=YourResponse)
async def perform_action(request: YourRequest):
    """Perform an action."""
    try:
        # Implementation here
        result = {"processed": request.field}
        return YourResponse(status="success", data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/items")
async def list_items():
    """List items."""
    return {"items": [], "count": 0}
```

### Step 2: Register in myca_main.py

Edit `mycosoft_mas/core/myca_main.py`:

```python
# Add import
from mycosoft_mas.core.routers.your_api import router as your_router

# Add router inclusion (in the router registration section)
app.include_router(your_router, tags=["your-domain"])
```

### Step 3: Update API catalog

Update `docs/API_CATALOG_FEB04_2026.md` with new endpoints:

```markdown
### Your Domain API
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/your-domain/health | GET | Health check |
| /api/your-domain/action | POST | Perform action |
| /api/your-domain/items | GET | List items |
```

### Step 4: Test endpoints

```bash
# Health check
curl http://192.168.0.188:8001/api/your-domain/health

# Test action
curl -X POST http://192.168.0.188:8001/api/your-domain/action \
  -H "Content-Type: application/json" \
  -d '{"field": "test"}'
```

## Key Rules

- Always include a `/health` endpoint per router
- Use Pydantic models for request/response validation
- Include proper error handling with HTTPException
- Use async endpoints
- Add tags for OpenAPI documentation grouping
- Update API_CATALOG after adding endpoints
