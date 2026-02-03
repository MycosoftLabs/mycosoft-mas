"""
Infrastructure Operations Service for MYCA
Provides operational loops for Proxmox, UniFi, NAS, GPU, and UART
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Import existing clients - make them optional for now
try:
    import sys
    import importlib.util
    
    # Try to import Proxmox client
    proxmox_path = Path(__file__).parent.parent.parent / "infra" / "bootstrap" / "proxmox_client.py"
    if proxmox_path.exists():
        spec = importlib.util.spec_from_file_location("proxmox_client", proxmox_path)
        proxmox_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(proxmox_module)
        ProxmoxClient = proxmox_module.ProxmoxClient
    else:
        ProxmoxClient = None
    
    # Try to import UniFi client
    unifi_path = Path(__file__).parent.parent.parent / "infra" / "bootstrap" / "unifi_client.py"
    if unifi_path.exists():
        spec = importlib.util.spec_from_file_location("unifi_client", unifi_path)
        unifi_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(unifi_module)
        UniFiClient = unifi_module.UniFiClient
    else:
        UniFiClient = None
except Exception as e:
    logger.warning(f"Could not import infrastructure clients: {e}")
    ProxmoxClient = None
    UniFiClient = None


class InfrastructureOpsService:
    """Service for infrastructure operations"""
    
    def __init__(
        self,
        vault_addr: str = "http://127.0.0.1:8200",
        nas_logs_path: str = "/mnt/mycosoft-nas/logs",
        audit_log_file: str = "audit.jsonl"
    ):
        self.vault_addr = vault_addr
        
        # Use fallback path if NAS not available
        if not os.path.exists("/mnt/mycosoft-nas"):
            # Fall back to local logs directory
            nas_logs_path = os.environ.get("MAS_LOGS_PATH", "/tmp/mas-logs")
            logger.warning(f"NAS not mounted, using fallback logs path: {nas_logs_path}")
        
        self.nas_logs_path = nas_logs_path
        self.audit_log_path = os.path.join(nas_logs_path, audit_log_file)
        
        # Ensure logs directory exists (gracefully handle permission errors)
        try:
            os.makedirs(nas_logs_path, exist_ok=True)
        except PermissionError:
            logger.warning(f"Cannot create logs directory {nas_logs_path}, using /tmp/mas-logs")
            self.nas_logs_path = "/tmp/mas-logs"
            self.audit_log_path = os.path.join(self.nas_logs_path, audit_log_file)
            os.makedirs(self.nas_logs_path, exist_ok=True)
    
    def _audit_log(self, action: str, status: str, details: Dict[str, Any]):
        """Write audit log entry"""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "actor": "myca-orchestrator",
            "status": status,
            "details": details
        }
        
        try:
            with open(self.audit_log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    # =========================================================================
    # Proxmox Operations
    # =========================================================================
    
    async def proxmox_inventory(self) -> Dict[str, Any]:
        """Get Proxmox inventory across all nodes"""
        try:
            # Get credentials from Vault
            client = ProxmoxClient.from_vault(
                host="192.168.0.202",
                vault_addr=self.vault_addr
            )
            
            # Get nodes
            nodes = client.get_nodes()
            
            # Get VMs
            vms = client.get_vms()
            
            # Get containers
            containers = client.get_containers()
            
            # Get storage
            storage = client.get_storage()
            
            result = {
                "nodes": nodes,
                "vms": vms,
                "containers": containers,
                "storage": storage,
                "summary": {
                    "total_nodes": len(nodes),
                    "total_vms": len(vms),
                    "total_containers": len(containers),
                    "total_storage": len(storage)
                }
            }
            
            self._audit_log("proxmox.inventory", "success", {
                "nodes": len(nodes),
                "vms": len(vms),
                "containers": len(containers)
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Proxmox inventory failed: {e}")
            self._audit_log("proxmox.inventory", "failure", {"error": str(e)})
            raise
    
    async def proxmox_snapshot(
        self,
        node: str,
        vmid: int,
        snapshot_name: str,
        confirm: bool = False
    ) -> Dict[str, Any]:
        """Create VM snapshot with confirmation gate"""
        if not confirm:
            return {
                "status": "dry-run",
                "message": "Would create snapshot (set confirm=true to execute)",
                "node": node,
                "vmid": vmid,
                "snapshot_name": snapshot_name
            }
        
        try:
            client = ProxmoxClient.from_vault(
                host="192.168.0.202",
                vault_addr=self.vault_addr
            )
            
            # Create snapshot
            result = client._request(
                "POST",
                f"nodes/{node}/qemu/{vmid}/snapshot",
                data={"snapname": snapshot_name}
            )
            
            self._audit_log("proxmox.snapshot", "success", {
                "node": node,
                "vmid": vmid,
                "snapshot_name": snapshot_name
            })
            
            return {
                "status": "success",
                "node": node,
                "vmid": vmid,
                "snapshot_name": snapshot_name,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Proxmox snapshot failed: {e}")
            self._audit_log("proxmox.snapshot", "failure", {
                "node": node,
                "vmid": vmid,
                "error": str(e)
            })
            raise
    
    async def proxmox_rollback(
        self,
        node: str,
        vmid: int,
        snapshot_name: str,
        confirm: bool = False
    ) -> Dict[str, Any]:
        """Rollback VM to snapshot with confirmation gate"""
        if not confirm:
            return {
                "status": "dry-run",
                "message": "Would rollback to snapshot (set confirm=true to execute)",
                "node": node,
                "vmid": vmid,
                "snapshot_name": snapshot_name,
                "warning": "This operation will revert VM state!"
            }
        
        try:
            client = ProxmoxClient.from_vault(
                host="192.168.0.202",
                vault_addr=self.vault_addr
            )
            
            # Rollback
            result = client._request(
                "POST",
                f"nodes/{node}/qemu/{vmid}/snapshot/{snapshot_name}/rollback"
            )
            
            self._audit_log("proxmox.rollback", "success", {
                "node": node,
                "vmid": vmid,
                "snapshot_name": snapshot_name
            })
            
            return {
                "status": "success",
                "node": node,
                "vmid": vmid,
                "snapshot_name": snapshot_name,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Proxmox rollback failed: {e}")
            self._audit_log("proxmox.rollback", "failure", {
                "node": node,
                "vmid": vmid,
                "error": str(e)
            })
            raise
    
    # =========================================================================
    # UniFi Operations
    # =========================================================================
    
    async def unifi_topology(self) -> Dict[str, Any]:
        """Get UniFi network topology"""
        try:
            client = UniFiClient.from_vault(
                host="192.168.0.1",
                vault_addr=self.vault_addr
            )
            
            # Get sites
            sites = client.get_sites()
            
            # Get devices
            devices = client.get_devices()
            
            # Get clients
            clients = client.get_clients()
            
            # Get networks
            networks = client.get_networks()
            
            # Get WLANs
            wlans = client.get_wlans()
            
            # Get health
            health = client.get_health()
            
            result = {
                "sites": sites,
                "devices": devices,
                "clients": clients,
                "networks": networks,
                "wlans": wlans,
                "health": health,
                "summary": {
                    "total_devices": len(devices),
                    "total_clients": len(clients),
                    "total_networks": len(networks),
                    "total_wlans": len(wlans)
                }
            }
            
            self._audit_log("unifi.topology", "success", {
                "devices": len(devices),
                "clients": len(clients)
            })
            
            return result
            
        except Exception as e:
            logger.error(f"UniFi topology failed: {e}")
            self._audit_log("unifi.topology", "failure", {"error": str(e)})
            raise
    
    async def unifi_client_info(self, mac: str) -> Dict[str, Any]:
        """Get detailed client information"""
        try:
            client = UniFiClient.from_vault(
                host="192.168.0.1",
                vault_addr=self.vault_addr
            )
            
            # Get all clients
            clients = client.get_clients()
            
            # Find specific client
            target = next((c for c in clients if c.get("mac") == mac), None)
            
            if not target:
                raise ValueError(f"Client {mac} not found")
            
            self._audit_log("unifi.client_info", "success", {"mac": mac})
            
            return target
            
        except Exception as e:
            logger.error(f"UniFi client info failed: {e}")
            self._audit_log("unifi.client_info", "failure", {
                "mac": mac,
                "error": str(e)
            })
            raise
    
    # =========================================================================
    # GPU Operations
    # =========================================================================
    
    async def gpu_run_test(self) -> Dict[str, Any]:
        """Run GPU validation test"""
        import subprocess
        
        try:
            # Run nvidia-smi
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"nvidia-smi failed: {result.stderr}")
            
            gpus = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) == 4:
                        gpus.append({
                            "name": parts[0],
                            "memory_total_mb": int(parts[1]),
                            "memory_free_mb": int(parts[2]),
                            "utilization_percent": int(parts[3])
                        })
            
            self._audit_log("gpu.test", "success", {"gpus": len(gpus)})
            
            return {
                "status": "success",
                "gpus": gpus,
                "test_passed": True
            }
            
        except Exception as e:
            logger.error(f"GPU test failed: {e}")
            self._audit_log("gpu.test", "failure", {"error": str(e)})
            raise
    
    # =========================================================================
    # UART Operations
    # =========================================================================
    
    async def uart_tail(self, lines: int = 100) -> Dict[str, Any]:
        """Get recent UART log entries"""
        uart_log_path = os.path.join(self.nas_logs_path, "uart_ingest.jsonl")
        
        try:
            if not os.path.exists(uart_log_path):
                return {
                    "status": "no_data",
                    "message": "No UART logs found",
                    "lines": []
                }
            
            # Read last N lines
            import subprocess
            result = subprocess.run(
                ["tail", "-n", str(lines), uart_log_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            log_lines = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    try:
                        log_lines.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            
            self._audit_log("uart.tail", "success", {"lines": len(log_lines)})
            
            return {
                "status": "success",
                "lines": log_lines,
                "total": len(log_lines)
            }
            
        except Exception as e:
            logger.error(f"UART tail failed: {e}")
            self._audit_log("uart.tail", "failure", {"error": str(e)})
            raise
    
    # =========================================================================
    # NAS Operations
    # =========================================================================
    
    async def nas_status(self) -> Dict[str, Any]:
        """Check NAS mount status and usage"""
        import subprocess
        import shutil
        
        try:
            # Check if mounted
            result = subprocess.run(
                ["mountpoint", "-q", "/mnt/mycosoft-nas"],
                capture_output=True,
                timeout=5
            )
            
            mounted = result.returncode == 0
            
            if not mounted:
                return {
                    "status": "not_mounted",
                    "message": "NAS is not mounted",
                    "path": "/mnt/mycosoft-nas"
                }
            
            # Get disk usage
            usage = shutil.disk_usage("/mnt/mycosoft-nas")
            
            self._audit_log("nas.status", "success", {
                "mounted": True,
                "total_gb": usage.total // (1024**3),
                "used_gb": usage.used // (1024**3),
                "free_gb": usage.free // (1024**3)
            })
            
            return {
                "status": "mounted",
                "path": "/mnt/mycosoft-nas",
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "total_gb": usage.total // (1024**3),
                "used_gb": usage.used // (1024**3),
                "free_gb": usage.free // (1024**3),
                "percent_used": (usage.used / usage.total * 100) if usage.total > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"NAS status check failed: {e}")
            self._audit_log("nas.status", "failure", {"error": str(e)})
            raise
    
    # =========================================================================
    # Overall Status
    # =========================================================================
    
    async def get_status(self) -> Dict[str, Any]:
        """Get overall infrastructure status"""
        status = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "services": {}
        }
        
        # Check Vault
        try:
            import subprocess
            result = subprocess.run(
                ["vault", "status", "-format=json"],
                capture_output=True,
                text=True,
                timeout=5,
                env={**os.environ, "VAULT_ADDR": self.vault_addr}
            )
            if result.returncode == 0:
                vault_status = json.loads(result.stdout)
                status["services"]["vault"] = {
                    "status": "ok" if not vault_status.get("sealed") else "sealed",
                    "initialized": vault_status.get("initialized"),
                    "sealed": vault_status.get("sealed")
                }
            else:
                status["services"]["vault"] = {"status": "error"}
        except:
            status["services"]["vault"] = {"status": "unavailable"}
        
        # Check Proxmox
        try:
            await self.proxmox_inventory()
            status["services"]["proxmox"] = {"status": "ok"}
        except:
            status["services"]["proxmox"] = {"status": "error"}
        
        # Check UniFi
        try:
            await self.unifi_topology()
            status["services"]["unifi"] = {"status": "ok"}
        except:
            status["services"]["unifi"] = {"status": "error"}
        
        # Check NAS
        try:
            nas = await self.nas_status()
            status["services"]["nas"] = {"status": nas["status"]}
        except:
            status["services"]["nas"] = {"status": "error"}
        
        # Check GPU
        try:
            await self.gpu_run_test()
            status["services"]["gpu"] = {"status": "ok"}
        except:
            status["services"]["gpu"] = {"status": "unavailable"}
        
        return status
