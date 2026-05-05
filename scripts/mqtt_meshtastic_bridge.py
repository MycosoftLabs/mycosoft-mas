#!/usr/bin/env python3
"""Run Meshtastic MQTT → MINDEX + Redis stream bridge (long-running, external process)."""

from mycosoft_mas.integrations.mqtt_meshtastic_bridge import main

if __name__ == "__main__":
    main()
