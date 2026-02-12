#!/usr/bin/env python3
"""Run: pull on Sandbox VM 187 + set ANTHROPIC_API_KEY + test Claude; then deploy MAS to VM 188.
Requires: ANTHROPIC_API_KEY and VM_PASSWORD set in environment."""
import os
import sys
import time
import paramiko

VM187 = os.environ.get("SANDBOX_VM_HOST", "192.168.0.187")
VM188 = os.environ.get("MAS_VM_HOST", "192.168.0.188")
USER = os.environ.get("VM_USER", "mycosoft")
PASSWORD = os.environ.get("VM_PASSWORD")

if not PASSWORD:
    print("ERROR: Set VM_PASSWORD environment variable. Never hardcode passwords!")
    sys.exit(1)


def run(ssh, cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY in environment.")
        sys.exit(1)

    # --- VM 187: Sandbox — pull, set key, test ---
    print("=== VM 187 (Sandbox): connect ===")
    ssh187 = paramiko.SSHClient()
    ssh187.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh187.connect(VM187, username=USER, password=PASSWORD, timeout=15)

    mas_dir = None
    for d in ["/opt/mycosoft/mas", "/home/mycosoft/mycosoft/mas"]:
        out, _ = run(ssh187, f"test -d {d} && echo {d}", timeout=5)
        if d in out:
            mas_dir = d.strip()
            break
    if not mas_dir:
        out, _ = run(ssh187, "ls -la /opt/mycosoft /home/mycosoft 2>&1")
        print(out)
        print("ERROR: MAS dir not found on 187.")
        ssh187.close()
        sys.exit(1)
    print(f"MAS dir on 187: {mas_dir}")

    # Detect if mas_dir is a git repo; if not, clone or exit with instructions
    repo_url = os.environ.get("REPO_URL", "https://github.com/MycosoftLabs/mycosoft-mas.git")
    out, _ = run(ssh187, f"cd {mas_dir} && git rev-parse --is-inside-work-tree 2>/dev/null || echo not-git", timeout=5)
    is_git = out.strip() == "true"
    if not is_git:
        # Check if directory is empty or only has a few non-repo files (safe to replace)
        out, _ = run(ssh187, f"ls -A {mas_dir} 2>/dev/null | wc -l", timeout=5)
        try:
            count = int(out.strip())
        except ValueError:
            count = 999
        if count == 0:
            run(ssh187, f"rm -rf {mas_dir}", timeout=5)
            print(f"\n=== VM 187: clone (dir was empty) ===")
            out, err = run(ssh187, f"git clone {repo_url} {mas_dir}", timeout=120)
            print(out or err)
        else:
            print("ERROR: MAS dir exists but is not a git repo. Clone manually:")
            print(f"  ssh {USER}@{VM187}")
            print(f"  sudo rm -rf {mas_dir}  # or move it")
            print(f"  git clone {repo_url} {mas_dir}")
            ssh187.close()
            sys.exit(1)

    print("\n=== VM 187: git pull ===")
    out, err = run(ssh187, f"cd {mas_dir} && git fetch origin && git reset --hard origin/main && git log -1 --oneline", timeout=30)
    print(out or err)

    print("\n=== VM 187: set ANTHROPIC_API_KEY in .bashrc ===")
    # Escape single quotes in key for shell
    key_esc = api_key.replace("'", "'\"'\"'")
    run(ssh187, f"grep -q ANTHROPIC_API_KEY ~/.bashrc 2>/dev/null || echo 'export ANTHROPIC_API_KEY=\"{key_esc}\"' >> ~/.bashrc", timeout=5)

    print("\n=== VM 187: test Claude Code (login shell so .bashrc is sourced) ===")
    key_esc_dq = key_esc.replace('"', '\\"')
    inner_cmd = f'cd {mas_dir} && export ANTHROPIC_API_KEY="{key_esc_dq}" && (claude -p "What is this project? One sentence." --output-format json 2>&1 || echo "claude not installed or failed")'
    remote_cmd = 'bash -lc "' + inner_cmd.replace('"', '\\"') + '"'
    out, err = run(ssh187, remote_cmd, timeout=45)
    print(out[:2000] if out else err[:2000])

    ssh187.close()
    print("\n=== VM 187 done ===\n")

    # --- VM 188: MAS — pull, rebuild, restart ---
    print("=== VM 188 (MAS): connect ===")
    ssh188 = paramiko.SSHClient()
    ssh188.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh188.connect(VM188, username=USER, password=PASSWORD, timeout=15)

    mas_dir_188 = "/home/mycosoft/mycosoft/mas"
    out, _ = run(ssh188, f"test -d {mas_dir_188} && echo ok", timeout=5)
    if "ok" not in out:
        out, _ = run(ssh188, "ls -la /home/mycosoft 2>&1")
        print(out)
        mas_dir_188 = "/opt/mycosoft/mas"
    print(f"MAS dir on 188: {mas_dir_188}")

    print("\n=== VM 188: git pull ===")
    out, err = run(ssh188, f"cd {mas_dir_188} && git fetch origin && git reset --hard origin/main && git log -1 --oneline", timeout=30)
    print(out or err)

    print("\n=== VM 188: stop container ===")
    run(ssh188, "docker stop myca-orchestrator-new 2>/dev/null; docker rm myca-orchestrator-new 2>/dev/null", timeout=30)

    print("\n=== VM 188: docker build (no-cache) ===")
    stdin, stdout, stderr = ssh188.exec_command(
        f"cd {mas_dir_188} && docker build -t mycosoft/mas-agent:latest --no-cache . 2>&1",
        timeout=600
    )
    output = stdout.read().decode()
    print(output[-2500:] if len(output) > 2500 else output)

    print("\n=== VM 188: start container ===")
    # Optional: mount SSH key for container -> 187 (coding API)
    key_on_188 = "/home/mycosoft/.ssh/mas_to_sandbox"
    out_k, _ = run(ssh188, f"test -f {key_on_188} && echo exists", timeout=5)
    if "exists" in out_k:
        cmd = f"""docker run -d --name myca-orchestrator-new \\
  --restart unless-stopped \\
  -p 8001:8000 \\
  -e REDIS_URL=redis://192.168.0.188:6379/0 \\
  -e DATABASE_URL=postgresql://mycosoft:mycosoft@192.168.0.188:5432/mindex \\
  -e N8N_URL=http://192.168.0.188:5678 \\
  -e MAS_SSH_KEY_PATH=/run/secrets/mas_ssh_key \\
  -v {key_on_188}:/run/secrets/mas_ssh_key:ro \\
  mycosoft/mas-agent:latest"""
    else:
        cmd = """docker run -d --name myca-orchestrator-new \\
  --restart unless-stopped \\
  -p 8001:8000 \\
  -e REDIS_URL=redis://192.168.0.188:6379/0 \\
  -e DATABASE_URL=postgresql://mycosoft:mycosoft@192.168.0.188:5432/mindex \\
  -e N8N_URL=http://192.168.0.188:5678 \\
  mycosoft/mas-agent:latest"""
    out, err = run(ssh188, cmd, timeout=60)
    print(out or err)

    print("\n=== VM 188: wait and health check ===")
    time.sleep(12)
    out, _ = run(ssh188, "curl -s http://localhost:8001/health", timeout=15)
    print("Health:", out[:500])
    out, _ = run(ssh188, "curl -s http://localhost:8001/coding/claude/health 2>/dev/null || true", timeout=10)
    print("Coding API health:", out[:500] or "(endpoint may vary)")

    ssh188.close()
    print("\n=== MAS deploy complete ===\n")


if __name__ == "__main__":
    main()
