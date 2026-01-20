# API Keys Setup Guide

This guide explains how to obtain and configure all required API keys for Mycosoft.

## Quick Status Check

Run this to check which keys are configured:
```powershell
.\scripts\check_api_keys.ps1
```

---

## Required Keys (Must Have)

### 1. Supabase (Already Configured ✅)

Your Supabase project: `hnevnsxnhfibhbsipqvz`

| Variable | Status | Where to Get |
|----------|--------|--------------|
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ Configured | Dashboard → Settings → API |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ Configured | Dashboard → Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | ⚠️ Needed | Dashboard → Settings → API → service_role |

**To get Service Role Key:**
1. Go to: https://supabase.com/dashboard/project/hnevnsxnhfibhbsipqvz/settings/api
2. Under "Project API keys", copy the `service_role` key (keep secret!)
3. Add to `.env`: `SUPABASE_SERVICE_ROLE_KEY=your_key_here`

---

### 2. NextAuth Secret (Generated ✅)

| Variable | Status | How to Generate |
|----------|--------|-----------------|
| `NEXTAUTH_SECRET` | ✅ Generated | Run `scripts/generate_nextauth_secret.ps1` |

**Value generated:**
```
NEXTAUTH_SECRET=hMG8sSNcsxX/W7DXUxsDpJ7m0VxPRCoNLWnrxUK7pLs=
```

Add this to the VM's `.env` file.

---

## Recommended Keys (For Full Functionality)

### 3. OpenAI API Key

**Purpose:** Embeddings, AI chat, content generation

| Variable | Where to Get |
|----------|--------------|
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |

**Steps:**
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (starts with `sk-`)
4. Add to `.env`: `OPENAI_API_KEY=sk-your_key_here`

**Cost:** Pay-as-you-go, ~$0.002/1K tokens for embeddings

---

### 4. Google OAuth (For Google Sign-In)

**Purpose:** Allow users to sign in with Google

| Variable | Where to Get |
|----------|--------------|
| `GOOGLE_CLIENT_ID` | Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | Google Cloud Console |

**Steps:**
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new project or select existing
3. Click "Create Credentials" → "OAuth client ID"
4. Application type: "Web application"
5. Add authorized redirect URIs:
   - `http://localhost:3000/auth/callback`
   - `https://sandbox.mycosoft.com/auth/callback`
   - `https://mycosoft.com/auth/callback`
6. Copy Client ID and Client Secret
7. Add to `.env`:
   ```
   GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your_client_secret
   ```

---

### 5. GitHub OAuth (For GitHub Sign-In)

**Purpose:** Allow users to sign in with GitHub

| Variable | Where to Get |
|----------|--------------|
| `GITHUB_CLIENT_ID` | GitHub Developer Settings |
| `GITHUB_CLIENT_SECRET` | GitHub Developer Settings |

**Steps:**
1. Go to https://github.com/settings/developers
2. Click "New OAuth App"
3. Fill in:
   - Application name: `Mycosoft`
   - Homepage URL: `https://mycosoft.com`
   - Authorization callback URL: `https://sandbox.mycosoft.com/auth/callback`
4. Click "Register application"
5. Copy Client ID
6. Click "Generate a new client secret" and copy it
7. Add to `.env`:
   ```
   GITHUB_CLIENT_ID=your_client_id
   GITHUB_CLIENT_SECRET=your_client_secret
   ```

---

### 6. Google Maps API Key (Already Configured ✅)

| Variable | Status |
|----------|--------|
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | ✅ Configured |

---

## Optional Keys (For Enhanced Features)

### 7. Anthropic API Key

**Purpose:** Claude AI integration

| Variable | Where to Get |
|----------|--------------|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/settings/keys |

---

### 8. MycoBrain API Key

**Purpose:** Secure device control endpoints

| Variable | How to Generate |
|----------|-----------------|
| `MYCOBRAIN_API_KEY` | Generate a random string |

**Generate:**
```powershell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])
```

---

## Configuration Files

### Local Development (`.env.local`)
Location: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.env.local`

### VM Production (`.env`)
Location: `/home/mycosoft/mycosoft/mas/.env` or similar

---

## After Adding Keys

1. **Local Development:**
   ```powershell
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
   npm run dev
   ```

2. **VM Deployment:**
   ```bash
   ssh mycosoft@192.168.0.187
   cd /home/mycosoft/mycosoft/mas
   docker compose -f docker-compose.always-on.yml up -d --build mycosoft-website
   ```

3. **Clear Cloudflare Cache:**
   - Go to Cloudflare Dashboard
   - Select mycosoft.com
   - Caching → Purge Everything

---

## Security Notes

- ⚠️ **Never commit `.env` files to git**
- ⚠️ **Service Role Key is admin-level - server-side only**
- ⚠️ **Rotate keys periodically**
- ⚠️ **Use different keys for dev/staging/prod**

---

*Last updated: January 20, 2026*
