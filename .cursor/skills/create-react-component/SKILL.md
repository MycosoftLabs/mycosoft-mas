---
name: create-react-component
description: Create a React component following Mycosoft patterns with Shadcn UI, Radix, and Tailwind CSS. Use when building new UI components, widgets, or interactive elements.
---

# Create a React Component

## Pattern

All components use functional style with TypeScript interfaces, Shadcn UI, and Tailwind CSS.

## Steps

```
Component Creation Progress:
- [ ] Step 1: Define the interface
- [ ] Step 2: Create the component
- [ ] Step 3: Export and organize
```

### Step 1: Create the component file

Create `components/your-component.tsx`:

```typescript
import { cn } from '@/lib/utils';

interface YourComponentProps {
  title: string;
  description?: string;
  isLoading?: boolean;
  className?: string;
}

export function YourComponent({
  title,
  description,
  isLoading = false,
  className,
}: YourComponentProps) {
  if (isLoading) {
    return <div className={cn("animate-pulse bg-muted rounded-lg h-32", className)} />;
  }

  return (
    <div className={cn("rounded-lg border bg-card p-6", className)}>
      <h3 className="text-lg font-semibold">{title}</h3>
      {description && (
        <p className="text-sm text-muted-foreground mt-2">{description}</p>
      )}
    </div>
  );
}
```

### With Shadcn UI Components

```typescript
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export function StatusCard({ title, status }: StatusCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          {title}
          <Badge variant={status === 'online' ? 'default' : 'destructive'}>
            {status}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Content */}
      </CardContent>
    </Card>
  );
}
```

### Client Component (only when needed)

```typescript
'use client';

import { useState, useCallback } from 'react';

export function InteractiveComponent() {
  const [isOpen, setIsOpen] = useState(false);
  const handleToggle = useCallback(() => setIsOpen(prev => !prev), []);
  // ...
}
```

## Key Rules

- Use TypeScript `interface` (not `type`) for props
- Named exports (not default exports)
- Use `cn()` utility for conditional classes
- Mobile-first Tailwind: base styles, then `md:`, `lg:` breakpoints
- Minimize `use client` -- only for interactivity (useState, useEffect, event handlers)
- Avoid enums, use maps instead
- Descriptive names: `isLoading`, `hasError`, `canSubmit`
- NEVER include mock/fake data in components
