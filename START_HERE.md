# 🚀 MYCOSOFT MAS - Start Here

## Quick Start Guide

This guide will help you test and improve the entire MYCOSOFT MAS platform to ensure everything is working perfectly.

## ✅ What Has Been Done

### 1. Test Infrastructure Created
- ✅ Comprehensive test suite (`scripts/comprehensive_test_suite.py`)
- ✅ Automated testing script (`scripts/test_and_improve_mas.ps1`)
- ✅ Testing plan documentation (`scripts/comprehensive_improvement_plan.md`)

### 2. System Improvements
- ✅ Fixed configuration loading to support multiple paths
- ✅ Created startup scripts
- ✅ Documented all endpoints and components

### 3. Documentation
- ✅ Created comprehensive testing plan
- ✅ Documented system architecture
- ✅ Created troubleshooting guide

## 🎯 Next Steps

### Step 1: Install All Dependencies

```powershell
# Install Python dependencies
pip install -r requirements.txt

# Install additional test dependencies
pip install aiohttp httpx prometheus-client

# Install Node.js dependencies (for dashboard)
npm install
```

### Step 2: Start Infrastructure Services

```powershell
# Start Docker services (PostgreSQL, Redis, Qdrant, Prometheus, Grafana)
docker-compose up -d postgres redis qdrant prometheus grafana

# Verify services are running
docker-compose ps
```

### Step 3: Start MAS API

```powershell
# Start the MAS FastAPI server
python -m uvicorn mycosoft_mas.core.myca_main:app --host 0.0.0.0 --port 8000

# Or use the automated script
.\scripts\test_and_improve_mas.ps1
```

### Step 4: Run Comprehensive Tests

In a new terminal:

```powershell
# Run the comprehensive test suite
python scripts\comprehensive_test_suite.py
```

### Step 5: Start Dashboard

In another terminal:

```powershell
# Start Next.js dashboard
npm run dev
```

## 📋 Testing Checklist

### Core System
- [ ] MAS API starts successfully
- [ ] Health endpoint responds (`GET /health`)
- [ ] Root endpoint responds (`GET /`)
- [ ] Metrics endpoint works (`GET /metrics`)

### Voice Integration (MYCA)
- [ ] Voice agents list (`GET /voice/agents`)
- [ ] Voice chat works (`POST /voice/orchestrator/chat`)
- [ ] Voice feedback system works
- [ ] STT → LLM → TTS pipeline works

### Agents
- [ ] All agents initialize successfully
- [ ] Agent registry works (`GET /agents/registry`)
- [ ] Agent status reporting works

### Integrations
- [ ] MINDEX integration connects
- [ ] NATUREOS integration connects
- [ ] Website integration connects
- [ ] Notion integration connects (if configured)
- [ ] N8N integration connects (if configured)

### Dashboard
- [ ] Dashboard loads successfully
- [ ] System metrics display correctly
- [ ] Agent status shows correctly
- [ ] Real-time updates work

## 🔧 Troubleshooting

### Issue: ModuleNotFoundError
**Solution:** Install missing dependencies
```powershell
pip install -r requirements.txt
```

### Issue: Config file not found
**Solution:** Ensure `config.yaml` exists in root directory
```powershell
# Copy example if needed
Copy-Item config.yaml.example config.yaml
```

### Issue: Port already in use
**Solution:** Change port or stop existing service
```powershell
# Check what's using port 8000
netstat -ano | findstr :8000

# Kill process if needed
taskkill /PID <process_id> /F
```

### Issue: Database connection errors
**Solution:** Ensure PostgreSQL/Redis are running
```powershell
# Start Docker services
docker-compose up -d postgres redis
```

## 📊 System Status

Check system status at:
- **MAS API:** http://localhost:8000
- **Health Check:** http://localhost:8000/health
- **Metrics:** http://localhost:8000/metrics
- **Dashboard:** http://localhost:3001 (Next.js)
- **Grafana:** http://localhost:3000
- **Prometheus:** http://localhost:9090

## 🎯 Key Endpoints to Test

### Voice Endpoints
```powershell
# Test voice chat
curl -X POST http://localhost:8000/voice/orchestrator/chat `
  -H "Content-Type: application/json" `
  -d '{\"message\":\"Hello MYCA\",\"conversation_id\":\"test\"}'

# List voice agents
curl http://localhost:8000/voice/agents
```

### Agent Endpoints
```powershell
# List agents
curl http://localhost:8000/agents

# Get agent registry
curl http://localhost:8000/agents/registry
```

### Twilio Endpoints
```powershell
# Check Twilio config
curl http://localhost:8000/twilio/config
```

## 📚 Documentation

- **Testing Plan:** `scripts/comprehensive_improvement_plan.md`
- **Test Summary:** `TESTING_AND_IMPROVEMENT_SUMMARY.md`
- **System Architecture:** `docs/architecture.md`
- **Integration Guide:** `docs/SYSTEM_INTEGRATIONS.md`

## 🎉 Success Criteria

The system is ready when:
1. ✅ All tests pass
2. ✅ MAS API starts without errors
3. ✅ All agents initialize successfully
4. ✅ Voice integration works flawlessly
5. ✅ All integrations connect
6. ✅ Dashboard displays correctly
7. ✅ System is production-ready

## 🆘 Need Help?

1. Check logs: `logs/mas.log`
2. Review test output for specific errors
3. Check service health: `http://localhost:8000/health`
4. Review configuration: `config.yaml`

## 🚀 Ready to Start?

Run this command to begin:

```powershell
.\scripts\test_and_improve_mas.ps1
```

This will:
1. Check dependencies
2. Start MAS service
3. Run comprehensive tests
4. Report results

Good luck! 🎯
