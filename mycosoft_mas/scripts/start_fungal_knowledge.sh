#!/bin/bash

# Start Oxigraph server
docker run --rm \
    -v $(pwd)/data/fungal_knowledge:/data \
    -p 7878:7878 \
    ghcr.io/oxigraph/oxigraph serve \
    --location /data \
    --bind 0.0.0.0:7878 &

# Wait for Oxigraph to start
sleep 5

# Initialize the fungal knowledge graph
python -m mycosoft_mas.agents.mycology_bio_agent \
    --config mycosoft_mas/config/fungal_knowledge_config.json 