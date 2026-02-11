r"""
MINDEX Blob Manager - Feb 5, 2026
Manages binary large objects (images, DNA sequences, PDFs) stored on NAS.

NAS Mount: /mnt/nas/mycosoft/mindex/
Windows Path: \\192.168.0.105\mycosoft\mindex\ (when mounted)

Directory structure:
/mnt/nas/mycosoft/mindex/
/mnt/nas/mycosoft/mindex/
|-- images/
|   |-- species/           # Species/taxon images
|   |   |-- by_id/         # Organized by taxon ID
|   |   `-- by_name/       # Organized by genus/species
|   `-- observations/      # Individual observation photos
|-- sequences/
|   |-- fasta/             # FASTA files
|   `-- genbank/           # GenBank format files
|-- research/
|   |-- pdfs/              # Research paper PDFs
|   `-- supplementary/     # Supplementary data files
|-- compounds/
|   |-- structures/        # 2D/3D structure images
|   `-- spectra/           # Spectral data
`-- temp/                  # Temporary downloads
"""

import asyncio
import hashlib
import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

import aiofiles
import aiohttp

logger = logging.getLogger(__name__)


class BlobManager:
    """Manages blob storage on NAS for MINDEX."""
    
    # NAS base path - should be mounted on the VM
    DEFAULT_NAS_PATH = "/mnt/nas/mycosoft/mindex"
    WINDOWS_NAS_PATH = r"\\192.168.0.105\mycosoft\mindex"
    
    # Subdirectories
    SUBDIRS = {
        "images": "images",
        "species_images": "images/species/by_id",
        "species_images_by_name": "images/species/by_name",
        "observations": "images/observations",
        "fasta": "sequences/fasta",
        "genbank": "sequences/genbank",
        "pdfs": "research/pdfs",
        "supplementary": "research/supplementary",
        "structures": "compounds/structures",
        "spectra": "compounds/spectra",
        "temp": "temp",
    }
    
    # File size limits (bytes)
    MAX_IMAGE_SIZE = 50 * 1024 * 1024      # 50 MB
    MAX_PDF_SIZE = 200 * 1024 * 1024       # 200 MB
    MAX_SEQUENCE_SIZE = 100 * 1024 * 1024  # 100 MB
    
    # Allowed extensions by type
    ALLOWED_EXTENSIONS = {
        "image": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".tif", ".bmp"},
        "dna_sequence": {".fasta", ".fa", ".fna", ".gb", ".gbk", ".seq", ".txt"},
        "research_pdf": {".pdf"},
        "document": {".pdf", ".doc", ".docx", ".txt", ".md"},
        "data": {".json", ".csv", ".tsv", ".xml", ".xlsx", ".xls"},
    }
    
    def __init__(
        self,
        base_path: Optional[str] = None,
        db=None,
        use_windows_path: bool = False,
    ):
        """
        Initialize blob manager.
        
        Args:
            base_path: Override default NAS path
            db: Database connection for tracking blobs
            use_windows_path: Use Windows UNC path instead of Unix mount
        """
        if base_path:
            self.base_path = Path(base_path)
        elif use_windows_path or os.name == "nt":
            self.base_path = Path(self.WINDOWS_NAS_PATH)
        else:
            self.base_path = Path(self.DEFAULT_NAS_PATH)
        
        self.db = db
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Create required subdirectories if they don't exist."""
        for subdir in self.SUBDIRS.values():
            path = self.base_path / subdir
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.warning(f"Could not create directory {path}: {e}")
    
    def get_path(self, subdir_key: str) -> Path:
        """Get full path for a subdirectory."""
        if subdir_key not in self.SUBDIRS:
            raise ValueError(f"Unknown subdirectory key: {subdir_key}")
        return self.base_path / self.SUBDIRS[subdir_key]
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal and invalid chars."""
        # Remove path components
        filename = os.path.basename(filename)
        # Replace problematic characters
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
        # Limit length
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200 - len(ext)] + ext
        return filename or "unnamed"
    
    def _generate_species_path(
        self,
        scientific_name: str,
        taxon_id: Optional[int] = None,
        filename: str = "primary.jpg",
    ) -> Path:
        """Generate path for species image."""
        filename = self._sanitize_filename(filename)
        
        if taxon_id:
            # Organize by ID (for quick lookup)
            subdir = str(taxon_id % 1000).zfill(3)  # Distribute across 1000 folders
            return self.get_path("species_images") / subdir / str(taxon_id) / filename
        else:
            # Organize by name (genus/species)
            parts = scientific_name.split()
            if len(parts) >= 2:
                genus = self._sanitize_filename(parts[0].lower())
                species = self._sanitize_filename("_".join(parts[1:]).lower())
                return self.get_path("species_images_by_name") / genus / species / filename
            else:
                return self.get_path("species_images_by_name") / "unknown" / self._sanitize_filename(scientific_name) / filename
    
    async def download_file(
        self,
        url: str,
        target_path: Path,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 60,
        max_size: Optional[int] = None,
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Download file from URL to target path.
        
        Returns:
            Tuple of (success, error_message, file_size)
        """
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = target_path.with_suffix(target_path.suffix + ".tmp")
            
            default_headers = {
                "User-Agent": "Mycosoft-MINDEX/1.0 (https://mycosoft.com)",
            }
            if headers:
                default_headers.update(headers)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=default_headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    if response.status != 200:
                        return False, f"HTTP {response.status}", None
                    
                    content_length = response.headers.get("Content-Length")
                    if content_length and max_size:
                        if int(content_length) > max_size:
                            return False, f"File too large: {content_length} bytes", None
                    
                    size = 0
                    async with aiofiles.open(temp_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            size += len(chunk)
                            if max_size and size > max_size:
                                await f.close()
                                temp_path.unlink(missing_ok=True)
                                return False, f"File too large: >{max_size} bytes", None
                            await f.write(chunk)
            
            # Move temp file to final location
            shutil.move(str(temp_path), str(target_path))
            return True, None, size
            
        except asyncio.TimeoutError:
            return False, "Download timeout", None
        except Exception as e:
            return False, str(e), None
    
    @staticmethod
    def compute_checksum(file_path: Path, algorithm: str = "sha256") -> str:
        """Compute file checksum."""
        hash_obj = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    
    async def download_species_image(
        self,
        url: str,
        scientific_name: str,
        taxon_id: Optional[int] = None,
        source: str = "unknown",
        source_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Download and store a species image.
        
        Returns:
            Dict with blob info or error
        """
        # Parse URL for filename
        parsed = urlparse(url)
        original_filename = os.path.basename(parsed.path) or "image.jpg"
        
        # Generate target path
        target_path = self._generate_species_path(
            scientific_name=scientific_name,
            taxon_id=taxon_id,
            filename=original_filename,
        )
        
        # Download
        success, error, size = await self.download_file(
            url=url,
            target_path=target_path,
            max_size=self.MAX_IMAGE_SIZE,
        )
        
        if not success:
            return {"success": False, "error": error}
        
        # Compute checksum
        checksum = self.compute_checksum(target_path)
        
        # Get relative path for storage
        relative_path = str(target_path.relative_to(self.base_path))
        
        # Detect MIME type
        ext = target_path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
        }
        mime_type = mime_types.get(ext, "application/octet-stream")
        
        result = {
            "success": True,
            "file_path": relative_path,
            "full_path": str(target_path),
            "original_url": url,
            "file_name": original_filename,
            "file_size": size,
            "mime_type": mime_type,
            "checksum": checksum,
            "checksum_algorithm": "sha256",
            "source": source,
            "source_id": source_id,
            "scientific_name": scientific_name,
            "taxon_id": taxon_id,
            "metadata": metadata or {},
        }
        
        # Register in database if available
        if self.db:
            try:
                await self._register_blob(result)
            except Exception as e:
                logger.error(f"Failed to register blob in database: {e}")
        
        return result
    
    async def download_sequence(
        self,
        url_or_content: str,
        accession: str,
        scientific_name: str,
        gene_region: Optional[str] = None,
        source: str = "genbank",
        is_content: bool = False,
    ) -> Dict[str, Any]:
        """
        Download or save DNA sequence.
        
        Args:
            url_or_content: URL to download or actual sequence content
            accession: Accession number
            scientific_name: Species name
            gene_region: Gene region (ITS, 18S, etc.)
            source: Data source
            is_content: If True, url_or_content is actual FASTA content
        """
        # Generate filename
        safe_name = self._sanitize_filename(scientific_name.replace(" ", "_"))
        filename = f"{accession}_{safe_name}"
        if gene_region:
            filename += f"_{gene_region}"
        filename += ".fasta"
        
        target_path = self.get_path("fasta") / accession[:3] / filename
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        if is_content:
            # Write content directly
            async with aiofiles.open(target_path, "w") as f:
                await f.write(url_or_content)
            size = len(url_or_content.encode())
        else:
            # Download
            success, error, size = await self.download_file(
                url=url_or_content,
                target_path=target_path,
                max_size=self.MAX_SEQUENCE_SIZE,
            )
            if not success:
                return {"success": False, "error": error}
        
        checksum = self.compute_checksum(target_path)
        relative_path = str(target_path.relative_to(self.base_path))
        
        return {
            "success": True,
            "file_path": relative_path,
            "full_path": str(target_path),
            "file_name": filename,
            "file_size": size,
            "checksum": checksum,
            "accession": accession,
            "scientific_name": scientific_name,
            "gene_region": gene_region,
            "source": source,
        }
    
    async def download_paper(
        self,
        url: str,
        pmid: Optional[str] = None,
        doi: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Download research paper PDF."""
        # Generate filename
        if pmid:
            filename = f"pmid_{pmid}.pdf"
        elif doi:
            safe_doi = self._sanitize_filename(doi.replace("/", "_"))
            filename = f"doi_{safe_doi}.pdf"
        else:
            filename = f"paper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Organize by year/month
        now = datetime.now()
        target_path = self.get_path("pdfs") / str(now.year) / str(now.month).zfill(2) / filename
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        success, error, size = await self.download_file(
            url=url,
            target_path=target_path,
            max_size=self.MAX_PDF_SIZE,
        )
        
        if not success:
            return {"success": False, "error": error}
        
        checksum = self.compute_checksum(target_path)
        relative_path = str(target_path.relative_to(self.base_path))
        
        return {
            "success": True,
            "file_path": relative_path,
            "full_path": str(target_path),
            "file_name": filename,
            "file_size": size,
            "checksum": checksum,
            "pmid": pmid,
            "doi": doi,
            "title": title,
        }
    
    async def _register_blob(self, blob_info: Dict[str, Any]) -> Optional[str]:
        """Register blob in database. Returns blob ID."""
        if not self.db:
            return None
        
        # Determine blob type
        ext = Path(blob_info.get("file_path", "")).suffix.lower()
        if ext in self.ALLOWED_EXTENSIONS["image"]:
            blob_type = "image"
        elif ext in self.ALLOWED_EXTENSIONS["dna_sequence"]:
            blob_type = "dna_sequence"
        elif ext in {".pdf"}:
            blob_type = "research_pdf"
        else:
            blob_type = "data"
        
        query = """
        INSERT INTO core.blobs (
            blob_type, source, source_id, file_path, original_url,
            file_name, file_size, mime_type, checksum, checksum_algorithm,
            metadata, is_processed, processing_status
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, TRUE, 'completed')
        ON CONFLICT (source, source_id, blob_type) DO UPDATE SET
            file_path = EXCLUDED.file_path,
            file_size = EXCLUDED.file_size,
            checksum = EXCLUDED.checksum,
            updated_at = NOW()
        RETURNING id
        """
        
        try:
            result = await self.db.fetchone(
                query,
                blob_type,
                blob_info.get("source", "unknown"),
                blob_info.get("source_id"),
                blob_info.get("file_path"),
                blob_info.get("original_url"),
                blob_info.get("file_name"),
                blob_info.get("file_size"),
                blob_info.get("mime_type"),
                blob_info.get("checksum"),
                blob_info.get("checksum_algorithm", "sha256"),
                blob_info.get("metadata", {}),
            )
            return str(result["id"]) if result else None
        except Exception as e:
            logger.error(f"Failed to register blob: {e}")
            return None
    
    def get_blob_url(self, relative_path: str, base_url: str = "http://192.168.0.189:8001") -> str:
        """Generate URL to access blob via MINDEX API."""
        return f"{base_url}/mindex/blobs/{relative_path}"
    
    def file_exists(self, relative_path: str) -> bool:
        """Check if a blob file exists."""
        full_path = self.base_path / relative_path
        return full_path.exists()
    
    async def get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage statistics for blob storage."""
        stats = {}
        total_size = 0
        total_files = 0
        
        for name, subdir in self.SUBDIRS.items():
            path = self.base_path / subdir
            if not path.exists():
                continue
            
            size = 0
            count = 0
            for root, _, files in os.walk(path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        size += os.path.getsize(fp)
                        count += 1
                    except OSError:
                        pass
            
            stats[name] = {
                "size_bytes": size,
                "size_human": self._human_readable_size(size),
                "file_count": count,
            }
            total_size += size
            total_files += count
        
        stats["total"] = {
            "size_bytes": total_size,
            "size_human": self._human_readable_size(total_size),
            "file_count": total_files,
        }
        
        return stats
    
    @staticmethod
    def _human_readable_size(size: int) -> str:
        """Convert bytes to human readable string."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"
    
    async def cleanup_temp(self, max_age_hours: int = 24) -> int:
        """Remove old files from temp directory. Returns count of removed files."""
        temp_path = self.get_path("temp")
        if not temp_path.exists():
            return 0
        
        removed = 0
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        
        for item in temp_path.iterdir():
            try:
                if item.stat().st_mtime < cutoff:
                    if item.is_file():
                        item.unlink()
                    else:
                        shutil.rmtree(item)
                    removed += 1
            except Exception as e:
                logger.warning(f"Could not remove {item}: {e}")
        
        return removed


class BlobDownloadQueue:
    """Queue manager for blob downloads."""
    
    def __init__(self, blob_manager: BlobManager, db=None, max_concurrent: int = 5):
        self.blob_manager = blob_manager
        self.db = db
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running = False
    
    async def add_to_queue(
        self,
        url: str,
        blob_type: str,
        source: str,
        source_id: Optional[str] = None,
        priority: int = 0,
        metadata: Optional[Dict] = None,
    ) -> Optional[int]:
        """Add download to queue. Returns queue ID."""
        if not self.db:
            logger.warning("No database connection - cannot queue download")
            return None
        
        query = """
        INSERT INTO core.blob_download_queue (url, target_path, blob_type, source, source_id, priority, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id
        """
        
        # Generate target path based on type
        target_path = f"{blob_type}/{source}/{source_id or 'unknown'}"
        
        try:
            result = await self.db.fetchone(
                query, url, target_path, blob_type, source, source_id, priority, metadata or {}
            )
            return result["id"] if result else None
        except Exception as e:
            logger.error(f"Failed to add to download queue: {e}")
            return None
    
    async def process_queue(self, batch_size: int = 100) -> Dict[str, int]:
        """Process pending downloads. Returns stats."""
        if not self.db:
            return {"error": "No database connection"}
        
        stats = {"processed": 0, "success": 0, "failed": 0}
        
        # Get pending items
        query = """
        SELECT id, url, blob_type, source, source_id, metadata
        FROM core.blob_download_queue
        WHERE status = 'pending' AND attempts < max_attempts
        ORDER BY priority DESC, created_at
        LIMIT $1
        """
        
        try:
            items = await self.db.fetch(query, batch_size)
        except Exception as e:
            logger.error(f"Failed to fetch queue: {e}")
            return {"error": str(e)}
        
        tasks = []
        for item in items:
            tasks.append(self._process_item(item))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            stats["processed"] += 1
            if isinstance(result, Exception):
                stats["failed"] += 1
            elif result.get("success"):
                stats["success"] += 1
            else:
                stats["failed"] += 1
        
        return stats
    
    async def _process_item(self, item: Dict) -> Dict[str, Any]:
        """Process single queue item."""
        async with self._semaphore:
            try:
                # Update status
                await self.db.execute(
                    "UPDATE core.blob_download_queue SET status='downloading', started_at=NOW(), attempts=attempts+1 WHERE id=$1",
                    item["id"],
                )
                
                # Download based on type
                blob_type = item["blob_type"]
                metadata = item.get("metadata", {})
                
                if blob_type == "image":
                    result = await self.blob_manager.download_species_image(
                        url=item["url"],
                        scientific_name=metadata.get("scientific_name", "Unknown"),
                        taxon_id=metadata.get("taxon_id"),
                        source=item["source"],
                        source_id=item["source_id"],
                        metadata=metadata,
                    )
                elif blob_type == "dna_sequence":
                    result = await self.blob_manager.download_sequence(
                        url_or_content=item["url"],
                        accession=item["source_id"] or "unknown",
                        scientific_name=metadata.get("scientific_name", "Unknown"),
                        gene_region=metadata.get("gene_region"),
                        source=item["source"],
                    )
                elif blob_type == "research_pdf":
                    result = await self.blob_manager.download_paper(
                        url=item["url"],
                        pmid=metadata.get("pmid"),
                        doi=metadata.get("doi"),
                        title=metadata.get("title"),
                    )
                else:
                    result = {"success": False, "error": f"Unknown blob type: {blob_type}"}
                
                # Update queue status
                if result.get("success"):
                    await self.db.execute(
                        "UPDATE core.blob_download_queue SET status='completed', completed_at=NOW() WHERE id=$1",
                        item["id"],
                    )
                else:
                    await self.db.execute(
                        "UPDATE core.blob_download_queue SET status='failed', last_error=$1 WHERE id=$2",
                        result.get("error", "Unknown error"),
                        item["id"],
                    )
                
                return result
                
            except Exception as e:
                logger.error(f"Error processing queue item {item['id']}: {e}")
                await self.db.execute(
                    "UPDATE core.blob_download_queue SET status='failed', last_error=$1 WHERE id=$2",
                    str(e),
                    item["id"],
                )
                return {"success": False, "error": str(e)}
