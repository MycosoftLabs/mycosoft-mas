# Proxmox & UniFi API Token Regeneration Guide

**Created**: January 23, 2026  
**Purpose**: Regenerate expired API tokens for full infrastructure scanning

---

## Part 1: Proxmox API Token Regeneration

### Current Issue
The existing Proxmox API token is returning **HTTP 401 (Unauthorized)**:
- Token ID: `root@pam!cursor_mycocomp`
- Status: **EXPIRED or INVALID**

### Step-by-Step Regeneration

#### Method A: Via Proxmox Web UI (Recommended)

1. **Open Proxmox Web UI**
   ```
   URL: https://192.168.0.202:8006
   Username: root
   Password: 20202020
   Realm: PAM
   ```
   > Note: You'll need to accept the self-signed certificate warning

2. **Navigate to API Tokens**
   - Click **Datacenter** in the left panel
   - Go to **Permissions** → **API Tokens**

3. **Delete Old Token (Optional)**
   - Find `cursor_mycocomp` in the list
   - Click **Remove** to delete the expired token

4. **Create New Token**
   - Click **Add**
   - Fill in:
     - **User**: `root@pam`
     - **Token ID**: `cursor_agent` (or any name you prefer)
     - **Privilege Separation**: **Unchecked** (No)
     - **Expire**: Leave empty for no expiration
   - Click **Add**
   - **IMPORTANT**: Copy the token secret shown - you won't see it again!

5. **Record the New Token**
   - Token format: `root@pam!cursor_agent=XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`

#### Method B: Via SSH Command Line

```bash
# SSH into Proxmox
ssh root@192.168.0.202
# Password: 20202020

# Delete old token
pveum user token remove root@pam cursor_mycocomp

# Create new token (privilege separation disabled)
pveum user token add root@pam cursor_agent --privsep=0

# The command will output the new token secret
```

### Update Configuration Files

After getting the new token, update these files:

#### 1. `docs/PROXMOX_UNIFI_API_REFERENCE.md`

Replace the old token in the Authentication section:
```python
# OLD (line ~25)
"Authorization": "PVEAPIToken=root@pam!cursor_mycocomp=9b86f08b-40ff-4eb9-b41b-93bc9e11700f"

# NEW (replace with your new token)
"Authorization": "PVEAPIToken=root@pam!cursor_agent=YOUR-NEW-TOKEN-HERE"
```

#### 2. `scripts/security_audit_scanner.py`

Update the PROXMOX_CONFIG section (around line 153):
```python
PROXMOX_CONFIG = {
    "host": "192.168.0.202",
    "port": 8006,
    "token": "root@pam!cursor_agent=YOUR-NEW-TOKEN-HERE"  # Update this
}
```

#### 3. Test the New Token

```powershell
# Quick test from PowerShell
curl.exe -k -H "Authorization: PVEAPIToken=root@pam!cursor_agent=YOUR-NEW-TOKEN-HERE" "https://192.168.0.202:8006/api2/json/nodes"

# Expected output: JSON with node data (not 401)
```

---

## Part 2: UniFi API Configuration

### Current Status
UniFi Dream Machine is reachable at `192.168.0.1` but API credentials are not configured.

### Step-by-Step Configuration

#### 1. Create UniFi Local Account

1. **Access UniFi Controller**
   ```
   URL: https://192.168.0.1
   ```

2. **Navigate to Settings**
   - Click the gear icon (Settings)
   - Go to **System** → **System Settings**

3. **Create Local Admin Account**
   - Go to **Admins & Users**
   - Click **Add New Admin**
   - Fill in:
     - **Name**: `api_scanner`
     - **Email**: `api@mycosoft.local`
     - **Password**: Create a strong password
     - **Role**: **Super Admin** (for full API access)
     - **Account Type**: **Local Access Only**
   - Save the account

#### 2. Get UniFi API Credentials

For UniFi OS (Dream Machine), you can use either:

**Option A: Username/Password Authentication**
```python
UNIFI_CONFIG = {
    "host": "192.168.0.1",
    "port": 443,
    "username": "api_scanner",
    "password": "YOUR_PASSWORD_HERE",
}
```

**Option B: Generate API Key (if available)**
- Some UniFi versions support API keys in Settings → System → Advanced

#### 3. Update Security Scanner

Edit `scripts/security_audit_scanner.py` (around line 160):
```python
UNIFI_CONFIG = {
    "host": "192.168.0.1",
    "port": 443,
    "username": "api_scanner",        # Add your username
    "password": "YOUR_PASSWORD_HERE", # Add your password
}
```

---

## Part 3: Post-Configuration Verification

### Run Full Security Audit

After updating both tokens:

```powershell
cd c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas

# Test Proxmox first
curl.exe -k -H "Authorization: PVEAPIToken=root@pam!cursor_agent=NEW-TOKEN" "https://192.168.0.202:8006/api2/json/nodes"

# Run full security audit
python scripts/security_audit_scanner.py --all
```

### Expected Results

| Component | Expected Status |
|-----------|-----------------|
| Proxmox API | HTTP 200, returns node list |
| UniFi API | Authenticated, device list returned |
| SSL Certs | Valid (79+ days) |
| API Auth | All protected endpoints reject unauth |

---

## Quick Reference: Token Format

### Proxmox Token
```
PVEAPIToken=USER@REALM!TOKEN_ID=SECRET
Example: PVEAPIToken=root@pam!cursor_agent=a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

### UniFi API (Username/Password)
```python
# Session-based authentication
session = requests.Session()
session.post("https://192.168.0.1/api/auth/login", json={
    "username": "api_scanner",
    "password": "your_password"
}, verify=False)
```

---

## Troubleshooting

### Proxmox 401 Still Occurring
1. Verify token ID matches exactly (case-sensitive)
2. Check if privilege separation is disabled
3. Ensure user has administrator permissions
4. Try creating token with different name

### UniFi Connection Issues
1. Verify Dream Machine IP is correct
2. Check if local access is enabled
3. Try both HTTP and HTTPS
4. Check if UniFi OS has API enabled

---

*Please run this guide and provide the new token, and I'll update all configuration files for you.*
