"""
DNA Data Storage System
Encode, store, and retrieve data using DNA synthesis
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
from enum import Enum
import uuid
import asyncio
import logging
import base64

logger = logging.getLogger(__name__)


class DNAJobType(str, Enum):
    ENCODE = "encode"
    DECODE = "decode"


class DNAJobStatus(str, Enum):
    PENDING = "pending"
    SYNTHESIZING = "synthesizing"
    SEQUENCING = "sequencing"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ErrorCorrectionLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DNAStorageJob(BaseModel):
    id: str
    type: DNAJobType
    status: DNAJobStatus
    dataSize: int
    dnaLength: Optional[int] = None
    redundancy: int = 3
    errorCorrectionLevel: ErrorCorrectionLevel = ErrorCorrectionLevel.MEDIUM
    createdAt: str
    completedAt: Optional[str] = None


class StoredData(BaseModel):
    id: str
    name: str
    size: int
    dnaSequenceLength: int
    redundancy: int
    storedAt: str
    expiresAt: Optional[str] = None
    verified: bool = False
    retrievalCount: int = 0


class EncodingResult(BaseModel):
    jobId: str
    dataId: str
    dnaSequence: str
    checksum: str
    redundancy: int
    compressionRatio: float


class DecodingResult(BaseModel):
    jobId: str
    dataId: str
    data: str
    errorsCorrected: int
    confidence: float


class StorageCapacity(BaseModel):
    totalCapacity: int  # bytes
    usedCapacity: int
    availableCapacity: int
    maxFileSize: int
    synthesisQueueLength: int
    sequencingQueueLength: int


class DNAStorageSystem:
    """
    DNA-based data storage system.
    Encodes data to DNA sequences and retrieves via sequencing.
    """
    
    def __init__(self):
        self.jobs: Dict[str, DNAStorageJob] = {}
        self.stored_data: Dict[str, StoredData] = {}
        self._init_sample_data()
    
    def _init_sample_data(self):
        """Initialize with sample stored data"""
        data = [
            StoredData(
                id="dna-001",
                name="Genome Backup v3",
                size=1024 * 1024 * 50,  # 50 MB
                dnaSequenceLength=200000000,
                redundancy=3,
                storedAt="2026-01-15T10:00:00Z",
                verified=True,
                retrievalCount=2
            ),
            StoredData(
                id="dna-002",
                name="Research Dataset Alpha",
                size=1024 * 1024 * 120,  # 120 MB
                dnaSequenceLength=480000000,
                redundancy=3,
                storedAt="2026-01-20T14:00:00Z",
                verified=True,
                retrievalCount=5
            ),
            StoredData(
                id="dna-003",
                name="Protocol Archive",
                size=1024 * 1024 * 8,  # 8 MB
                dnaSequenceLength=32000000,
                redundancy=5,
                storedAt="2026-02-01T09:00:00Z",
                verified=False,
                retrievalCount=0
            ),
        ]
        for d in data:
            self.stored_data[d.id] = d
    
    async def get_capacity(self) -> StorageCapacity:
        """Get storage capacity information"""
        total = 1024 * 1024 * 1024  # 1 GB
        used = sum(d.size for d in self.stored_data.values())
        
        return StorageCapacity(
            totalCapacity=total,
            usedCapacity=used,
            availableCapacity=total - used,
            maxFileSize=1024 * 1024 * 500,  # 500 MB
            synthesisQueueLength=len([j for j in self.jobs.values() if j.status == DNAJobStatus.SYNTHESIZING]),
            sequencingQueueLength=len([j for j in self.jobs.values() if j.status == DNAJobStatus.SEQUENCING])
        )
    
    async def list_stored_data(self) -> List[StoredData]:
        """List all stored data"""
        return list(self.stored_data.values())
    
    async def get_stored_data(self, data_id: str) -> Optional[StoredData]:
        """Get stored data by ID"""
        return self.stored_data.get(data_id)
    
    async def encode_data(
        self,
        data: str,
        name: str,
        redundancy: int = 3,
        error_correction: str = "medium"
    ) -> DNAStorageJob:
        """Encode data to DNA and store"""
        job_id = f"dna-job-{uuid.uuid4().hex[:8]}"
        
        # Calculate data size (base64 encoded)
        data_size = len(data.encode('utf-8'))
        
        job = DNAStorageJob(
            id=job_id,
            type=DNAJobType.ENCODE,
            status=DNAJobStatus.PENDING,
            dataSize=data_size,
            redundancy=redundancy,
            errorCorrectionLevel=ErrorCorrectionLevel(error_correction),
            createdAt=datetime.utcnow().isoformat()
        )
        
        self.jobs[job_id] = job
        
        # Start async processing
        asyncio.create_task(self._process_encode(job_id, data, name))
        
        return job
    
    async def _process_encode(self, job_id: str, data: str, name: str):
        """Process encoding job"""
        job = self.jobs[job_id]
        
        # Simulate synthesis stages
        job.status = DNAJobStatus.SYNTHESIZING
        await asyncio.sleep(2)  # Simulate synthesis time
        
        job.status = DNAJobStatus.PROCESSING
        await asyncio.sleep(1)
        
        # Create stored data entry
        data_id = f"dna-{uuid.uuid4().hex[:6]}"
        dna_length = job.dataSize * 4 * job.redundancy  # Approximate DNA length
        
        stored = StoredData(
            id=data_id,
            name=name,
            size=job.dataSize,
            dnaSequenceLength=dna_length,
            redundancy=job.redundancy,
            storedAt=datetime.utcnow().isoformat(),
            verified=False,
            retrievalCount=0
        )
        
        self.stored_data[data_id] = stored
        
        job.status = DNAJobStatus.COMPLETED
        job.completedAt = datetime.utcnow().isoformat()
        job.dnaLength = dna_length
    
    async def get_encoding_result(self, job_id: str) -> Optional[EncodingResult]:
        """Get encoding result for a completed job"""
        job = self.jobs.get(job_id)
        if not job or job.status != DNAJobStatus.COMPLETED:
            return None
        
        # Find the stored data for this job
        data_id = None
        for did, data in self.stored_data.items():
            if data.size == job.dataSize:
                data_id = did
                break
        
        if not data_id:
            data_id = f"dna-{uuid.uuid4().hex[:6]}"
        
        return EncodingResult(
            jobId=job_id,
            dataId=data_id,
            dnaSequence=f"ATCG{'ATCG' * 100}...",  # Truncated for display
            checksum=f"sha256:{uuid.uuid4().hex[:16]}",
            redundancy=job.redundancy,
            compressionRatio=0.25  # DNA encoding typically expands data
        )
    
    async def decode_data(self, data_id: str) -> DNAStorageJob:
        """Retrieve and decode stored data"""
        if data_id not in self.stored_data:
            raise ValueError(f"Data {data_id} not found")
        
        stored = self.stored_data[data_id]
        job_id = f"dna-job-{uuid.uuid4().hex[:8]}"
        
        job = DNAStorageJob(
            id=job_id,
            type=DNAJobType.DECODE,
            status=DNAJobStatus.PENDING,
            dataSize=stored.size,
            dnaLength=stored.dnaSequenceLength,
            redundancy=stored.redundancy,
            createdAt=datetime.utcnow().isoformat()
        )
        
        self.jobs[job_id] = job
        
        # Start async processing
        asyncio.create_task(self._process_decode(job_id, data_id))
        
        return job
    
    async def _process_decode(self, job_id: str, data_id: str):
        """Process decoding job"""
        job = self.jobs[job_id]
        stored = self.stored_data[data_id]
        
        # Simulate sequencing stages
        job.status = DNAJobStatus.SEQUENCING
        await asyncio.sleep(2)  # Simulate sequencing time
        
        job.status = DNAJobStatus.PROCESSING
        await asyncio.sleep(1)
        
        job.status = DNAJobStatus.COMPLETED
        job.completedAt = datetime.utcnow().isoformat()
        
        # Update retrieval count
        stored.retrievalCount += 1
    
    async def get_decoding_result(self, job_id: str) -> Optional[DecodingResult]:
        """Get decoding result for a completed job"""
        job = self.jobs.get(job_id)
        if not job or job.status != DNAJobStatus.COMPLETED:
            return None
        
        return DecodingResult(
            jobId=job_id,
            dataId=f"dna-{uuid.uuid4().hex[:6]}",
            data="[Decoded data content]",
            errorsCorrected=3,
            confidence=0.9997
        )
    
    async def get_job(self, job_id: str) -> Optional[DNAStorageJob]:
        """Get a job by ID"""
        return self.jobs.get(job_id)
    
    async def list_jobs(self, job_type: Optional[str] = None) -> List[DNAStorageJob]:
        """List all jobs, optionally filtered by type"""
        jobs = list(self.jobs.values())
        if job_type:
            jobs = [j for j in jobs if j.type.value == job_type]
        return jobs
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job"""
        job = self.jobs.get(job_id)
        if not job or job.status not in [DNAJobStatus.PENDING, DNAJobStatus.SYNTHESIZING]:
            return False
        
        job.status = DNAJobStatus.FAILED
        return True
    
    async def delete_data(self, data_id: str) -> bool:
        """Delete stored data"""
        if data_id in self.stored_data:
            del self.stored_data[data_id]
            return True
        return False
    
    async def verify_data(self, data_id: str) -> Dict[str, Any]:
        """Verify stored data integrity"""
        if data_id not in self.stored_data:
            raise ValueError(f"Data {data_id} not found")
        
        stored = self.stored_data[data_id]
        stored.verified = True
        
        return {
            "valid": True,
            "errors": 0,
            "dataId": data_id,
            "verifiedAt": datetime.utcnow().isoformat()
        }
    
    async def duplicate_data(self, data_id: str, copies: int) -> Dict[str, Any]:
        """Create additional copies of stored data"""
        if data_id not in self.stored_data:
            raise ValueError(f"Data {data_id} not found")
        
        stored = self.stored_data[data_id]
        stored.redundancy += copies
        
        return {
            "dataId": data_id,
            "newRedundancy": stored.redundancy,
            "copiesAdded": copies
        }


# Global instance
dna_storage_system = DNAStorageSystem()
