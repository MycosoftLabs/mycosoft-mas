#!/usr/bin/env python3
"""
MAS VM Provisioning Script

Creates a dedicated VM for the MAS v2 Agent Runtime System.
Uses the Proxmox API to create and configure the VM.
"""

import os
import sys
import json
import urllib3
from typing import Any, Dict, Optional

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import requests
except ImportError:
    print("Please install requests: pip install requests")
    sys.exit(1)


class ProxmoxAPI:
    """Proxmox API client for VM provisioning."""
    
    def __init__(
        self,
        host: str,
        token_id: str,
        token_secret: str,
        verify_ssl: bool = False
    ):
        self.base_url = f"https://{host}:8006/api2/json"
        self.headers = {
            "Authorization": f"PVEAPIToken={token_id}={token_secret}",
            "Content-Type": "application/json",
        }
        self.verify_ssl = verify_ssl
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make API request."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=self.headers, verify=self.verify_ssl)
            elif method == "POST":
                resp = requests.post(url, headers=self.headers, data=data, verify=self.verify_ssl)
            elif method == "PUT":
                resp = requests.put(url, headers=self.headers, data=data, verify=self.verify_ssl)
            elif method == "DELETE":
                resp = requests.delete(url, headers=self.headers, verify=self.verify_ssl)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            resp.raise_for_status()
            return resp.json().get("data", {})
            
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            raise
    
    def get_nodes(self) -> list:
        """Get list of Proxmox nodes."""
        return self._request("GET", "/nodes")
    
    def get_vms(self, node: str) -> list:
        """Get list of VMs on a node."""
        return self._request("GET", f"/nodes/{node}/qemu")
    
    def get_next_vmid(self) -> int:
        """Get next available VMID."""
        return int(self._request("GET", "/cluster/nextid"))
    
    def create_vm(
        self,
        node: str,
        vmid: int,
        name: str,
        memory: int = 65536,  # 64GB
        cores: int = 16,
        storage: str = "local-lvm",
        disk_size: int = 500,  # GB
        iso: Optional[str] = None,
    ) -> str:
        """Create a new VM."""
        data = {
            "vmid": vmid,
            "name": name,
            "memory": memory,
            "cores": cores,
            "sockets": 1,
            "cpu": "host",
            "ostype": "l26",  # Linux 2.6+
            "scsihw": "virtio-scsi-single",
            "scsi0": f"{storage}:{disk_size},discard=on,iothread=1,ssd=1",
            "net0": "virtio,bridge=vmbr0,firewall=1",
            "boot": "order=scsi0;net0",
            "agent": 1,
        }
        
        if iso:
            data["ide2"] = f"local:iso/{iso},media=cdrom"
            data["boot"] = "order=ide2;scsi0;net0"
        
        return self._request("POST", f"/nodes/{node}/qemu", data)
    
    def start_vm(self, node: str, vmid: int) -> str:
        """Start a VM."""
        return self._request("POST", f"/nodes/{node}/qemu/{vmid}/status/start")
    
    def stop_vm(self, node: str, vmid: int) -> str:
        """Stop a VM."""
        return self._request("POST", f"/nodes/{node}/qemu/{vmid}/status/stop")
    
    def create_snapshot(self, node: str, vmid: int, name: str, description: str = "") -> str:
        """Create VM snapshot."""
        return self._request("POST", f"/nodes/{node}/qemu/{vmid}/snapshot", {
            "snapname": name,
            "description": description,
        })
    
    def get_vm_status(self, node: str, vmid: int) -> Dict[str, Any]:
        """Get VM status."""
        return self._request("GET", f"/nodes/{node}/qemu/{vmid}/status/current")


def provision_mas_vm():
    """Provision the MAS VM."""
    
    # Configuration
    config = {
        "host": os.environ.get("PROXMOX_HOST", "192.168.0.100"),
        "token_id": os.environ.get("PROXMOX_TOKEN_ID", "mas@pve!mas-token"),
        "token_secret": os.environ.get("PROXMOX_TOKEN_SECRET", ""),
        "node": os.environ.get("PROXMOX_NODE", "pve1"),
        "vm_name": "mas-vm",
        "vmid": 188,  # Requested VM ID
        "memory": 65536,  # 64 GB
        "cores": 16,
        "disk_size": 500,  # GB
        "storage": "local-lvm",
    }
    
    if not config["token_secret"]:
        print("Error: PROXMOX_TOKEN_SECRET environment variable not set")
        print()
        print("Please set the following environment variables:")
        print("  PROXMOX_HOST - Proxmox server IP/hostname")
        print("  PROXMOX_TOKEN_ID - API token ID (e.g., mas@pve!mas-token)")
        print("  PROXMOX_TOKEN_SECRET - API token secret")
        print("  PROXMOX_NODE - Proxmox node name (e.g., pve1)")
        print()
        print("Example:")
        print("  $env:PROXMOX_TOKEN_SECRET = 'your-token-secret'")
        print("  python scripts/provision_mas_vm.py")
        return False
    
    print("=" * 60)
    print("MAS VM Provisioning Script")
    print("=" * 60)
    print()
    print("Configuration:")
    print(f"  Proxmox Host: {config['host']}")
    print(f"  Node: {config['node']}")
    print(f"  VM Name: {config['vm_name']}")
    print(f"  VMID: {config['vmid']}")
    print(f"  Memory: {config['memory']} MB ({config['memory'] // 1024} GB)")
    print(f"  Cores: {config['cores']}")
    print(f"  Disk: {config['disk_size']} GB")
    print(f"  Storage: {config['storage']}")
    print()
    
    # Confirm
    confirm = input("Proceed with VM creation? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        return False
    
    try:
        # Connect to Proxmox
        print()
        print("Connecting to Proxmox API...")
        api = ProxmoxAPI(
            host=config["host"],
            token_id=config["token_id"],
            token_secret=config["token_secret"],
        )
        
        # Check connection
        nodes = api.get_nodes()
        print(f"Connected. Available nodes: {[n['node'] for n in nodes]}")
        
        # Check if VM already exists
        vms = api.get_vms(config["node"])
        existing = [v for v in vms if v["vmid"] == config["vmid"]]
        
        if existing:
            print(f"VM {config['vmid']} already exists: {existing[0]['name']}")
            status = api.get_vm_status(config["node"], config["vmid"])
            print(f"Status: {status.get('status', 'unknown')}")
            return True
        
        # Create VM
        print()
        print(f"Creating VM {config['vm_name']} (VMID: {config['vmid']})...")
        result = api.create_vm(
            node=config["node"],
            vmid=config["vmid"],
            name=config["vm_name"],
            memory=config["memory"],
            cores=config["cores"],
            storage=config["storage"],
            disk_size=config["disk_size"],
        )
        print(f"VM creation task: {result}")
        
        print()
        print("=" * 60)
        print("VM Created Successfully!")
        print("=" * 60)
        print()
        print("Next Steps:")
        print("1. Attach Ubuntu 22.04 Server ISO to the VM")
        print("2. Start the VM and install Ubuntu")
        print("3. Configure static IP: 192.168.0.188")
        print("4. Follow the MAS_VM_PROVISIONING_GUIDE.md for setup")
        print()
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Main entry point."""
    success = provision_mas_vm()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
