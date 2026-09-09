#!/bin/bash
# Switch MAS 188 working tree to origin/main (PR 135) without reverting fusarium_api.
set -euo pipefail
cd /home/mycosoft/mycosoft/mas

mkdir -p /tmp/itdx-hot-sep09
cp -a mycosoft_mas/core/routers/fusarium_api.py /tmp/itdx-hot-sep09/fusarium_api.py
sha_before=$(git hash-object mycosoft_mas/core/routers/fusarium_api.py)

# Move untracked ITDX copies aside so checkout can write main versions.
for f in \
  mycosoft_mas/agents/itdx_task8_agent.py \
  mycosoft_mas/core/routers/itdx_api.py \
  mycosoft_mas/core/routers/itdx_public_sources.py \
  mycosoft_mas/engines/intention/intention_service.py \
  tests/test_itdx_task8_api.py
do
  if [ -e "$f" ]; then
    mv "$f" "/tmp/itdx-hot-sep09/$(basename "$f")"
  fi
done

git stash push -m "cmmc-hot-pre-main-sep09" -- \
  mycosoft_mas/agents/__init__.py \
  mycosoft_mas/core/agent_registry.py \
  mycosoft_mas/core/myca_main.py \
  mycosoft_mas/core/routers/avani_router.py \
  mycosoft_mas/core/routers/compliance_api.py \
  mycosoft_mas/core/routers/nlm_api.py \
  mycosoft_mas/core/routers/psathyrella_api.py \
  mycosoft_mas/nlm/inference/service.py \
  mycosoft_mas/security/posture_integrity_monitor.py \
  mycosoft_mas/core/routers/fusarium_api.py || true

git fetch origin main
git checkout main
git pull --ff-only origin main

echo "HEAD=$(git rev-parse --short HEAD)"
echo "STATUS=$(git status -sb)"

# Restore live fusarium_api if main somehow differs (it should match).
sha_main=$(git hash-object mycosoft_mas/core/routers/fusarium_api.py)
if [ "$sha_before" != "$sha_main" ]; then
  echo "RESTORING_FUSARIUM_API"
  cp -a /tmp/itdx-hot-sep09/fusarium_api.py mycosoft_mas/core/routers/fusarium_api.py
else
  echo "FUSARIUM_API_UNCHANGED"
fi

git diff --stat HEAD -- mycosoft_mas/core/routers/fusarium_api.py || true
