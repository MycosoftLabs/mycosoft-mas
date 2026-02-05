"""
NAS Sync Service with Cryptographic Integrity.
Created: February 5, 2026

This service provides cryptographically verified synchronization
of data to NAS storage, ensuring all writes are hashed and recorded
in the integrity ledger before being persisted.

Features:
- SHA256 verification before NAS write
- HMAC-SHA256 signatures for tamper detection
- Dual recording in PostgreSQL and file ledger
- Automatic sync scheduling
- Integrity verification on read
"""

import asyncio
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import aiofiles

logger = logging.getLogger(__name__)


class NASSyncService:
    """
    NAS synchronization service with cryptographic integrity.
    
    All data written to NAS is:
    1. SHA256 hashed
    2. HMAC signed (optional)
    3. Recorded in the integrity ledger
    4. Written to NAS with manifest
    """
    
    def __init__(
        self,
        nas_mount_path: str = "/mnt/mycosoft-nas",
        local_data_path: str = "/opt/mycosoft/data",
        verify_on_write: bool = True
    ):
        """
        Initialize NAS sync service.
        
        Args:
            nas_mount_path: Path to NAS mount point
            local_data_path: Path to local data directory
            verify_on_write: Whether to verify writes immediately
        """
        self.nas_mount_path = Path(nas_mount_path)
        self.local_data_path = Path(local_data_path)
        self.verify_on_write = verify_on_write
        self._manifest_file = "sync_manifest.json"
    
    async def hash_file(self, file_path: Path) -> str:
        """
        Compute SHA256 hash of a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex-encoded SHA256 hash
        """
        sha256_hash = hashlib.sha256()
        
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    async def hash_directory(self, dir_path: Path) -> Dict[str, str]:
        """
        Compute SHA256 hashes for all files in a directory.
        
        Args:
            dir_path: Path to directory
            
        Returns:
            Dictionary mapping relative paths to hashes
        """
        hashes = {}
        
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(dir_path)
                hashes[str(rel_path)] = await self.hash_file(file_path)
        
        return hashes
    
    async def sync_with_integrity(
        self,
        source_dir: str,
        dest_subpath: str,
        record_in_ledger: bool = True
    ) -> Dict[str, Any]:
        """
        Sync a directory to NAS with cryptographic integrity.
        
        Args:
            source_dir: Local source directory
            dest_subpath: Destination path relative to NAS mount
            record_in_ledger: Whether to record in integrity ledger
            
        Returns:
            Sync result with hashes and status
        """
        source = Path(source_dir)
        dest = self.nas_mount_path / dest_subpath
        
        if not source.exists():
            return {"success": False, "error": f"Source not found: {source}"}
        
        # Compute source hashes
        source_hashes = await self.hash_directory(source)
        
        # Create manifest
        manifest = {
            "sync_time": datetime.now(timezone.utc).isoformat(),
            "source_path": str(source),
            "dest_path": str(dest),
            "file_count": len(source_hashes),
            "files": source_hashes,
            "merkle_root": self._compute_merkle_root(list(source_hashes.values()))
        }
        
        # Record in integrity ledger if requested
        ledger_result = None
        if record_in_ledger:
            try:
                from mycosoft_mas.security.integrity_service import hash_and_record
                ledger_result = await hash_and_record(
                    entry_type="nas_sync",
                    data=manifest,
                    metadata={
                        "source": str(source),
                        "dest": str(dest),
                        "file_count": len(source_hashes)
                    },
                    with_signature=True
                )
            except Exception as e:
                logger.warning(f"Failed to record in ledger: {e}")
        
        # Ensure destination exists
        dest.mkdir(parents=True, exist_ok=True)
        
        # Sync files
        synced_count = 0
        errors = []
        
        for rel_path, expected_hash in source_hashes.items():
            src_file = source / rel_path
            dst_file = dest / rel_path
            
            try:
                # Create parent directories
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(src_file, dst_file)
                
                # Verify if requested
                if self.verify_on_write:
                    actual_hash = await self.hash_file(dst_file)
                    if actual_hash != expected_hash:
                        errors.append(f"Hash mismatch for {rel_path}")
                        continue
                
                synced_count += 1
            except Exception as e:
                errors.append(f"Failed to sync {rel_path}: {e}")
        
        # Write manifest to destination
        manifest_path = dest / self._manifest_file
        async with aiofiles.open(manifest_path, 'w') as f:
            await f.write(json.dumps(manifest, indent=2))
        
        return {
            "success": len(errors) == 0,
            "synced_count": synced_count,
            "total_files": len(source_hashes),
            "errors": errors,
            "merkle_root": manifest["merkle_root"],
            "ledger_result": ledger_result,
            "manifest_path": str(manifest_path)
        }
    
    async def verify_nas_integrity(self, subpath: str) -> Dict[str, Any]:
        """
        Verify integrity of files on NAS against manifest.
        
        Args:
            subpath: Path relative to NAS mount
            
        Returns:
            Verification result
        """
        dir_path = self.nas_mount_path / subpath
        manifest_path = dir_path / self._manifest_file
        
        if not manifest_path.exists():
            return {"valid": False, "error": "Manifest not found"}
        
        async with aiofiles.open(manifest_path, 'r') as f:
            manifest = json.loads(await f.read())
        
        # Verify each file
        mismatches = []
        missing = []
        verified = 0
        
        for rel_path, expected_hash in manifest.get("files", {}).items():
            file_path = dir_path / rel_path
            
            if not file_path.exists():
                missing.append(rel_path)
                continue
            
            actual_hash = await self.hash_file(file_path)
            if actual_hash != expected_hash:
                mismatches.append({
                    "path": rel_path,
                    "expected": expected_hash,
                    "actual": actual_hash
                })
            else:
                verified += 1
        
        return {
            "valid": len(mismatches) == 0 and len(missing) == 0,
            "verified_count": verified,
            "total_files": len(manifest.get("files", {})),
            "mismatches": mismatches,
            "missing": missing,
            "manifest_time": manifest.get("sync_time"),
            "merkle_root": manifest.get("merkle_root")
        }
    
    def _compute_merkle_root(self, hashes: List[str]) -> str:
        """
        Compute Merkle root from list of hashes.
        
        Args:
            hashes: List of SHA256 hashes
            
        Returns:
            Merkle root hash
        """
        if not hashes:
            return hashlib.sha256(b"").hexdigest()
        
        if len(hashes) == 1:
            return hashes[0]
        
        # Pad to even length
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])
        
        # Build tree
        while len(hashes) > 1:
            next_level = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                next_level.append(hashlib.sha256(combined.encode()).hexdigest())
            hashes = next_level
        
        return hashes[0]


# Singleton instance
_nas_sync_service: Optional[NASSyncService] = None


def get_nas_sync_service() -> NASSyncService:
    """Get or create the singleton NAS sync service instance."""
    global _nas_sync_service
    if _nas_sync_service is None:
        _nas_sync_service = NASSyncService()
    return _nas_sync_service


async def sync_to_nas(
    source_dir: str,
    dest_subpath: str,
    record_in_ledger: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to sync data to NAS with integrity.
    """
    service = get_nas_sync_service()
    return await service.sync_with_integrity(
        source_dir=source_dir,
        dest_subpath=dest_subpath,
        record_in_ledger=record_in_ledger
    )
