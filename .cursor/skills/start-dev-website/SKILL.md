---
name: start-dev-website
description: Start the Mycosoft website dev server on port 3010. Use when the user wants to run the dev server, start development, or test the website locally.
---

# Start Website Dev Server

## CRITICAL: Execute Yourself

**NEVER ask the user to run these commands.** You MUST execute them yourself via run_terminal_cmd. See `agent-must-execute-operations.mdc`.

## Quick Start

The dev server MUST run on port 3010. Use `dev:next-only` to avoid starting GPU services.

### Step 1: Free port 3010 if needed (Windows PowerShell)

```powershell
$conn = Get-NetTCPConnection -LocalPort 3010 -ErrorAction SilentlyContinue
if ($conn) {
    Stop-Process -Id $conn.OwningProcess -Force
    Write-Host "Freed port 3010"
}
```

### Step 2: Start dev server

```bash
npm run dev:next-only
```

This runs `next dev --port 3010` without starting GPU services (PersonaPlex, Moshi, Earth2).

### Step 3: Verify

Open http://localhost:3010 in browser.

## Environment Variables

The website connects to backend VMs. Ensure `.env.local` has:

```env
MAS_API_URL=http://192.168.0.188:8001
NEXT_PUBLIC_MAS_API_URL=http://192.168.0.188:8001
MINDEX_API_URL=http://192.168.0.189:8000
MINDEX_API_BASE_URL=http://192.168.0.189:8000
```

## When to use `npm run dev` (full stack)

Only use `npm run dev` when you need GPU services (voice, Earth2). It spawns a separate "GPU Services" window with Python processes that persist after terminal close.

If GPU services were started and are no longer needed, run:

```powershell
cd scripts
.\dev-machine-cleanup.ps1 -KillStaleGPU
```

## Key Details

| Item | Value |
|------|-------|
| Dev URL | http://localhost:3010 |
| Command | `npm run dev:next-only` |
| Port | 3010 (NEVER use another port) |
| GPU-free | Yes (no PersonaPlex/Earth2) |
