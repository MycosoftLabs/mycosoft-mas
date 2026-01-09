#!/usr/bin/env python3
"""
Create Agent VM Template on Proxmox

This script creates a clonable template for agent VMs.
The template uses cloud-init for automated configuration.
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


# Template Configuration
AGENT_TEMPLATE_CONFIG = {
    "vmid": 9000,
    "name": "myca-agent-template",
    "description": "MYCA Agent VM Template with cloud-init",
    "node": "build",
    "cores": 4,
    "memory": 8192,  # 8GB RAM
    "balloon": 4096,  # Minimum 4GB
    "cpu": "host",
    "scsihw": "virtio-scsi-pci",
    "ostype": "l26",
    "agent": 1,
    "template": 0,  # Will convert to template after creation
}

DISK_CONFIG = {
    "scsi0": "local-lvm:50",  # 50GB
    "format": "qcow2",
}

NETWORK_CONFIG = {
    "net0": "virtio,bridge=vmbr0,tag=30",  # VLAN 30 (Agents)
}

# Cloud-init for automated agent configuration
CLOUD_INIT_CONFIG = {
    "ciuser": "myca-agent",
    "ipconfig0": "ip=dhcp",
    "searchdomain": "mycosoft.local",
    "nameserver": "192.168.0.1",
}

# User data for cloud-init (installs Docker and agent dependencies)
CLOUD_INIT_USER_DATA = """#cloud-config
package_update: true
package_upgrade: true

packages:
  - docker.io
  - docker-compose
  - python3
  - python3-pip
  - curl
  - git
  - nfs-common

runcmd:
  # Enable Docker
  - systemctl enable docker
  - systemctl start docker
  
  # Add user to docker group
  - usermod -aG docker myca-agent
  
  # Create mount point for NAS
  - mkdir -p /mnt/mycosoft
  
  # Add NFS mount (will be configured at clone time)
  - echo "192.168.0.1:/mycosoft /mnt/mycosoft nfs defaults,_netdev,nofail 0 0" >> /etc/fstab
  
  # Create agent work directory
  - mkdir -p /opt/myca-agent
  - chown myca-agent:myca-agent /opt/myca-agent
  
  # Signal ready
  - touch /var/lib/cloud/instance/agent-ready

final_message: "MYCA Agent VM ready after $UPTIME seconds"
"""


def create_agent_template(
    proxmox_host: str,
    token_id: str,
    token_secret: str,
    dry_run: bool = False
) -> dict:
    """Create the agent VM template"""
    
    print("=" * 50)
    print("  MYCA Agent Template Creation")
    print("=" * 50)
    print()
    
    # Prepare configuration
    template_config = {
        **AGENT_TEMPLATE_CONFIG,
        **DISK_CONFIG,
        **NETWORK_CONFIG,
    }
    
    print("Template Configuration:")
    for key, value in template_config.items():
        print(f"  {key}: {value}")
    
    if dry_run:
        print()
        print("DRY RUN - Template would be created with above configuration")
        print(f"Target Proxmox Host: {proxmox_host}")
        print()
        print("Cloud-init user data would be:")
        print("-" * 40)
        print(CLOUD_INIT_USER_DATA[:500] + "...")
        return {"status": "dry_run", "config": template_config}
    
    # Connect to Proxmox (only if not dry run)
    print()
    print(f"Connecting to Proxmox at {proxmox_host}...")
    client = ProxmoxClient(
        host=proxmox_host,
        token_id=token_id,
        token_secret=token_secret
    )
    
    # Check if template already exists
    print(f"Checking if template {AGENT_TEMPLATE_CONFIG['vmid']} exists...")
    vms = client.get_vms(node=AGENT_TEMPLATE_CONFIG['node'])
    for vm in vms:
        if vm.get('vmid') == AGENT_TEMPLATE_CONFIG['vmid']:
            print(f"WARNING: VM/Template {AGENT_TEMPLATE_CONFIG['vmid']} already exists!")
            print(f"  Name: {vm.get('name')}")
            print(f"  Template: {vm.get('template', 0)}")
            return {"status": "exists", "vm": vm}
    
    print()
    print("Creating VM...")
    
    try:
        # Create base VM
        result = client.create_vm(
            node=AGENT_TEMPLATE_CONFIG['node'],
            vmid=AGENT_TEMPLATE_CONFIG['vmid'],
            name=AGENT_TEMPLATE_CONFIG['name'],
            **{k: v for k, v in template_config.items() if k not in ['vmid', 'name', 'node']}
        )
        
        print(f"Base VM created: {result}")
        
        # Note: Converting to template and adding cloud-init drive
        # requires additional API calls or manual steps
        print()
        print("NEXT STEPS (manual):")
        print("1. Install Ubuntu 24.04 on the VM")
        print("2. Configure cloud-init")
        print("3. Convert to template: qm template 9000")
        
        return {"status": "created", "result": result}
        
    except Exception as e:
        print(f"ERROR: Failed to create template: {e}")
        return {"status": "error", "error": str(e)}


def clone_agent_vm(
    proxmox_host: str,
    token_id: str,
    token_secret: str,
    new_vmid: int,
    new_name: str,
    target_node: str = None,
    dry_run: bool = False
) -> dict:
    """Clone an agent VM from the template"""
    
    print("=" * 50)
    print(f"  Cloning Agent VM: {new_name}")
    print("=" * 50)
    print()
    
    # Connect to Proxmox
    client = ProxmoxClient(
        host=proxmox_host,
        token_id=token_id,
        token_secret=token_secret
    )
    
    target = target_node or AGENT_TEMPLATE_CONFIG['node']
    
    print(f"Cloning template {AGENT_TEMPLATE_CONFIG['vmid']} to VM {new_vmid}")
    print(f"  Name: {new_name}")
    print(f"  Target Node: {target}")
    
    if dry_run:
        print()
        print("DRY RUN - Would clone with above configuration")
        return {"status": "dry_run"}
    
    try:
        result = client.clone_vm(
            node=AGENT_TEMPLATE_CONFIG['node'],
            vmid=AGENT_TEMPLATE_CONFIG['vmid'],
            newid=new_vmid,
            name=new_name,
            target=target,
            full=1  # Full clone, not linked
        )
        
        print(f"Clone initiated: {result}")
        return {"status": "cloning", "result": result}
        
    except Exception as e:
        print(f"ERROR: Failed to clone: {e}")
        return {"status": "error", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Manage MYCA Agent Templates on Proxmox")
    parser.add_argument(
        "action",
        choices=["create", "clone"],
        help="Action to perform"
    )
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
        help="Show what would be done without making changes"
    )
    # Clone-specific arguments
    parser.add_argument(
        "--new-vmid",
        type=int,
        help="New VM ID for clone"
    )
    parser.add_argument(
        "--new-name",
        help="New VM name for clone"
    )
    parser.add_argument(
        "--target-node",
        help="Target node for clone"
    )
    
    args = parser.parse_args()
    
    if not args.token_id or not args.token_secret:
        print("ERROR: Proxmox token credentials required")
        print("Set PROXMOX_TOKEN_ID and PROXMOX_TOKEN_SECRET environment variables")
        sys.exit(1)
    
    if args.action == "create":
        result = create_agent_template(
            proxmox_host=args.host,
            token_id=args.token_id,
            token_secret=args.token_secret,
            dry_run=args.dry_run
        )
    elif args.action == "clone":
        if not args.new_vmid or not args.new_name:
            print("ERROR: --new-vmid and --new-name required for clone")
            sys.exit(1)
        result = clone_agent_vm(
            proxmox_host=args.host,
            token_id=args.token_id,
            token_secret=args.token_secret,
            new_vmid=args.new_vmid,
            new_name=args.new_name,
            target_node=args.target_node,
            dry_run=args.dry_run
        )
    
    print()
    print("Result:", json.dumps(result, indent=2, default=str))
    
    if result.get("status") == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
