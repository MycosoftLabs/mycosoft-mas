"""
MYCA Lab Automation Agents
Agents for laboratory instrument control and automation.
Created: February 3, 2026
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel
from .scientific_agents import BaseScientificAgent, ScientificTask

logger = logging.getLogger(__name__)

class InstrumentType(str, Enum):
    INCUBATOR = "incubator"
    CENTRIFUGE = "centrifuge"
    SPECTROPHOTOMETER = "spectrophotometer"
    MICROSCOPE = "microscope"
    PIPETTOR = "pipettor"
    THERMOCYCLER = "thermocycler"
    HPLC = "hplc"
    MASS_SPEC = "mass_spec"
    ELECTROPORATOR = "electroporator"
    BIOREACTOR = "bioreactor"
    MICROFLUIDIC = "microfluidic"

class InstrumentStatus(str, Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    OFFLINE = "offline"

class Instrument(BaseModel):
    instrument_id: UUID
    instrument_type: InstrumentType
    name: str
    status: InstrumentStatus = InstrumentStatus.AVAILABLE
    location: str = ""
    capabilities: Dict[str, Any] = {}
    current_job: Optional[UUID] = None
    last_calibration: Optional[datetime] = None

class ProtocolStep(BaseModel):
    step_number: int
    action: str
    instrument: Optional[str] = None
    parameters: Dict[str, Any] = {}
    duration_seconds: Optional[int] = None
    conditions: Dict[str, Any] = {}

class LabProtocol(BaseModel):
    protocol_id: UUID
    name: str
    description: str
    steps: List[ProtocolStep]
    reagents: List[str] = []
    equipment: List[str] = []
    estimated_duration_minutes: int = 0


class IncubatorAgent(BaseScientificAgent):
    """Controls incubators and growth chambers."""
    def __init__(self):
        super().__init__("incubator_agent", "Incubator Agent", "Controls temperature, humidity, and CO2 for growth chambers")
        self.chambers: Dict[str, Any] = {}
    
    async def execute_task(self, task: ScientificTask) -> Dict[str, Any]:
        task_type = task.task_type
        if task_type == "set_temperature":
            return await self._set_temperature(task.input_data)
        elif task_type == "set_humidity":
            return await self._set_humidity(task.input_data)
        elif task_type == "start_program":
            return await self._start_program(task.input_data)
        else:
            return {"error": f"Unknown task type: {task_type}"}
    
    async def _set_temperature(self, data: Dict[str, Any]) -> Dict[str, Any]:
        chamber_id = data.get("chamber_id")
        temperature_c = data.get("temperature_c", 25.0)
        logger.info(f"Setting chamber {chamber_id} to {temperature_c}C")
        return {"chamber_id": chamber_id, "temperature_c": temperature_c, "status": "set"}
    
    async def _set_humidity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        chamber_id = data.get("chamber_id")
        humidity_pct = data.get("humidity_pct", 50.0)
        return {"chamber_id": chamber_id, "humidity_pct": humidity_pct, "status": "set"}
    
    async def _start_program(self, data: Dict[str, Any]) -> Dict[str, Any]:
        chamber_id = data.get("chamber_id")
        program = data.get("program")
        return {"chamber_id": chamber_id, "program": program, "status": "running"}


class PipettorAgent(BaseScientificAgent):
    """Controls robotic pipettors for liquid handling."""
    def __init__(self):
        super().__init__("pipettor_agent", "Pipettor Agent", "Controls robotic liquid handling systems")
    
    async def execute_task(self, task: ScientificTask) -> Dict[str, Any]:
        task_type = task.task_type
        if task_type == "transfer":
            return await self._transfer(task.input_data)
        elif task_type == "dilute":
            return await self._dilute(task.input_data)
        elif task_type == "mix":
            return await self._mix(task.input_data)
        else:
            return {"error": f"Unknown task type: {task_type}"}
    
    async def _transfer(self, data: Dict[str, Any]) -> Dict[str, Any]:
        source = data.get("source")
        destination = data.get("destination")
        volume_ul = data.get("volume_ul", 100)
        return {"source": source, "destination": destination, "volume_ul": volume_ul, "status": "completed"}
    
    async def _dilute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        sample = data.get("sample")
        dilution_factor = data.get("dilution_factor", 10)
        return {"sample": sample, "dilution_factor": dilution_factor, "status": "completed"}
    
    async def _mix(self, data: Dict[str, Any]) -> Dict[str, Any]:
        well = data.get("well")
        cycles = data.get("cycles", 3)
        return {"well": well, "cycles": cycles, "status": "completed"}


class BioreactorAgent(BaseScientificAgent):
    """Controls bioreactors for cell culture and fermentation."""
    def __init__(self):
        super().__init__("bioreactor_agent", "Bioreactor Agent", "Controls bioreactors for cultivation and fermentation")
        self.reactors: Dict[str, Any] = {}
    
    async def execute_task(self, task: ScientificTask) -> Dict[str, Any]:
        task_type = task.task_type
        if task_type == "start_culture":
            return await self._start_culture(task.input_data)
        elif task_type == "feed":
            return await self._feed(task.input_data)
        elif task_type == "sample":
            return await self._sample(task.input_data)
        elif task_type == "harvest":
            return await self._harvest(task.input_data)
        else:
            return {"error": f"Unknown task type: {task_type}"}
    
    async def _start_culture(self, data: Dict[str, Any]) -> Dict[str, Any]:
        reactor_id = data.get("reactor_id")
        organism = data.get("organism")
        medium = data.get("medium")
        return {"reactor_id": reactor_id, "organism": organism, "medium": medium, "status": "started"}
    
    async def _feed(self, data: Dict[str, Any]) -> Dict[str, Any]:
        reactor_id = data.get("reactor_id")
        feed_composition = data.get("feed_composition", {})
        return {"reactor_id": reactor_id, "fed": True}
    
    async def _sample(self, data: Dict[str, Any]) -> Dict[str, Any]:
        reactor_id = data.get("reactor_id")
        sample_volume_ml = data.get("sample_volume_ml", 1.0)
        return {"reactor_id": reactor_id, "sample_id": str(uuid4()), "volume_ml": sample_volume_ml}
    
    async def _harvest(self, data: Dict[str, Any]) -> Dict[str, Any]:
        reactor_id = data.get("reactor_id")
        return {"reactor_id": reactor_id, "harvest_id": str(uuid4()), "status": "harvested"}


class MicroscopyAgent(BaseScientificAgent):
    """Controls microscopes for imaging."""
    def __init__(self):
        super().__init__("microscopy_agent", "Microscopy Agent", "Controls microscopes for imaging and analysis")
    
    async def execute_task(self, task: ScientificTask) -> Dict[str, Any]:
        task_type = task.task_type
        if task_type == "capture_image":
            return await self._capture_image(task.input_data)
        elif task_type == "timelapse":
            return await self._timelapse(task.input_data)
        elif task_type == "z_stack":
            return await self._z_stack(task.input_data)
        else:
            return {"error": f"Unknown task type: {task_type}"}
    
    async def _capture_image(self, data: Dict[str, Any]) -> Dict[str, Any]:
        position = data.get("position")
        magnification = data.get("magnification", "10x")
        channel = data.get("channel", "brightfield")
        return {"image_id": str(uuid4()), "position": position, "magnification": magnification, "channel": channel}
    
    async def _timelapse(self, data: Dict[str, Any]) -> Dict[str, Any]:
        duration_hours = data.get("duration_hours", 24)
        interval_minutes = data.get("interval_minutes", 10)
        return {"timelapse_id": str(uuid4()), "duration_hours": duration_hours, "interval_minutes": interval_minutes}
    
    async def _z_stack(self, data: Dict[str, Any]) -> Dict[str, Any]:
        z_range_um = data.get("z_range_um", 50)
        step_size_um = data.get("step_size_um", 1)
        return {"zstack_id": str(uuid4()), "z_range_um": z_range_um, "step_size_um": step_size_um, "slices": z_range_um // step_size_um}


LAB_AGENTS = {
    "incubator": IncubatorAgent,
    "pipettor": PipettorAgent,
    "bioreactor": BioreactorAgent,
    "microscopy": MicroscopyAgent,
}

def get_lab_agent(agent_type: str) -> BaseScientificAgent:
    if agent_type not in LAB_AGENTS:
        raise ValueError(f"Unknown lab agent type: {agent_type}")
    return LAB_AGENTS[agent_type]()
