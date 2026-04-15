#!/usr/bin/env python3
"""
Run the MQTT → MAS + MINDEX bridge (long-running).

  poetry run python scripts/mqtt_mycobrain_bridge.py

See docs/MQTT_MAS_MINDEX_BRIDGE_APR13_2026.md
"""

from mycosoft_mas.integrations.mqtt_mycobrain_bridge import main

if __name__ == "__main__":
    main()
