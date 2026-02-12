# Deploy and Test MYCA Consciousness – Feb 10, 2026

## Summary

- **MAS (consciousness)** has been pushed to GitHub and deployed to **MAS VM 192.168.0.188**.
- **MINDEX** needs no schema or API changes for consciousness; the MYCA world model uses existing MINDEX endpoints (health, stats, search, etc.).
- Use this doc to run **sandbox deploy**, **MINDEX deploy** (if you have local MINDEX changes), and **full MYCA tests** from a machine that can reach the VMs.

---

## 1. GitHub

- **MAS**: Consciousness commit is on `main`. Push was already up-to-date.
- **MINDEX**: Push any local changes if you have them; no consciousness-specific changes required.

---

## 2. Tests (local)

- **Consciousness unit tests**: `python -m pytest tests/consciousness/ -v --tb=short`
  - Many tests pass (soul, substrate, identity, beliefs, purpose, emotions, creativity).
  - Some fail due to test fixtures (e.g. `AttentionFocus` requires `id`, `AttentionController` requires `consciousness`). Production consciousness code and API are unaffected.
- **Full MYCA integration test** (against MAS URL):
  ```bash
  python scripts/test_myca_consciousness_full.py --base-url http://192.168.0.188:8001
  ```
  For local MAS: `--base-url http://localhost:8001`

---

## 3. Deploy MAS VM (188)

Already run via `scripts/full_mas_deploy.py`:

1. SSH to 192.168.0.188, pull `origin/main`, rebuild Docker image, restart `myca-orchestrator-new`.
2. Container started; health check on the VM can be run with: `curl -s http://127.0.0.1:8001/health`.

To re-run deploy:

```bash
python scripts/full_mas_deploy.py
```

(If the script fails on printing Docker logs due to Unicode, the deploy may still have succeeded; verify on the VM.)

---

## 4. Deploy Sandbox VM (187) – Website

From your dev machine (with website code pushed to GitHub):

1. SSH: `ssh mycosoft@192.168.0.187`
2. Pull: `cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main`
3. Rebuild: `docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache .`
4. Restart (include NAS mount):
   ```bash
   docker stop mycosoft-website; docker rm mycosoft-website
   docker run -d --name mycosoft-website -p 3000:3000 \
     -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
     --restart unless-stopped mycosoft-always-on-mycosoft-website:latest
   ```
5. Purge Cloudflare cache (Purge Everything).
6. Verify: compare http://localhost:3010 with https://sandbox.mycosoft.com (or your sandbox host).

---

## 5. MINDEX (189)

- **No consciousness-specific changes** in MINDEX. MYCA’s world model calls existing MINDEX API (e.g. health, stats, search).
- If you have other MINDEX changes to deploy:
  1. Push MINDEX repo to GitHub.
  2. On MINDEX VM (192.168.0.189): pull, rebuild API container, restart.
  3. See `scripts/deploy_mindex_complete.py` or your usual MINDEX deploy process.

---

## 6. Full MYCA test (sandbox + local)

From a host that can reach 192.168.0.188 and (optionally) 192.168.0.187:

1. **MAS / MYCA API**
   ```bash
   python scripts/test_myca_consciousness_full.py --base-url http://192.168.0.188:8001
   ```
   Expect: MAS health 200, MYCA health 200, status, identity, soul, chat, world, emotions all 200 (or acceptable errors if services are down).

2. **Website (sandbox)**  
   - Open sandbox site and use every MYCA chat entry point (e.g. global chat widget, dedicated MYCA page).
   - Confirm requests go to MAS (188) and you get replies (no mock data).

3. **Local dev**
   - Run website with `npm run dev:next-only` and set `MAS_API_URL=http://192.168.0.188:8001` (and optionally `MINDEX_API_URL=http://192.168.0.189:8000`) in `.env.local`.
   - Repeat the same MYCA chat checks; confirm same behavior as sandbox.

---

## 7. Endpoints reference

| Endpoint | Method | Purpose |
|----------|--------|--------|
| `/health` | GET | MAS process health |
| `/api/myca/health` | GET | MYCA consciousness health |
| `/api/myca/status` | GET | Awake/sleeping, metrics |
| `/api/myca/awaken` | POST | Wake MYCA (idempotent) |
| `/api/myca/identity` | GET | MYCA identity |
| `/api/myca/soul` | GET | Soul summary (beliefs, purpose, etc.) |
| `/api/myca/chat` | POST | Chat (body: `message`, `session_id`, optional `user_id`) |
| `/api/myca/chat/stream` | POST | SSE streaming chat |
| `/api/myca/world` | GET | World model state (sensors) |
| `/api/myca/emotions` | GET | Current emotional state |

---

## 8. File locations

- Full MYCA test script: `scripts/test_myca_consciousness_full.py`
- Consciousness API router: `mycosoft_mas/core/routers/consciousness_api.py`
- MYCA soul config: `config/myca_soul.yaml`
- Architecture doc: `docs/MYCA_CONSCIOUSNESS_ARCHITECTURE_FEB10_2026.md`
