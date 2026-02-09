"""
Bio-Computing API Router
REST endpoints for MycoBrain production and DNA storage
"""

from fastapi import APIRouter, HTTPException, Body, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

router = APIRouter()

# Import systems
from mycosoft_mas.bio.mycobrain_production import mycobrain_system
from mycosoft_mas.bio.dna_storage import dna_storage_system


# --- MycoBrain API ---

class ComputeJobRequest(BaseModel):
    mode: str
    input: Dict[str, Any]
    priority: str = "normal"


class GraphSolveRequest(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    algorithm: str = "shortest_path"


class PatternRecognitionRequest(BaseModel):
    signal: List[List[float]]
    patternType: str = "unknown"


class OptimizationRequest(BaseModel):
    objective: str
    constraints: List[Any]
    variables: List[Any]


class AnalogComputeRequest(BaseModel):
    inputMatrix: List[List[float]]
    operation: str


# MycoBrain endpoints

@router.get("/mycobrain/status")
async def get_mycobrain_status():
    status = await mycobrain_system.get_status()
    return status.dict()


@router.get("/mycobrain/metrics")
async def get_mycobrain_metrics():
    metrics = await mycobrain_system.get_metrics()
    return metrics.dict()


@router.get("/mycobrain/network")
async def get_network_stats():
    stats = await mycobrain_system.get_network_stats()
    return stats.dict()


@router.get("/mycobrain/jobs")
async def list_mycobrain_jobs(status: Optional[str] = None, limit: int = 50):
    jobs = await mycobrain_system.list_jobs(status, limit)
    return {"jobs": [j.dict() for j in jobs]}


@router.post("/mycobrain/jobs")
async def submit_job(data: ComputeJobRequest):
    job = await mycobrain_system.submit_job(data.mode, data.input, data.priority)
    return job.dict()


@router.get("/mycobrain/jobs/{job_id}")
async def get_mycobrain_job(job_id: str):
    job = await mycobrain_system.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.dict()


@router.delete("/mycobrain/jobs/{job_id}")
async def cancel_mycobrain_job(job_id: str):
    success = await mycobrain_system.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel job")
    return {"cancelled": True}


@router.get("/mycobrain/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    result = await mycobrain_system.get_result(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result.dict()


@router.post("/mycobrain/compute/graph")
async def solve_graph(data: GraphSolveRequest):
    job = await mycobrain_system.solve_graph(data.nodes, data.edges, data.algorithm)
    return job.dict()


@router.post("/mycobrain/compute/pattern")
async def recognize_pattern(data: PatternRecognitionRequest):
    job = await mycobrain_system.recognize_pattern(data.signal, data.patternType)
    return job.dict()


@router.post("/mycobrain/compute/optimize")
async def optimize(data: OptimizationRequest):
    job = await mycobrain_system.optimize(data.objective, data.constraints, data.variables)
    return job.dict()


@router.post("/mycobrain/compute/analog")
async def analog_compute(data: AnalogComputeRequest):
    job = await mycobrain_system.analog_compute(data.inputMatrix, data.operation)
    return job.dict()


@router.post("/mycobrain/calibrate")
async def calibrate():
    result = await mycobrain_system.calibrate()
    return result


@router.get("/mycobrain/diagnostics")
async def run_diagnostics():
    result = await mycobrain_system.run_diagnostics()
    return result


@router.post("/mycobrain/jobs/{job_id}/validate")
async def validate_job_result(job_id: str):
    result = await mycobrain_system.validate_result(job_id)
    return result.dict()


# --- DNA Storage API ---

class EncodeDataRequest(BaseModel):
    data: str
    name: str
    redundancy: int = 3
    errorCorrection: str = "medium"


@router.get("/dna-storage/capacity")
async def get_storage_capacity():
    capacity = await dna_storage_system.get_capacity()
    return capacity.dict()


@router.get("/dna-storage/data")
async def list_stored_data():
    data = await dna_storage_system.list_stored_data()
    return {"data": [d.dict() for d in data]}


@router.get("/dna-storage/data/{data_id}")
async def get_stored_data(data_id: str):
    data = await dna_storage_system.get_stored_data(data_id)
    if not data:
        raise HTTPException(status_code=404, detail="Data not found")
    return data.dict()


@router.post("/dna-storage/encode")
async def encode_data(request: EncodeDataRequest):
    job = await dna_storage_system.encode_data(
        request.data,
        request.name,
        request.redundancy,
        request.errorCorrection
    )
    return job.dict()


@router.get("/dna-storage/encode/{job_id}/result")
async def get_encoding_result(job_id: str):
    result = await dna_storage_system.get_encoding_result(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Encoding result not found")
    return result.dict()


@router.post("/dna-storage/decode/{data_id}")
async def decode_data(data_id: str):
    try:
        job = await dna_storage_system.decode_data(data_id)
        return job.dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/dna-storage/decode/{job_id}/result")
async def get_decoding_result(job_id: str):
    result = await dna_storage_system.get_decoding_result(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Decoding result not found")
    return result.dict()


@router.get("/dna-storage/jobs")
async def list_dna_jobs(job_type: Optional[str] = None):
    jobs = await dna_storage_system.list_jobs(job_type)
    return {"jobs": [j.dict() for j in jobs]}


@router.get("/dna-storage/jobs/{job_id}")
async def get_dna_job(job_id: str):
    job = await dna_storage_system.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.dict()


@router.delete("/dna-storage/jobs/{job_id}")
async def cancel_dna_job(job_id: str):
    success = await dna_storage_system.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel job")
    return {"cancelled": True}


@router.delete("/dna-storage/data/{data_id}")
async def delete_stored_data(data_id: str):
    success = await dna_storage_system.delete_data(data_id)
    if not success:
        raise HTTPException(status_code=404, detail="Data not found")
    return {"deleted": True}


@router.post("/dna-storage/data/{data_id}/verify")
async def verify_stored_data(data_id: str):
    try:
        result = await dna_storage_system.verify_data(data_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/dna-storage/data/{data_id}/duplicate")
async def duplicate_data(data_id: str, copies: int = Body(1)):
    try:
        result = await dna_storage_system.duplicate_data(data_id, copies)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
