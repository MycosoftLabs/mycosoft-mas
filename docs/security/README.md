# Mycosoft Security Operations Center (SOC) Documentation

**Version:** 2.0.0  
**Last Updated:** January 18, 2026

---

## Quick Links

| Document | Description |
|----------|-------------|
| [📚 Complete Documentation](./SOC_COMPLETE_DOCUMENTATION.md) | Full technical documentation with capabilities, protocols, and architecture |
| [🚀 Setup & Deployment Guide](./SETUP_DEPLOYMENT_GUIDE.md) | Step-by-step setup for dev, sandbox, and production |
| [📋 Missing Features & Requirements](./MISSING_FEATURES_REQUIREMENTS.md) | Gap analysis and implementation roadmap |
| [🤖 Automation & HITL Requirements](./AUTOMATION_HITL_REQUIREMENTS.md) | Automation tiers and human oversight requirements |
| [🧪 Test Suite](./TEST_SUITE.md) | Comprehensive test cases and scripts |

---

## Quick Start

### Development

```powershell
# 1. Navigate to website
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website

# 2. Start dev server
npm run dev

# 3. Open browser
Start-Process "http://localhost:3000/security"
```

### Run Tests

```powershell
# Quick smoke test
.\scripts\security\smoke-test.ps1

# Full test suite
.\scripts\security\run-all-tests.ps1 -Environment dev
```

---

## SOC Pages

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/security` | Main security overview |
| Network | `/security/network` | UniFi integration |
| Incidents | `/security/incidents` | Incident management |
| Red Team | `/security/redteam` | Penetration testing |
| Compliance | `/security/compliance` | NIST compliance |

---

## Key Features

### ✅ Implemented
- UniFi Dream Machine Pro integration
- Real-time network monitoring
- Geo-IP lookup with US-only restriction
- Authorized user management
- Incident tracking
- Red Team scanner interface
- NIST CSF compliance tracking

### ⚠️ Partial Implementation
- Threat intelligence (needs API keys)
- Response playbooks (structure only)
- Network scanning (mock data)
- PDF report export

### 🔴 Not Yet Implemented
- Real Suricata IDS
- WebSocket real-time alerts
- Email notifications
- Automated quarantine
- MYCA-SEC AI integration

---

## Authorized Users

| Name | Role | Location |
|------|------|----------|
| Morgan | super_admin | Chula Vista, CA |
| Chris | admin | Portland, OR |
| Garrett | admin | Pasadena/Chula Vista, CA |
| RJ | admin | Chula Vista/San Diego, CA |
| Beto | admin | Chula Vista, CA |

---

## Security Notes

- **Allowed Countries:** US only
- **High-Risk Countries:** CN, RU, KP, IR, BY, VE, SY, CU
- **VPN Access:** Allowed for authorized users
- **MFA:** Required (not yet enforced)

---

## Support

For issues or questions:
1. Check the [Troubleshooting section](./SETUP_DEPLOYMENT_GUIDE.md#troubleshooting)
2. Review the [Test Suite](./TEST_SUITE.md) for debugging
3. Contact Morgan (super_admin)

---

**Document Maintainer:** Security Team  
**Review Cycle:** Monthly
