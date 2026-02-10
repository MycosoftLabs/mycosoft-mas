"""
Tailscale Utilities for MycoBrain Service

Auto-detects Tailscale IP for device registration.
Falls back to local IP if Tailscale is not available.

Created: February 10, 2026
"""

import socket
import subprocess
import logging
import platform
from typing import Optional, Tuple

logger = logging.getLogger("TailscaleUtils")


def get_tailscale_ip() -> Optional[str]:
    """
    Detect Tailscale IP if available.
    
    Returns:
        Tailscale IP (100.x.x.x) if connected, None otherwise.
    """
    try:
        # Try using tailscale CLI first (most reliable)
        result = subprocess.run(
            ["tailscale", "ip", "-4"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            ip = result.stdout.strip()
            if ip.startswith("100."):
                logger.info(f"Tailscale IP detected via CLI: {ip}")
                return ip
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.debug(f"Tailscale CLI not available: {e}")
    
    # Fallback: check network interfaces for Tailscale IP range (100.x.x.x)
    try:
        import psutil
        for interface, addrs in psutil.net_if_addrs().items():
            # Look for Tailscale interface (named "Tailscale" on Windows, "tailscale0" on Linux)
            if "tailscale" in interface.lower():
                for addr in addrs:
                    if addr.family == socket.AF_INET and addr.address.startswith("100."):
                        logger.info(f"Tailscale IP detected via interface {interface}: {addr.address}")
                        return addr.address
    except ImportError:
        logger.debug("psutil not available for interface detection")
    except Exception as e:
        logger.debug(f"Interface detection failed: {e}")
    
    # Fallback: check all interfaces for 100.x.x.x range
    try:
        import netifaces
        for iface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr.get("addr", "")
                    if ip.startswith("100."):
                        logger.info(f"Tailscale IP detected via netifaces {iface}: {ip}")
                        return ip
    except ImportError:
        logger.debug("netifaces not available")
    except Exception as e:
        logger.debug(f"netifaces detection failed: {e}")
    
    return None


def get_local_ip() -> str:
    """
    Get the local LAN IP address.
    
    Returns:
        Local IP address (e.g., 192.168.x.x)
    """
    try:
        # Create a socket to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        # Connect to a public IP (doesn't actually send data)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_reachable_address(public_host: Optional[str] = None, port: int = 8003) -> Tuple[str, str]:
    """
    Determine the best reachable address for this device.
    
    Priority:
    1. Explicit public host (MYCOBRAIN_PUBLIC_HOST env var)
    2. Tailscale IP if available
    3. Local LAN IP
    
    Args:
        public_host: Explicit public host/URL
        port: Service port
        
    Returns:
        Tuple of (host, connection_type)
        connection_type is one of: "cloudflare", "tailscale", "lan"
    """
    # Priority 1: Explicit public host (Cloudflare tunnel or custom)
    if public_host:
        if public_host.startswith("http"):
            # It's a full URL (Cloudflare tunnel)
            logger.info(f"Using public host: {public_host}")
            return public_host, "cloudflare"
        else:
            # It's an IP or hostname
            logger.info(f"Using custom host: {public_host}")
            return public_host, "cloudflare"
    
    # Priority 2: Tailscale IP
    tailscale_ip = get_tailscale_ip()
    if tailscale_ip:
        logger.info(f"Using Tailscale IP: {tailscale_ip}")
        return tailscale_ip, "tailscale"
    
    # Priority 3: Local LAN IP
    local_ip = get_local_ip()
    logger.info(f"Using local IP: {local_ip}")
    return local_ip, "lan"


def is_tailscale_connected() -> bool:
    """Check if Tailscale is connected."""
    try:
        result = subprocess.run(
            ["tailscale", "status"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0 and "stopped" not in result.stdout.lower()
    except Exception:
        return False


def get_tailscale_hostname() -> Optional[str]:
    """Get the Tailscale MagicDNS hostname."""
    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            import json
            status = json.loads(result.stdout)
            self_info = status.get("Self", {})
            dns_name = self_info.get("DNSName", "")
            if dns_name:
                # Remove trailing dot
                return dns_name.rstrip(".")
    except Exception:
        pass
    return None


if __name__ == "__main__":
    # Test utilities
    logging.basicConfig(level=logging.DEBUG)
    
    print("Tailscale Utils Test")
    print("=" * 40)
    
    tailscale_ip = get_tailscale_ip()
    print(f"Tailscale IP: {tailscale_ip}")
    
    local_ip = get_local_ip()
    print(f"Local IP: {local_ip}")
    
    host, conn_type = get_reachable_address()
    print(f"Reachable address: {host} ({conn_type})")
    
    connected = is_tailscale_connected()
    print(f"Tailscale connected: {connected}")
    
    hostname = get_tailscale_hostname()
    print(f"Tailscale hostname: {hostname}")
