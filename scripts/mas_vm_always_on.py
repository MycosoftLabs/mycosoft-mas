#!/usr/bin/env python3
"""
MAS VM Always-On Monitor
Ensures the MAS VM (192.168.0.188) stays online 24/7/365

Features:
- Monitors VM status via Proxmox API
- Auto-restarts if VM goes down
- Creates daily snapshots for backup
- Alerts on failures
- Runs as a background service

Usage:
    python scripts/mas_vm_always_on.py --daemon
    python scripts/mas_vm_always_on.py --check
    python scripts/mas_vm_always_on.py --snapshot
"""

import os
import sys
import time
import json
import logging
import argparse
import requests
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
PROXMOX_HOST = "192.168.0.202"
PROXMOX_PORT = 8006
PROXMOX_NODE = "dc1"  # or dc2
MAS_VM_ID = 188
MAS_VM_IP = "192.168.0.188"
MAS_VM_NAME = "mycosoft-mas"

# Credentials (should be in env vars in production)
PROXMOX_USER = os.getenv("PROXMOX_USER", "root@pam")
PROXMOX_PASSWORD = os.getenv("PROXMOX_PASSWORD", "Mushroom1!")

# Monitoring settings
CHECK_INTERVAL = 60  # seconds
SNAPSHOT_INTERVAL = 86400  # 24 hours
MAX_SNAPSHOTS = 7  # Keep 1 week of daily snapshots

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent.parent / "logs" / "mas_vm_monitor.log")
    ]
)
logger = logging.getLogger(__name__)


class ProxmoxClient:
    """Simple Proxmox API client"""
    
    def __init__(self, host: str, port: int, user: str, password: str):
        self.base_url = f"https://{host}:{port}/api2/json"
        self.user = user
        self.password = password
        self.ticket = None
        self.csrf = None
        
    def authenticate(self) -> bool:
        """Get authentication ticket"""
        try:
            response = requests.post(
                f"{self.base_url}/access/ticket",
                data={"username": self.user, "password": self.password},
                verify=False,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()["data"]
                self.ticket = data["ticket"]
                self.csrf = data["CSRFPreventionToken"]
                return True
            logger.error(f"Auth failed: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return False
    
    def _headers(self) -> dict:
        return {
            "Cookie": f"PVEAuthCookie={self.ticket}",
            "CSRFPreventionToken": self.csrf
        }
    
    def get_vm_status(self, node: str, vmid: int) -> dict | None:
        """Get VM status"""
        try:
            response = requests.get(
                f"{self.base_url}/nodes/{node}/qemu/{vmid}/status/current",
                headers=self._headers(),
                verify=False,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()["data"]
            return None
        except Exception as e:
            logger.error(f"Get VM status error: {e}")
            return None
    
    def start_vm(self, node: str, vmid: int) -> bool:
        """Start a VM"""
        try:
            response = requests.post(
                f"{self.base_url}/nodes/{node}/qemu/{vmid}/status/start",
                headers=self._headers(),
                verify=False,
                timeout=30
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Start VM error: {e}")
            return False
    
    def create_snapshot(self, node: str, vmid: int, name: str, description: str = "") -> bool:
        """Create VM snapshot"""
        try:
            response = requests.post(
                f"{self.base_url}/nodes/{node}/qemu/{vmid}/snapshot",
                headers=self._headers(),
                data={"snapname": name, "description": description},
                verify=False,
                timeout=60
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Snapshot error: {e}")
            return False
    
    def list_snapshots(self, node: str, vmid: int) -> list:
        """List VM snapshots"""
        try:
            response = requests.get(
                f"{self.base_url}/nodes/{node}/qemu/{vmid}/snapshot",
                headers=self._headers(),
                verify=False,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()["data"]
            return []
        except Exception as e:
            logger.error(f"List snapshots error: {e}")
            return []
    
    def delete_snapshot(self, node: str, vmid: int, snapname: str) -> bool:
        """Delete a snapshot"""
        try:
            response = requests.delete(
                f"{self.base_url}/nodes/{node}/qemu/{vmid}/snapshot/{snapname}",
                headers=self._headers(),
                verify=False,
                timeout=60
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Delete snapshot error: {e}")
            return False


def ping_host(host: str, timeout: int = 5) -> bool:
    """Ping a host to check if it's reachable"""
    try:
        # Use subprocess for cross-platform ping
        if sys.platform == "win32":
            cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), host]
        else:
            cmd = ["ping", "-c", "1", "-W", str(timeout), host]
        
        result = subprocess.run(cmd, capture_output=True, timeout=timeout + 5)
        return result.returncode == 0
    except Exception:
        return False


def check_ssh(host: str, port: int = 22, timeout: int = 5) -> bool:
    """Check if SSH port is open"""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def check_services(host: str) -> dict:
    """Check if key services are running on MAS VM"""
    services = {
        "ssh": check_ssh(host, 22),
        "orchestrator": False,
        "redis": False,
    }
    
    # Check orchestrator API
    try:
        response = requests.get(f"http://{host}:8001/health", timeout=5)
        services["orchestrator"] = response.status_code == 200
    except Exception:
        pass
    
    # Check Redis
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, 6379))
        sock.close()
        services["redis"] = result == 0
    except Exception:
        pass
    
    return services


class MASVMMonitor:
    """Main monitor class"""
    
    def __init__(self):
        self.proxmox = ProxmoxClient(PROXMOX_HOST, PROXMOX_PORT, PROXMOX_USER, PROXMOX_PASSWORD)
        self.last_snapshot = None
        self.consecutive_failures = 0
        
    def check_and_start(self) -> bool:
        """Check VM status and start if needed"""
        # First try simple ping
        if ping_host(MAS_VM_IP):
            services = check_services(MAS_VM_IP)
            if all(services.values()):
                logger.info(f"MAS VM is healthy - all services running")
                self.consecutive_failures = 0
                return True
            else:
                failed = [k for k, v in services.items() if not v]
                logger.warning(f"MAS VM reachable but services down: {failed}")
        
        # VM might be down, check via Proxmox
        logger.info("Checking VM status via Proxmox...")
        
        if not self.proxmox.authenticate():
            logger.error("Failed to authenticate with Proxmox")
            return False
        
        status = self.proxmox.get_vm_status(PROXMOX_NODE, MAS_VM_ID)
        if not status:
            # Try other node
            status = self.proxmox.get_vm_status("dc2", MAS_VM_ID)
        
        if not status:
            logger.error("Could not get VM status from any node")
            return False
        
        vm_status = status.get("status", "unknown")
        logger.info(f"VM status: {vm_status}")
        
        if vm_status != "running":
            logger.warning(f"VM is not running (status: {vm_status}), starting...")
            
            # Try to start on primary node first
            if self.proxmox.start_vm(PROXMOX_NODE, MAS_VM_ID):
                logger.info("VM start command sent successfully")
                # Wait for VM to boot
                time.sleep(60)
                
                if ping_host(MAS_VM_IP):
                    logger.info("VM is now reachable!")
                    return True
                else:
                    logger.warning("VM started but not yet reachable")
                    return False
            else:
                logger.error("Failed to start VM")
                return False
        
        return True
    
    def create_daily_snapshot(self) -> bool:
        """Create a daily snapshot of the VM"""
        now = datetime.now()
        snapshot_name = f"daily-{now.strftime('%Y%m%d')}"
        description = f"Auto snapshot {now.strftime('%Y-%m-%d %H:%M')}"
        
        if not self.proxmox.authenticate():
            return False
        
        # Check if snapshot already exists today
        snapshots = self.proxmox.list_snapshots(PROXMOX_NODE, MAS_VM_ID)
        existing_names = [s.get("name", "") for s in snapshots]
        
        if snapshot_name in existing_names:
            logger.info(f"Snapshot {snapshot_name} already exists")
            return True
        
        logger.info(f"Creating snapshot: {snapshot_name}")
        if self.proxmox.create_snapshot(PROXMOX_NODE, MAS_VM_ID, snapshot_name, description):
            logger.info("Snapshot created successfully")
            
            # Cleanup old snapshots
            self.cleanup_old_snapshots()
            return True
        else:
            logger.error("Failed to create snapshot")
            return False
    
    def cleanup_old_snapshots(self):
        """Remove snapshots older than MAX_SNAPSHOTS days"""
        snapshots = self.proxmox.list_snapshots(PROXMOX_NODE, MAS_VM_ID)
        
        # Filter auto snapshots
        auto_snapshots = [s for s in snapshots if s.get("name", "").startswith("daily-")]
        
        if len(auto_snapshots) > MAX_SNAPSHOTS:
            # Sort by name (date) and delete oldest
            auto_snapshots.sort(key=lambda x: x.get("name", ""))
            to_delete = auto_snapshots[:-MAX_SNAPSHOTS]
            
            for snap in to_delete:
                name = snap.get("name")
                logger.info(f"Deleting old snapshot: {name}")
                self.proxmox.delete_snapshot(PROXMOX_NODE, MAS_VM_ID, name)
    
    def run_daemon(self):
        """Run as a daemon, checking status periodically"""
        logger.info("Starting MAS VM Monitor daemon")
        logger.info(f"Monitoring VM {MAS_VM_ID} ({MAS_VM_IP})")
        logger.info(f"Check interval: {CHECK_INTERVAL}s, Snapshot interval: {SNAPSHOT_INTERVAL}s")
        
        last_snapshot_check = time.time()
        
        while True:
            try:
                # Check VM status
                if not self.check_and_start():
                    self.consecutive_failures += 1
                    if self.consecutive_failures >= 3:
                        logger.critical(f"VM has been down for {self.consecutive_failures} checks!")
                        # Could send alert here (email, Slack, etc.)
                
                # Check if it's time for a snapshot
                if time.time() - last_snapshot_check >= SNAPSHOT_INTERVAL:
                    self.create_daily_snapshot()
                    last_snapshot_check = time.time()
                
            except Exception as e:
                logger.error(f"Monitor error: {e}")
            
            time.sleep(CHECK_INTERVAL)


def main():
    parser = argparse.ArgumentParser(description="MAS VM Always-On Monitor")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--check", action="store_true", help="Check VM status once")
    parser.add_argument("--snapshot", action="store_true", help="Create snapshot now")
    parser.add_argument("--start", action="store_true", help="Start VM if not running")
    args = parser.parse_args()
    
    # Suppress SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    monitor = MASVMMonitor()
    
    if args.daemon:
        monitor.run_daemon()
    elif args.check:
        if ping_host(MAS_VM_IP):
            services = check_services(MAS_VM_IP)
            print(f"VM Reachable: Yes")
            print(f"Services: {json.dumps(services, indent=2)}")
        else:
            print(f"VM Reachable: No")
    elif args.snapshot:
        if monitor.create_daily_snapshot():
            print("Snapshot created successfully")
        else:
            print("Snapshot failed")
    elif args.start:
        if monitor.check_and_start():
            print("VM is running")
        else:
            print("Failed to start VM")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
