#!/usr/bin/env python3
"""
Create MYCA Core VM on Proxmox

This script creates the main MYCA orchestrator VM on the Proxmox cluster.
Designed to run on the Build node (192.168.0.202).
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from infra.bootstrap.proxmox_client import ProxmoxClient
except ImportError:
    print("ERROR: Could not import ProxmoxClient")
    print("Make sure infra/bootstrap/proxmox_client.py exists")
    sys.exit(1)


# VM Configuration
MYCA_CORE_CONFIG = {
    "vmid": 100,
    "name": "myca-core",
    "description": "MYCA Production Orchestrator - CPU Only",
    "node": "build",  # Primary node
    "cores": 8,
    "memory": 32768,  # 32GB RAM
    "balloon": 16384,  # Minimum 16GB
    "cpu": "host",
    "scsihw": "virtio-scsi-pci",
    "ostype": "l26",  # Linux 6.x
    "agent": 1,  # Enable QEMU guest agent
    "onboot": 1,  # Start on boot
    "boot": "order=scsi0",
    "startup": "order=1",  # Start first
}

DISK_CONFIG = {
    "scsi0": "local-lvm:100",  # 100GB on local storage
    "format": "qcow2",
}

NETWORK_CONFIG = {
    "net0": "virtio,bridge=vmbr0,tag=20",  # VLAN 20 (Production)
}

# Cloud-init configuration for automated setup
CLOUD_INIT_CONFIG = {
    "ciuser": "myca",
    "cipassword": "changeme",  # Should be changed post-install
    "ipconfig0": "ip=dhcp",
    "searchdomain": "mycosoft.local",
    "nameserver": "192.168.0.1",
}


def create_myca_core_vm(
    proxmox_host: str,
    token_id: str,
    token_secret: str,
    dry_run: bool = False
) -> dict:
    """Create the MYCA Core VM"""
    
    print("=" * 50)
    print("  MYCA Core VM Creation")
    print("=" * 50)
    print()
    
    # Prepare full configuration
    vm_config = {
        **MYCA_CORE_CONFIG,
        **DISK_CONFIG,
        **NETWORK_CONFIG,
    }
    
    print("VM Configuration:")
    for key, value in vm_config.items():
        print(f"  {key}: {value}")
    
    if dry_run:
        print()
        print("DRY RUN - VM would be created with above configuration")
        print(f"Target Proxmox Host: {proxmox_host}")
        return {"status": "dry_run", "config": vm_config}
    
    # Connect to Proxmox (only if not dry run)
    print()
    print(f"Connecting to Proxmox at {proxmox_host}...")
    client = ProxmoxClient(
        host=proxmox_host,
        token_id=token_id,
        token_secret=token_secret
    )
    
    # Check if VM already exists
    print(f"Checking if VM {MYCA_CORE_CONFIG['vmid']} exists...")
    vms = client.get_vms(node=MYCA_CORE_CONFIG['node'])
    for vm in vms:
        if vm.get('vmid') == MYCA_CORE_CONFIG['vmid']:
            print(f"WARNING: VM {MYCA_CORE_CONFIG['vmid']} already exists!")
            print(f"  Name: {vm.get('name')}")
            print(f"  Status: {vm.get('status')}")
            return {"status": "exists", "vm": vm}
    
    print()
    print("Creating VM...")
    
    try:
        result = client.create_vm(
            node=MYCA_CORE_CONFIG['node'],
            vmid=MYCA_CORE_CONFIG['vmid'],
            name=MYCA_CORE_CONFIG['name'],
            **{k: v for k, v in vm_config.items() if k not in ['vmid', 'name', 'node']}
        )
        
        print("VM created successfully!")
        print(f"  Task ID: {result}")
        
        return {"status": "created", "result": result}
        
    except Exception as e:
        print(f"ERROR: Failed to create VM: {e}")
        return {"status": "error", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Create MYCA Core VM on Proxmox")
    parser.add_argument(
        "--host",
        default=os.getenv("PROXMOX_HOST_BUILD", "192.168.0.202"),
        help="Proxmox host address"
    )
    parser.add_argument(
        "--token-id",
        default=os.getenv("PROXMOX_TOKEN_ID"),
        help="Proxmox API token ID"
    )
    parser.add_argument(
        "--token-secret",
        default=os.getenv("PROXMOX_TOKEN_SECRET"),
        help="Proxmox API token secret"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without making changes"
    )
    
    args = parser.parse_args()
    
    if not args.token_id or not args.token_secret:
        print("ERROR: Proxmox token credentials required")
        print("Set PROXMOX_TOKEN_ID and PROXMOX_TOKEN_SECRET environment variables")
        print("Or use --token-id and --token-secret arguments")
        sys.exit(1)
    
    result = create_myca_core_vm(
        proxmox_host=args.host,
        token_id=args.token_id,
        token_secret=args.token_secret,
        dry_run=args.dry_run
    )
    
    print()
    print("Result:", json.dumps(result, indent=2, default=str))
    
    if result["status"] == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
