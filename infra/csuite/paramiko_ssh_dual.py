"""
SSH to Ubuntu/cloud guests: try SSH keys, then password + keyboard-interactive (PAM).

Many cloud images disable SSH 'password' method but still accept the same credential
via 'keyboard-interactive' (often "login:" + "Password:" prompts).

Date: 2026-04-08
"""
from __future__ import annotations

import socket
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import paramiko


def _kbd_handler(username: str, password: str, title: str, instructions: str, prompt_list: list) -> list[str]:
    if not prompt_list:
        return [password]
    answers: list[str] = []
    for pr, show_echo in prompt_list:
        text = (str(pr) if pr is not None else "").strip().lower()
        if any(x in text for x in ("user", "login", "account")):
            answers.append(username)
        elif any(x in text for x in ("password", "passphrase", "pin")):
            answers.append(password)
        elif not show_echo:
            answers.append(password)
        else:
            answers.append("")
    return answers


def ssh_client_password_or_keyboard_interactive(
    host: str,
    username: str,
    password: str,
    *,
    port: int = 22,
    timeout: float = 30.0,
) -> "paramiko.SSHClient":
    import paramiko
    from paramiko.ssh_exception import AuthenticationException

    sock = socket.create_connection((host, port), timeout=timeout)
    transport = paramiko.Transport(sock)
    transport.start_client(timeout=timeout)

    def handler(title: str, instructions: str, prompt_list: list) -> list[str]:
        return _kbd_handler(username, password, title, instructions, prompt_list)

    authenticated = False
    try:
        transport.auth_password(username=username, password=password)
        authenticated = transport.is_authenticated()
    except Exception:
        pass

    if not authenticated:
        try:
            transport.auth_interactive(username, handler)
            authenticated = transport.is_authenticated()
        except Exception as e:
            transport.close()
            raise AuthenticationException(
                f"keyboard-interactive failed for {username}@{host}: {e}"
            ) from e

    if not authenticated:
        transport.close()
        raise AuthenticationException(f"SSH auth failed for {username}@{host}")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client._transport = transport
    return client


def _default_key_paths() -> list[Path]:
    home = Path.home() / ".ssh"
    return [home / "id_ed25519", home / "id_rsa", home / "id_ecdsa"]


def _load_private_key(path: Path):
    """Load Ed25519/RSA/ECDSA only (skip broken or legacy DSA keys)."""
    import paramiko

    for loader in (
        paramiko.Ed25519Key.from_private_key_file,
        paramiko.RSAKey.from_private_key_file,
        paramiko.ECDSAKey.from_private_key_file,
    ):
        try:
            return loader(str(path))
        except Exception:
            continue
    return None


def ssh_client_try_keys_password_kbd(
    host: str,
    username: str,
    password: str,
    *,
    port: int = 22,
    timeout: float = 30.0,
    key_paths: list[Path] | None = None,
) -> "paramiko.SSHClient":
    """
    Try SSH private keys first (no passphrase assumed), then password + keyboard-interactive.
    """
    import paramiko

    paths = key_paths if key_paths is not None else _default_key_paths()
    for kp in paths:
        if not kp.is_file():
            continue
        pkey = _load_private_key(kp)
        if pkey is None:
            continue
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                host,
                port=port,
                username=username,
                pkey=pkey,
                timeout=timeout,
                banner_timeout=timeout,
                auth_timeout=timeout,
                allow_agent=False,
                look_for_keys=False,
            )
            return client
        except Exception:
            try:
                client.close()
            except Exception:
                pass

    return ssh_client_password_or_keyboard_interactive(
        host, username, password, port=port, timeout=timeout
    )
