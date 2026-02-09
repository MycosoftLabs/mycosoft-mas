"""Create integrity_service.py"""
import os

content = '''"""
Integrity Service for MYCA
Created: February 4, 2026

Provides file integrity verification and tamper detection.
"""

import hashlib
import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class IntegrityStatus(Enum):
    VERIFIED = "verified"
    MODIFIED = "modified"
    MISSING = "missing"
    NEW = "new"
    ERROR = "error"


@dataclass
class FileIntegrityRecord:
    path: str
    sha256: str
    size: int
    modified_time: float
    last_verified: datetime = field(default_factory=datetime.now)
    status: IntegrityStatus = IntegrityStatus.VERIFIED


class IntegrityService:
    """Service for monitoring and verifying file integrity."""
    
    def __init__(self, baseline_path: str = "data/integrity_baseline.json"):
        self.baseline_path = baseline_path
        self.baseline: Dict[str, FileIntegrityRecord] = {}
        self._load_baseline()
        logger.info("IntegrityService initialized")
    
    def _load_baseline(self) -> None:
        """Load the integrity baseline from file."""
        if os.path.exists(self.baseline_path):
            try:
                with open(self.baseline_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for path, record in data.items():
                    self.baseline[path] = FileIntegrityRecord(
                        path=record['path'],
                        sha256=record['sha256'],
                        size=record['size'],
                        modified_time=record['modified_time'],
                        last_verified=datetime.fromisoformat(record.get('last_verified', datetime.now().isoformat())),
                        status=IntegrityStatus(record.get('status', 'verified'))
                    )
                logger.info(f"Loaded {len(self.baseline)} integrity records")
            except Exception as e:
                logger.error(f"Error loading baseline: {e}")
    
    def _save_baseline(self) -> None:
        """Save the integrity baseline to file."""
        os.makedirs(os.path.dirname(self.baseline_path), exist_ok=True)
        data = {}
        for path, record in self.baseline.items():
            data[path] = {
                'path': record.path,
                'sha256': record.sha256,
                'size': record.size,
                'modified_time': record.modified_time,
                'last_verified': record.last_verified.isoformat(),
                'status': record.status.value
            }
        with open(self.baseline_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    @staticmethod
    def compute_hash(filepath: str) -> Optional[str]:
        """Compute SHA256 hash of a file."""
        try:
            sha256 = hashlib.sha256()
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error computing hash for {filepath}: {e}")
            return None
    
    def add_file(self, filepath: str) -> Optional[FileIntegrityRecord]:
        """Add a file to the integrity baseline."""
        if not os.path.exists(filepath):
            return None
        
        file_hash = self.compute_hash(filepath)
        if not file_hash:
            return None
        
        stat = os.stat(filepath)
        record = FileIntegrityRecord(
            path=filepath,
            sha256=file_hash,
            size=stat.st_size,
            modified_time=stat.st_mtime,
            status=IntegrityStatus.VERIFIED
        )
        self.baseline[filepath] = record
        self._save_baseline()
        return record
    
    def verify_file(self, filepath: str) -> IntegrityStatus:
        """Verify a single file against the baseline."""
        if filepath not in self.baseline:
            if os.path.exists(filepath):
                return IntegrityStatus.NEW
            return IntegrityStatus.MISSING
        
        if not os.path.exists(filepath):
            return IntegrityStatus.MISSING
        
        record = self.baseline[filepath]
        current_hash = self.compute_hash(filepath)
        
        if current_hash is None:
            return IntegrityStatus.ERROR
        
        if current_hash != record.sha256:
            record.status = IntegrityStatus.MODIFIED
            record.last_verified = datetime.now()
            self._save_baseline()
            return IntegrityStatus.MODIFIED
        
        record.status = IntegrityStatus.VERIFIED
        record.last_verified = datetime.now()
        self._save_baseline()
        return IntegrityStatus.VERIFIED
    
    def verify_all(self) -> Dict[str, IntegrityStatus]:
        """Verify all files in the baseline."""
        results = {}
        for filepath in self.baseline:
            results[filepath] = self.verify_file(filepath)
        return results
    
    def scan_directory(self, directory: str, extensions: List[str] = None) -> List[str]:
        """Scan a directory for files to add to baseline."""
        extensions = extensions or ['.py', '.json', '.yaml', '.yml']
        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if any(filename.endswith(ext) for ext in extensions):
                    files.append(os.path.join(root, filename))
        return files
    
    def update_baseline(self, directory: str) -> Dict[str, str]:
        """Update the baseline with all files in a directory."""
        files = self.scan_directory(directory)
        results = {}
        for filepath in files:
            record = self.add_file(filepath)
            if record:
                results[filepath] = "added"
            else:
                results[filepath] = "failed"
        return results
    
    def get_modified_files(self) -> List[str]:
        """Get list of files that have been modified."""
        results = self.verify_all()
        return [path for path, status in results.items() if status == IntegrityStatus.MODIFIED]
    
    def get_missing_files(self) -> List[str]:
        """Get list of files that are missing."""
        results = self.verify_all()
        return [path for path, status in results.items() if status == IntegrityStatus.MISSING]


_service_instance: Optional[IntegrityService] = None


def get_integrity_service() -> IntegrityService:
    """Get the singleton IntegrityService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = IntegrityService()
    return _service_instance


__all__ = [
    "IntegrityService",
    "IntegrityStatus", 
    "FileIntegrityRecord",
    "get_integrity_service",
]
'''

os.makedirs('mycosoft_mas/security', exist_ok=True)
with open('mycosoft_mas/security/integrity_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Created integrity_service.py')
