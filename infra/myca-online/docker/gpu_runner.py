#!/usr/bin/env python3
"""
GPU Job Runner for MYCA
Executes GPU workloads and logs results
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime

# Configuration
LOG_DIR = os.getenv("LOG_DIR", "/logs")
LOG_FILE = os.path.join(LOG_DIR, "gpu_runner.jsonl")


def log_event(event_type: str, data: dict):
    """Write event to JSON log"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": "INFO",
        "message": f"GPU event: {event_type}",
        "data": data
    }
    
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    print(json.dumps(log_entry))


def check_gpu():
    """Check GPU availability"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            gpus = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) == 3:
                        gpus.append({
                            "name": parts[0],
                            "memory_total_mb": int(parts[1]),
                            "memory_free_mb": int(parts[2])
                        })
            
            log_event("gpu_detected", {"gpus": gpus})
            return gpus
        else:
            log_event("gpu_check_failed", {"error": result.stderr})
            return []
    except Exception as e:
        log_event("gpu_check_error", {"error": str(e)})
        return []


def run_cuda_test():
    """Run CUDA test to validate GPU"""
    try:
        # Simple CUDA device query
        result = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            log_event("cuda_test_passed", {"output": result.stdout.strip()})
            return True
        else:
            log_event("cuda_test_failed", {"error": result.stderr})
            return False
    except Exception as e:
        log_event("cuda_test_error", {"error": str(e)})
        return False


def run_sample_job():
    """Run a sample GPU job (placeholder)"""
    log_event("sample_job_start", {"job_type": "vector_addition"})
    
    try:
        import numpy as np
        
        # Simulate GPU workload (this would use cupy/torch in real scenario)
        size = 10000000
        a = np.random.rand(size)
        b = np.random.rand(size)
        
        start = time.time()
        c = a + b
        duration = time.time() - start
        
        log_event("sample_job_complete", {
            "job_type": "vector_addition",
            "size": size,
            "duration_seconds": duration
        })
        
        return True
    except Exception as e:
        log_event("sample_job_error", {"error": str(e)})
        return False


def main():
    """Entry point"""
    log_event("gpu_runner_start", {"log_file": LOG_FILE})
    
    # Check GPU availability
    gpus = check_gpu()
    
    if not gpus:
        log_event("no_gpu_detected", {"message": "GPU runner will idle"})
        # Keep container running for manual jobs
        while True:
            time.sleep(60)
        return
    
    # Run CUDA test
    if run_cuda_test():
        log_event("gpu_validation_passed", {"gpus": len(gpus)})
    else:
        log_event("gpu_validation_failed", {})
    
    # Run sample job
    run_sample_job()
    
    # Keep running and listen for job requests (placeholder)
    log_event("gpu_runner_ready", {"message": "Waiting for job requests"})
    
    while True:
        time.sleep(60)
        # In production: poll Redis queue for GPU jobs


if __name__ == "__main__":
    main()
