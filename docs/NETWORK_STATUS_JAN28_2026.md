# NETWORK STATUS REPORT - January 28, 2026
## Post-Rewiring Infrastructure Assessment

**Date:** January 28, 2026
**Status:** INFRASTRUCTURE PARTIALLY OFFLINE
**Priority:** CRITICAL - VMs need to be started

---

## CURRENT NETWORK TOPOLOGY

### Discovered Devices (11 Total)

| IP | MAC | Type | Ports Open | Role | Status |
|----|-----|------|------------|------|--------|
| 192.168.0.1 | 58:D6:1F:21:13:18 | Gateway | - | **Dream Machine Pro Max** | ✅ ONLINE |
| 192.168.0.2 | 24:6E:96:63:7F:14 | Switch | - | **USW Pro Max 24 PoE** | ✅ ONLINE |
| 192.168.0.34 | 84:7B:EB:F5:E3:C2 | Web Device | 80 | ASUS WiFi? | ✅ ONLINE |
| 192.168.0.68 | 8C:30:66:7A:3F:70 | Linux | 22 | Unknown Server | ✅ ONLINE |
| 192.168.0.85 | 84:7B:EB:F7:61:F6 | Unknown | - | ASUS WiFi? | ✅ ONLINE |
| 192.168.0.90 | 24:6E:96:60:65:CC | **PROXMOX** | 22, 8006 | **Dell Server #1** | ⚠️ AUTH FAIL |
| 192.168.0.104 | 6C:63:F8:37:12:25 | Unknown | - | NAS Interface? | ✅ ONLINE |
| 192.168.0.105 | 6C:63:F8:37:12:26 | NAS | - | **UNAS-Pro** | ✅ ONLINE |
| 192.168.0.120 | 84:2B:2B:46:13:EE | UniFi/Server | 22, 443 | **Dell Server #2?** | ✅ ONLINE |
| 192.168.0.163 | 58:D6:1F:47:33:EB | Unknown | - | UniFi Device | ✅ ONLINE |
| 192.168.0.172 | - | Windows | Many | **Windows Dev PC** | ✅ ONLINE |

### MAC Address Vendor Analysis

| MAC Prefix | Vendor | Devices |
|------------|--------|---------|
| 24:6E:96 | **Dell** | 192.168.0.2 (Switch), 192.168.0.90 (Proxmox) |
| 58:D6:1F | **Ubiquiti** | 192.168.0.1 (Dream Machine), 192.168.0.163 |
| 84:7B:EB | **ASUS** | 192.168.0.34, 192.168.0.85 |
| 6C:63:F8 | **ODROID/NAS** | 192.168.0.104, 192.168.0.105 |
| 8C:30:66 | **Virtual/Server** | 192.168.0.68 |
| 84:2B:2B | **Dell** | 192.168.0.120 |

---

## CRITICAL ISSUES

### 1. Proxmox Authentication Failing

**IP:** 192.168.0.90
**Issue:** Web UI and API returning 401 Unauthorized
**Expected Credentials:** root / 20202020
**SSH:** Port 22 is open

**Recommended Action:**
1. Access Proxmox via physical console
2. Or SSH to 192.168.0.90 with root / 20202020 and run:
   ```bash
   pveum user list
   passwd root  # Reset password if needed
   ```

### 2. VMs Not Running

| VM | Expected IP | Current Status | Action Needed |
|----|-------------|----------------|---------------|
| **Sandbox VM (103)** | 192.168.0.187 | ❌ OFFLINE | Start from Proxmox |
| **MAS VM** | 192.168.0.188 | ❌ OFFLINE | Start from Proxmox |

**Impact:**
- Website (sandbox.mycosoft.com) is DOWN
- MAS Orchestrator is DOWN
- MINDEX API is DOWN
- n8n workflows are DOWN

### 3. IP Address Changes

After rewiring with new USW Pro Max 24 PoE switch:

| Device | Old IP | New IP | Change |
|--------|--------|--------|--------|
| Proxmox Server #1 | 192.168.0.202 | 192.168.0.90 | CHANGED |
| USW Pro Max 24 PoE | N/A | 192.168.0.2 | NEW |

---

## NETWORK WIRING STATUS

### Current Physical Topology

```
                    ISP FIBER
                        │
                ┌───────▼───────┐
                │ Dream Machine │ 192.168.0.1
                │ Pro Max       │
                └───────┬───────┘
                        │ 10GbE (Cat8)
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
  ┌───────────┐  ┌───────────┐  ┌───────────┐
  │ Dell #1   │  │ Dell #2   │  │ Dell #3   │
  │ Proxmox   │  │ (Unknown) │  │ (Unknown) │
  │ .90       │  │ .120      │  │ .68?      │
  └───────────┘  └───────────┘  └───────────┘
        │
        │ (Also to USW Pro Max 24 PoE)
        ▼
  ┌───────────────────┐
  │ USW Pro Max 24PoE │ 192.168.0.2
  │ (New Switch)      │
  └─────────┬─────────┘
            │
            ▼
  ┌───────────────────┐
  │ UNAS-Pro (NAS)    │ 192.168.0.105
  │ 10GbE (SFP+/RJ45) │
  └───────────────────┘
```

### Recommended Wiring Verification

1. **Dell Server #1 (Proxmox - 192.168.0.90)**
   - Verify 10GbE connection to Dream Machine or USW switch
   - Should host Sandbox VM (103) and potentially MAS VM

2. **Dell Server #2 (192.168.0.120)**
   - Check if this has Proxmox installed
   - May need port 8006 enabled or service started

3. **Dell Server #3 (192.168.0.68?)**
   - Verify role and configuration
   - SSH is open - may be accessible

---

## IMMEDIATE ACTION PLAN

### Step 1: Fix Proxmox Access (CRITICAL)

Option A - SSH Access:
```powershell
# From Windows PC
ssh root@192.168.0.90
# Password: 20202020

# Once logged in:
pveum user list
systemctl status pveproxy
```

Option B - Physical Console:
1. Connect monitor/keyboard to Proxmox server
2. Login with root / 20202020
3. Check pveproxy service status

### Step 2: Start VMs

Once Proxmox access is restored:
```bash
# On Proxmox server
qm list                    # List all VMs
qm start 103               # Start Sandbox VM
qm start <MAS_VMID>        # Start MAS VM (find ID first)
```

### Step 3: Verify VM IPs

After VMs start:
```bash
# Check VM IPs via QEMU agent
qm guest exec 103 -- ip addr show
```

### Step 4: Update Configuration Files

If VM IPs changed, update:
- `config/production.env` - PROXMOX_HOST_BUILD
- `.env.local` - N8N_URL
- Cloudflare tunnel configurations

---

## SERVICES IMPACT SUMMARY

| Service | Location | Expected Status | Current |
|---------|----------|-----------------|---------|
| Website | Sandbox VM:3000 | Running | ❌ VM OFFLINE |
| MINDEX API | Sandbox VM:8000 | Running | ❌ VM OFFLINE |
| n8n | MAS VM:5678 | Running | ❌ VM OFFLINE |
| MycoBrain | Windows:8003 | Running | ✅ ONLINE |
| Cloudflare Tunnel | Sandbox VM | Running | ❌ VM OFFLINE |

---

## FILES TO UPDATE AFTER FIX

| File | Update Needed |
|------|---------------|
| `config/production.env` | PROXMOX_HOST_BUILD if IP changed |
| `scripts/network_topology_scanner.py` | Add new IP 192.168.0.90 |
| `docs/NETWORK_INFRASTRUCTURE_JAN21_2026.md` | Update with new topology |

---

**Document Created:** 2026-01-28 12:55 UTC
**Created By:** Infrastructure Agent
**Next Review:** After Proxmox access restored
