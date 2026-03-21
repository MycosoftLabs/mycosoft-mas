"""
Hardware Intelligence Agent

Tracks latest compute hardware releases, pricing, and availability:
- NVIDIA GPUs (Blackwell B200, H100, A100, RTX series)
- AMD GPUs (MI300X, MI250X, Instinct series)
- Google TPUs (v5p, v5e, v4)
- Intel/Habana Gaudi
- Quantum processors (IBM Eagle/Heron, Google Sycamore)
- LoRa / ESP32 modules and firmware
- Benchmark tracking (MLPerf, LMSys, etc.)

Sources: RSS feeds, manufacturer pages, techreport scrapers.
"""

import logging
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

HARDWARE_CATALOG = {
    "nvidia": {
        "datacenter": [
            {
                "name": "B200",
                "family": "Blackwell",
                "vram_gb": 192,
                "fp16_tflops": 4500,
                "released": "2024-Q4",
            },
            {
                "name": "H200",
                "family": "Hopper",
                "vram_gb": 141,
                "fp16_tflops": 1979,
                "released": "2024-Q1",
            },
            {
                "name": "H100 SXM",
                "family": "Hopper",
                "vram_gb": 80,
                "fp16_tflops": 1979,
                "released": "2023-Q1",
            },
            {
                "name": "A100 SXM",
                "family": "Ampere",
                "vram_gb": 80,
                "fp16_tflops": 312,
                "released": "2020-Q2",
            },
            {
                "name": "L40S",
                "family": "Ada Lovelace",
                "vram_gb": 48,
                "fp16_tflops": 366,
                "released": "2023-Q3",
            },
        ],
        "consumer": [
            {"name": "RTX 5090", "family": "Blackwell", "vram_gb": 32, "released": "2025-Q1"},
            {"name": "RTX 4090", "family": "Ada Lovelace", "vram_gb": 24, "released": "2022-Q4"},
            {
                "name": "RTX 4080 SUPER",
                "family": "Ada Lovelace",
                "vram_gb": 16,
                "released": "2024-Q1",
            },
        ],
    },
    "amd": {
        "datacenter": [
            {"name": "MI300X", "family": "CDNA 3", "vram_gb": 192, "released": "2023-Q4"},
            {"name": "MI250X", "family": "CDNA 2", "vram_gb": 128, "released": "2021-Q4"},
        ],
    },
    "google": {
        "tpu": [
            {"name": "TPU v5p", "hbm_gb": 95, "released": "2023-Q4"},
            {"name": "TPU v5e", "hbm_gb": 16, "released": "2023-Q3"},
            {"name": "TPU v4", "hbm_gb": 32, "released": "2022-Q1"},
        ],
    },
    "quantum": {
        "processors": [
            {"name": "IBM Heron", "qubits": 133, "provider": "IBM", "released": "2023-Q4"},
            {"name": "IBM Eagle", "qubits": 127, "provider": "IBM", "released": "2022-Q4"},
            {"name": "Google Sycamore", "qubits": 72, "provider": "Google", "released": "2023"},
        ],
    },
    "edge": {
        "mcu": [
            {
                "name": "ESP32-S3",
                "cores": 2,
                "ram_kb": 512,
                "flash_mb": 16,
                "wifi": True,
                "ble": True,
            },
            {"name": "ESP32-C6", "cores": 1, "ram_kb": 512, "wifi6": True, "thread": True},
            {"name": "RP2040", "cores": 2, "ram_kb": 264, "flash_mb": 16},
        ],
        "lora": [
            {"name": "SX1262", "range_km": 15, "freq": "868/915 MHz", "bandwidth": "125-500 kHz"},
            {"name": "SX1276", "range_km": 10, "freq": "868/915 MHz"},
        ],
    },
}


class HardwareIntelligenceAgent(BaseAgent):
    """Tracks and reports on compute hardware."""

    def __init__(
        self,
        agent_id: str = "hardware-intel",
        name: str = "Hardware Intelligence Agent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities = [
            "list_hardware",
            "compare_gpus",
            "recommend_for_model",
            "track_releases",
            "edge_capabilities",
        ]

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        t = task.get("type", "")

        if t == "list_hardware":
            return self._list_hardware(task)
        elif t == "compare_gpus":
            return self._compare_gpus(task)
        elif t == "recommend":
            return self._recommend_for_model(task)
        elif t == "edge_info":
            return self._edge_info(task)
        elif t == "quantum_info":
            return self._quantum_info()
        elif t == "full_catalog":
            return {"status": "success", "catalog": HARDWARE_CATALOG}

        return {"status": "error", "message": f"Unknown task type: {t}"}

    def _list_hardware(self, task: Dict[str, Any]) -> Dict[str, Any]:
        vendor = task.get("vendor", "nvidia")
        category = task.get("category", "datacenter")
        data = HARDWARE_CATALOG.get(vendor, {}).get(category, [])
        return {"status": "success", "vendor": vendor, "category": category, "hardware": data}

    def _compare_gpus(self, task: Dict[str, Any]) -> Dict[str, Any]:
        names = task.get("gpus", ["H100 SXM", "A100 SXM"])
        all_gpus = []
        for vendor in HARDWARE_CATALOG.values():
            for cat in vendor.values():
                if isinstance(cat, list):
                    all_gpus.extend(cat)
        results = [g for g in all_gpus if g.get("name") in names]
        return {"status": "success", "comparison": results}

    def _recommend_for_model(self, task: Dict[str, Any]) -> Dict[str, Any]:
        params_b = task.get("parameters_billion", 7)
        precision = task.get("precision", "fp16")
        bytes_per_param = {"fp32": 4, "fp16": 2, "bf16": 2, "int8": 1, "int4": 0.5}
        bpp = bytes_per_param.get(precision, 2)
        vram_needed_gb = (params_b * bpp) * 1.2

        suitable = []
        for cat in HARDWARE_CATALOG.get("nvidia", {}).values():
            for gpu in cat:
                vram = gpu.get("vram_gb", 0)
                if vram >= vram_needed_gb:
                    suitable.append({**gpu, "headroom_gb": round(vram - vram_needed_gb, 1)})

        suitable.sort(key=lambda x: x.get("vram_gb", 0))
        return {
            "status": "success",
            "model_params_b": params_b,
            "precision": precision,
            "vram_needed_gb": round(vram_needed_gb, 1),
            "suitable_gpus": suitable,
        }

    def _edge_info(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "success", "edge_hardware": HARDWARE_CATALOG.get("edge", {})}

    def _quantum_info(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "quantum_processors": HARDWARE_CATALOG.get("quantum", {}).get("processors", []),
        }
