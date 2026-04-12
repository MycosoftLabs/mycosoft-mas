# TAC-O NIST 800-171 Rev. 2 Control Mapping
## Zeetachec + Mycosoft NUWC Tactical Oceanography
**Date:** April 8, 2026
**Status:** Self-Assessment In Progress
**System Boundary:** FUSARIUM Maritime (MycoBrain, MINDEX, MAS/MYCA, Dashboard, Network Links, Zeetachec Interfaces)

---

## Overview

This document maps all 110 NIST SP 800-171 Rev. 2 security requirements to specific TAC-O system components. The system boundary includes all components that process, store, or transmit CUI (Controlled Unclassified Information) from underwater sensor data.

---

## Control Family Mapping

### 3.1 Access Control (22 controls)

| Control | Requirement | TAC-O Component | Implementation |
|---|---|---|---|
| 3.1.1 | Limit system access to authorized users | MAS API, MINDEX API | API key authentication, RBAC roles |
| 3.1.2 | Limit system access to authorized functions | MAS Orchestrator | Per-agent capability scoping, cluster isolation |
| 3.1.3 | Control CUI flow | MINDEX, MDP protocol | Encrypted MDP channels, TLS 1.3 API endpoints |
| 3.1.4 | Separate duties of individuals | MAS Agent Permissions | TAC-O agents have distinct role scopes |
| 3.1.5 | Least privilege | MAS RBAC | Agents scoped to taco cluster only |
| 3.1.6 | Use non-privileged accounts | VM access | mycosoft user (non-root) on all VMs |
| 3.1.7 | Prevent non-privileged users from executing privileged functions | sudo controls | Sudo restricted, API keys scoped |
| 3.1.8 | Limit unsuccessful logon attempts | MAS Auth | Rate limiting on auth endpoints |
| 3.1.9 | Privacy and security notices | Dashboard | Login banners, CUI marking notices |
| 3.1.10 | Session lock | Dashboard | Auto-logout after inactivity |
| 3.1.11 | Session termination | MAS sessions | Redis session TTL (24 hours) |
| 3.1.12 | Monitor and control remote access | SSH, VPN | SSH key auth, firewall rules |
| 3.1.13 | Route remote access via managed access control points | VPN/Firewall | All access through Cloudflare tunnel or VPN |
| 3.1.14 | Limit remote access to specific points | Firewall | Port-specific firewall rules per VM |
| 3.1.15 | Authorize remote execution | MAS Orchestrator | Task authorization through agent permissions |
| 3.1.16 | Authorize wireless access | Network | WPA3 on lab network |
| 3.1.17 | Protect wireless access | Network | WPA3 encryption |
| 3.1.18 | Control connection of mobile devices | Policy | Mobile device policy (documented) |
| 3.1.19 | Encrypt CUI on mobile devices | Policy | N/A — no mobile CUI processing planned |
| 3.1.20 | Verify and control connections to external systems | Integration clients | Zeetachec client validates connections |
| 3.1.21 | Limit use of portable storage | Policy | USB storage policy for field equipment |
| 3.1.22 | Control publicly accessible CUI | Dashboard | Auth required for all CUI displays |

### 3.2 Awareness and Training (3 controls)

| Control | Requirement | Implementation |
|---|---|---|
| 3.2.1 | Security awareness training | Documented training program for team |
| 3.2.2 | Role-based training for CUI handling | CUI handling procedures (TACO_CUI_HANDLING.md) |
| 3.2.3 | Insider threat awareness | Security awareness program |

### 3.3 Audit and Accountability (9 controls)

| Control | Requirement | TAC-O Component | Implementation |
|---|---|---|---|
| 3.3.1 | Create and retain audit logs | MINDEX, MAS | All API calls logged, Merkle audit trail |
| 3.3.2 | Individual accountability through audit | MINDEX taco_assessments | All actions tied to agent/user ID |
| 3.3.3 | Review and update audit events | PolicyComplianceAgent | Automated log review |
| 3.3.4 | Alert on audit process failure | MAS monitoring | Prometheus alerts |
| 3.3.5 | Correlate audit review and reporting | MINDEX event ledger | Cross-table correlation queries |
| 3.3.6 | Provide audit reduction and report generation | Dashboard | Compliance status panel |
| 3.3.7 | System clocks synchronized | NTP | All VMs synchronized via NTP |
| 3.3.8 | Protect audit information | MINDEX | Merkle-hashed, append-only ledger |
| 3.3.9 | Limit audit log management | Access controls | Admin-only access to audit tables |

### 3.4 Configuration Management (9 controls)

| Control | Requirement | Implementation |
|---|---|---|
| 3.4.1 | Establish and maintain baseline configurations | Docker images, firmware versions |
| 3.4.2 | Establish and enforce security configuration settings | Hardened Docker configs, VM hardening |
| 3.4.3 | Track, review, approve changes | Git version control, PR reviews |
| 3.4.4 | Analyze security impact of changes | Pre-deploy regression guard |
| 3.4.5 | Define and enforce physical/logical access restrictions | VM firewall rules, RBAC |
| 3.4.6 | Least functionality | Minimal services per VM |
| 3.4.7 | Restrict/disable nonessential programs | Docker containers — minimal base images |
| 3.4.8 | Apply deny-by-exception policy | Firewall default deny |
| 3.4.9 | Control and monitor user-installed software | Docker-only deployment model |

### 3.5 Identification and Authentication (11 controls)

| Control | Requirement | Implementation |
|---|---|---|
| 3.5.1 | Identify system users | API key per user/agent |
| 3.5.2 | Authenticate users | API key + MFA for admin |
| 3.5.3 | Use multifactor authentication | MFA for admin access |
| 3.5.4 | Replay-resistant authentication | Token-based auth with nonce |
| 3.5.5 | Prevent identifier reuse | UUID-based identifiers |
| 3.5.6 | Disable identifiers after inactivity | API key expiration policy |
| 3.5.7 | Minimum password complexity | Policy enforced |
| 3.5.8 | Prohibit password reuse | Policy enforced |
| 3.5.9 | Allow temporary passwords | One-time tokens for initial setup |
| 3.5.10 | Cryptographically protect passwords | bcrypt hashing (Supabase Auth) |
| 3.5.11 | Obscure feedback during authentication | Standard web auth practices |

### 3.6 Incident Response (3 controls)

| Control | Requirement | Implementation |
|---|---|---|
| 3.6.1 | Establish incident handling capability | SecurityAgent, alert API, SOC dashboard |
| 3.6.2 | Track and report incidents | MINDEX incident logging, Prometheus alerts |
| 3.6.3 | Test incident response capability | Periodic red team exercises |

### 3.7 Maintenance (6 controls)

| Control | Requirement | Implementation |
|---|---|---|
| 3.7.1 | Perform system maintenance | CI/CD pipelines, automated updates |
| 3.7.2 | Provide controls for maintenance tools | Approved tool list |
| 3.7.3 | Ensure maintenance tools are sanitized | Docker clean builds |
| 3.7.4 | Supervise maintenance activities | Git audit trail, PR reviews |
| 3.7.5 | Require MFA for nonlocal maintenance | SSH + MFA for remote access |
| 3.7.6 | Supervise nonlocal maintenance | Logged SSH sessions |

### 3.8 Media Protection (9 controls)

| Control | Requirement | Implementation |
|---|---|---|
| 3.8.1 | Protect system media (digital/physical) | Encrypted volumes (AES-256-GCM) |
| 3.8.2 | Limit access to CUI on media | RBAC on MINDEX tables |
| 3.8.3 | Sanitize media before disposal | Secure wipe procedures |
| 3.8.4 | Mark media with CUI markings | CUI banners in data headers |
| 3.8.5 | Control access to media with CUI | Physical and logical controls |
| 3.8.6 | Implement cryptographic protection during transport | TLS 1.3 for all data in transit |
| 3.8.7 | Control removable media | USB policy for field equipment |
| 3.8.8 | Prohibit portable storage without owner | Policy documented |
| 3.8.9 | Protect backup CUI | Encrypted backups |

### 3.9 Personnel Security (2 controls)

| Control | Requirement | Implementation |
|---|---|---|
| 3.9.1 | Screen individuals before CUI access | Background checks (coordinated with Zeetachec) |
| 3.9.2 | Protect CUI during personnel actions | Access revocation procedures |

### 3.10 Physical Protection (6 controls)

| Control | Requirement | Implementation |
|---|---|---|
| 3.10.1 | Limit physical access | Server room access controls |
| 3.10.2 | Protect and monitor physical facility | Physical security measures |
| 3.10.3 | Escort visitors | Visitor policy |
| 3.10.4 | Maintain audit logs of physical access | Access logs |
| 3.10.5 | Control and manage physical access devices | Key/badge management |
| 3.10.6 | Enforce safeguarding measures at alternate work sites | Remote work policy |

### 3.11 Risk Assessment (3 controls)

| Control | Requirement | Implementation |
|---|---|---|
| 3.11.1 | Periodically assess risk | Quarterly security assessments |
| 3.11.2 | Scan for vulnerabilities | Automated vulnerability scanning |
| 3.11.3 | Remediate vulnerabilities | POA&M tracking, SPRS calculator |

### 3.12 Security Assessment (4 controls)

| Control | Requirement | Implementation |
|---|---|---|
| 3.12.1 | Periodically assess security controls | PolicyComplianceAgent automated checks |
| 3.12.2 | Develop and implement plans of action | POA&M in SPRS calculator |
| 3.12.3 | Monitor security controls continuously | Real-time compliance monitoring |
| 3.12.4 | Develop and update SSP | This document + TAC-O SSP |

### 3.13 System and Communications Protection (16 controls)

| Control | Requirement | Implementation |
|---|---|---|
| 3.13.1 | Monitor at external boundaries | Firewall logging, Cloudflare WAF |
| 3.13.2 | Employ architectural designs | Defense-in-depth (edge -> backend -> DB) |
| 3.13.3 | Separate user and system functionality | Distinct VM roles |
| 3.13.4 | Prevent unauthorized data transfer | Network segmentation |
| 3.13.5 | Implement subnetworks | VLAN segmentation |
| 3.13.6 | Deny by default | Firewall default deny |
| 3.13.7 | Prevent remote device split tunneling | VPN policy |
| 3.13.8 | Implement cryptographic mechanisms for CUI in transit | TLS 1.3 (all API), encrypted MDP |
| 3.13.9 | Terminate network connections after inactivity | Session timeout policies |
| 3.13.10 | Establish cryptographic key management | Key rotation procedures |
| 3.13.11 | Employ FIPS-validated cryptography for CUI | AES-256-GCM (FIPS 197) |
| 3.13.12 | Prohibit remote activation of collaborative devices | Policy |
| 3.13.13 | Control and monitor mobile code | No mobile code in CUI systems |
| 3.13.14 | Control and monitor VoIP | PersonaPlex voice encrypted |
| 3.13.15 | Protect communications session authenticity | TLS certificate validation |
| 3.13.16 | Protect CUI at rest | AES-256-GCM encryption at rest (MINDEX volumes) |

### 3.14 System and Information Integrity (7 controls)

| Control | Requirement | Implementation |
|---|---|---|
| 3.14.1 | Identify and report system flaws | Automated vulnerability detection |
| 3.14.2 | Protect against malicious code | Container scanning, no external code execution |
| 3.14.3 | Monitor security alerts | Prometheus + AlertManager |
| 3.14.4 | Update malicious code protection | Regular container base image updates |
| 3.14.5 | Perform periodic security scans | Automated scanning pipeline |
| 3.14.6 | Monitor inbound/outbound communications | Network logging, IDS |
| 3.14.7 | Identify unauthorized use | MINDEX audit trail, Merkle provenance |

---

## SPRS Score Summary

| Metric | Value |
|---|---|
| Total controls | 110 |
| Implemented | TBD (self-assessment in progress) |
| Partially implemented | TBD |
| Not implemented | TBD |
| SPRS Score | TBD (calculated by sprs_calculator.py) |

---

## System Boundary Components

| Component | VM | CUI Processing | Control Coverage |
|---|---|---|---|
| MycoBrain Edge | Field/Local | Sensor data ingestion | 3.1, 3.4, 3.8, 3.13 |
| Jetson Inference | Field/Local | Edge AI classification | 3.1, 3.4, 3.13, 3.14 |
| MAS Orchestrator | 188 | Classification, decision support | 3.1, 3.3, 3.5, 3.13, 3.14 |
| MINDEX Database | 189 | CUI storage, provenance | 3.1, 3.3, 3.8, 3.13, 3.14 |
| FUSARIUM Dashboard | 187 | CUI display | 3.1, 3.5, 3.9, 3.13 |
| Network Links | All | CUI transmission | 3.13 |
| Zeetachec Interfaces | External | Data ingestion | 3.1, 3.13 |
