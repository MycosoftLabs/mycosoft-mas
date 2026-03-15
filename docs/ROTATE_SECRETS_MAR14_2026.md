# Secrets to Rotate — Mar 14, 2026

**Date:** March 14, 2026  
**Purpose:** Clear list of credentials that may have been exposed on GitHub or in code. Rotate these now and store new values only in `.credentials.local` / `.env` (gitignored) or environment variables.

---

## 1. VM SSH / sudo password

| Item | Exposure | Action |
|------|----------|--------|
| **VM_SSH_PASSWORD / VM_PASSWORD** | Past commits or placeholders (`REDACTED_VM_SSH_PASSWORD`, or any literal in `_force_restart.py`, `setup_mycobrain_cloudflare.py`, `check_mycobrain_device_service.py`) may have been replaced with real values in history. Rule doc: old value `Mushroom1!Mushroom1!` was revoked. | **Rotate now.** Set new password on all VMs (187, 188, 189, 190, 191). Update `.credentials.local` and any CI/env with `VM_PASSWORD` and `VM_SSH_PASSWORD`. Never commit the new value. |

---

## 2. Proxmox API password

| Item | Exposure | Action |
|------|----------|--------|
| **Proxmox / API password** | `scripts/full_network_discovery.py` previously used literal `"20202020"` when API status password started with `"202"`. | **Rotate if that was the real Proxmox password.** Set new value in `.credentials.local` as `PROXMOX_PASSWORD` (or `VM_PASSWORD` if shared). Update Proxmox user password and any automation that uses it. |

---

## 3. MINDEX database password

| Item | Exposure | Action |
|------|----------|--------|
| **MINDEX_DB_PASSWORD** | Rule doc: old value `mycosoft_mindex_2026` was rotated; do not use. | **Ensure rotated.** If ever committed or in history, rotate again. Store only in `.env` / `.credentials.local` and VM env. |

---

## 4. API keys (NCBI, NGC, etc.)

| Item | Exposure | Action |
|------|----------|--------|
| **NCBI_API_KEY** | Rule doc: old key was rotated; never type in code. | **Use env only.** If old key is in git history, revoke/regenerate in NCBI and set new key in env only. |
| **NGC_API_KEY** | Rule doc: NGC key revoked. | **Do not use revoked key.** Create new key if needed; store in env only. |
| **NEMOTRON_API_KEY** | Used in `backend_selection.py` via `os.getenv`. | **No rotation** unless key was ever committed. If in doubt, regenerate and set in env only. |

---

## 5. SSH keys (GitHub / VMs)

| Item | Exposure | Action |
|------|----------|--------|
| **GitHub deploy keys / SSH keys** | If any private key was ever committed (e.g. in scripts or docs), it is compromised. | **Rotate now.** Generate new key pair; add new public key to GitHub and to VMs; remove old key from GitHub and from `~/.ssh/authorized_keys` on each VM. |
| **VM authorized_keys** | If VM SSH password was exposed, assume keys could have been used; rotation of password plus key audit is recommended. | After rotating VM password, review `authorized_keys` on each VM and remove any unknown or old keys. |

---

## 6. Checklist after rotation

- [ ] VM password rotated on 187, 188, 189, 190, 191; `.credentials.local` updated (local and any secure CI store).
- [ ] Proxmox password rotated if it was ever the literal in full_network_discovery; env/creds updated.
- [ ] MINDEX DB password rotated if ever in history; `.env` and VM env updated.
- [ ] NCBI / NGC keys revoked or regenerated; new values only in env.
- [ ] GitHub and VM SSH keys rotated if any private key was ever committed; new public keys deployed.
- [ ] No secrets committed in this or future commits; all scripts use `os.environ.get(...)` or load from `.credentials.local` only.

---

**Reference:** `docs/GAPS_AND_SECURITY_AUDIT_MAR14_2026.md`, `.cursor/rules/no-hardcoded-secrets.mdc`, `.cursor/rules/vm-credentials.mdc`
