"""
MYCA World Sensors

Sensors that feed the world model with data from various sources.

Per-sensor try/except so one missing module doesn't collapse all sensors.

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

from mycosoft_mas.consciousness.sensors.base_sensor import BaseSensor, SensorStatus

try:
    from mycosoft_mas.consciousness.sensors.crep_sensor import CREPSensor
except Exception:
    CREPSensor = None  # type: ignore[assignment,misc]

try:
    from mycosoft_mas.consciousness.sensors.earth2_sensor import Earth2Sensor
except Exception:
    Earth2Sensor = None  # type: ignore[assignment,misc]

try:
    from mycosoft_mas.consciousness.sensors.earthlive_sensor import EarthLIVESensor
except Exception:
    EarthLIVESensor = None  # type: ignore[assignment,misc]

try:
    from mycosoft_mas.consciousness.sensors.mindex_sensor import MINDEXSensor
except Exception:
    MINDEXSensor = None  # type: ignore[assignment,misc]

try:
    from mycosoft_mas.consciousness.sensors.mycobrain_sensor import MycoBrainSensor
except Exception:
    MycoBrainSensor = None  # type: ignore[assignment,misc]

try:
    from mycosoft_mas.consciousness.sensors.natureos_sensor import NatureOSSensor
except Exception:
    NatureOSSensor = None  # type: ignore[assignment,misc]

try:
    from mycosoft_mas.consciousness.sensors.nlm_sensor import NLMSensor
except Exception:
    NLMSensor = None  # type: ignore[assignment,misc]

try:
    from mycosoft_mas.consciousness.sensors.workspace_sensor import WorkspaceSensor
except Exception:
    WorkspaceSensor = None  # type: ignore[assignment,misc]

try:
    from mycosoft_mas.consciousness.sensors.presence_sensor import PresenceSensor
except Exception:
    PresenceSensor = None  # type: ignore[assignment,misc]

__all__ = [
    "BaseSensor",
    "SensorStatus",
    "CREPSensor",
    "Earth2Sensor",
    "NatureOSSensor",
    "MINDEXSensor",
    "MycoBrainSensor",
    "NLMSensor",
    "EarthLIVESensor",
    "WorkspaceSensor",
    "PresenceSensor",
]
