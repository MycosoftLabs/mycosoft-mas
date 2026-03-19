# Secret Rotation Runbook — Mar 14, 2026

**Status:** PR [#79](https://github.com/MycosoftLabs/mycosoft-mas/pull/79) has removed all hardcoded secrets from code.  
**Next:** Follow these steps to rotate the actual credentials and purge git history.

---

## Pre-Rotation: Merge the PR

```bash
# Review and merge PR #79 first
gh pr merge 79 --squash --repo MycosoftLabs/mycosoft-mas
git pull origin main
```

---

## Step 1: Rotate VM SSH Passwords (All 5 VMs)

The old password `Mushroom1!Mushroom1!` is compromised. Rotate on all VMs.

```bash
# Generate a strong new password (run on your dev machine)
openssl rand -base64 24
# Example output: aB3xK9mP2qR7vN5wL8jF4hD6tY1uC0s
# Save this — you'll use it on all VMs

# SSH into each VM and change the password
for VM_IP in 192.168.0.187 192.168.0.188 192.168.0.189 192.168.0.190 192.168.0.191; do
    echo "=== Rotating password on $VM_IP ==="
    ssh mycosoft@$VM_IP "echo 'mycosoft:NEW_PASSWORD_HERE' | sudo chpasswd"
done
```

After rotating, update your local credentials:

```bash
# In your project root, update .credentials.local
cat >> .credentials.local << 'EOF'
VM_PASSWORD=<new-password>
VM_SSH_PASSWORD=<new-password>
EOF
```

Also set on each VM's environment:
```bash
for VM_IP in 192.168.0.187 192.168.0.188 192.168.0.189 192.168.0.190 192.168.0.191; do
    ssh mycosoft@$VM_IP "echo 'export VM_PASSWORD=<new-password>' >> ~/.bashrc"
done
```

---

## Step 2: Rotate Proxmox API Token

The token `ca23b6c8-5746-46c4-8e36-fc6caad5a9e5` and password `20202020` are compromised.

### 2a: Rotate Proxmox Password
```bash
# SSH into the Proxmox host
# Change the root or myca user password
pveum passwd myca@pve
# Enter new password when prompted

# Or via API if you have access:
# https://<proxmox-host>:8006 → Datacenter → Permissions → Users → myca@pve → Change Password
```

### 2b: Revoke Old API Token and Create New One
```bash
# On the Proxmox host, revoke the old token
pveum token remove myca@pve mas

# Create a new token
pveum token add myca@pve mas --privsep 0
# This outputs a new token secret — SAVE IT

# The output will look like:
# ┌──────────────┬──────────────────────────────────────┐
# │ key          │ value                                │
# ├──────────────┼──────────────────────────────────────┤
# │ full-tokenid │ myca@pve!mas                         │
# │ info         │ {"privsep":"0"}                      │
# │ value        │ xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx │
# └──────────────┴──────────────────────────────────────┘
```

Update credentials:
```bash
# In .credentials.local
PROXMOX_PASSWORD=<new-proxmox-password>
PROXMOX_TOKEN_ID=myca@pve!mas
PROXMOX_TOKEN_SECRET=<new-token-value>
```

---

## Step 3: Rotate MINDEX Database Password

The old password `mycosoft_mindex_2026` (and `Diamond1!` as a fallback) are compromised.

```bash
# SSH into the MINDEX VM (192.168.0.189)
ssh mycosoft@192.168.0.189

# Connect to PostgreSQL as superuser
sudo -u postgres psql

# Change the password for the mycosoft database user
ALTER USER mycosoft WITH PASSWORD '<new-strong-password>';
# Or if using a different user:
ALTER USER postgres WITH PASSWORD '<new-strong-password>';

\q
```

Update the connection string in `.env` on the MINDEX VM:
```bash
# On VM 189
echo 'DATABASE_URL=postgresql://mycosoft:<new-password>@localhost:5432/mycosoft' >> ~/.env
echo 'MINDEX_DB_PASSWORD=<new-password>' >> ~/.env
echo 'MINDEX_DATABASE_URL=postgresql://mycosoft:<new-password>@192.168.0.189:5432/mycosoft' >> ~/.env
```

Update `.credentials.local` on your dev machine:
```bash
MINDEX_DB_PASSWORD=<new-password>
DATABASE_URL=postgresql://mycosoft:<new-password>@192.168.0.189:5432/mycosoft
MINDEX_DATABASE_URL=postgresql://mycosoft:<new-password>@192.168.0.189:5432/mycosoft
```

---

## Step 4: Rotate API Keys

### NCBI API Key
1. Go to https://www.ncbi.nlm.nih.gov/account/settings/
2. Under "API Key Management", click "Create an API Key" (or regenerate)
3. Copy the new key
4. Set in env only: `NCBI_API_KEY=<new-key>`

### NGC API Key
1. Go to https://org.ngc.nvidia.com/setup/api-key
2. Generate a new API key (old one is revoked)
3. Set in env only: `NGC_API_KEY=<new-key>`

### NEMOTRON API Key
- Only rotate if you suspect it was ever committed
- If regenerating: https://build.nvidia.com/ → API Keys
- Set in env only: `NEMOTRON_API_KEY=<new-key>`

---

## Step 5: Rotate SSH Keys

### 5a: Generate New SSH Key Pair
```bash
# On your dev machine
ssh-keygen -t ed25519 -C "mycosoft-deploy-$(date +%Y%m%d)" -f ~/.ssh/mycosoft_deploy_ed25519

# Do NOT set an empty passphrase for deploy keys — use a strong passphrase
```

### 5b: Deploy New Public Key to All VMs
```bash
for VM_IP in 192.168.0.187 192.168.0.188 192.168.0.189 192.168.0.190 192.168.0.191; do
    echo "=== Deploying key to $VM_IP ==="
    ssh-copy-id -i ~/.ssh/mycosoft_deploy_ed25519.pub mycosoft@$VM_IP
done
```

### 5c: Remove Old/Unknown Keys from VMs
```bash
for VM_IP in 192.168.0.187 192.168.0.188 192.168.0.189 192.168.0.190 192.168.0.191; do
    echo "=== Reviewing authorized_keys on $VM_IP ==="
    ssh mycosoft@$VM_IP "cat ~/.ssh/authorized_keys"
    # Review output — remove any keys you don't recognize
    # ssh mycosoft@$VM_IP "nano ~/.ssh/authorized_keys"
done
```

### 5d: Update GitHub Deploy Keys
1. Go to https://github.com/MycosoftLabs/mycosoft-mas/settings/keys
2. Delete any old deploy keys
3. Add the new public key: `cat ~/.ssh/mycosoft_deploy_ed25519.pub`

---

## Step 6: Purge Git History

This removes all traces of old secrets from the repository history.

```bash
# Install git-filter-repo if not already installed
pip install git-filter-repo

# Create replacements file
cat > /tmp/replacements.txt << 'EOF'
Mushroom1!Mushroom1!==>***REDACTED***
20202020==>***REDACTED***
ca23b6c8-5746-46c4-8e36-fc6caad5a9e5==>***REDACTED***
mycosoft_mindex_2026==>***REDACTED***
Diamond1!==>***REDACTED***
Mushroom1!==>***REDACTED***
EOF

# Clone a fresh copy for the filter operation
cd /tmp
git clone https://github.com/MycosoftLabs/mycosoft-mas.git mycosoft-mas-clean
cd mycosoft-mas-clean

# Run filter-repo
git filter-repo --replace-text /tmp/replacements.txt --force

# Force-push (this rewrites ALL history — coordinate with team)
git remote add origin https://github.com/MycosoftLabs/mycosoft-mas.git
git push --force --all origin
git push --force --tags origin
```

**Warning:** Force-pushing rewrites history. All team members will need to re-clone the repo after this.

---

## Step 7: Install Pre-Commit Hook

On every developer machine:
```bash
cd /path/to/mycosoft-mas
bash .githooks/install.sh
```

This configures git to use `.githooks/pre-commit` which blocks commits containing known secret patterns.

---

## Step 8: Verify Everything Works

```bash
# Test Proxmox API access with new token
curl -k -s -H "Authorization: PVEAPIToken=myca@pve!mas=<new-token>" \
    https://<proxmox-host>:8006/api2/json/nodes

# Test SSH access to each VM with new password
for VM_IP in 192.168.0.187 192.168.0.188 192.168.0.189 192.168.0.190 192.168.0.191; do
    echo "Testing $VM_IP..."
    ssh -i ~/.ssh/mycosoft_deploy_ed25519 mycosoft@$VM_IP "hostname && echo OK"
done

# Test MINDEX database connection
PGPASSWORD=<new-password> psql -h 192.168.0.189 -U mycosoft -d mycosoft -c "SELECT 1;"

# Test that MAS services can start with new env vars
# (on MAS VM 188)
ssh mycosoft@192.168.0.188
source ~/.env  # or .credentials.local
docker-compose up -d
docker-compose logs --tail=50
```

---

## Post-Rotation Checklist

- [ ] PR #79 merged
- [ ] VM password rotated on all 5 VMs (187, 188, 189, 190, 191)
- [ ] `.credentials.local` updated with new VM password
- [ ] Proxmox password changed
- [ ] Proxmox API token revoked and regenerated
- [ ] `.credentials.local` updated with new Proxmox creds
- [ ] MINDEX DB password changed in PostgreSQL
- [ ] `.env` on VM 189 updated with new DB password
- [ ] `.credentials.local` updated with new DB password
- [ ] NCBI API key regenerated (if was in git history)
- [ ] NGC API key regenerated
- [ ] New SSH key pair generated
- [ ] New public key deployed to all VMs
- [ ] Old/unknown keys removed from all VMs `authorized_keys`
- [ ] Old deploy keys removed from GitHub
- [ ] New deploy key added to GitHub
- [ ] Git history purged with `git filter-repo`
- [ ] Force-pushed clean history
- [ ] Team notified to re-clone
- [ ] Pre-commit hook installed on all dev machines
- [ ] All services verified working with new credentials
- [ ] No secrets in any committed files (verify with `grep -r` after)
