"""
KVTC Calibration Pipeline — orchestrates model inventory, KV capture,
PCA fitting, bit allocation, and artifact persistence.

Pipeline flow:
    1. inventory.inventory_model()       — assess architecture compatibility
    2. dataset_builder.build_dataset()   — prepare calibration sequences
    3. capture.capture_kv_tensors()      — prefill + hook attention for K/V
    4. pca_fitting.fit_pca_per_layer()   — PCA projection matrices
    5. bit_allocation.allocate_bits()    — DP optimal bit budget
    6. artifact_writer.write_artifact()  — persist + hash artifacts

Date: 2026-03-21
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Optional
from uuid import UUID

from mycosoft_mas.serving.schemas import (
    CalibrationRequest,
    CalibrationResponse,
    CompressionTarget,
    KvtcArtifact,
    KvtcArtifactCreate,
)

from .artifact_writer import write_artifact
from .bit_allocation import allocate_bits
from .capture import capture_kv_tensors
from .dataset_builder import build_calibration_dataset
from .inventory import inventory_model
from .pca_fitting import fit_pca_per_layer

logger = logging.getLogger(__name__)

__all__ = [
    "run_calibration_pipeline",
    "inventory_model",
    "build_calibration_dataset",
    "capture_kv_tensors",
    "fit_pca_per_layer",
    "allocate_bits",
    "write_artifact",
]


async def run_calibration_pipeline(
    request: CalibrationRequest,
    model_path: Optional[str] = None,
    storage_base: str = "/opt/mycosoft/artifacts/kvtc",
) -> CalibrationResponse:
    """Run the full KVTC calibration pipeline.

    Args:
        request: Calibration parameters (model_build_id, compression_target, etc.)
        model_path: Local path to the model checkpoint. If None, resolves from registry.
        storage_base: Base path for artifact storage.

    Returns:
        CalibrationResponse with artifact references and summary.

    Raises:
        ValueError: If model is not KVTC-eligible.
    """
    model_id = str(request.model_build_id)
    logger.info(
        "Starting KVTC calibration for model=%s target=%s",
        model_id,
        request.compression_target.value,
    )

    # Step 1: Inventory
    inv = inventory_model(model_build_id=model_id, model_path=model_path or "")
    if not inv.kvtc_eligible:
        raise ValueError(
            f"Model {model_id} is not KVTC-eligible: {inv.architecture_type.value}. "
            f"Notes: {inv.notes}"
        )

    if inv.has_mamba_layers and not request.attention_only:
        logger.warning(
            "Model has Mamba layers — forcing attention_only=True to protect recurrent state"
        )
        request.attention_only = True

    logger.info(
        "Inventory: arch=%s kvtc_mode=%s layers=%d kv_heads=%d",
        inv.architecture_type.value,
        inv.kvtc_mode,
        inv.num_layers,
        inv.num_kv_heads,
    )

    # Step 2: Build calibration dataset
    dataset = await build_calibration_dataset(
        profile=request.dataset_profile,
        num_tokens=request.calibration_tokens,
    )
    dataset_hash = hashlib.sha256(
        str(dataset.get("sequences", [])).encode()
    ).hexdigest()[:16]

    # Step 3: Capture KV tensors
    kv_tensors = await capture_kv_tensors(
        model_path=model_path or "",
        sequences=dataset["sequences"],
        sink_tokens=4,
        attention_only=request.attention_only,
    )

    # Step 4: PCA fitting
    pca_result = fit_pca_per_layer(
        kv_tensors=kv_tensors,
        rank_cap=request.pca_rank_cap,
    )

    # Step 5: Bit allocation
    bit_result = allocate_bits(
        pca_result=pca_result,
        compression_target=request.compression_target,
        num_layers=inv.num_layers,
        head_dim=inv.head_dim,
    )

    # Step 6: Write artifacts
    artifact = await write_artifact(
        model_build_id=model_id,
        compression_target=request.compression_target,
        pca_result=pca_result,
        bit_result=bit_result,
        dataset_hash=dataset_hash,
        storage_base=storage_base,
        attention_only=request.attention_only,
        mla_latent_mode=inv.mla_latent,
        rope_undo_required=inv.rope_type is not None,
    )

    logger.info(
        "Calibration complete: artifact=%s hash=%s",
        artifact.kvtc_artifact_id,
        artifact.artifact_hash,
    )

    return CalibrationResponse(
        kvtc_artifact_id=artifact.kvtc_artifact_id,
        model_build_id=request.model_build_id,
        compression_target=request.compression_target,
        vk_uri=artifact.vk_uri,
        vv_uri=artifact.vv_uri,
        artifact_hash=artifact.artifact_hash,
        calibration_summary={
            "architecture": inv.architecture_type.value,
            "kvtc_mode": inv.kvtc_mode,
            "num_layers": inv.num_layers,
            "pca_rank": pca_result.get("effective_rank"),
            "key_bits": bit_result.get("key_bitplan"),
            "value_bits": bit_result.get("value_bitplan"),
            "dataset_hash": dataset_hash,
            "calibration_tokens": request.calibration_tokens,
        },
    )
