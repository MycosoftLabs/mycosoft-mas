# Edge Operator Safety, Audit, Approval, and Rollback

**Date:** March 7, 2026  
**Status:** Active  
**Related:** `DEVICE_JETSON16_CORTEX_ARCHITECTURE_MAR07_2026.md`, Jetson-Backed MycoBrain Field Architecture plan

---

## Overview

The on-device 16GB Jetson runs the edge operator runtime. It can propose actions, scripts, and firmware updates. **All code and firmware mutation requires explicit approval and safety gates.** This document defines safety boundaries, audit requirements, approval flows, and rollback procedures.

---

## 1. Safety Boundaries

### 1.1 What the Edge Operator May Do Without Approval

| Action | Scope | Notes |
|--------|-------|-------|
| Read sensors | Side A telemetry | Already authorized |
| Stream sensors | Rate-limited reads | Within rate_hz limits |
| Send transport directives | Side B (lora_send, ble_advertise, etc.) | Transport only, no app logic |
| Local inference | Camera, audio, Whisper | On-device only |
| Report to MAS | Heartbeat, operator state | Summary only |
| Propose actions | MYCA/operator session | Proposal only; no execution |

### 1.2 What Requires Approval

| Action | Approval Gate | Approver |
|--------|---------------|----------|
| Firmware flash (Side A, Side B) | Explicit human or MYCA-with-Morgan-oversight | Morgan or delegated keyholder |
| Code/script execution on device | Approval required | Morgan or delegated |
| OTA update to Jetson | Approval required | Morgan or delegated |
| Estop override / reset | May require confirmation | Depends on context |
| Configuration change (persistent) | Logged; high-risk changes need approval | Morgan or delegated |

### 1.3 What Is Forbidden

| Action | Reason |
|--------|--------|
| Auto-flash firmware | Risk of bricking; no rollback without approval flow |
| Auto-execute arbitrary code | Security; must have audit and approval |
| Replace canonical device_id | Identity invariant |
| Bypass command arbitration | All commands through Jetson |
| Mutate Side A/Side B without audit log | Forensics and rollback require audit |

---

## 2. Audit Requirements

### 2.1 What Must Be Logged

| Event | Log Fields | Retention |
|-------|------------|-----------|
| Command to Side A | cmd, params, seq, timestamp, source | Local ring buffer + persistent |
| Command to Side B | cmd, params, seq, timestamp, source | Local ring buffer + persistent |
| Proposal (script, firmware) | proposal_id, type, hash, timestamp | Persistent |
| Approval / rejection | proposal_id, approver, decision, timestamp | Persistent |
| Firmware flash | device, version, hash, result | Persistent |
| Estop | timestamp, source | Persistent |

### 2.2 Audit Trail Format

- **Local**: JSONL or structured log on Jetson
- **Upstream**: Optional sync to MAS or MINDEX for central audit (future)
- **Integrity**: Optional checksum per entry for tamper detection

### 2.3 Access and Retention

- Audit logs are readable by Morgan and delegated operators
- Minimum retention: 30 days local; configurable
- Export for compliance: Manual or scheduled

---

## 3. Approval Flows

### 3.1 Firmware Update

```
Edge Operator proposes firmware update
    → Log proposal (hash, target, version)
    → Notify MYCA / Morgan
    → MYCA or Morgan approves or rejects
    → If approved: Execute flash; log result
    → If rejected: Log rejection; do not execute
```

- **No auto-approval** for firmware
- **Morgan** or **RJ (MYCA 2nd Key)** may approve
- Delegation: Document in skill_permissions or equivalent

### 3.2 Script / Code Execution

```
Edge Operator proposes script/code
    → Log proposal (hash, scope, risk level)
    → Approval required
    → If approved: Execute in sandbox; log output
    → If rejected: Do not execute
```

- Scripts that touch hardware (GPIO, I2C, serial) require higher scrutiny
- Read-only scripts (e.g. diagnostics) may have lower bar; still logged

### 3.3 Configuration Change

- Non-destructive config (e.g. telemetry interval): Log only
- Destructive or security-affecting: Approval required

---

## 4. Rollback Procedures

### 4.1 Firmware Rollback

1. **Pre-flash**: Record current firmware version and hash
2. **Post-flash**: If boot fails or device unreachable, use recovery path
3. **Recovery**: Flash MycoBrain_Working (minimal) via serial to restore serial and basic I/O
4. **Restore**: Re-flash last known good firmware (DeviceManager or Side A) after recovery

### 4.2 Operator State Rollback

- Local operator state (e.g. rate limits, config) stored in mutable config
- Keep last-known-good snapshot before approval-triggered changes
- Rollback = restore snapshot; log rollback event

### 4.3 Command Revert

- Commands to Side A (e.g. MOSFET on) are not automatically reverted
- Estop clears outputs; follow-up commands required to restore prior state
- Audit log enables manual reconstruction of prior state if needed

---

## 5. Code and Firmware Mutation Boundaries

### 5.1 Invariants

1. **No auto-apply** — All firmware and code mutation requires explicit approval
2. **Audit always** — Every mutation attempt (proposed or executed) is logged
3. **Rollback path** — Recovery firmware and procedure must exist before flash
4. **Identity unchanged** — Firmware update does not change canonical device_id

### 5.2 Proposal Contract

When the edge operator proposes a mutation:

```json
{
  "proposal_id": "uuid",
  "type": "firmware|script|config",
  "target": "side_a|side_b|jetson",
  "hash": "sha256",
  "version": "1.2.3",
  "risk": "low|medium|high|critical",
  "timestamp": "ISO8601"
}
```

- **risk**: Drives approval threshold (critical = Morgan only)

### 5.3 Gates Before Execution

1. Approval present and valid
2. Hash matches proposal
3. Target is reachable
4. Rollback path documented
5. No conflicting mutation in progress

---

## 6. Implementation Phases

| Phase | Deliverable |
|-------|-------------|
| 1 (Design) | This document |
| 2 | Audit logging in jetson_server.py (or edge operator module) |
| 3 | Proposal API and approval webhook/UI |
| 4 | Firmware flash with pre/post checks and rollback |
| 5 | MYCA integration for approval workflow |

---

## 7. References

- `DEVICE_JETSON16_CORTEX_ARCHITECTURE_MAR07_2026.md` — Jetson role, command arbitration
- `MYCOBRAIN_FIRMWARE_BASELINE_REBASELINE_MAR07_2026.md` — Recovery firmware (MycoBrain_Working)
- `mycosoft_mas/edge/jetson_server.py` — Current Jetson server
- `mycosoft_mas/myca/skill_permissions/` — Skill and delegation model
