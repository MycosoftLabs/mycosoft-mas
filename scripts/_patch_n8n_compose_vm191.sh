#!/bin/bash
# Add EXECUTIONS_MODE=regular to fix n8n task broker port conflict
cd /opt/myca || exit 1
sudo sed -i '/GENERIC_TIMEZONE=America\/Los_Angeles/a\      - EXECUTIONS_MODE=regular' docker-compose.yml
grep -E "GENERIC|EXECUTIONS" docker-compose.yml
