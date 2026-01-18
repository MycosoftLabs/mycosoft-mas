# Supabase OAuth Provider Configuration Guide

**Document Version**: 1.0.0  
**Date**: 2026-01-17  
**Author**: AI Development Agent  
**Status**: 📋 CONFIGURATION REQUIRED

---

## 📋 Overview

This guide walks through configuring OAuth providers (Google, GitHub) in the Supabase dashboard for the Mycosoft platform.

## ⚙️ Prerequisites

1. ✅ Supabase project created (`hnevnsxnhfibhbsipqvz`)
2. ✅ Environment variables added to `.env.local`
3. ⏳ OAuth credentials from Google Cloud Console
4. ⏳ OAuth credentials from GitHub Developer Settings

---

## 🔐 Step 1: Configure Google OAuth

### 1.1 Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select or create a project for Mycosoft
3. Navigate to **APIs & Services** > **Credentials**
4. Click **Create Credentials** > **OAuth client ID**
5. Application type: **Web application**
6. Name: `Mycosoft Auth`
7. Add Authorized JavaScript origins:
   - `http://localhost:3000` (local development)
   - `http://localhost:3001`
   - `http://localhost:3002`
   - `https://sandbox.mycosoft.com` (production)
   - `https://mycosoft.com` (future production)

8. Add Authorized redirect URIs:
   - `https://hnevnsxnhfibhbsipqvz.supabase.co/auth/v1/callback`

9. Copy the **Client ID** and **Client Secret**

### 1.2 Add to Supabase Dashboard

1. Go to [Supabase Dashboard](https://supabase.com/dashboard/project/hnevnsxnhfibhbsipqvz)
2. Navigate to **Authentication** > **Providers**
3. Find **Google** and click to expand
4. Toggle **Enable Sign in with Google** to ON
5. Enter:
   - **Client ID**: (from Google Cloud Console)
   - **Client Secret**: (from Google Cloud Console)
6. Click **Save**

---

## 🐙 Step 2: Configure GitHub OAuth

### 2.1 Create GitHub OAuth App

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **OAuth Apps** > **New OAuth App**
3. Fill in:
   - **Application name**: `Mycosoft`
   - **Homepage URL**: `https://mycosoft.com` (or `http://localhost:3000` for now)
   - **Authorization callback URL**: `https://hnevnsxnhfibhbsipqvz.supabase.co/auth/v1/callback`
4. Click **Register application**
5. Copy the **Client ID**
6. Click **Generate a new client secret** and copy it

### 2.2 Add to Supabase Dashboard

1. Go to [Supabase Dashboard](https://supabase.com/dashboard/project/hnevnsxnhfibhbsipqvz)
2. Navigate to **Authentication** > **Providers**
3. Find **GitHub** and click to expand
4. Toggle **Enable Sign in with GitHub** to ON
5. Enter:
   - **Client ID**: (from GitHub)
   - **Client Secret**: (from GitHub)
6. Click **Save**

---

## 🌐 Step 3: Configure Redirect URLs

In Supabase Dashboard:

1. Navigate to **Authentication** > **URL Configuration**
2. Set the following:
   - **Site URL**: `http://localhost:3000` (for development)
   - **Redirect URLs** (add all):
     ```
     http://localhost:3000/auth/callback
     http://localhost:3001/auth/callback
     http://localhost:3002/auth/callback
     https://sandbox.mycosoft.com/auth/callback
     https://mycosoft.com/auth/callback
     ```

---

## 🧪 Step 4: Test Authentication

### 4.1 Start Local Development Server

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
npm run dev
```

### 4.2 Test Login Flow

1. Open browser to `http://localhost:3000/login` (or the port shown)
2. Click **Continue with Google** or **Continue with GitHub**
3. Authenticate with your Google/GitHub account
4. Verify redirect back to `/dashboard`
5. Check user session is maintained

### 4.3 Test Email/Password Flow

1. Go to `http://localhost:3000/signup`
2. Create a new account with email/password
3. Check email for confirmation link
4. Confirm account and test login

---

## 🔧 Troubleshooting

### OAuth Redirect Errors

- **Error**: `redirect_uri_mismatch`
  - Ensure the callback URL in Google/GitHub matches exactly: `https://hnevnsxnhfibhbsipqvz.supabase.co/auth/v1/callback`

### Missing Environment Variables

- **Error**: `Your project's URL and Key are required`
  - Add to `.env.local`:
    ```
    NEXT_PUBLIC_SUPABASE_URL=https://hnevnsxnhfibhbsipqvz.supabase.co
    NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGci...
    ```
  - Restart the dev server

### Session Not Persisting

- Ensure middleware is properly configured
- Check browser cookies for `sb-*` entries
- Verify the callback route is working

---

## 📝 Configuration Checklist

| Step | Status | Notes |
|------|--------|-------|
| Create Google OAuth credentials | ⏳ | Required for Google login |
| Add Google to Supabase | ⏳ | After Google credentials |
| Create GitHub OAuth app | ⏳ | Required for GitHub login |
| Add GitHub to Supabase | ⏳ | After GitHub credentials |
| Configure redirect URLs | ⏳ | Add all localhost ports |
| Test Google login | ⏳ | After Google configured |
| Test GitHub login | ⏳ | After GitHub configured |
| Test email/password | ⏳ | Should work immediately |

---

## 🔗 Quick Links

- [Supabase Dashboard](https://supabase.com/dashboard/project/hnevnsxnhfibhbsipqvz)
- [Supabase Auth Settings](https://supabase.com/dashboard/project/hnevnsxnhfibhbsipqvz/auth/providers)
- [Google Cloud Console](https://console.cloud.google.com/)
- [GitHub Developer Settings](https://github.com/settings/developers)

---

## 📅 Next Steps After OAuth Configuration

1. ✅ Phase 1: Authentication - Complete
2. ⏳ Phase 2: Database & Vectors - MINDEX integration
3. ⏳ Phase 3: Realtime - Telemetry subscriptions
4. ⏳ Phase 4: Storage - Image and file management
5. ⏳ Phase 5: Edge Functions - Serverless operations
6. ⏳ Phase 6: LangChain - AI/ML vector embeddings
