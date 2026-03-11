"""
C-Suite executive assistant VM infrastructure.

Provides role-based provisioning for CEO, CFO, CTO, COO VMs on Proxmox 90.
Date: March 7, 2026
"""
from .provision_base import load_credentials, load_proxmox_config, pve_request, wait_for_port
from .provision_csuite import (
    create_windows_vm,
    get_all_roles,
    get_role_config,
    get_proxmox_settings,
    get_vm_spec,
)

__all__ = [
    "load_credentials",
    "load_proxmox_config",
    "pve_request",
    "wait_for_port",
    "create_windows_vm",
    "get_all_roles",
    "get_role_config",
    "get_proxmox_settings",
    "get_vm_spec",
]
