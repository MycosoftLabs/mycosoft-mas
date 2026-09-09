#!/bin/bash
set -u
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  code=$(curl -sS -m 8 -o /tmp/itdx_h.json -w '%{http_code}' http://127.0.0.1:8001/api/itdx/health || echo 000)
  echo "TRY $i $code"
  if [ "$code" = "200" ]; then
    python3 -c 'import json; print(json.load(open("/tmp/itdx_h.json")))'
    break
  fi
  sleep 5
done
ss -lnt | grep 8001 || true
systemctl is-active mas-orchestrator
echo "--- SA ---"
curl -sS -m 60 -o /tmp/itdx_sa.json -w "SA %{http_code}\n" \
  -H "Content-Type: application/json" \
  -d '{"slice":{"name":"Fort Stewart","bbox":[-81.70,31.80,-81.45,32.05],"center":[31.88,-81.61]}}' \
  http://127.0.0.1:8001/api/itdx/situation-assessment || echo "SA FAIL"
python3 - <<'PY'
import json
from pathlib import Path
p=Path("/tmp/itdx_sa.json")
if not p.exists() or p.stat().st_size==0:
    print("SA empty")
else:
    d=json.loads(p.read_text())
    ch=d.get("channels") or {}
    print(d.get("schema_version"), d.get("agent_id"), d.get("ao",{}).get("name"))
    print({k: (v.get("status"), v.get("agent_id"), v.get("p")) for k,v in ch.items()})
    print("fusion", {k: v.get("status") for k,v in (d.get("fusion") or {}).items()})
PY
echo "--- T8 ---"
curl -sS -m 90 -o /tmp/itdx_t8.json -w "T8 %{http_code}\n" \
  -H "Content-Type: application/json" -d '{}' \
  http://127.0.0.1:8001/api/itdx/task8 || echo "T8 FAIL"
python3 - <<'PY'
import json
from pathlib import Path
p=Path("/tmp/itdx_t8.json")
if not p.exists() or p.stat().st_size==0:
    print("T8 empty")
else:
    d=json.loads(p.read_text())
    roles=d.get("roles") or d.get("agents") or []
    print(d.get("schema_version"), d.get("agent_id"), len(roles), d.get("avani_gate"))
    print([(r.get("label"), r.get("agent_id"), r.get("verdict"), r.get("bound")) for r in roles])
PY
echo "--- ALIASES ---"
curl -sS -m 90 -o /dev/null -w "AVANI %{http_code}\n" -H "Content-Type: application/json" -d '{}' http://127.0.0.1:8001/api/avani/task8 || true
curl -sS -m 90 -o /dev/null -w "MYCA %{http_code}\n" -H "Content-Type: application/json" -d '{}' http://127.0.0.1:8001/api/myca/task8 || true
curl -sS -m 90 -o /dev/null -w "AUTH %{http_code}\n" -H "Content-Type: application/json" -d '{}' http://127.0.0.1:8001/api/itdx/authority || true
journalctl -u mas-orchestrator -n 20 --no-pager | tail -20
