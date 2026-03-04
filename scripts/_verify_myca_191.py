#!/usr/bin/env python3
"""Verify MYCA desktop install on VM 191."""
import os
import paramiko
VM_IP = "192.168.0.191"
VM_USER = "mycosoft"
KEY_PATH = os.path.expanduser("~/.ssh/myca_vm191")
creds_file = os.path.join(os.path.dirname(__file__), "../.credentials.local")
VM_PASSWORD = ""
if os.path.exists(creds_file):
    for line in open(creds_file, encoding="utf-8").read().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                VM_PASSWORD = v.strip()
                break
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
if os.path.exists(KEY_PATH):
    ssh.connect(VM_IP, username=VM_USER, pkey=paramiko.Ed25519Key.from_private_key_file(KEY_PATH), timeout=20)
else:
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=20)
def r(c):
    _, o, _ = ssh.exec_command(c, timeout=30)
    return o.read().decode().strip()
print("node:", r("node -v"))
print("chrome:", r("which google-chrome"))
print("code:", r("which code"))
print("gh:", r("which gh"))
print("xrdp:", r("systemctl is-active xrdp"))
print("novnc:", r("systemctl is-active novnc"))
print("noVNC HTTP:", r("curl -s -o /dev/null -w '%{http_code}' http://localhost:6080/vnc.html"))
