# API Keys & Credentials Status

**Last Updated:** January 17, 2026

## ✅ Configured Keys

| Service | Key Type | Location | Status |
|---------|----------|----------|--------|
| **Supabase** | URL + Anon Key | Website `.env.local`, MAS `.env` | ✅ Active |
| **Google Maps** | API Key | Website `.env.local`, MAS `.env` | ✅ Active |
| **UniFi** | API Key | Website `.env.local`, MAS `.env` | ✅ Active |
| **Anthropic/Claude** | API Key | Website `.env.local`, MAS `.env` | ✅ Active |
| **iNaturalist** | JWT Token | Website `.env.local`, MAS `.env` | ✅ Active |
| **NIH** | API Key | Website `.env.local`, MAS `.env` | ✅ Active |
| **Elsevier** | API Key | Website `.env.local`, MAS `.env` | ✅ Active |
| **Infura (Ethereum)** | API Key | Website `.env.local`, MAS `.env` | ✅ Active |
| **QuickNode (Solana)** | Endpoint URL | Website `.env.local`, MAS `.env` | ✅ Active |
| **FlightRadar24** | API Key | Website `.env.local`, MAS `.env` | ✅ Active |
| **Discord** | Bot Token | MAS `.env` | ✅ Active |
| **Asana** | Client ID + Secret | MAS `.env` | ✅ Active |
| **Cursor** | API Keys (2) | MAS `.env` | ✅ Active |

## ⚠️ Keys That Need Setup

| Service | Key Type | Required For | How to Get |
|---------|----------|--------------|------------|
| **Supabase Service Role** | Service Key | Server-side admin operations | Supabase Dashboard → Settings → API |
| **OpenAI** | API Key | Embeddings, GPT-4 | https://platform.openai.com/api-keys |
| **Google OAuth** | Client ID + Secret | Google Sign-In | Google Cloud Console |
| **GitHub OAuth** | Client ID + Secret | GitHub Sign-In | GitHub Developer Settings |
| **MQTT** | Username + Password | MycoBrain secure connections | Configure in broker |

## 📋 Key Details

### Supabase
- **Project URL:** `https://hnevnsxnhfibhbsipqvz.supabase.co`
- **Anon Key:** Configured (JWT token)
- **Service Role Key:** ⚠️ MISSING - Get from Supabase Dashboard → Settings → API → `service_role`

### Google Maps
- **API Key:** `AIzaSyA9wzTz5MiDhYBdY1vHJQtOnw9uikwauBk`
- **Services enabled:** Maps JavaScript API, Geocoding, Places

### UniFi
- **API Key:** Configured
- **Host:** `192.168.0.1` (default, update if different)

### Anthropic/Claude
- **API Key:** Configured (sk-ant-api03-...)
- **Usage:** LLM provider for MYCA agents

### Research APIs
- **iNaturalist:** JWT token configured (expires: check exp claim)
- **NIH:** API key configured
- **Elsevier:** API key configured (for research paper access)

### Blockchain
- **Infura (Ethereum):** `512bd4125cb94be780179a3c3a3ee232`
- **QuickNode (Solana):** Full endpoint URL configured

### FlightRadar24
- **API Key:** Compound key with session ID configured
- **Usage:** CREP dashboard aviation tracking

### Discord
- **Bot Token:** Configured for Mycosoft Discord bot
- **Bot ID:** `1450212628117979227`

### Asana
- **Client ID:** `1212449690857813`
- **Client Secret:** Configured
- **Usage:** Task management integration for MAS

### Cursor
- **Primary Key:** `key_be2febce62e4...` (general use)
- **Shell Key:** `key_98a45a95224...` (Mycosoft Shell specific)

## 🔑 Unidentified Key

The following key was provided but purpose is unclear:
```
12b49cb1-568e-4623-9fc3-52ec21002298
```
Format suggests a UUID - possibly a project ID or integration ID.

## 📁 File Locations

| File | Purpose |
|------|---------|
| `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.env.local` | Website environment |
| `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.env` | MAS environment |
| `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\keys\` | Service account JSON files |

## ⚠️ Security Notes

1. **Never commit `.env` files to Git** - They're in `.gitignore`
2. **Service Role Key** - Only use server-side, never expose to client
3. **Rotate keys** if compromised
4. **Use environment-specific keys** for dev/staging/production
