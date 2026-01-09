# Developer Remote Access Guide

> **Version**: 1.0.0  
> **Last Updated**: January 2026  
> **For**: Remote developers (Alberto and team)

This guide explains how to access the MYCA system remotely for development and debugging. No local infrastructure setup is required - you'll access the live staging environment and use centralized AI services.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Accessing the Website](#accessing-the-website)
3. [API Access](#api-access)
4. [Remote AI Services](#remote-ai-services)
5. [Development Workflow](#development-workflow)
6. [Debugging Tools](#debugging-tools)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### What You Need

- Modern web browser (Chrome, Firefox, Edge)
- Git (for code access)
- Your preferred code editor (VS Code recommended)
- API credentials (provided by admin)

### What You DON'T Need

- Docker or container runtime
- Local databases (PostgreSQL, Redis, Qdrant)
- GPU or AI models (Ollama, Whisper)
- VPN (Cloudflare handles secure access)

---

## Accessing the Website

### Live URLs

| Environment | URL | Purpose |
|-------------|-----|---------|
| **Production** | https://mycosoft.com | Live site (read-only testing) |
| **Staging** | https://staging.mycosoft.com | Development testing |
| **API** | https://api.mycosoft.com | Backend API |
| **Dashboard** | https://dashboard.mycosoft.com | MICA voice interface |

### Browser Developer Tools

1. Open the staging site: https://staging.mycosoft.com
2. Press `F12` to open DevTools
3. Key tabs for debugging:
   - **Console**: JavaScript errors and logs
   - **Network**: API calls and responses
   - **Elements**: DOM inspection
   - **Application**: Storage, cookies, service workers

### Testing Checklist

- [ ] Site loads without errors
- [ ] All pages navigate correctly
- [ ] Forms submit properly
- [ ] API calls return expected data
- [ ] No console errors

---

## API Access

### Authentication

You'll receive an API token from the admin. Use it in all API requests:

```bash
# Set your token
export MYCA_API_TOKEN="your-token-here"

# Test API access
curl -H "Authorization: Bearer $MYCA_API_TOKEN" \
     https://api.mycosoft.com/health
```

### Common Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | API health check |
| `/agents` | GET | List all agents |
| `/agents/{id}` | GET | Get agent details |
| `/agents/run` | POST | Execute an agent |
| `/config` | GET | System configuration |

### API Testing with cURL

```bash
# Health check
curl https://api.mycosoft.com/health

# List agents (authenticated)
curl -H "Authorization: Bearer $MYCA_API_TOKEN" \
     https://api.mycosoft.com/agents

# Run an agent
curl -X POST \
     -H "Authorization: Bearer $MYCA_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"agent_id": "project-manager", "input": "test"}' \
     https://api.mycosoft.com/agents/run
```

### API Testing with Postman/Insomnia

1. Import the collection from `docs/api/myca-api.postman_collection.json`
2. Set environment variable `MYCA_API_TOKEN`
3. Set base URL to `https://api.mycosoft.com`

---

## Remote AI Services

The heavy compute (LLM, Speech-to-Text) runs on centralized infrastructure. Your requests are routed through the API.

### LLM Access (Ollama)

LLM requests go through the MYCA API, which forwards to the central Ollama instance:

```bash
# Via MYCA API (recommended)
curl -X POST \
     -H "Authorization: Bearer $MYCA_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Hello, how are you?", "model": "llama3.1"}' \
     https://api.mycosoft.com/llm/generate
```

### Speech-to-Text (Whisper)

Audio transcription is handled centrally:

```bash
# Upload audio for transcription
curl -X POST \
     -H "Authorization: Bearer $MYCA_API_TOKEN" \
     -F "audio=@recording.wav" \
     https://api.mycosoft.com/stt/transcribe
```

### Text-to-Speech

```bash
# Generate speech
curl -X POST \
     -H "Authorization: Bearer $MYCA_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello world", "voice": "default"}' \
     https://api.mycosoft.com/tts/synthesize \
     --output speech.mp3
```

### Available Models

| Service | Models | Notes |
|---------|--------|-------|
| LLM | llama3.1, codellama, mistral | GPU-accelerated |
| STT | whisper-large-v3 | GPU-accelerated |
| TTS | ElevenLabs, Piper | Voice options available |

---

## Development Workflow

### Getting the Code

```bash
# Clone the repository
git clone https://github.com/mycosoft/mycosoft-mas.git
cd mycosoft-mas

# Create your feature branch
git checkout -b feature/your-feature-name
```

### Local Development (Frontend Only)

If you need to run the frontend locally for rapid iteration:

```bash
# Install dependencies
npm install

# Create local env pointing to remote services
cp config/remote-dev.env .env.local

# Start development server
npm run dev

# Access at http://localhost:3000
```

The `.env.local` will point all API calls to the remote staging environment.

### Environment Configuration

Create `.env.local` for local frontend development:

```bash
# Remote API endpoints
NEXT_PUBLIC_API_URL=https://api.mycosoft.com
NEXT_PUBLIC_WS_URL=wss://api.mycosoft.com

# Your developer token
MYCA_API_TOKEN=your-token-here

# Environment
NODE_ENV=development
```

### Making Changes

1. Make your code changes locally
2. Test against the staging API
3. Commit and push to your branch
4. Create a Pull Request
5. Changes will be reviewed and deployed

```bash
# Commit your changes
git add .
git commit -m "feat: description of your change"

# Push to GitHub
git push origin feature/your-feature-name
```

---

## Debugging Tools

### Browser Console Commands

The staging site includes debugging helpers:

```javascript
// Check API connection
window.__MYCA_DEBUG__.checkAPI()

// View current state
window.__MYCA_DEBUG__.getState()

// Toggle verbose logging
window.__MYCA_DEBUG__.setVerbose(true)

// View pending requests
window.__MYCA_DEBUG__.getPendingRequests()
```

### Network Debugging

1. Open DevTools > Network tab
2. Filter by "Fetch/XHR" for API calls
3. Check:
   - Response status codes
   - Response body
   - Request headers (Authorization)
   - Timing

### Common Debug Scenarios

**API returns 401 Unauthorized:**
```bash
# Check your token is valid
curl -H "Authorization: Bearer $MYCA_API_TOKEN" \
     https://api.mycosoft.com/auth/verify
```

**CORS errors:**
- Ensure you're accessing from allowed origins
- Check browser console for specific CORS error message
- Report to admin if your origin needs to be added

**Slow responses:**
- Check Network tab for timing breakdown
- AI operations (LLM, STT) may take 5-30 seconds
- Report consistently slow endpoints

---

## Troubleshooting

### Cannot Access Staging Site

1. **Check URL**: Ensure you're using `https://staging.mycosoft.com`
2. **Check Internet**: Verify general internet connectivity
3. **Clear Cache**: Try incognito/private browsing
4. **Check Status**: Ask admin if services are running

### API Authentication Failed

1. **Verify Token**: Ensure token is correct and not expired
2. **Check Header**: Must be `Authorization: Bearer <token>`
3. **Request New Token**: Contact admin if token expired

### AI Services Not Responding

1. **Check Endpoint**: Use the correct API endpoints (not direct Ollama)
2. **Check Timeout**: AI operations may take longer
3. **Report Issue**: Contact admin with request details

### Local Frontend Not Connecting

1. **Check .env.local**: Verify API URLs are correct
2. **Check Network**: Ensure firewall allows outbound HTTPS
3. **Check Console**: Look for specific error messages

---

## Contact

### For Access Issues
- Contact: Admin (Morgan)
- Method: MYCA Dashboard or direct message

### For Technical Issues
- Create GitHub Issue with:
  - Description of problem
  - Steps to reproduce
  - Browser/environment details
  - Screenshots if applicable

### Emergency
- If staging site is completely down, contact admin immediately
- Check #infrastructure channel for announcements

---

## Quick Reference

### URLs
```
Website:   https://staging.mycosoft.com
API:       https://api.mycosoft.com
Dashboard: https://dashboard.mycosoft.com
GitHub:    https://github.com/mycosoft/mycosoft-mas
```

### Headers
```
Authorization: Bearer <your-token>
Content-Type: application/json
```

### Test Commands
```bash
# Health check
curl https://api.mycosoft.com/health

# Authenticated request
curl -H "Authorization: Bearer $MYCA_API_TOKEN" https://api.mycosoft.com/agents
```

---

*Welcome to the team! Reach out if you have any questions.*
