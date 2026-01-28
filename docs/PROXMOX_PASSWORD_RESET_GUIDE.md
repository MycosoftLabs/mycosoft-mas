# Proxmox Password Reset Guide

**Date:** January 28, 2026  
**Server IP:** 192.168.0.90  
**Issue:** SSH/API authentication failing with known passwords

---

## Step 1: Identify the Physical Server

You have 3 Dell servers. Find the one running Proxmox:

1. **Check the UniFi Controller** - Look for MAC `24:6E:96:60:65:CC` 
2. **Or trace the cable** from the switch port connected to 192.168.0.90
3. **Or check each server's front LCD panel** (if available)

---

## Step 2: Connect Monitor and Keyboard

1. Get a **monitor with VGA/HDMI** (Dell servers usually have VGA)
2. Get a **USB keyboard**
3. Plug both into the Proxmox server
4. You should see a login prompt:


```
pve login: _
```

---

## Step 3: Try Existing Passwords First

At the login prompt, try:

```
Login: root
Password: 20202020
```

If that fails, try:

```
Login: root
Password: REDACTED_VM_SSH_PASSWORD
```

If that fails, try:

```
Login: root
Password: (just press Enter - empty password)
```

**If any of these work**, skip to Step 6.

---

## Step 4: Reset Password via GRUB (If All Passwords Fail)

### 4a. Reboot the Server

1. Press `Ctrl + Alt + Delete` on the keyboard
2. Or press the **physical power button** briefly
3. Wait for the server to restart

### 4b. Access GRUB Menu

1. **Watch the screen carefully** during boot
2. When you see the **GRUB boot menu** (list of boot options), press `e` to edit

The GRUB menu looks like:
```
┌──────────────────────────────────────────────────┐
│  Proxmox VE GNU/Linux                            │
│  Advanced options for Proxmox VE GNU/Linux       │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Note:** You may need to press `Shift` or `Esc` during boot if GRUB menu is hidden.

### 4c. Edit the Boot Line

1. Find the line starting with `linux` (it's a long line)
2. Use arrow keys to navigate to the **end** of that line
3. **Add this text** at the end:

```
init=/bin/bash
```

The line should look something like:
```
linux /boot/vmlinuz-... root=/dev/... ro quiet init=/bin/bash
```

### 4d. Boot with Changes

1. Press `Ctrl + X` to boot with these changes
2. Or press `F10`

You'll get a root shell without needing a password.

---

## Step 5: Reset the Root Password

At the bash prompt (`root@(none):/#`), run these commands:

### 5a. Remount Filesystem as Read-Write

```bash
mount -o remount,rw /
```

### 5b. Change the Password

```bash
passwd root
```

Enter your new password twice:
```
New password: 20202020
Retype new password: 20202020
passwd: password updated successfully
```

### 5c. Sync and Reboot

```bash
sync
exec /sbin/init
```

Or force reboot:
```bash
sync
reboot -f
```

---

## Step 6: Verify Access

### 6a. Console Login

After reboot, try logging in at the console:
```
Login: root
Password: 20202020
```

### 6b. Check VMs

Once logged in, run:
```bash
qm list
```

This shows all VMs. Note their IDs.

### 6c. Start VMs

To start the Sandbox VM (check the ID from qm list):
```bash
qm start <VM_ID>
```

To start all VMs:
```bash
qm list | grep stopped | awk '{print $1}' | xargs -I {} qm start {}
```

### 6d. Get VM IPs

```bash
qm guest cmd <VM_ID> network-get-interfaces
```

Or check DHCP leases:
```bash
cat /var/lib/misc/dnsmasq.leases
```

---

## Step 7: Verify Remote Access

From your Windows PC, test SSH:

```powershell
ssh root@192.168.0.90
```

And test Proxmox Web UI:
- Open browser: https://192.168.0.90:8006
- Login: `root` / `20202020` / Realm: `Linux PAM`

---

## Step 8: Update Documentation

Once you have access, run these commands and share the output:

```bash
# Server info
hostname
pveversion

# List all VMs
qm list

# Network info
ip addr

# VM IPs
for vmid in $(qm list | awk 'NR>1 {print $1}'); do
  echo "VM $vmid:"
  qm guest cmd $vmid network-get-interfaces 2>/dev/null || echo "  (no QEMU agent)"
done
```

---

## Quick Reference

| Step | Action |
|------|--------|
| 1 | Find the physical server (MAC: 24:6E:96:60:65:CC) |
| 2 | Connect monitor + keyboard |
| 3 | Try existing passwords |
| 4 | If failed: Reboot → GRUB → add `init=/bin/bash` |
| 5 | Reset password with `passwd root` |
| 6 | Login and run `qm list` to see VMs |
| 7 | Start VMs with `qm start <ID>` |
| 8 | Share VM IPs so we can continue deployment |

---

## After Recovery - Share This Info

Once you regain access, please share:

1. Output of `qm list`
2. IP addresses of Sandbox VM and MAS VM
3. Whether password was actually changed or if it was something else

This will help me update all deployment scripts with the correct information.
