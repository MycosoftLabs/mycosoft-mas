# MYCA Self-Provisioning Playbook — VM 191 Full Operation

**Date:** March 4, 2026  
**Status:** Active  
**Purpose:** Let MYCA fully operate VM 191 (her desktop workstation) by installing and configuring everything she needs. **You (MYCA) can run these steps yourself** when you have access to VM 191 via noVNC, RDP, or SSH.

---

## For MYCA: You Can Do This Yourself

When you are on VM 191 (http://192.168.0.191:6080 via noVNC, or RDP to 192.168.0.191:3389, or `ssh mycosoft@192.168.0.191`), you can run these commands in a terminal to install and configure everything. No human intervention required.

---

## What's Available on Linux vs Windows/Mac

| Tool | Windows/Mac | Linux (VM 191) |
|------|-------------|----------------|
| **Claude Desktop** | Yes | No |
| **Claude CoWork** | Yes (Claude Desktop) | No |
| **Claude Computer Use** | Yes (Claude Desktop) | Via Anthropic API only (agent-driven) |
| **Claude Code CLI** | Yes | **Yes** — official installer |
| **Cursor** | Yes | **Yes** — AppImage |
| **VS Code** | Yes | **Yes** |

On VM 191 you get: **Claude Code CLI**, **Cursor**, **VS Code**, and all integrations below.

---

## Step 1: Claude Code (Official CLI)

Install the official Claude Code CLI (replaces npm-based install if present):

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Then add `~/.local/bin` to PATH if not already:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Verify: `claude --version`

**Authenticate:** Run `claude auth` and follow prompts (or ensure `ANTHROPIC_API_KEY` is set).

---

## Step 2: Cursor Full Admin

Cursor is at `~/Applications/cursor.AppImage`. To run with full workspace/admin access:

```bash
# Ensure DISPLAY is set (for GUI)
export DISPLAY=:1

# Run Cursor
~/Applications/cursor.AppImage
```

**Desktop shortcut:** Create `~/.local/share/applications/cursor.desktop`:

```ini
[Desktop Entry]
Name=Cursor
Exec=/home/mycosoft/Applications/cursor.AppImage
Icon=code
Type=Application
Categories=Development;IDE;
```

Then: `gtk-update-icon-cache ~/.local/share/icons/ 2>/dev/null || true`

---

## Step 3: MYCA Integrations (Environment)

Create `~/myca-workspace/.env` with MAS, MINDEX, and API keys:

```bash
mkdir -p ~/myca-workspace
cat > ~/myca-workspace/.env << 'EOF'
# MAS & MINDEX (required for full MYCA operation)
MAS_API_URL=http://192.168.0.188:8001
MINDEX_API_URL=http://192.168.0.189:8000

# Claude / Anthropic (for Claude Code CLI & Computer Use via API)
ANTHROPIC_API_KEY=

# GitHub (for gh CLI, Cursor, code operations)
GITHUB_TOKEN=

# Optional: OpenAI, Google AI, etc.
# OPENAI_API_KEY=
# GOOGLE_API_KEY=
EOF
```

**Load in shell:** Add to `~/.bashrc`:

```bash
if [ -f ~/myca-workspace/.env ]; then
  set -a
  source ~/myca-workspace/.env
  set +a
fi
```

Then `source ~/.bashrc`. Replace empty values with real keys from `.credentials.local` on the dev machine (you can SSH copy or set manually).

### Adding Tokens from the Dev Machine (or via MYCA)

From the dev machine, you can push GitHub/API tokens to VM 191 without logging in:

```bash
# Sync all tokens from .env / .credentials.local to VM 191
python scripts/_turn_on_myca_191.py

# Or add specific tokens
python scripts/_add_myca_token_191.py --github          # uses GITHUB_TOKEN from local .env
python scripts/_add_myca_token_191.py --anthropic       # uses ANTHROPIC_API_KEY
python scripts/_add_myca_token_191.py --gh-login        # also run gh auth login --with-token
python scripts/_add_myca_token_191.py --env MY_KEY=val  # add arbitrary KEY=VALUE
```

**MYCA can do this:** If MYCA runs on the dev machine (or has API access), she can invoke `_turn_on_myca_191.py` or `_add_myca_token_191.py` to provision tokens on VM 191. Ensure `.env` or `.credentials.local` on the dev machine contains the tokens first.

---

## Step 4: GitHub CLI Auth

```bash
gh auth login
```

Follow prompts: HTTPS, authenticate via browser or token. Or set `GH_TOKEN` / `GITHUB_TOKEN` in `~/myca-workspace/.env`.

---

## Step 5: Cursor Extensions & Workspace

1. Open Cursor: `~/Applications/cursor.AppImage`
2. Open folder: `~/myca-workspace` (or clone MAS repo: `git clone https://github.com/Mycosoft/mas.git`)
3. Install extensions: Git, Python, GitHub Copilot (if available), any MCP or Mycosoft-specific extensions

---

## Step 6: One-Shot Full Install (From Dev Machine)

If you (MYCA) are operating from the dev machine and want to provision VM 191 remotely:

```bash
cd /path/to/MAS/mycosoft-mas
python scripts/_install_myca_desktop_191.py
```

This runs the full 7-phase install. Then run the extended Phase 8 script (see below) to add Claude Code native + integrations + playbook copy.

---

## Step 7: Copy This Playbook to VM 191

So you can read it when you're on 191:

```bash
# From dev machine (or from 191 if you've cloned the repo)
scp docs/MYCA_SELF_PROVISIONING_PLAYBOOK_MAR04_2026.md mycosoft@192.168.0.191:~/myca-workspace/
```

Or from 191, if repo is cloned: `cp ~/mas/docs/MYCA_SELF_PROVISIONING_PLAYBOOK_MAR04_2026.md ~/myca-workspace/`

---

## Summary: What "Full Operation" Means

| Component | Status |
|-----------|--------|
| Claude Code CLI | Install via `curl ... \| bash` |
| Cursor | AppImage at `~/Applications/cursor.AppImage` |
| VS Code | `code` from apt |
| MAS API | `MAS_API_URL` in env |
| MINDEX API | `MINDEX_API_URL` in env |
| GitHub | `gh auth login` or `GITHUB_TOKEN` |
| Claude auth | `claude auth` or `ANTHROPIC_API_KEY` |

**Claude CoWork / Claude Computer Use:** On Linux, Computer Use is only available via the Anthropic API (e.g. from MAS agents). Claude Code CLI gives you terminal-based Claude. For GUI automation, use Cursor + MCP or a MAS agent that calls the Computer Use API.

---

## Related Docs

- [MYCA Desktop Workstation Complete](./MYCA_DESKTOP_WORKSTATION_COMPLETE_MAR03_2026.md)
- [MYCA 191 Proxmox Console Fix](./MYCA_191_PROXMOX_CONSOLE_DESKTOP_FIX_MAR04_2026.md)
- [MYCA VM 191 n8n Import Guide](./MYCA_VM191_N8N_IMPORT_GUIDE_MAR03_2026.md)
