# MYCOSOFT 90-DAY SCALING PLAN

**Document Version**: 1.0.0  
**Date**: 2026-01-17  
**Timeline**: January 17, 2026 - April 17, 2026  
**Author**: AI Infrastructure Planning  
**Status**: 📋 APPROVED FOR IMPLEMENTATION

---

## 📊 EXECUTIVE SUMMARY

This document outlines the 90-day plan to scale the Mycosoft platform to efficiently handle:
- Growing API data ingestion
- Local data resilience (offline-capable MINDEX)
- Increased compute for AI/ML workloads
- Multi-region redundancy preparation

### Key Goals

1. **Data Resilience**: All scraped API data stored locally in MINDEX
2. **Offline Capability**: System functional even if external APIs go down
3. **Scalability**: Handle 10x current data volume
4. **Performance**: Maintain <500ms response times under load

---

## 📈 CURRENT STATE (Day 0)

### Resource Allocation

| Resource | VM 103 (Sandbox) | Windows Dev | Total |
|----------|------------------|-------------|-------|
| CPU Cores | 4 | 8 | 12 |
| RAM | 8 GB | 32 GB | 40 GB |
| Storage | 100 GB | 500 GB | 600 GB |
| Network | 1 Gbps | 1 Gbps | Shared |

### Data Volumes

| Data Type | Current Size | Growth Rate |
|-----------|--------------|-------------|
| MINDEX Observations | 500 MB | +50 MB/day |
| PostgreSQL (total) | 2 GB | +100 MB/day |
| Qdrant Vectors | 100 MB | +20 MB/day |
| Docker Images | 15 GB | +1 GB/week |
| Logs | 500 MB | +200 MB/day |
| Backups | 5 GB | +500 MB/day |

### External API Dependencies

| API | Data Volume | Refresh Rate | Critical |
|-----|-------------|--------------|----------|
| iNaturalist | 21,757 obs | Daily | Yes |
| GBIF | ~100K records | Weekly | Yes |
| OpenSky | Real-time | 15 sec | Yes |
| AISStream | Real-time | Streaming | Yes |
| OpenAQ | 1000+ stations | Hourly | Medium |
| NWS Alerts | Variable | 5 min | Yes |

---

## 📅 PHASE 1: STABILIZATION (Days 1-14)

### Week 1 (Jan 17-24)

| Day | Task | Owner | Status |
|-----|------|-------|--------|
| 1 | Fix MINDEX ETL container | DevOps | Pending |
| 1 | Resolve Ollama health issues | DevOps | Pending |
| 2 | Configure brain-sandbox route | DevOps | Pending |
| 3 | Implement MycoBrain API auth | Backend | Pending |
| 4 | Set up automated backups | DevOps | Pending |
| 5 | Security audit remediation | Security | Pending |
| 6-7 | Documentation review | Team | Pending |

### Week 2 (Jan 24-31)

| Day | Task | Owner | Status |
|-----|------|-------|--------|
| 8 | MINDEX full data sync | Data | Pending |
| 9 | Performance baseline testing | QA | Pending |
| 10 | Monitoring alerts setup | DevOps | Pending |
| 11 | Grafana dashboard creation | DevOps | Pending |
| 12 | Load testing (baseline) | QA | Pending |
| 13-14 | Phase 1 review | Team | Pending |

### Phase 1 Deliverables

- [ ] All 17 containers healthy
- [ ] MINDEX synced with 21,757+ observations
- [ ] Automated daily backups
- [ ] Monitoring dashboards live
- [ ] Performance baseline documented

---

## 📅 PHASE 2: INFRASTRUCTURE UPGRADE (Days 15-45)

### Week 3-4 (Feb 1-14)

**VM Resource Upgrade**

| Resource | Current | Target | Action |
|----------|---------|--------|--------|
| CPU | 4 cores | 16 cores | Proxmox resize |
| RAM | 8 GB | 32 GB | Proxmox resize |
| Storage | 100 GB | 500 GB | Add disk |

```bash
# Proxmox commands (on hypervisor)
qm set 103 --cores 16
qm set 103 --memory 32768
qm resize 103 scsi0 +400G
```

### Week 5-6 (Feb 15-28)

**Data Layer Enhancements**

| Enhancement | Purpose | Priority |
|-------------|---------|----------|
| PostgreSQL read replicas | Query performance | High |
| Redis Cluster | Cache scalability | Medium |
| Qdrant sharding | Vector search speed | Medium |
| S3-compatible storage | Blob storage | Medium |

### Phase 2 Deliverables

- [ ] VM upgraded to 16 cores, 32 GB RAM
- [ ] 500 GB storage allocated
- [ ] Database replication configured
- [ ] Cache layer optimized
- [ ] Load tested at 5x current capacity

---

## 📅 PHASE 3: DATA RESILIENCE (Days 46-75)

### Week 7-8 (Mar 1-14)

**Local Data Caching Strategy**

Implement local mirrors for all external APIs:

```
External API → ETL Pipeline → MINDEX → Local Cache → Application
                    ↓
              Fallback Mode (if API down)
                    ↓
              Use Local Cache
```

| Data Source | Cache Strategy | Freshness |
|-------------|----------------|-----------|
| iNaturalist | Full mirror | 24 hours |
| GBIF | Incremental sync | 7 days |
| OpenSky | Rolling 24h cache | Real-time |
| AISStream | Rolling 24h cache | Real-time |
| OpenAQ | Full mirror | 1 hour |
| NWS | Full mirror | 5 min |
| Weather | Full mirror | 30 min |

### Week 9-10 (Mar 15-28)

**Offline Capability Implementation**

| Component | Offline Mode | Implementation |
|-----------|--------------|----------------|
| CREP Dashboard | Use cached data | Service worker |
| MycoBrain | Continue logging | Local queue |
| Species Search | Local MINDEX | Full index |
| Weather | Cached forecasts | 48h cache |
| Alerts | Cached alerts | 24h cache |

### Phase 3 Deliverables

- [ ] All external data cached locally
- [ ] Offline mode tested and verified
- [ ] Automatic fallback on API failure
- [ ] Data freshness indicators in UI
- [ ] Recovery procedures documented

---

## 📅 PHASE 4: PRODUCTION READINESS (Days 76-90)

### Week 11-12 (Mar 29 - Apr 14)

**Production Environment Setup**

| Component | Sandbox | Production |
|-----------|---------|------------|
| Domain | sandbox.mycosoft.com | mycosoft.com |
| VM | 103 | 104 (new) |
| Data | Subset | Full |
| Backups | Daily | Hourly |
| Monitoring | Basic | Full |

### Week 13 (Apr 14-17)

**Final Validation**

| Test | Target | Acceptance |
|------|--------|------------|
| Load test | 1000 req/sec | Pass |
| Failover test | <30 sec | Pass |
| Offline test | Full function | Pass |
| Security scan | No critical | Pass |
| Performance | <500ms p95 | Pass |

### Phase 4 Deliverables

- [ ] Production VM provisioned
- [ ] Data migrated
- [ ] DNS cutover plan ready
- [ ] Rollback procedures tested
- [ ] Go-live checklist complete

---

## 💾 STORAGE PROJECTIONS

### 90-Day Growth Estimates

| Data Type | Day 0 | Day 30 | Day 60 | Day 90 |
|-----------|-------|--------|--------|--------|
| MINDEX | 500 MB | 2 GB | 4 GB | 6 GB |
| PostgreSQL | 2 GB | 5 GB | 10 GB | 15 GB |
| Qdrant | 100 MB | 500 MB | 1 GB | 2 GB |
| Images | 15 GB | 18 GB | 22 GB | 25 GB |
| Logs | 500 MB | 6 GB | 12 GB | 18 GB |
| Backups | 5 GB | 20 GB | 40 GB | 60 GB |
| **Total** | **23 GB** | **51 GB** | **89 GB** | **126 GB** |

### Recommended Storage Allocation

```
/opt/mycosoft/           500 GB (NVMe SSD)
├── data/                300 GB
│   ├── postgres/        100 GB
│   ├── mindex/          50 GB
│   ├── qdrant/          20 GB
│   ├── redis/           5 GB
│   └── n8n/             5 GB
├── backups/             100 GB
├── logs/                50 GB
└── docker/              50 GB
```

---

## 🖥️ COMPUTE REQUIREMENTS

### Current vs Target

| Workload | Current | Day 30 | Day 60 | Day 90 |
|----------|---------|--------|--------|--------|
| Website | 1 core | 2 cores | 2 cores | 4 cores |
| MINDEX | 1 core | 2 cores | 4 cores | 4 cores |
| MAS Orch | 1 core | 2 cores | 2 cores | 4 cores |
| n8n | 0.5 core | 1 core | 2 cores | 2 cores |
| Ollama | 4 cores | 8 cores | 8 cores | 8 cores |
| Databases | 2 cores | 4 cores | 4 cores | 8 cores |
| Other | 2 cores | 2 cores | 4 cores | 4 cores |
| **Total** | **12** | **21** | **26** | **34** |

### Memory Requirements

| Service | Current | Target |
|---------|---------|--------|
| Website | 2 GB | 4 GB |
| MINDEX API | 1 GB | 2 GB |
| PostgreSQL | 2 GB | 8 GB |
| Redis | 256 MB | 1 GB |
| Qdrant | 512 MB | 2 GB |
| Ollama | 8 GB | 16 GB |
| n8n | 512 MB | 1 GB |
| Other | 2 GB | 4 GB |
| **Total** | **16 GB** | **38 GB** |

---

## 📊 METRICS & KPIs

### Performance Targets

| Metric | Current | Target | Monitoring |
|--------|---------|--------|------------|
| API p50 latency | ~200ms | <100ms | Prometheus |
| API p95 latency | ~800ms | <500ms | Prometheus |
| Page load time | ~2s | <1s | Grafana |
| Container uptime | 88% | 99.9% | Docker |
| Data freshness | Variable | <5 min | Custom |
| Error rate | 5% | <0.1% | Grafana |

### Capacity Targets

| Metric | Day 0 | Day 90 |
|--------|-------|--------|
| Concurrent users | 10 | 1000 |
| API requests/sec | 10 | 1000 |
| Data points/day | 10K | 1M |
| Storage I/O | 100 MB/s | 1 GB/s |

---

## 💰 COST ESTIMATES

### Infrastructure Costs (Monthly)

| Resource | Current | Day 90 | Provider |
|----------|---------|--------|----------|
| Proxmox VM | $0 | $0 | Self-hosted |
| Cloudflare | $0 | $20 | Cloudflare |
| API costs | $50 | $200 | Various |
| Backups | $0 | $20 | Cloudflare R2 |
| **Total** | **$50** | **$240** | - |

### API Cost Breakdown

| API | Current | Projected | Notes |
|-----|---------|-----------|-------|
| OpenAI | $30/mo | $100/mo | MYCA usage |
| Google Maps | $10/mo | $50/mo | Tile requests |
| OpenSky | Free | Free | Rate limited |
| iNaturalist | Free | Free | Rate limited |
| **Total** | $40/mo | $150/mo | - |

---

## ✅ SUCCESS CRITERIA

### Day 30 Milestone

- [ ] All containers stable (>99% uptime)
- [ ] VM upgraded to 16 cores, 32 GB
- [ ] Automated backups running
- [ ] Monitoring dashboards complete
- [ ] Security issues remediated

### Day 60 Milestone

- [ ] 500 GB storage utilized
- [ ] Local data caching operational
- [ ] Offline mode tested
- [ ] 5x load test passed
- [ ] Documentation complete

### Day 90 Milestone

- [ ] Production environment ready
- [ ] 10x capacity achieved
- [ ] Full data resilience
- [ ] <500ms p95 latency
- [ ] Go-live approved

---

## 📝 RISK REGISTER

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| API rate limits | High | Medium | Implement caching |
| Storage exhaustion | Medium | High | Monitor growth |
| VM resource contention | Medium | Medium | Upgrade proactively |
| Data corruption | Low | Critical | Regular backups |
| Security breach | Low | Critical | Implement audit |

---

**END OF 90-DAY SCALING PLAN**

*Review and update this document weekly during execution.*
