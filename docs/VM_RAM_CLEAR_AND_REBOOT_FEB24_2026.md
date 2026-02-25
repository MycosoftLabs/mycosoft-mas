# VM RAM Clear and Reboot (Feb 24, 2026)

When website Docker builds fail with OOM during `pnpm install`, clear RAM cache and optionally reboot VMs.

## Automated Script

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python scripts/vm_clear_ram_and_reboot.py
```

Does: Sandbox 187 and MAS 188 cache clear, then MAS 188 reboot. Requires `.credentials.local` with `VM_SSH_PASSWORD`.

## Manual Commands (when SSH works)

### Clear RAM cache (on each VM)

```bash
# SSH first, then:
free -m
echo $VM_PASSWORD | sudo -S sh -c 'sync && echo 3 > /proc/sys/vm/drop_caches'
free -m
```

### Reboot MAS VM only

```bash
ssh mycosoft@192.168.0.188
echo $VM_PASSWORD | sudo -S reboot
```

### If VMs are unresponsive

1. **Proxmox/VM host:** Reboot VMs from the hypervisor UI.
2. **Sandbox (187):** Kill any stuck `docker build` first:
   ```bash
   pkill -9 -f 'docker build.*mycosoft-always-on-mycosoft-website'
   ```
3. **Increase VM RAM:** If builds keep OOMing, raise Sandbox VM RAM in Proxmox.
4. **Build locally:** Build the Docker image on the dev machine, push to registry, pull on VM.

## VM IPs

| VM      | IP           | Role              |
|---------|--------------|-------------------|
| Sandbox | 192.168.0.187| Website build/host|
| MAS     | 192.168.0.188| Orchestrator      |
| MINDEX  | 192.168.0.189| Database API      |
