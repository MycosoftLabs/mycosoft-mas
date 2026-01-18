#!/usr/bin/env python3
"""
Proxmox VM Creator for Mycosoft System
Creates Sandbox (103) and Production (104) VMs
"""
import requests
import urllib3
import json
import time
import sys

urllib3.disable_warnings()

# Configuration
TOKEN_ID = "root@pam!cursor_mycocomp"
TOKEN_SECRET = "74cbcb9b-53cd-4750-b77e-7b5fc395201c"

NODES = [
    ("build", "192.168.0.202"),
    ("dc1", "192.168.0.2"),
    ("dc2", "192.168.0.131"),
]

# VM Specifications
VM_SPECS = {
    "sandbox": {
        "vmid": 103,
        "name": "mycosoft-sandbox",
        "cores": 8,
        "memory": 32768,  # 32 GB
        "disk_size": "256G",
        "start_on_boot": False,
    },
    "production": {
        "vmid": 104,
        "name": "mycosoft-prod",
        "cores": 16,
        "memory": 65536,  # 64 GB
        "disk_size": "500G",
        "start_on_boot": True,
    }
}

class ProxmoxAPI:
    def __init__(self, token_id: str, token_secret: str):
        self.token_id = token_id
        self.token_secret = token_secret
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers["Authorization"] = f"PVEAPIToken={token_id}={token_secret}"
        self.working_node = None
        self.working_ip = None
        
    def find_working_node(self) -> bool:
        """Find first accessible Proxmox node"""
        print("=" * 60)
        print("  PROXMOX CONNECTION TEST")
        print("=" * 60)
        print()
        
        for name, ip in NODES:
            try:
                r = self.session.get(f"https://{ip}:8006/api2/json/version", timeout=10)
                if r.status_code == 200:
                    v = r.json().get("data", {}).get("version", "?")
                    print(f"  [OK] {name} ({ip}): online v{v}")
                    if not self.working_node:
                        self.working_node = name
                        self.working_ip = ip
                else:
                    print(f"  [!!] {name} ({ip}): HTTP {r.status_code}")
            except requests.exceptions.Timeout:
                print(f"  [--] {name} ({ip}): timeout")
            except Exception as e:
                print(f"  [!!] {name} ({ip}): {str(e)[:50]}")
        
        print()
        if self.working_node:
            print(f"Using node: {self.working_node} ({self.working_ip})")
            return True
        return False
    
    def api_get(self, endpoint: str):
        """GET request to Proxmox API"""
        url = f"https://{self.working_ip}:8006/api2/json/{endpoint}"
        r = self.session.get(url, timeout=30)
        return r.json().get("data", [])
    
    def api_post(self, endpoint: str, data: dict = None):
        """POST request to Proxmox API"""
        url = f"https://{self.working_ip}:8006/api2/json/{endpoint}"
        r = self.session.post(url, data=data, timeout=60)
        return r.json()
    
    def get_storage(self):
        """Get available storage"""
        print()
        print("STORAGE:")
        storage_list = self.api_get("storage")
        if storage_list is None:
            storage_list = []
        result = {}
        for s in storage_list:
            name = s.get("storage")
            stype = s.get("type")
            content = s.get("content", "")
            print(f"  - {name}: type={stype}, content={content}")
            result[name] = s
        if not result:
            print("  (no storage found - checking node storage)")
            # Try getting storage from node directly
            node_name = getattr(self, 'actual_node_name', None)
            if node_name:
                node_storage = self.api_get(f"nodes/{node_name}/storage")
                if node_storage:
                    for s in node_storage:
                        name = s.get("storage")
                        stype = s.get("type", "unknown")
                        status = s.get("active", 0)
                        total = s.get("total", 0) / 1024 / 1024 / 1024
                        used = s.get("used", 0) / 1024 / 1024 / 1024
                        print(f"  - {name}: type={stype}, active={status}, {used:.1f}GB/{total:.1f}GB")
                        result[name] = s
        return result
    
    def get_nodes(self):
        """Get cluster nodes"""
        print()
        print("CLUSTER NODES:")
        node_list = self.api_get("nodes")
        for n in node_list:
            mem_gb = n.get("mem", 0) / 1024 / 1024 / 1024
            maxmem_gb = n.get("maxmem", 0) / 1024 / 1024 / 1024
            cpu = n.get("cpu", 0) * 100
            print(f"  - {n.get('node')}: status={n.get('status')}, cpu={cpu:.1f}%, mem={mem_gb:.1f}GB/{maxmem_gb:.1f}GB")
        return node_list
    
    def get_vms(self, node_name: str = None):
        """Get existing VMs"""
        print()
        print("EXISTING VMS:")
        if not node_name:
            # Get actual node name from cluster (not the hostname we used to connect)
            nodes = self.api_get("nodes")
            if nodes:
                node_name = nodes[0].get("node", self.working_node)
            else:
                node_name = self.working_node
        
        self.actual_node_name = node_name  # Store for later use
        
        vms = self.api_get(f"nodes/{node_name}/qemu")
        if vms is None:
            vms = []
        for vm in vms:
            status_char = "R" if vm.get("status") == "running" else "S"
            vmid = vm.get("vmid")
            name = vm.get("name", "unnamed")
            print(f"  [{status_char}] {vmid:>4}: {name:<30} ({vm.get('status')})")
        return vms
    
    def check_vm_exists(self, vmid: int, node_name: str = None) -> bool:
        """Check if VM with given ID exists"""
        if not node_name:
            node_name = self.working_node
        vms = self.api_get(f"nodes/{node_name}/qemu")
        for vm in vms:
            if vm.get("vmid") == vmid:
                return True
        return False
    
    def get_available_isos(self, storage: str = "local"):
        """Get available ISO images"""
        print()
        print(f"AVAILABLE ISOs on {storage}:")
        node_name = getattr(self, 'actual_node_name', None) or self.working_node
        content = self.api_get(f"nodes/{node_name}/storage/{storage}/content")
        if content is None:
            content = []
        isos = [c for c in content if c.get("content") == "iso"]
        for iso in isos:
            volid = iso.get("volid", "")
            size_mb = iso.get("size", 0) / 1024 / 1024
            print(f"  - {volid} ({size_mb:.0f} MB)")
        if not isos:
            print("  (no ISOs found)")
        return isos
    
    def create_vm(self, spec: dict, storage: str = "local-lvm", iso_storage: str = "local", 
                  iso_name: str = None, node_name: str = None) -> dict:
        """Create a new VM with given specifications"""
        if not node_name:
            node_name = getattr(self, 'actual_node_name', None) or self.working_node
        
        vmid = spec["vmid"]
        name = spec["name"]
        
        print()
        print("=" * 60)
        print(f"  CREATING VM {vmid}: {name}")
        print("=" * 60)
        
        # Check if VM already exists
        if self.check_vm_exists(vmid, node_name):
            print(f"  [!!] VM {vmid} already exists!")
            return {"error": f"VM {vmid} already exists"}
        
        # Build VM creation parameters
        params = {
            "vmid": vmid,
            "name": name,
            "memory": spec["memory"],
            "cores": spec["cores"],
            "sockets": 1,
            "cpu": "host",
            "ostype": "l26",  # Linux 2.6+ kernel
            "bios": "ovmf",  # UEFI
            "machine": "q35",
            "scsihw": "virtio-scsi-single",
            "agent": 1,  # Enable QEMU agent
            "net0": "virtio,bridge=vmbr0,firewall=1",
            "boot": "order=scsi0;ide2;net0",
        }
        
        # Add EFI disk
        params["efidisk0"] = f"{storage}:1,efitype=4m,pre-enrolled-keys=0"
        
        # Add main disk
        params["scsi0"] = f"{storage}:{spec['disk_size'].replace('G', '')},cache=writeback,discard=on,iothread=1,ssd=1"
        
        # Add ISO if specified
        if iso_name:
            params["ide2"] = f"{iso_storage}:iso/{iso_name},media=cdrom"
        
        # Start on boot
        if spec.get("start_on_boot"):
            params["onboot"] = 1
        
        print(f"  Parameters: {json.dumps(params, indent=2)}")
        
        # Create the VM
        try:
            result = self.api_post(f"nodes/{node_name}/qemu", params)
            print(f"  Result: {result}")
            if "data" in result:
                print(f"  [OK] VM {vmid} creation started!")
                return {"success": True, "task": result.get("data")}
            else:
                print(f"  [!!] Error: {result}")
                return {"error": result}
        except Exception as e:
            print(f"  [!!] Exception: {e}")
            return {"error": str(e)}


def main():
    print()
    print("=" * 60)
    print("  MYCOSOFT PROXMOX VM CREATOR")
    print("  Creates Sandbox (103) and Production (104) VMs")
    print("=" * 60)
    print()
    
    # Initialize API
    api = ProxmoxAPI(TOKEN_ID, TOKEN_SECRET)
    
    # Find working node
    if not api.find_working_node():
        print("ERROR: No Proxmox nodes accessible!")
        sys.exit(1)
    
    # Get storage info
    storage = api.get_storage()
    
    # Get nodes info
    nodes = api.get_nodes()
    
    # Get existing VMs
    vms = api.get_vms()
    
    # Get available ISOs
    isos = api.get_available_isos("local")
    
    # Find Ubuntu ISO
    ubuntu_iso = None
    for iso in isos:
        volid = iso.get("volid", "")
        if "ubuntu" in volid.lower() and "24.04" in volid:
            ubuntu_iso = volid.split("/")[-1]  # Get just the filename
            print(f"\n  Found Ubuntu ISO: {ubuntu_iso}")
            break
    
    if not ubuntu_iso:
        print("\n  [!!] Ubuntu 24.04 ISO not found! Looking for any Ubuntu...")
        for iso in isos:
            volid = iso.get("volid", "")
            if "ubuntu" in volid.lower():
                ubuntu_iso = volid.split("/")[-1]
                print(f"  Found Ubuntu ISO: {ubuntu_iso}")
                break
    
    if not ubuntu_iso:
        print("\n  [!!] No Ubuntu ISO found!")
        print("  Please upload ubuntu-24.04.2-live-server-amd64.iso to local storage")
        ubuntu_iso = "ubuntu-24.04.2-live-server-amd64.iso"  # Will fail but show expected name
    
    print()
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Working Node: {api.working_node}")
    print(f"  Ubuntu ISO: {ubuntu_iso}")
    print(f"  VM Storage: local-lvm (for disk)")
    print()
    
    # Check what action to take
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        
        if action == "create-sandbox":
            api.create_vm(VM_SPECS["sandbox"], iso_name=ubuntu_iso)
        elif action == "create-production":
            api.create_vm(VM_SPECS["production"], iso_name=ubuntu_iso)
        elif action == "create-all":
            api.create_vm(VM_SPECS["sandbox"], iso_name=ubuntu_iso)
            time.sleep(5)
            api.create_vm(VM_SPECS["production"], iso_name=ubuntu_iso)
        else:
            print(f"Unknown action: {action}")
            print("Usage: python proxmox_vm_creator.py [create-sandbox|create-production|create-all]")
    else:
        print("Run with arguments:")
        print("  python proxmox_vm_creator.py create-sandbox     - Create VM 103")
        print("  python proxmox_vm_creator.py create-production  - Create VM 104")
        print("  python proxmox_vm_creator.py create-all         - Create both VMs")


if __name__ == "__main__":
    main()
