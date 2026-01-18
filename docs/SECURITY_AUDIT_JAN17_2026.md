# MYCOSOFT SECURITY AUDIT

**Document Version**: 1.0.0  
**Date**: 2026-01-17  
**Classification**: CONFIDENTIAL - Internal Only  
**Author**: AI Security Analysis  
**Status**: ⚠️ REQUIRES IMMEDIATE ATTENTION

---

## 🔴 CRITICAL SECURITY ISSUES

### 1. Exposed Credentials in Documentation

| Issue | Location | Risk |
|-------|----------|------|
| SSH Password in plain text | Multiple .md files | 🔴 Critical |
| `Mushroom1!Mushroom1!` | PROXMOX_VM_SPECIFICATIONS.md | 🔴 Critical |

**Immediate Action Required:**
```bash
# On VM 192.168.0.187
sudo passwd mycosoft
# Enter new strong password
```

### 2. Environment Files with Secrets

| File | Path | Contains |
|------|------|----------|
| `.env` | MAS/mycosoft-mas/ | API keys, DB passwords |
| `.env.local` | MAS/mycosoft-mas/ | Local overrides |
| `.env.local` | WEBSITE/website/ | Auth secrets |
| `.env.local` | unifi-dashboard/ | Dashboard secrets |
| `development.env` | config/ | Dev credentials |
| `production.env` | config/ | **PROD CREDENTIALS** |
| `remote-dev.env` | config/ | Remote access keys |
| `.env` | MINDEX/mindex/ | Database strings |
| `.env` | platform-infra/ | Infrastructure keys |
| `.env.prod` | platform-infra/ | Production keys |

**Recommendation:** Move all secrets to Docker Secrets or HashiCorp Vault

---

## 🔑 API KEYS INVENTORY

### External Services (Rotate Quarterly)

| Service | Key Type | Location | Last Rotated | Next Rotation |
|---------|----------|----------|--------------|---------------|
| Cloudflare | API Token | .env | Unknown | **IMMEDIATE** |
| OpenAI | API Key | .env | Unknown | 2026-04-17 |
| Anthropic | API Key | .env | Unknown | 2026-04-17 |
| Google Maps | API Key | .env.local | Unknown | 2026-04-17 |
| Firebase | Service Account | config/ | Unknown | 2026-04-17 |
| ElevenLabs | API Key | .env | Unknown | 2026-04-17 |

### Data APIs

| Service | Key Type | Location | Priority |
|---------|----------|----------|----------|
| iNaturalist | API Token | .env | Medium |
| GBIF | API Key | .env | Medium |
| OpenSky | API Key | .env | Medium |
| AISStream | API Key | .env | Medium |
| FlightRadar24 | API Key | .env | Medium |
| OpenAQ | API Key | .env | Medium |
| Space-Track | Credentials | .env | Medium |

### Infrastructure

| Service | Key Type | Location | Priority |
|---------|----------|----------|----------|
| Proxmox | API Token | config/ | High |
| UniFi | API Credentials | unifi-dashboard/.env | High |
| PostgreSQL | Password | docker-compose.yml | High |
| Redis | Password | docker-compose.yml | Medium |
| n8n | Encryption Key | n8n/.env | High |

---

## 🔒 PASSWORD ROTATION SCHEDULE

### Immediate Rotation Required

| Account | Current | Action |
|---------|---------|--------|
| VM SSH (mycosoft@192.168.0.187) | `Mushroom1!Mushroom1!` | **CHANGE NOW** |
| PostgreSQL (main) | Check .env | Rotate |
| PostgreSQL (mas) | Check .env | Rotate |
| n8n Admin | Check UI | Rotate |
| Grafana Admin | Check UI | Rotate |

### Password Requirements

```
Minimum: 16 characters
Must include: Uppercase, lowercase, numbers, special characters
No dictionary words
No sequential patterns
Store in password manager only
```

---

## 🌐 NETWORK SECURITY

### Exposed Ports (Public)

| Port | Service | Exposure | Risk |
|------|---------|----------|------|
| 3000 | Website | Cloudflare Tunnel | Low |
| 8000 | MINDEX API | Cloudflare Tunnel | Medium |
| 8003 | MycoBrain | Windows Firewall | **High** |

### Internal Ports (LAN Only)

| Port | Service | Recommendation |
|------|---------|----------------|
| 5432 | PostgreSQL | Firewall restrict |
| 5433 | PostgreSQL (MAS) | Firewall restrict |
| 6379 | Redis | No external access |
| 6390 | Redis (MAS) | No external access |
| 5678 | n8n | Internal only |
| 3002 | Grafana | Internal only |
| 9090 | Prometheus | Internal only |

### Firewall Rules Needed

```powershell
# Windows - Only allow 8003 from known IPs
netsh advfirewall firewall add rule name="MycoBrain API" dir=in action=allow protocol=tcp localport=8003 remoteip=192.168.0.187

# Block all other external access to 8003
netsh advfirewall firewall add rule name="MycoBrain Block" dir=in action=block protocol=tcp localport=8003
```

---

## 🛡️ SECURITY VULNERABILITIES

### High Risk

| Vulnerability | Component | Mitigation |
|---------------|-----------|------------|
| No API auth on MycoBrain | /api/mycobrain/* | Add JWT/API key auth |
| SSH with password | VM 103 | Switch to key-only auth |
| Secrets in git history | All repos | Use git-filter-repo |
| Default Docker socket | Docker | Restrict access |

### Medium Risk

| Vulnerability | Component | Mitigation |
|---------------|-----------|------------|
| No rate limiting | All APIs | Add rate limit middleware |
| CORS too permissive | Website | Restrict origins |
| No request logging | APIs | Add audit logging |
| Unencrypted Redis | Redis containers | Enable TLS |

### Low Risk

| Vulnerability | Component | Mitigation |
|---------------|-----------|------------|
| Verbose error messages | APIs | Use production mode |
| Debug endpoints exposed | Development | Remove in prod |
| Old dependencies | node_modules | Run npm audit |

---

## ✅ SECURITY CHECKLIST

### Immediate (Next 24 Hours)

- [ ] Change VM SSH password
- [ ] Remove passwords from all .md files
- [ ] Verify Cloudflare tunnel settings
- [ ] Check firewall rules on port 8003

### This Week

- [ ] Implement API key authentication for MycoBrain
- [ ] Set up SSH key-only authentication
- [ ] Create secrets management strategy
- [ ] Run npm audit on all projects
- [ ] Enable PostgreSQL connection encryption

### This Month

- [ ] Deploy HashiCorp Vault or Docker Secrets
- [ ] Implement API rate limiting
- [ ] Set up intrusion detection
- [ ] Create security incident response plan
- [ ] Complete penetration testing

### Quarterly

- [ ] Rotate all API keys
- [ ] Update all dependencies
- [ ] Review access logs
- [ ] Update security documentation

---

## 📋 SECRET FILES TO PROTECT

### Files to Add to .gitignore

```gitignore
# Environment files
.env
.env.local
.env.prod
*.env
config/*.env

# Secrets
secrets/
credentials/
*.pem
*.key
*.crt

# SSH
id_rsa*
known_hosts
```

### Files to Encrypt at Rest

| File | Method |
|------|--------|
| production.env | GPG encrypt |
| n8n/credentials/ | Docker secrets |
| SSL certificates | Vault |
| API key backups | Encrypted backup |

---

## 🚨 INCIDENT RESPONSE

### If Credentials Are Compromised

1. **Immediately** rotate all API keys
2. Revoke old tokens in provider dashboards
3. Change all passwords
4. Review access logs for unauthorized access
5. Update all deployment configurations
6. Document incident

### Contact List

| Role | Contact |
|------|---------|
| System Admin | [TBD] |
| Security Lead | [TBD] |
| Cloudflare Account | [TBD] |

---

## 📝 AUDIT LOG

| Date | Action | By |
|------|--------|-----|
| 2026-01-17 | Initial security audit | AI Agent |
| 2026-01-17 | Identified 5 critical issues | AI Agent |
| [Future] | [Actions taken] | [Person] |

---

**END OF SECURITY AUDIT**

*This document contains sensitive security information. Do not share externally.*
