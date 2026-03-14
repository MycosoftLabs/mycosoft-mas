# Supabase OAuth Parity: mycosoft.com vs sandbox.mycosoft.com

**Date:** March 14, 2026  
**Status:** Checklist for verification  
**Supabase project:** `hnevnsxnhfibhbsipqvz` (production)

---

## Auth Flow (Shared)

Both sandbox and production use the **same Supabase project**. OAuth flow:

1. User on `mycosoft.com` (or `sandbox.mycosoft.com`) clicks "Continue with Google/GitHub"
2. `LoginForm.tsx` uses `window.location.origin` → callback URL = `{origin}/auth/callback?next=...`
3. Supabase redirects to Google/GitHub with redirect_uri = `https://hnevnsxnhfibhbsipqvz.supabase.co/auth/v1/callback`
4. Provider redirects back to Supabase with code
5. Supabase redirects to our `redirectTo` URL (e.g. `https://mycosoft.com/auth/callback`)
6. `/auth/callback` exchanges code for session and sets cookies

---

## Supabase Dashboard Checklist

**Project:** https://supabase.com/dashboard/project/hnevnsxnhfibhbsipqvz

### Authentication → URL Configuration

| Setting | Value | Notes |
|--------|-------|-------|
| **Site URL** | `https://mycosoft.com` | Primary production domain |
| **Redirect URLs** | Add ALL of: | Comma-separated or one per line |
| | `https://mycosoft.com/auth/callback` | Production |
| | `https://www.mycosoft.com/auth/callback` | If www is used |
| | `https://sandbox.mycosoft.com/auth/callback` | Sandbox |
| | `http://localhost:3010/auth/callback` | Local dev |

**Critical:** `mycosoft.com/auth/callback` must be in Redirect URLs or Google/GitHub login will fail with "Redirect URL not allowed".

### Authentication → Providers

| Provider | Status | Callback URL (in provider console) |
|----------|--------|-----------------------------------|
| **Google** | Enable | `https://hnevnsxnhfibhbsipqvz.supabase.co/auth/v1/callback` |
| **GitHub** | Enable | `https://hnevnsxnhfibhbsipqvz.supabase.co/auth/v1/callback` |

The callback URL is **Supabase’s** — same for sandbox and production.

---

## Google Cloud Console

**OAuth 2.0 Client (Web application):**

- **Authorized redirect URIs:** `https://hnevnsxnhfibhbsipqvz.supabase.co/auth/v1/callback`
- No change needed for mycosoft.com — Supabase is the OAuth callback target.

**Authorized JavaScript origins** (if used):  
- `https://mycosoft.com`  
- `https://www.mycosoft.com`  
- `https://sandbox.mycosoft.com`  
- `http://localhost:3010` (dev)

---

## GitHub OAuth App

**Authorization callback URL:** `https://hnevnsxnhfibhbsipqvz.supabase.co/auth/v1/callback`  
- No change needed for mycosoft.com.

---

## Verification Steps

1. **Supabase Dashboard**
   - [ ] Site URL = `https://mycosoft.com`
   - [ ] Redirect URLs include `https://mycosoft.com/auth/callback` and `https://sandbox.mycosoft.com/auth/callback`
   - [ ] Google and GitHub providers enabled

2. **Google**
   - [ ] Login on https://mycosoft.com/login with Google → works
   - [ ] Login on https://sandbox.mycosoft.com/login with Google → works

3. **GitHub**
   - [ ] Login on https://mycosoft.com/login with GitHub → works
   - [ ] Login on https://sandbox.mycosoft.com/login with GitHub → works

4. **Magic link**
   - [ ] Magic link from mycosoft.com lands on mycosoft.com (emailRedirectTo uses `window.location.origin`)

---

## Code References

| File | Role |
|------|------|
| `WEBSITE/website/app/login/LoginForm.tsx` | Uses `window.location.origin` for callback |
| `WEBSITE/website/app/auth/callback/route.ts` | Exchanges code, uses `x-forwarded-host` for origin |
| `WEBSITE/website/lib/supabase/client.ts` | Uses `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Redirect URL not allowed" | `mycosoft.com/auth/callback` missing in Supabase Redirect URLs | Add it in Supabase Dashboard |
| Redirects to sandbox after login on mycosoft.com | `NEXT_PUBLIC_SITE_URL` or origin detection wrong | Verify env and `x-forwarded-host` in callback |
| Google/GitHub "invalid redirect" | Provider callback not set to Supabase URL | Set to `https://hnevnsxnhfibhbsipqvz.supabase.co/auth/v1/callback` |
