# SUPABASE AUTHENTICATION QUICKSTART

**Document Version**: 1.0.0  
**Date**: 2026-01-17  
**Priority**: 🔴 CRITICAL - PHASE 1  
**Estimated Time**: 2-4 hours

---

## 🚀 QUICK START STEPS

### Step 1: Install Supabase SDK

```bash
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
npm install @supabase/supabase-js @supabase/ssr
```

### Step 2: Configure Environment Variables

Add to `.env.local`:
```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://hnevnsxnhfibhbsipqvz.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_CKkfrniLH2865uGRsVKr7g_w5CVl1FI
```

### Step 3: Create Supabase Client Files

#### Browser Client (`lib/supabase/client.ts`)
```typescript
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
```

#### Server Client (`lib/supabase/server.ts`)
```typescript
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createClient() {
  const cookieStore = await cookies()

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            )
          } catch {
            // Ignore in Server Component
          }
        },
      },
    }
  )
}
```

#### Middleware Client (`lib/supabase/middleware.ts`)
```typescript
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({
    request,
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
          supabaseResponse = NextResponse.next({
            request,
          })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  // Refresh session if needed
  const { data: { user } } = await supabase.auth.getUser()

  return supabaseResponse
}
```

### Step 4: Create Auth Middleware (`middleware.ts`)

```typescript
import { type NextRequest } from 'next/server'
import { updateSession } from '@/lib/supabase/middleware'

export async function middleware(request: NextRequest) {
  return await updateSession(request)
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
```

### Step 5: Create Login Page (`app/auth/login/page.tsx`)

```tsx
'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()
  const supabase = createClient()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (error) {
      setError(error.message)
      setLoading(false)
    } else {
      router.push('/dashboard')
      router.refresh()
    }
  }

  const handleMagicLink = async () => {
    setLoading(true)
    setError(null)

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    })

    if (error) {
      setError(error.message)
    } else {
      setError('Check your email for the login link!')
    }
    setLoading(false)
  }

  const handleGoogleLogin = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    })
    if (error) setError(error.message)
  }

  const handleGitHubLogin = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'github',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    })
    if (error) setError(error.message)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-background to-muted p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">Welcome to Mycosoft</CardTitle>
          <CardDescription>Sign in to access your dashboard</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-2">
              <Input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {error && (
              <p className={`text-sm ${error.includes('Check your email') ? 'text-green-600' : 'text-red-600'}`}>
                {error}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Loading...' : 'Sign In'}
            </Button>
          </form>

          <div className="my-4 flex items-center">
            <div className="flex-1 border-t" />
            <span className="px-4 text-sm text-muted-foreground">or</span>
            <div className="flex-1 border-t" />
          </div>

          <div className="space-y-2">
            <Button variant="outline" className="w-full" onClick={handleMagicLink} disabled={loading || !email}>
              Send Magic Link
            </Button>
            <Button variant="outline" className="w-full" onClick={handleGoogleLogin}>
              Continue with Google
            </Button>
            <Button variant="outline" className="w-full" onClick={handleGitHubLogin}>
              Continue with GitHub
            </Button>
          </div>
        </CardContent>
        <CardFooter className="text-center text-sm text-muted-foreground">
          <p className="w-full">
            Don't have an account?{' '}
            <a href="/auth/signup" className="text-primary hover:underline">
              Sign up
            </a>
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}
```

### Step 6: Create Auth Callback Route (`app/auth/callback/route.ts`)

```typescript
import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')
  const next = searchParams.get('next') ?? '/dashboard'

  if (code) {
    const supabase = await createClient()
    const { error } = await supabase.auth.exchangeCodeForSession(code)
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`)
    }
  }

  return NextResponse.redirect(`${origin}/auth/login?error=Could not authenticate`)
}
```

### Step 7: Create Logout Route (`app/auth/logout/route.ts`)

```typescript
import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  const supabase = await createClient()
  await supabase.auth.signOut()
  
  return NextResponse.redirect(new URL('/auth/login', request.url))
}
```

### Step 8: Create User Hook (`hooks/useUser.ts`)

```typescript
'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import type { User } from '@supabase/supabase-js'

export function useUser() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const supabase = createClient()

  useEffect(() => {
    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      setUser(user)
      setLoading(false)
    }

    getUser()

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_, session) => {
      setUser(session?.user ?? null)
      setLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [supabase.auth])

  return { user, loading }
}
```

### Step 9: Protect Routes (Server-Side)

```typescript
// app/dashboard/page.tsx
import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

export default async function DashboardPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  return (
    <div>
      <h1>Welcome, {user.email}</h1>
      {/* Dashboard content */}
    </div>
  )
}
```

---

## ✅ VERIFICATION CHECKLIST

- [ ] SDK installed (`@supabase/supabase-js`, `@supabase/ssr`)
- [ ] Environment variables configured
- [ ] Supabase client files created
- [ ] Middleware configured
- [ ] Login page working
- [ ] Magic link authentication working
- [ ] OAuth (Google/GitHub) configured in Supabase dashboard
- [ ] Auth callback route working
- [ ] Protected routes redirecting
- [ ] Logout working

---

## 🔧 SUPABASE DASHBOARD CONFIGURATION

### Enable OAuth Providers

1. Go to: https://supabase.com/dashboard/project/hnevnsxnhfibhbsipqvz/auth/providers
2. Enable Google:
   - Client ID: From Google Cloud Console
   - Client Secret: From Google Cloud Console
3. Enable GitHub:
   - Client ID: From GitHub OAuth App
   - Client Secret: From GitHub OAuth App

### Configure Redirect URLs

1. Go to: https://supabase.com/dashboard/project/hnevnsxnhfibhbsipqvz/auth/url-configuration
2. Add Redirect URLs:
   - `http://localhost:3000/auth/callback` (development)
   - `https://mycosoft.com/auth/callback` (production)
   - `https://sandbox.mycosoft.com/auth/callback` (staging)

---

## 🔗 RELATED DOCUMENTATION

- [Full Integration Plan](./SUPABASE_INTEGRATION_PLAN.md)
- [Supabase Auth Docs](https://supabase.com/docs/guides/auth)
- [Next.js App Router Auth](https://supabase.com/docs/guides/auth/server-side/nextjs)

---

**Created**: 2026-01-17  
**Author**: AI Development Agent
