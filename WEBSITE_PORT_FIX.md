# Website Port 3000 Fix - Why Port Kept Changing

## Problem

The website port kept changing because **multiple Node.js processes** were trying to start the website simultaneously:

1. **Multiple `npm run dev` processes** running at the same time
2. **Multiple `next dev` processes** competing for port 3000
3. **No cleanup** when processes were started in different terminals
4. **Next.js automatically picks next available port** (3001, 3002, etc.) if 3000 is busy

## Root Cause

Every time the website was started (manually, via script, or by Cursor), a new Node process was created without killing the old one. This led to:
- Process 1: Takes port 3000
- Process 2: Can't use 3000, uses 3001
- Process 3: Can't use 3000 or 3001, uses 3002
- etc.

## Solution

Created `START_WEBSITE_PERSISTENT.ps1` script that:
1. **Kills any existing process on port 3000** before starting
2. **Kills all other Next.js dev servers** to prevent conflicts
3. **Explicitly sets PORT=3000** environment variable
4. **Starts in a persistent window** that stays open

## How to Use

### Start Website (Always on Port 3000)

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
.\START_WEBSITE_PERSISTENT.ps1
```

Or manually:
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
$env:PORT = "3000"
npm run dev
```

### Stop Website

Find the PowerShell window running `npm run dev` and close it, OR:
```powershell
Get-NetTCPConnection -LocalPort 3000 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

## Prevention

**ALWAYS use the persistent script** or ensure you:
1. Kill existing processes before starting new ones
2. Set `PORT=3000` explicitly
3. Don't start multiple instances

## Current Status

✅ Website is now running on port 3000
✅ Persistent script created for future use
✅ All duplicate processes cleaned up
