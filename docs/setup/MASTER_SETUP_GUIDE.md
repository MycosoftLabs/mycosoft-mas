# MYCA Infrastructure Master Setup Guide

> **Version**: 1.0.0  
> **Last Updated**: January 2026  
> **Audience**: System Administrators, DevOps Engineers

This is the master reference document for deploying the MYCA (Mycosoft Autonomous Cognitive Agent) Multi-Agent System infrastructure. It provides an architectural overview, component inventory, and execution roadmap for moving from development to production.

---

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Component Inventory](#component-inventory)
3. [Network Topology](#network-topology)
4. [IP Address Assignments](#ip-address-assignments)
5. [Service Port Reference](#service-port-reference)
6. [VLAN Configuration](#vlan-configuration)
7. [Setup Order and Dependencies](#setup-order-and-dependencies)
8. [Quick Reference Links](#quick-reference-links)

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                        │
│                                  │                                           │
│                         ┌────────┴────────┐                                 │
│                         │   Cloudflare    │                                 │
│                         │  mycosoft.com   │                                 │
│                         │  (DNS + Tunnel) │                                 │
│                         └────────┬────────┘                                 │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┼──────────────────────────────────────────┐
│  GARAGE SERVER NETWORK           │                                          │
│                         ┌────────┴────────┐                                 │
│                         │   Dream Machine │                                 │
│                         │   192.168.0.1   │                                 │
│                         │   + 26TB NAS    │                                 │
│                         │   + Cloudflared │                                 │
│                         └────────┬────────┘                                 │
│                                  │                                           │
│    ┌─────────────────────────────┼─────────────────────────────────────┐    │
│    │                             │                                      │    │
│    │  ┌─────────────┐   ┌───────┴───────┐   ┌─────────────┐           │    │
│    │  │  mycocomp   │   │   PROXMOX     │   │  MycoBrain  │           │    │
│    │  │  (Dev Box)  │   │   CLUSTER     │   │   Devices   │           │    │
│    │  │             │   │               │   │             │           │    │
│    │  │  RTX 5090   │   │ ┌───────────┐ │   │  ESP32-S3   │           │    │
│    │  │  64GB RAM   │   │ │   DC1     │ │   │  Sensors    │           │    │
│    │  │             │   │ │   DC2     │ │   │             │           │    │
│    │  └─────────────┘   │ │   Build   │ │   └─────────────┘           │    │
│    │                     │ └───────────┘ │                             │    │
│    │  VLAN 1 (Default)   │               │   VLAN 40 (IoT)            │    │
│    │  192.168.0.x        │ VLAN 20 (Prod)│   192.168.40.x             │    │
│    │                     │ 192.168.20.x  │                             │    │
│    │                     │               │                             │    │
│    │                     │ VLAN 30 (Agent)                            │    │
│    │                     │ 192.168.30.x  │                             │    │
│    └─────────────────────┴───────────────┴─────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   User Request                                                               │
│       │                                                                      │
│       ▼                                                                      │
│   ┌───────────────┐    ┌───────────────┐    ┌───────────────┐               │
│   │  Cloudflare   │───▶│  Cloudflared  │───▶│    Nginx      │               │
│   │  (DNS/WAF)    │    │  (Tunnel)     │    │  (Reverse     │               │
│   └───────────────┘    └───────────────┘    │   Proxy)      │               │
│                                              └───────┬───────┘               │
│                                                      │                       │
│                    ┌─────────────────────────────────┼─────────────────────┐ │
│                    │                                 │                     │ │
│                    ▼                                 ▼                     │ │
│   ┌───────────────────────────┐    ┌───────────────────────────────────┐  │ │
│   │       Website (3000)      │    │      MYCA API (8001)              │  │ │
│   │       Next.js Frontend    │    │      FastAPI Orchestrator         │  │ │
│   └───────────────────────────┘    └─────────────────┬─────────────────┘  │ │
│                                                      │                     │ │
│                    ┌─────────────────────────────────┼─────────────────┐   │ │
│                    │                                 │                 │   │ │
│                    ▼                                 ▼                 ▼   │ │
│   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────────┐    │ │
│   │    PostgreSQL   │   │      Redis      │   │       Qdrant        │    │ │
│   │    (Persistent) │   │     (Cache)     │   │   (Vector Store)    │    │ │
│   └─────────────────┘   └─────────────────┘   └─────────────────────┘    │ │
│                    │                                 │                     │ │
│                    └─────────────────────────────────┘                     │ │
│                                    │                                       │ │
│                                    ▼                                       │ │
│                    ┌───────────────────────────────────┐                   │ │
│                    │       26TB NAS (UDM Pro)          │                   │ │
│                    │    All Persistent Data Storage    │                   │ │
│                    └───────────────────────────────────┘                   │ │
│                                                                             │ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Inventory

### Hardware

| Component | Role | Specifications | IP Address |
|-----------|------|----------------|------------|
| **UDM Pro** | Network Gateway + NAS | 26TB Storage, UniFi OS | 192.168.0.1 |
| **mycocomp** | Development Workstation | RTX 5090, 64GB RAM, Windows 11 | 192.168.0.x (DHCP) |
| **DC1** | Proxmox Node 1 | Dell Server, 128GB RAM | 192.168.0.2 |
| **DC2** | Proxmox Node 2 | Dell Server, 128GB RAM | 192.168.0.131 |
| **Build** | Proxmox Node 3 (Primary) | Dell Server, 256GB RAM | 192.168.0.202 |
| **MycoBrain** | IoT Sensors | ESP32-S3, BME688, I2C | VLAN 40 |

### Virtual Machines (Proxmox)

| VM Name | Node | VLAN | IP Address | Purpose |
|---------|------|------|------------|---------|
| **myca-core** | Build | 20 | 192.168.20.10 | MYCA Orchestrator + Core Services |
| **myca-website** | DC1 | 20 | 192.168.20.11 | Next.js Website + Nginx |
| **myca-database** | DC2 | 20 | 192.168.20.12 | PostgreSQL, Redis, Qdrant |
| **agent-template** | Build | 30 | Template | Clonable agent template |
| **agent-001..N** | Any | 30 | 192.168.30.x | Dynamic agent VMs |

### Software Stack

| Layer | Components |
|-------|------------|
| **Frontend** | Next.js 14, React, TailwindCSS, Shadcn/UI |
| **Backend** | FastAPI (Python 3.11), CrewAI, LangChain |
| **Databases** | PostgreSQL 16, Redis 7, Qdrant 1.x |
| **AI Services** | Ollama (LLM), Whisper (STT), ElevenLabs (TTS) |
| **Automation** | n8n, Docker, Systemd |
| **Security** | HashiCorp Vault, Cloudflare, Nginx |
| **Monitoring** | Prometheus, Grafana, Loki |

---

## Network Topology

### Physical Layout

```
Internet
    │
    └── Fiber ONT
            │
            └── UDM Pro (192.168.0.1)
                    │
                    ├── Port 1: WAN
                    ├── Port 2: Core Switch
                    │       │
                    │       ├── DC1 (192.168.0.2)
                    │       ├── DC2 (192.168.0.131)
                    │       ├── Build (192.168.0.202)
                    │       └── mycocomp (DHCP)
                    │
                    ├── Port 3: IoT Switch (VLAN 40)
                    │       │
                    │       └── MycoBrain Devices
                    │
                    └── 26TB Internal Storage (SMB/NFS)
```

### DNS Configuration

| Domain | Target | Service |
|--------|--------|---------|
| mycosoft.com | Cloudflare Tunnel | Next.js Website |
| www.mycosoft.com | Cloudflare Tunnel | Next.js Website |
| api.mycosoft.com | Cloudflare Tunnel | MYCA API (8001) |
| dashboard.mycosoft.com | Cloudflare Tunnel | MICA Dashboard (3100) |
| webhooks.mycosoft.com | Cloudflare Tunnel | n8n Webhooks (5678) |

---

## IP Address Assignments

### VLAN 1 - Default (192.168.0.0/24)

| IP | Device | Description |
|----|--------|-------------|
| 192.168.0.1 | UDM Pro | Gateway, NAS, Cloudflared |
| 192.168.0.2 | DC1 | Proxmox Node |
| 192.168.0.131 | DC2 | Proxmox Node |
| 192.168.0.202 | Build | Primary Proxmox Node |
| 192.168.0.100-199 | Reserved | Development/Testing |

### VLAN 20 - Production (192.168.20.0/24)

| IP | VM/Service | Description |
|----|------------|-------------|
| 192.168.20.1 | Gateway | VLAN Gateway |
| 192.168.20.10 | myca-core | Orchestrator, n8n, Vault |
| 192.168.20.11 | myca-website | Website, Nginx |
| 192.168.20.12 | myca-database | All databases |
| 192.168.20.50-99 | Reserved | Future services |

### VLAN 30 - Agent Pool (192.168.30.0/24)

| IP Range | Purpose |
|----------|---------|
| 192.168.30.1 | Gateway |
| 192.168.30.10-99 | Dynamic Agent VMs |
| 192.168.30.100-199 | Reserved |

### VLAN 40 - IoT (192.168.40.0/24)

| IP Range | Purpose |
|----------|---------|
| 192.168.40.1 | Gateway |
| 192.168.40.10-99 | MycoBrain Devices |
| 192.168.40.100-199 | Other IoT |

---

## Service Port Reference

### Production Services (VLAN 20)

| Port | Service | VM | Description |
|------|---------|-----|-------------|
| **3000** | Website | myca-website | Next.js Frontend |
| **3100** | Dashboard | myca-core | MICA Voice Dashboard |
| **5432** | PostgreSQL | myca-database | Primary Database |
| **5678** | n8n | myca-core | Workflow Automation |
| **6333** | Qdrant | myca-database | Vector Database |
| **6379** | Redis | myca-database | Cache/Message Broker |
| **8000** | MINDEX | myca-core | Search API |
| **8001** | MYCA API | myca-core | Main Orchestrator API |
| **8002** | NatureOS | myca-core | Earth Simulator API |
| **8200** | Vault | myca-core | Secret Management |
| **9090** | Prometheus | myca-core | Metrics |
| **3002** | Grafana | myca-core | Monitoring Dashboards |

### Development Services (mycocomp)

| Port | Service | Description |
|------|---------|-------------|
| 3000 | Website | Dev Next.js |
| 5433 | PostgreSQL | Dev Database |
| 6345 | Qdrant | Dev Vector DB |
| 6390 | Redis | Dev Cache |
| 8001 | MAS API | Dev Orchestrator |
| 8765 | Whisper | STT (GPU) |
| 11434 | Ollama | LLM (GPU) |

> **Note**: See [PORT_ASSIGNMENTS.md](../../PORT_ASSIGNMENTS.md) for complete port reference.

---

## VLAN Configuration

### VLAN Summary

| VLAN | Name | Subnet | Purpose | Security |
|------|------|--------|---------|----------|
| 1 | Default | 192.168.0.0/24 | Management, Dev | Open |
| 20 | Production | 192.168.20.0/24 | Production VMs | Restricted |
| 30 | Agents | 192.168.30.0/24 | Agent VMs | Isolated |
| 40 | IoT | 192.168.40.0/24 | MycoBrain devices | Quarantine |

### Inter-VLAN Routing Rules

```
VLAN 1 (Management)
    ├── → VLAN 20: ALLOW (admin access)
    ├── → VLAN 30: ALLOW (management)
    └── → VLAN 40: ALLOW (IoT management)

VLAN 20 (Production)
    ├── → VLAN 1: DENY (security boundary)
    ├── → VLAN 30: ALLOW (agent control)
    └── → VLAN 40: ALLOW (sensor data ingestion)

VLAN 30 (Agents)
    ├── → VLAN 1: DENY
    ├── → VLAN 20: ALLOW (API calls only, specific ports)
    └── → VLAN 40: DENY

VLAN 40 (IoT)
    ├── → VLAN 1: DENY
    ├── → VLAN 20: ALLOW (data push, specific ports)
    └── → VLAN 30: DENY
```

---

## Setup Order and Dependencies

### Phase 1: Network Foundation

```
1.1  UDM Pro Configuration
      │
      ├── 1.1.1  26TB Storage Setup (SMB/NFS shares)
      ├── 1.1.2  VLAN Configuration
      ├── 1.1.3  Firewall Rules
      └── 1.1.4  Static IP Assignments
      │
      └── Document: UBIQUITI_NETWORK_INTEGRATION.md
```

### Phase 2: Development Environment

```
2.1  mycocomp Setup
      │
      ├── 2.1.1  Mount NAS Storage
      ├── 2.1.2  Docker Desktop Configuration
      ├── 2.1.3  GPU Drivers (RTX 5090)
      └── 2.1.4  Development Environment Variables
      │
      └── Scripts: mount_nas.ps1, start_dev.ps1
```

### Phase 3: Proxmox Cluster

```
3.1  Proxmox Configuration
      │
      ├── 3.1.1  Cluster Formation (DC1, DC2, Build)
      ├── 3.1.2  NAS Storage Integration
      ├── 3.1.3  VM Templates
      └── 3.1.4  HA Configuration
      │
      └── Document: PROXMOX_VM_DEPLOYMENT.md
```

### Phase 4: Core VMs

```
4.1  Production VMs
      │
      ├── 4.1.1  myca-core VM
      ├── 4.1.2  myca-website VM
      ├── 4.1.3  myca-database VM
      └── 4.1.4  Agent template
      │
      └── Scripts: create_myca_core_vm.py, create_agent_template.py
```

### Phase 5: External Access

```
5.1  Domain & Cloudflare
      │
      ├── 5.1.1  Cloudflare Account Setup
      ├── 5.1.2  Tunnel Installation
      ├── 5.1.3  DNS Configuration
      └── 5.1.4  SSL/TLS Setup
      │
      └── Document: DOMAIN_CLOUDFLARE_SETUP.md
```

### Phase 6: Security Hardening

```
6.1  Security Implementation
      │
      ├── 6.1.1  HashiCorp Vault Setup
      ├── 6.1.2  Secret Migration
      ├── 6.1.3  Access Control Configuration
      └── 6.1.4  Audit Logging
      │
      └── Document: SECURITY_HARDENING_GUIDE.md
```

### Phase 7: Migration

```
7.1  Dev to Prod Migration
      │
      ├── 7.1.1  Data Backup
      ├── 7.1.2  Database Migration
      ├── 7.1.3  Docker Image Transfer
      └── 7.1.4  Configuration Updates
      │
      └── Document: MIGRATION_CHECKLIST.md
```

### Phase 8: Testing & Launch

```
8.1  Pre-Launch Validation
      │
      ├── 8.1.1  Cloudflare Tunnel Testing
      ├── 8.1.2  API Endpoint Verification
      ├── 8.1.3  Security Audit
      └── 8.1.4  Performance Testing
      │
      └── Document: TESTING_DEBUGGING_PROCEDURES.md
```

---

## Quick Reference Links

### Setup Documents

| Document | Purpose |
|----------|---------|
| [UBIQUITI_NETWORK_INTEGRATION.md](./UBIQUITI_NETWORK_INTEGRATION.md) | Dream Machine & NAS setup |
| [PROXMOX_VM_DEPLOYMENT.md](./PROXMOX_VM_DEPLOYMENT.md) | VM creation & always-on services |
| [DOMAIN_CLOUDFLARE_SETUP.md](./DOMAIN_CLOUDFLARE_SETUP.md) | mycosoft.com domain integration |
| [SECURITY_HARDENING_GUIDE.md](./SECURITY_HARDENING_GUIDE.md) | NIST/DoD security alignment |
| [MIGRATION_CHECKLIST.md](./MIGRATION_CHECKLIST.md) | Dev to production migration |
| [TESTING_DEBUGGING_PROCEDURES.md](./TESTING_DEBUGGING_PROCEDURES.md) | Pre-launch testing |

### Configuration Files

| File | Purpose |
|------|---------|
| [config/development.env](../../config/development.env) | Development environment |
| [config/production.env](../../config/production.env) | Production environment |
| [config/cloudflared/config.yml](../../config/cloudflared/config.yml) | Cloudflare Tunnel |
| [config/nginx/mycosoft.conf](../../config/nginx/mycosoft.conf) | Nginx reverse proxy |

### Scripts

| Script | Purpose |
|--------|---------|
| [scripts/mount_nas.ps1](../../scripts/mount_nas.ps1) | Mount UDM Pro storage |
| [scripts/verify_storage.ps1](../../scripts/verify_storage.ps1) | Verify NAS configuration |
| [scripts/start_dev.ps1](../../scripts/start_dev.ps1) | Start development environment |
| [scripts/deploy_production.ps1](../../scripts/deploy_production.ps1) | Deploy to production |
| [scripts/proxmox/create_myca_core_vm.py](../../scripts/proxmox/create_myca_core_vm.py) | Create MYCA Core VM |
| [scripts/proxmox/create_agent_template.py](../../scripts/proxmox/create_agent_template.py) | Create agent template |

### Existing Documentation

| Document | Content |
|----------|---------|
| [docs/infrastructure/INFRASTRUCTURE_INDEX.md](../infrastructure/INFRASTRUCTURE_INDEX.md) | Implementation status |
| [PORT_ASSIGNMENTS.md](../../PORT_ASSIGNMENTS.md) | Port allocation reference |

---

## Next Steps

After reviewing this guide:

1. **Start with network** → [UBIQUITI_NETWORK_INTEGRATION.md](./UBIQUITI_NETWORK_INTEGRATION.md)
2. **Set up compute** → [PROXMOX_VM_DEPLOYMENT.md](./PROXMOX_VM_DEPLOYMENT.md)
3. **Connect domain** → [DOMAIN_CLOUDFLARE_SETUP.md](./DOMAIN_CLOUDFLARE_SETUP.md)
4. **Harden security** → [SECURITY_HARDENING_GUIDE.md](./SECURITY_HARDENING_GUIDE.md)
5. **Migrate system** → [MIGRATION_CHECKLIST.md](./MIGRATION_CHECKLIST.md)
6. **Test everything** → [TESTING_DEBUGGING_PROCEDURES.md](./TESTING_DEBUGGING_PROCEDURES.md)

---

## Appendix: Environment Quick Check

```powershell
# Verify development environment
.\scripts\verify_storage.ps1

# Check service ports
netstat -ano | findstr ":3000 :8001 :5432"

# Test NAS connectivity
Test-NetConnection -ComputerName 192.168.0.1 -Port 445

# Verify Docker
docker ps

# Check Proxmox API (from management network)
curl -k https://192.168.0.202:8006/api2/json/version
```

---

*Document maintained by MYCA Infrastructure Team*
