# Remove MYCA App Pages from Mycosoft MAS
## These pages should NOT exist in mycosoft-mas - they interfere with the website

**Date**: January 6, 2026  
**Issue**: MYCA app pages in mycosoft-mas are interfering with the website on port 3000  
**Solution**: Remove or disable MYCA app pages from mycosoft-mas

---

## Problem

The mycosoft-mas project (`C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas`) contains MYCA app pages that should NOT run on port 3000. Port 3000 is reserved exclusively for the website codebase at `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`.

---

## Files to Remove/Disable

### 1. MYCA App Pages (Remove These)

**Location**: `app/myca/` directory

**Files to DELETE:**
- `app/myca/page.tsx` - MYCA page with dashboard tabs
- `app/myca/dashboard/page.tsx` - MAS Dashboard page

**Reason**: These pages are interfering with the website. The MYCA app should integrate with the UniFi dashboard, not have its own pages in mycosoft-mas.

### 2. MYCA Dashboard Components (Keep but don't use in routes)

**Location**: `components/` directory

**Files to KEEP (but not use in routes):**
- `components/myca-dashboard.tsx` - Can be used by UniFi dashboard integration
- `components/mas-dashboard.tsx` - Can be used by UniFi dashboard integration
- `components/myca-dashboard-unifi.tsx` - Can be used by UniFi dashboard integration

**Reason**: These components might be needed for UniFi dashboard integration, but should NOT be served as pages.

---

## Action Plan

### Step 1: Delete MYCA App Pages

```powershell
# Delete MYCA app pages
Remove-Item -Recurse -Force "app\myca"
```

### Step 2: Verify Website Codebase is Separate

The website codebase is at:
- `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`

This is where:
- Device Manager lives
- Mycosoft logo homepage lives
- All website work is done
- Port 3000 should serve from here

### Step 3: Ensure mycosoft-mas Doesn't Run on Port 3000

**Never run `npm run dev` in mycosoft-mas on port 3000.**

The mycosoft-mas project should:
- Run MAS orchestrator services (port 8001)
- Provide API endpoints
- NOT serve web pages on port 3000

---

## Correct Architecture

```
┌─────────────────────────────────────────────────────────┐
│  WEBSITE Codebase                                       │
│  C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website │
│  Port 3000 - Website Homepage                           │
│  - Device Manager                                        │
│  - Mycosoft logo                                         │
│  - NatureOS                                              │
│  - MINDEX Search                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  MYCOSOFT MAS Codebase                                  │
│  C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas  │
│  Port 8001 - MAS Orchestrator API                       │
│  - Agent management                                     │
│  - API endpoints                                        │
│  - NO web pages on port 3000                            │
└─────────────────────────────────────────────────────────┘
```

---

## Prevention

**NEVER:**
- Run `npm run dev` in mycosoft-mas on port 3000
- Create web pages in mycosoft-mas that serve on port 3000
- Mix website code with MAS code

**ALWAYS:**
- Run website from `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`
- Keep website code separate from MAS code
- Use MAS as API backend only

---

## Files to Delete

1. `app/myca/page.tsx` - DELETE
2. `app/myca/dashboard/page.tsx` - DELETE
3. `app/myca/` directory - DELETE (if empty after removing pages)

---

**Status**: Ready to remove MYCA app pages from mycosoft-mas
