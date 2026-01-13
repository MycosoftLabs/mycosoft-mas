#!/usr/bin/env python3
"""
Create all production VMs for MYCA deployment.
Creates: myca-website, myca-api, myca-database
"""

import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from proxmox.create_myca_core_vm import ProxmoxClient

# VM Definitions
VMS = [
    {
        "vmid": 110,
        "name": "myca-website",
        "node": "dc1",
        "cores": 4,
        "memory": 8192,  # 8GB
        "disk_size": "50G",
        "ip": "192.168.20.11/24",
        "gateway": "192.168.20.1",
        "vlan": 20,
        "description": "Next.js frontend, nginx reverse proxy"
    },
    {
        "vmid": 100,
        "name": "myca-api",
        "node": "build",
        "cores": 8,
        "memory": 32768,  # 32GB
        "disk_size": "100G",
        "ip": "192.168.20.10/24",
        "gateway": "192.168.20.1",
        "vlan": 20,
        "description": "MAS Orchestrator, Agents, n8n, MINDEX, NatureOS"
    },
    {
        "vmid": 120,
        "name": "myca-database",
        "node": "dc2",
        "cores": 4,
        "memory": 16384,  # 16GB
        "disk_size": "200G",
        "ip": "192.168.20.12/24",
        "gateway": "192.168.20.1",
        "vlan": 20,
        "description": "PostgreSQL, Redis, Qdrant - NAS-backed storage"
    }
]

# Proxmox node IPs
NODES = {
    "build": "192.168.0.202",
    "dc1": "192.168.0.2",
    "dc2": "192.168.0.131"
}


def create_vm(client: ProxmoxClient, vm_config: dict, template_id: int = 9000) -> bool:
    """Create a single VM from template."""
    print(f"\n{'='*60}")
    print(f"Creating VM: {vm_config['name']} (ID: {vm_config['vmid']})")
    print(f"{'='*60}")
    print(f"  Node: {vm_config['node']}")
    print(f"  Resources: {vm_config['cores']} CPU, {vm_config['memory']}MB RAM")
    print(f"  Disk: {vm_config['disk_size']}")
    print(f"  Network: {vm_config['ip']} (VLAN {vm_config['vlan']})")
    print(f"  Purpose: {vm_config['description']}")
    
    try:
        # Clone from template
        print(f"\n  Cloning from template {template_id}...")
        result = client.clone_vm(
            node=vm_config['node'],
            vmid=template_id,
            newid=vm_config['vmid'],
            name=vm_config['name'],
            full=True
        )
        print(f"  Clone initiated: {result}")
        
        # Wait for clone to complete
        time.sleep(5)
        
        # Configure VM resources
        print(f"  Configuring resources...")
        client.set_vm_config(
            node=vm_config['node'],
            vmid=vm_config['vmid'],
            cores=vm_config['cores'],
            memory=vm_config['memory'],
            description=vm_config['description']
        )
        
        # Resize disk
        print(f"  Resizing disk to {vm_config['disk_size']}...")
        client.resize_disk(
            node=vm_config['node'],
            vmid=vm_config['vmid'],
            disk="scsi0",
            size=vm_config['disk_size']
        )
        
        # Configure network with VLAN
        print(f"  Configuring network (VLAN {vm_config['vlan']})...")
        client.set_vm_config(
            node=vm_config['node'],
            vmid=vm_config['vmid'],
            net0=f"virtio,bridge=vmbr0,tag={vm_config['vlan']}"
        )
        
        # Set cloud-init IP
        print(f"  Setting IP via cloud-init: {vm_config['ip']}...")
        client.set_vm_config(
            node=vm_config['node'],
            vmid=vm_config['vmid'],
            ipconfig0=f"ip={vm_config['ip']},gw={vm_config['gateway']}"
        )
        
        # Enable auto-start
        print(f"  Enabling auto-start on boot...")
        client.set_vm_config(
            node=vm_config['node'],
            vmid=vm_config['vmid'],
            onboot=1
        )
        
        print(f"\n  [OK] VM {vm_config['name']} created successfully!")
        return True
        
    except Exception as e:
        print(f"\n  [ERROR] Failed to create VM: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Create MYCA production VMs")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created")
    parser.add_argument("--vm", choices=["website", "api", "database", "all"], default="all",
                        help="Which VM to create")
    parser.add_argument("--start", action="store_true", help="Start VMs after creation")
    args = parser.parse_args()
    
    # Get credentials from environment
    token_id = os.environ.get("PROXMOX_TOKEN_ID")
    token_secret = os.environ.get("PROXMOX_TOKEN_SECRET")
    
    if args.dry_run:
        print("\n" + "="*60)
        print("  DRY RUN - VMs to be created:")
        print("="*60)
        
        for vm in VMS:
            if args.vm != "all" and args.vm not in vm['name']:
                continue
            print(f"\n  {vm['name']} (vmid: {vm['vmid']})")
            print(f"    Node: {vm['node']} ({NODES[vm['node']]})")
            print(f"    Resources: {vm['cores']} CPU, {vm['memory']}MB RAM, {vm['disk_size']} disk")
            print(f"    Network: {vm['ip']} on VLAN {vm['vlan']}")
            print(f"    Purpose: {vm['description']}")
        
        print("\n" + "="*60)
        print("  To create these VMs, run without --dry-run")
        print("  Required env vars: PROXMOX_TOKEN_ID, PROXMOX_TOKEN_SECRET")
        print("="*60 + "\n")
        return
    
    if not token_id or not token_secret:
        print("ERROR: Set PROXMOX_TOKEN_ID and PROXMOX_TOKEN_SECRET environment variables")
        sys.exit(1)
    
    # Determine which node to connect to
    primary_node = "build"
    primary_ip = NODES[primary_node]
    
    print(f"Connecting to Proxmox at {primary_ip}...")
    client = ProxmoxClient(
        host=primary_ip,
        token_id=token_id,
        token_secret=token_secret
    )
    
    # Create VMs
    created = []
    failed = []
    
    for vm in VMS:
        if args.vm != "all" and args.vm not in vm['name']:
            continue
        
        if create_vm(client, vm):
            created.append(vm['name'])
            if args.start:
                print(f"  Starting {vm['name']}...")
                client.start_vm(node=vm['node'], vmid=vm['vmid'])
        else:
            failed.append(vm['name'])
    
    # Summary
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    print(f"  Created: {', '.join(created) if created else 'None'}")
    print(f"  Failed: {', '.join(failed) if failed else 'None'}")
    
    if created:
        print("\n  Next steps:")
        print("  1. SSH to each VM and run initial setup")
        print("  2. Mount NAS storage: /mnt/mycosoft")
        print("  3. Install Docker and required packages")
        print("  4. Deploy services")


if __name__ == "__main__":
    main()
