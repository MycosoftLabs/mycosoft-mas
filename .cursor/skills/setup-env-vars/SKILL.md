---
name: setup-env-vars
description: Configure .env.local with correct VM URLs and API keys for the Mycosoft website. Use when setting up the dev environment, fixing API connection issues, or after VM changes.
---

# Setup Environment Variables

## Quick Setup

Create or update `.env.local` in the website root:

```env
# Backend VM connections
MAS_API_URL=http://192.168.0.188:8001
NEXT_PUBLIC_MAS_API_URL=http://192.168.0.188:8001
MINDEX_API_URL=http://192.168.0.189:8000
MINDEX_API_BASE_URL=http://192.168.0.189:8000

# Optional services
MYCORRHIZAE_API_URL=http://192.168.0.187:8002
REDIS_URL=redis://192.168.0.187:6379
N8N_URL=http://192.168.0.188:5678

# Supabase (get from Supabase dashboard)
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# For VM callbacks to local dev
NEXT_PUBLIC_BASE_URL=http://YOUR_PC_LAN_IP:3010
```

## Get API Keys

### From Internal Keys API

```bash
# Dev keys
curl http://localhost:3010/api/internal/keys/dev

# Sandbox keys
curl http://localhost:3010/api/internal/keys/sandbox
```

The response includes a `keys` object and `envSnippet` for `.env.local`.

### From PowerShell Script

```powershell
cd scripts
.\get-dev-keys.ps1
```

## VM-to-Dev Callbacks

If MAS or MINDEX needs to call back to your local dev server:

1. Find your PC's LAN IP: `ipconfig` (look for 192.168.0.x)
2. Set `NEXT_PUBLIC_BASE_URL=http://192.168.0.YOUR_IP:3010`
3. Ensure Windows Firewall allows inbound TCP 3010 from 192.168.0.0/24

## Verification

After setting env vars, restart the dev server and check:

```bash
npm run dev:next-only
# Then visit http://localhost:3010 and check browser console for API errors
```
