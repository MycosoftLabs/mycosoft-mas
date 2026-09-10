# Port Conflict Resolution

The MAS Docker Compose stack maps containers to non-standard **external** ports
to avoid collisions with services already running on the host. Internal
container ports are unchanged.

## Port map (docker-compose.yml)

| Service | Container port | Host port | Why offset |
|---------|---------------|-----------|------------|
| mas-orchestrator | 8000 | **8001** | Avoids conflict with MINDEX API (8000) |
| Postgres | 5432 | **5433** | Avoids local PostgreSQL 17 on 5432 |
| Redis | 6379 | **6390** | Avoids local Redis on 6379 |
| Qdrant | 6333 | **6345** | Avoids local Qdrant on 6333 |
| Grafana | 3000 | **3002** | Avoids website dev (3000/3010) |
| Prometheus | 9090 | 9090 | Standard |
| Ollama | 11434 | 11434 | Standard |

## Common conflicts and fixes

### "Address already in use" on Postgres 5433

Another Compose project or a previous `docker compose up` left a container
bound to that port.

```bash
# Find the process
lsof -i :5433          # Linux/macOS
netstat -ano | findstr 5433   # Windows

# Stop the old stack
docker compose down

# Or kill the specific process
kill <PID>             # Linux/macOS
Stop-Process -Id <PID> # Windows (PowerShell)
```

### Website dev server collides with Grafana (port 3000)

The website dev server defaults to 3010 (`npm run dev:next-only`).
Grafana maps to 3002. These should not conflict. If they do, check for a
stray `next dev` running on port 3000:

```bash
lsof -i :3000
```

### MAS API on 8001 vs MINDEX API on 8000

These are separate VMs in production (MAS on 188:8001, MINDEX on 189:8000).
Locally, `docker-compose.yml` maps MAS to 8001 to keep them distinct. If you
run MINDEX locally on 8000 at the same time, there is no conflict.

### Redis / Qdrant collisions with VM services

If you connect to VM Redis (189:6379) or Qdrant (189:6333) directly, the
local Compose ports (6390, 6345) are already offset and will not collide.
