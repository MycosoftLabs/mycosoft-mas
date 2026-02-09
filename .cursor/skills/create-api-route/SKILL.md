---
name: create-api-route
description: Create a new Next.js API route for the Mycosoft website. Use when adding backend API endpoints, proxy routes to MAS/MINDEX, or webhook handlers.
---

# Create a Next.js API Route

## Steps

```
API Route Progress:
- [ ] Step 1: Create route file
- [ ] Step 2: Implement handlers
- [ ] Step 3: Test the endpoint
```

### Step 1: Create the route file

Create `app/api/your-endpoint/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    const response = await fetch(
      `${process.env.MAS_API_URL}/api/endpoint`,
      {
        headers: {
          'Content-Type': 'application/json',
        },
        next: { revalidate: 60 }, // Cache for 60 seconds
      }
    );

    if (!response.ok) {
      throw new Error(`Backend API error: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('API route error:', error);
    return NextResponse.json(
      { error: 'Service unavailable' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const response = await fetch(
      `${process.env.MAS_API_URL}/api/endpoint`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }
    );

    if (!response.ok) {
      throw new Error(`Backend API error: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('API route error:', error);
    return NextResponse.json(
      { error: 'Failed to process request' },
      { status: 500 }
    );
  }
}
```

### Step 2: Dynamic routes

Create `app/api/your-endpoint/[id]/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server';

interface RouteParams {
  params: Promise<{ id: string }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  const { id } = await params;

  try {
    const response = await fetch(
      `${process.env.MAS_API_URL}/api/endpoint/${id}`
    );
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }
}
```

### Step 3: Test the endpoint

```bash
# GET
curl http://localhost:3010/api/your-endpoint

# POST
curl -X POST http://localhost:3010/api/your-endpoint \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

## Key Rules

- Use env vars for backend URLs: `process.env.MAS_API_URL`, `process.env.MINDEX_API_URL`
- NEVER hardcode VM IPs in route handlers
- Always wrap in try/catch with proper error responses
- Return appropriate HTTP status codes
- No mock data -- all data from real backend APIs
- Log errors to console.error for debugging
