#!/bin/bash
# ChemSpider Environment Variable Setup Script
# Run this on the sandbox VM (192.168.0.187)
# Date: 2026-01-24

CHEMSPIDER_KEY="TSif8NaGxFixrCft4O581jGjIz2GnIo4TCQqM01h"
CHEMSPIDER_URL="https://api.rsc.org/compounds/v1"

echo "Setting up ChemSpider environment variables..."

# MAS .env
if [ -f /home/mycosoft/mycosoft/mas/.env ]; then
    if ! grep -q "CHEMSPIDER_API_KEY" /home/mycosoft/mycosoft/mas/.env; then
        cat >> /home/mycosoft/mycosoft/mas/.env << EOF

# ChemSpider API Configuration (Added 2026-01-24)
CHEMSPIDER_API_KEY=${CHEMSPIDER_KEY}
CHEMSPIDER_API_URL=${CHEMSPIDER_URL}
CHEMSPIDER_RATE_LIMIT=0.6
CHEMSPIDER_CACHE_TTL=86400
EOF
        echo "✓ Added to MAS .env"
    else
        echo "○ MAS .env already has ChemSpider config"
    fi
fi

# Website .env (if exists)
if [ -f /home/mycosoft/mycosoft/website/.env ]; then
    if ! grep -q "CHEMSPIDER_API_KEY" /home/mycosoft/mycosoft/website/.env; then
        cat >> /home/mycosoft/mycosoft/website/.env << EOF

# ChemSpider API Configuration (Added 2026-01-24)
CHEMSPIDER_API_KEY=${CHEMSPIDER_KEY}
NEXT_PUBLIC_MINDEX_API_URL=http://localhost:8000
EOF
        echo "✓ Added to Website .env"
    else
        echo "○ Website .env already has ChemSpider config"
    fi
fi

# Also set as system environment variable for current session
export CHEMSPIDER_API_KEY="${CHEMSPIDER_KEY}"
export CHEMSPIDER_API_URL="${CHEMSPIDER_URL}"

echo ""
echo "ChemSpider setup complete!"
echo "Key: ${CHEMSPIDER_KEY:0:10}..."
