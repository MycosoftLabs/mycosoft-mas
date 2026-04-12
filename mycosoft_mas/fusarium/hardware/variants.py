from __future__ import annotations

from typing import Dict, List


HARDWARE_VARIANTS: Dict[str, Dict[str, object]] = {
    "mushroom1-d": {
        "role": "expeditionary_edge_gateway",
        "sensors": ["bme688", "hydrophone", "magnetometer", "imu"],
        "comms": ["lora", "wifi", "mqtt", "mdp-v2"],
        "power": "12v_battery_or_vehicle",
    },
    "hyphae-one-d": {
        "role": "shoreline_or_buoy_payload",
        "sensors": ["hydrophone_array", "acoustic_modem", "pressure", "gps"],
        "comms": ["mdp-v2", "mmp", "sat_backhaul"],
        "power": "solar_plus_battery",
    },
    "sporebase-d": {
        "role": "fixed_installation_sensor_hub",
        "sensors": ["lidar", "radar", "wifisense", "fci"],
        "comms": ["ethernet", "fiber", "tls13"],
        "power": "site_power_redundant_ups",
    },
    "myconode-subsurface": {
        "role": "subsurface_passive_listening_node",
        "sensors": ["hydrophone", "magnetometer", "temperature", "salinity"],
        "comms": ["acoustic_modem", "delay_tolerant_sync", "mdp-v2"],
        "power": "long_life_battery_pack",
    },
}


def list_hardware_variants() -> List[Dict[str, object]]:
    return [{"variant": name, **spec} for name, spec in HARDWARE_VARIANTS.items()]
