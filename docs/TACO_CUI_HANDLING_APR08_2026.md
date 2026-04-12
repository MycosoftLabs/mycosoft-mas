# TAC-O CUI Handling Procedures
## Controlled Unclassified Information Management
**Date:** April 8, 2026
**Status:** Active
**Applicable To:** All TAC-O sensor data, classifications, and assessments
**Authority:** NIST SP 800-171 Rev. 2, 32 CFR Part 2002

---

## 1. CUI Categories in TAC-O

| Data Type | CUI Category | Marking | Source |
|---|---|---|---|
| Raw acoustic sensor data | CTI (Critical Infrastructure) | CUI//SP-CTI | Zeeta Fuze |
| Raw magnetic sensor data | CTI | CUI//SP-CTI | Zeeta Fuze |
| NLM classification results | OPSEC | CUI//SP-OPSEC | NLM Engine |
| Tactical assessments | OPSEC | CUI//SP-OPSEC | MYCA Agents |
| Sonar performance predictions | OPSEC | CUI//SP-OPSEC | NLM Engine |
| Environmental baselines | Basic CUI | CUI | NOAA/HYCOM |
| Training datasets (labeled) | CTI | CUI//SP-CTI | Zeetachec field data |
| System configuration | PRVCY | CUI//SP-PRVCY | System admin |

---

## 2. CUI Marking Requirements

### Digital Files
- All CUI files must include a CUI banner in the first line/header
- Format: `CUI//SP-[CATEGORY] — Distribution limited to [scope]`
- JSON/JSONB fields in MINDEX include `cui_marking` field

### Database Records
- MINDEX `taco_observations` and `taco_assessments` tables include CUI marking columns
- Merkle hash provides provenance chain for all stored CUI

### API Responses
- All TAC-O API responses include `X-CUI-Category` header
- CUI data is never cached in browser or CDN (Cache-Control: no-store)

### Dashboard Display
- CUI banner displayed on all FUSARIUM Maritime dashboard pages
- Session-locked display with auto-logout after 15 minutes idle

---

## 3. Storage Requirements

### Encryption at Rest
- **Standard:** AES-256-GCM (FIPS 197 compliant)
- **MINDEX PostgreSQL:** Encrypted volumes on VM 189
- **Redis Cache:** Encrypted memory, session data TTL 24 hours max
- **Qdrant Vectors:** Encrypted vector storage volumes
- **MycoBrain Edge:** Encrypted flash storage for buffered data

### Access Controls
- RBAC on all MINDEX tables containing CUI
- API key authentication required for all TAC-O endpoints
- MFA required for admin access to CUI tables

### Backup
- CUI backups encrypted with AES-256-GCM
- Backup media stored in controlled access location
- Backup retention: 90 days (aligned with OTA terms)

---

## 4. Transmission Requirements

### In Transit Encryption
- **Standard:** TLS 1.3 for all API communications
- **MDP Protocol:** Encrypted payload between MycoBrain and MAS
- **LoRa/RF Link:** Application-layer encryption (AES-128 minimum)
- **WebSocket Streams:** WSS (TLS 1.3) for real-time dashboard feeds

### Network Controls
- CUI only transmitted over private network (192.168.0.x)
- External access via Cloudflare tunnel (HTTPS only)
- No CUI transmission over public internet without encryption

---

## 5. Processing Requirements

### Edge Processing (MycoBrain/Jetson)
- CUI processed in memory only; not persisted unencrypted
- Edge inference results encrypted before MDP transmission
- Raw sensor data cleared from edge buffer after transmission

### Server Processing (MAS/MINDEX)
- CUI processed within authenticated API context
- All processing logged to MINDEX audit trail
- AVANI ecological gate reviews all classifications before display

### Provenance
- Every CUI observation receives a Merkle hash at ingestion
- Hash chain links observations to assessments
- Full audit trail queryable via MINDEX ledger API

---

## 6. Destruction Requirements

### Digital Destruction
- CUI data destroyed via secure overwrite (DoD 5220.22-M standard)
- Database records: cryptographic erasure (destroy encryption keys)
- Edge device: secure flash erase on decommission
- Backup media: degaussing or physical destruction

### Retention Period
- Active CUI retained for duration of OTA prototype period
- Post-contract retention per Government data rights terms
- Training data retained with Government Purpose Rights

---

## 7. Incident Response for CUI Breach

### Detection
- PolicyComplianceAgent monitors all CUI access in real-time
- Unauthorized access triggers immediate alert via MAS SecurityAgent
- Network anomalies logged and correlated

### Response
1. Isolate affected system component
2. Notify Zeetachec (prime contractor) within 1 hour
3. Notify NUWC contracting officer within 72 hours (per DFARS 252.204-7012)
4. Preserve forensic evidence in MINDEX audit trail
5. Conduct root cause analysis
6. Implement corrective actions and update POA&M

### Reporting
- Incident details logged in MINDEX with Merkle-verified timestamps
- After-action report generated and stored
- SPRS score updated if controls affected

---

## 8. Personnel Requirements

| Role | CUI Access | Training Required |
|---|---|---|
| Morgan (CEO) | Full | CUI awareness, NIST 800-171 |
| Zeetachec team (field) | Sensor data | CUI handling for field ops |
| MYCA agents (automated) | All TAC-O CUI | Constrained by PolicyComplianceAgent |
| Operators (NUWC) | Dashboard CUI | Operator CUI training |

---

## 9. System Components and CUI Flow

```
Zeeta Fuze (CUI//SP-CTI) 
  -> encrypted LoRa/RF -> Zeeta Buoy
  -> MycoBrain (process in memory, encrypt for MDP)
  -> encrypted MDP -> Jetson (edge inference, no persist)
  -> encrypted stream -> MAS (CUI//SP-OPSEC classification)
  -> encrypted insert -> MINDEX (CUI at rest, AES-256-GCM)
  -> TLS 1.3 -> FUSARIUM Dashboard (CUI display, session-locked)
```

All transitions are encrypted. No unencrypted CUI at any point.
