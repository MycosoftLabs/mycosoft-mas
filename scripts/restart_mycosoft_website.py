#!/usr/bin/env python3
"""
Restart the Mycosoft website container on the sandbox VM and re-check static assets.

Why this exists:
- Next.js (standalone) pre-scans `public/` at startup. If we mount `/app/public/assets`
  and sync files after the container is already running, Next can continue returning 404
  until the process restarts and re-scans the public folder.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class VmTarget:
    host: str
    username: str
    password: str


def run(ssh: paramiko.SSHClient, cmd: str, *, timeout: int = 60) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    return code, out, err


def main() -> int:
    target = VmTarget(host="192.168.0.187", username="mycosoft", password="Mushroom1!Mushroom1!")
    container_name = "mycosoft-website"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {target.host} ...")
    ssh.connect(target.host, username=target.username, password=target.password, timeout=30)

    try:
        print(f"Restarting container: {container_name}")
        code, out, err = run(ssh, f"docker restart {container_name}", timeout=60)
        print(out.strip())
        if code != 0:
            print(err.strip())
            return code or 1

        # Quick sanity check from inside the container (doesn't rely on external networking)
        check_cmd = (
            "docker exec "
            + container_name
            + " node -e "
            + "\"const http=require('http');"
            + "const urls=['/placeholder.svg','/assets/test.txt','/assets/mushroom1/1.jpg','/assets/mushroom1/Main%20A.jpg'];"
            + "let pending=urls.length;"
            + "for (const u of urls){"
            + "http.get({host:'127.0.0.1',port:3000,path:u},res=>{"
            + "console.log(u,res.statusCode,res.headers['content-type']);"
            + "res.resume();"
            + "if(--pending===0) process.exit(0);"
            + "}).on('error',e=>{"
            + "console.log(u,'ERROR',e.message);"
            + "if(--pending===0) process.exit(0);"
            + "});"
            + "}\""
        )

        print("Re-checking static files inside container ...")
        code, out, err = run(ssh, check_cmd, timeout=60)
        print(out.strip())
        if err.strip():
            print("---stderr---")
            print(err.strip())

        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())

