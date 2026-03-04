# Mycosoft SSH MCP – Secure VM Access for Claude Code, Cursor, Claude Cowork

**Date**: March 3, 2026  
**Status**: Complete

## Overview

The **mycosoft-ssh** MCP server provides secure SSH/SFTP access to all Mycosoft VMs from Claude Code, Cursor, and Claude Cowork. Operations are restricted to the `192.168.0.x` subnet and audited to `~/.mycosoft-ssh-audit.log`.

## Tools

| Tool | Purpose |
|------|---------|
| `ssh_exec(host, command, sudo?, timeout?)` | Run a shell command on a VM |
| `ssh_upload(host, local_path, remote_path)` | Upload a file via SFTP |
| `ssh_download(host, remote_path, local_path?)` | Download a file; omit `local_path` to get content in response |
| `ssh_status()` | Check SSH connectivity to all 5 VMs |

## Host Aliases

| Alias | IP | Role |
|-------|-----|------|
| sandbox | 192.168.0.187 | Website, MycoBrain host |
| mas | 192.168.0.188 | MAS orchestrator, n8n, Ollama |
| mindex | 192.168.0.189 | PostgreSQL, Redis, Qdrant, MINDEX API |
| gpu | 192.168.0.190 | GPU workloads |
| myca | 192.168.0.191 | MYCA AI Secretary, n8n, platform connectors |

You can also pass raw IPs (e.g. `192.168.0.191`) as long as they are in `192.168.0.x`.

## Setup (One-Time)

### 1. Install Dependencies

```bash
pip install -r mcp/requirements.txt
# or
pip install paramiko fastmcp
```

### 2. Set Credentials

Use **one** of these:

- **Option A – Env vars (recommended for Claude Code):**
  ```bash
  set VM_PASSWORD=your-vm-password
  set VM_SSH_USER=mycosoft
  ```

- **Option B – `.credentials.local` in MAS repo:**
  ```
  VM_SSH_USER=mycosoft
  VM_SSH_PASSWORD=your-vm-password
  ```

- **Option C – `~/.mycosoft-credentials`:**
  Same format as Option B.

### 3. Enable MCP for Your Tool

**Claude Code (Desktop):**

1. Open the MAS repo as project: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas`
2. The repo includes `.mcp.json`; Claude Code picks it up if configured for project MCP.
3. Or add manually:
   ```bash
   claude mcp add --transport stdio mycosoft-ssh -- python mcp/run_mycosoft_ssh.py
   ```
   (Run from MAS repo root.)

**Cursor:**

The MAS repo includes `.cursor/mcp.json` — Cursor auto-loads it when the MAS folder is in your workspace. No manual config needed.

If you use a global config, add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "mycosoft-ssh": {
      "command": "python",
      "args": ["C:\\Users\\admin2\\Desktop\\MYCOSOFT\\CODE\\MAS\\mycosoft-mas\\mcp\\run_mycosoft_ssh.py"]
    }
  }
}
```

(Adjust path if MAS repo is elsewhere.)

**Claude Cowork:**

Use the same stdio config; Cowork supports MCP servers via project config.

## Adding Future VMs

Edit `mcp/mycosoft_ssh/server.py` and add entries to `VM_HOSTS`:

```python
VM_HOSTS = {
    "sandbox": "192.168.0.187",
    "mas": "192.168.0.188",
    "mindex": "192.168.0.189",
    "gpu": "192.168.0.190",
    "myca": "192.168.0.191",
    "newvm": "192.168.0.192",  # add here
}
```

Only IPs matching `^192\.168\.0\.\d{1,3}$` are allowed.

## Security

- **Subnet restriction:** Only `192.168.0.x` IPs are permitted.
- **Audit log:** All operations are logged to `~/.mycosoft-ssh-audit.log`.
- **Credentials:** Never committed; use env vars or gitignored files.

## Related Documents

- [VM Layout and Dev Remote Services](../.cursor/rules/vm-layout-and-dev-remote-services.mdc)
- [VM Credentials](../.cursor/rules/vm-credentials.mdc)
- [VM SSH MCP Rule](../.cursor/rules/vm-ssh-mcp.mdc)
