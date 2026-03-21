"""
Model Compression Agent

Handles model optimization for deployment:
- Quantization (GPTQ, AWQ, GGUF, INT8, INT4)
- Pruning (structured, unstructured)
- Knowledge distillation
- ONNX export and optimization
- TensorRT compilation
- Edge deployment targeting (ESP32, Jetson, mobile)

Provides task-based interface for compression workflows.
"""

import logging
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

QUANTIZATION_METHODS = {
    "gptq": {"bits": [4, 8], "desc": "GPTQ post-training quantization for LLMs"},
    "awq": {"bits": [4], "desc": "Activation-aware Weight Quantization"},
    "gguf": {"bits": [2, 3, 4, 5, 6, 8], "desc": "GGML Unified Format for llama.cpp"},
    "int8": {"bits": [8], "desc": "Dynamic INT8 quantization (PyTorch/ONNX)"},
    "int4": {"bits": [4], "desc": "INT4 weight-only quantization"},
    "fp16": {"bits": [16], "desc": "Half-precision float"},
    "bf16": {"bits": [16], "desc": "Brain floating point 16"},
}

EDGE_TARGETS = {
    "esp32": {"max_model_mb": 4, "framework": "tflite_micro", "precision": "int8"},
    "jetson_nano": {"max_model_mb": 2048, "framework": "tensorrt", "precision": "fp16"},
    "jetson_orin": {"max_model_mb": 16384, "framework": "tensorrt", "precision": "fp16"},
    "mobile_ios": {"max_model_mb": 200, "framework": "coreml", "precision": "fp16"},
    "mobile_android": {"max_model_mb": 200, "framework": "tflite", "precision": "fp16"},
    "raspberry_pi": {"max_model_mb": 512, "framework": "onnx", "precision": "int8"},
}


class ModelCompressionAgent(BaseAgent):
    """Agent for model compression and edge deployment."""

    def __init__(
        self,
        agent_id: str = "model-compression",
        name: str = "Model Compression Agent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities = [
            "quantize",
            "prune",
            "distill",
            "export_onnx",
            "target_edge",
            "estimate_size",
        ]

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        t = task.get("type", "")

        if t == "quantize":
            return await self._quantize(task)
        elif t == "estimate_size":
            return await self._estimate_size(task)
        elif t == "list_methods":
            return self._list_methods()
        elif t == "target_edge":
            return self._target_edge(task)
        elif t == "export_onnx":
            return await self._export_onnx(task)
        elif t == "prune":
            return await self._prune(task)

        return {"status": "error", "message": f"Unknown task type: {t}"}

    async def _quantize(self, task: Dict[str, Any]) -> Dict[str, Any]:
        model = task.get("model", "")
        method = task.get("method", "gguf")
        bits = task.get("bits", 4)
        info = QUANTIZATION_METHODS.get(method, {})

        return {
            "status": "success",
            "model": model,
            "method": method,
            "bits": bits,
            "description": info.get("desc", "Unknown method"),
            "command": self._build_command(model, method, bits),
        }

    def _build_command(self, model: str, method: str, bits: int) -> str:
        if method == "gguf":
            q_map = {2: "Q2_K", 3: "Q3_K_M", 4: "Q4_K_M", 5: "Q5_K_M", 6: "Q6_K", 8: "Q8_0"}
            q = q_map.get(bits, "Q4_K_M")
            return f"python llama.cpp/convert.py {model} --outtype f16 && ./quantize model-f16.gguf model-{q}.gguf {q}"
        elif method == "gptq":
            return f"python -m auto_gptq {model} --bits {bits} --group_size 128"
        elif method == "awq":
            return f"python -m awq.entry --model_path {model} --w_bit {bits} --q_group_size 128"
        return f"# {method} quantization for {model} at {bits}-bit"

    async def _estimate_size(self, task: Dict[str, Any]) -> Dict[str, Any]:
        params_b = task.get("parameters_billion", 7)
        bits = task.get("bits", 4)
        size_gb = (params_b * bits) / 8
        return {
            "status": "success",
            "parameters_billion": params_b,
            "bits": bits,
            "estimated_size_gb": round(size_gb, 2),
            "estimated_size_mb": round(size_gb * 1024, 0),
            "estimated_vram_gb": round(size_gb * 1.2, 2),
        }

    def _list_methods(self) -> Dict[str, Any]:
        return {"status": "success", "methods": QUANTIZATION_METHODS, "edge_targets": EDGE_TARGETS}

    def _target_edge(self, task: Dict[str, Any]) -> Dict[str, Any]:
        target = task.get("target", "esp32")
        model_size_mb = task.get("model_size_mb", 0)
        spec = EDGE_TARGETS.get(target, {})
        fits = model_size_mb <= spec.get("max_model_mb", 0) if model_size_mb else None
        return {
            "status": "success",
            "target": target,
            "spec": spec,
            "model_size_mb": model_size_mb,
            "fits": fits,
            "recommendation": (
                f"Use {spec.get('framework')} with {spec.get('precision')} precision"
                if spec
                else "Unknown target"
            ),
        }

    async def _export_onnx(self, task: Dict[str, Any]) -> Dict[str, Any]:
        model = task.get("model", "")
        return {
            "status": "success",
            "model": model,
            "command": f"python -c \"from optimum.exporters.onnx import main_export; main_export('{model}', 'onnx_output/')\"",
            "optimize_command": "python -m onnxruntime.transformers.optimizer --input onnx_output/model.onnx --output onnx_output/model_opt.onnx",
        }

    async def _prune(self, task: Dict[str, Any]) -> Dict[str, Any]:
        model = task.get("model", "")
        sparsity = task.get("sparsity", 0.5)
        method = task.get("pruning_method", "magnitude")
        return {
            "status": "success",
            "model": model,
            "sparsity": sparsity,
            "method": method,
            "note": f"Apply {method} pruning at {sparsity*100}% sparsity using torch.nn.utils.prune",
        }
