#!/usr/bin/env python3
"""
Check GPU availability on MAS VM for PersonaPlex
Date: January 27, 2026
"""
import requests
import urllib3
import time
import base64
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN = "root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
NODE = "pve"
headers = {"Authorization": f"PVEAPIToken={PROXMOX_TOKEN}"}

VMS = {
    101: "MAS VM",
    103: "Sandbox VM",
}

def exec_cmd(vm_id, cmd, timeout=60):
    """Execute command via QEMU Guest Agent"""
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{vm_id}/agent/exec"
    try:
        data = {"command": "/bin/bash", "input-data": cmd}
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
        if not r.ok:
            return None, f"Exec failed: {r.status_code}"
        
        pid = r.json().get("data", {}).get("pid")
        if not pid:
            return None, "No PID"
        
        status_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{vm_id}/agent/exec-status"
        start = time.time()
        
        while time.time() - start < timeout:
            time.sleep(2)
            s = requests.get(status_url, headers=headers, params={"pid": pid}, verify=False, timeout=5)
            if s.ok:
                data = s.json().get("data", {})
                if data.get("exited"):
                    out_b64 = data.get("out-data", "")
                    err_b64 = data.get("err-data", "")
                    try:
                        out = base64.b64decode(out_b64).decode() if out_b64 else ""
                    except:
                        out = out_b64
                    try:
                        err = base64.b64decode(err_b64).decode() if err_b64 else ""
                    except:
                        err = err_b64
                    return data.get("exitcode", 0) == 0, out or err
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

def check_gpu(vm_id, vm_name):
    """Check GPU availability on a VM"""
    print(f"\n{'='*60}")
    print(f"Checking GPU on VM {vm_id} ({vm_name})")
    print('='*60)
    
    # Check nvidia-smi
    print("\n[nvidia-smi]")
    success, output = exec_cmd(vm_id, "nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 || echo 'No NVIDIA GPU detected'")
    if output:
        for line in output.strip().split('\n')[:5]:
            print(f"  {line}")
    
    # Check lspci for GPUs
    print("\n[lspci | grep -i nvidia]")
    success, output = exec_cmd(vm_id, "lspci | grep -i nvidia 2>&1 || echo 'No NVIDIA devices in lspci'")
    if output:
        for line in output.strip().split('\n')[:5]:
            print(f"  {line}")
    
    # Check Docker GPU support
    print("\n[Docker GPU support]")
    success, output = exec_cmd(vm_id, "docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi 2>&1 | head -10 || echo 'Docker GPU not available'")
    if output:
        for line in output.strip().split('\n')[:5]:
            print(f"  {line}")
    
    # Check system RAM
    print("\n[System Memory]")
    success, output = exec_cmd(vm_id, "free -h | head -2")
    if output:
        for line in output.strip().split('\n'):
            print(f"  {line}")
    
    return success

def check_proxmox_gpu():
    """Check GPU availability on Proxmox host"""
    print(f"\n{'='*60}")
    print("Checking GPU passthrough configuration on Proxmox")
    print('='*60)
    
    # Get node hardware info
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/hardware/pci"
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=10)
        if r.ok:
            pci_devices = r.json().get("data", [])
            gpu_devices = [d for d in pci_devices if "nvidia" in d.get("device_name", "").lower() or "vga" in d.get("class", "").lower()]
            print(f"\nGPU/VGA devices found: {len(gpu_devices)}")
            for dev in gpu_devices[:5]:
                print(f"  - {dev.get('id')}: {dev.get('device_name', 'Unknown')} (class: {dev.get('class', 'N/A')})")
    except Exception as e:
        print(f"  Error: {e}")

def main():
    print("="*60)
    print("GPU AVAILABILITY CHECK FOR PERSONAPLEX")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print("\nPersonaPlex Requirements:")
    print("  - NVIDIA GPU with 16GB+ VRAM (A100/H100 recommended)")
    print("  - CUDA support in Docker")
    print("  - 32GB+ System RAM")
    
    # Check Proxmox host
    check_proxmox_gpu()
    
    # Check each VM
    for vm_id, vm_name in VMS.items():
        check_gpu(vm_id, vm_name)
    
    print("\n" + "="*60)
    print("RECOMMENDATION")
    print("="*60)
    print("""
Based on the checks above, determine hosting strategy:

1. If MAS VM (101) has GPU passthrough configured:
   - Deploy PersonaPlex directly on MAS VM
   - Use docker-compose.voice.yml with GPU reservation

2. If no GPU available on VMs:
   - Option A: Configure GPU passthrough in Proxmox for VM 101
   - Option B: Use cloud GPU (RunPod, Lambda Labs, Vast.ai)
   - Option C: Use CPU offload mode (slower, ~1-2s latency)

3. For immediate testing without GPU:
   - PersonaPlex supports --cpu-offload flag
   - Latency will be 5-10x slower but functional
""")

if __name__ == "__main__":
    main()
