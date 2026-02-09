---
name: create-nextjs-page
description: Create a new Next.js App Router page for the Mycosoft website. Use when adding a new page, route, or section to the website.
---

# Create a New Next.js Page

## Steps

```
Page Creation Progress:
- [ ] Step 1: Create page file
- [ ] Step 2: Add metadata
- [ ] Step 3: Implement component
- [ ] Step 4: Add to navigation/sitemap if needed
```

### Step 1: Create the page file

Create `app/your-page/page.tsx`:

```typescript
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Page Title | Mycosoft',
  description: 'Description for SEO',
};

export default async function YourPage() {
  // Fetch data server-side (React Server Component)
  const data = await fetchData();

  return (
    <main className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Page Title</h1>
      {/* Page content */}
    </main>
  );
}

async function fetchData() {
  try {
    const res = await fetch(`${process.env.MAS_API_URL}/api/endpoint`, {
      next: { revalidate: 60 }, // ISR: revalidate every 60s
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
```

### Step 2: For dynamic routes

Create `app/your-page/[id]/page.tsx`:

```typescript
interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function DetailPage({ params }: PageProps) {
  const { id } = await params;
  // Fetch by id
}
```

### Step 3: For pages with client interactivity

Create a server component page that renders a client component:

```typescript
// app/your-page/page.tsx (Server Component)
import { YourClientComponent } from '@/components/your-client-component';

export default function YourPage() {
  return (
    <main className="container mx-auto px-4 py-8">
      <YourClientComponent />
    </main>
  );
}
```

```typescript
// components/your-client-component.tsx (Client Component)
'use client';

import { useState } from 'react';

export function YourClientComponent() {
  const [state, setState] = useState(false);
  return <div>Interactive content</div>;
}
```

## Key Rules

- Default to React Server Components (no 'use client')
- Use `Metadata` export for SEO
- Fetch data server-side when possible
- Mobile-first with Tailwind CSS
- Use Shadcn UI components
- Connect to real APIs via env vars, NEVER mock data
- Add to sitemap.ts if the page should be indexed
