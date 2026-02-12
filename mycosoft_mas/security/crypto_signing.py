"""
Ed25519 Cryptographic Signing for Audit Logs
February 12, 2026

Provides cryptographic signatures for audit log entries to ensure:
- Log integrity: Detect tampering with historical logs
- Non-repudiation: Prove who created each log entry
- DoD compliance: Meets audit trail security requirements

Uses Ed25519 which is:
- Fast and efficient
- Small signatures (64 bytes)
- High security (128-bit security level)
- Deterministic (same input = same signature)
"""

import os
import json
import hashlib
import logging
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime
from base64 import b64encode, b64decode

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger(__name__)

# Default key paths
DEFAULT_PRIVATE_KEY_PATH = Path(os.getenv(
    "AUDIT_SIGNING_KEY_PATH",
    "/opt/mycosoft/keys/audit_signing_key.pem"
))
DEFAULT_PUBLIC_KEY_PATH = Path(os.getenv(
    "AUDIT_VERIFY_KEY_PATH",
    "/opt/mycosoft/keys/audit_verify_key.pem"
))


class AuditLogSigner:
    """
    Ed25519-based signer for audit log entries.
    
    Usage:
        signer = AuditLogSigner()
        signer.generate_keys()  # One-time setup
        
        # Sign a log entry
        signature = signer.sign_log_entry(log_data)
        
        # Verify a log entry
        is_valid = signer.verify_log_entry(log_data, signature)
    """
    
    def __init__(
        self,
        private_key_path: Optional[Path] = None,
        public_key_path: Optional[Path] = None,
        password: Optional[bytes] = None,
    ):
        """
        Initialize the signer.
        
        Args:
            private_key_path: Path to Ed25519 private key PEM file
            public_key_path: Path to Ed25519 public key PEM file
            password: Optional password for encrypted private key
        """
        if not CRYPTO_AVAILABLE:
            logger.warning(
                "cryptography library not available. "
                "Install with: pip install cryptography"
            )
            self._private_key = None
            self._public_key = None
            self._enabled = False
            return
        
        self._private_key_path = private_key_path or DEFAULT_PRIVATE_KEY_PATH
        self._public_key_path = public_key_path or DEFAULT_PUBLIC_KEY_PATH
        self._password = password
        self._private_key: Optional[Ed25519PrivateKey] = None
        self._public_key: Optional[Ed25519PublicKey] = None
        self._enabled = True
        
        # Try to load existing keys
        self._load_keys()
    
    def _load_keys(self) -> bool:
        """Load keys from files if they exist."""
        loaded = False
        
        # Load private key
        if self._private_key_path.exists():
            try:
                with open(self._private_key_path, "rb") as f:
                    self._private_key = serialization.load_pem_private_key(
                        f.read(),
                        password=self._password,
                    )
                    # Derive public key from private
                    self._public_key = self._private_key.public_key()
                    loaded = True
                    logger.info(f"Loaded signing key from {self._private_key_path}")
            except Exception as e:
                logger.error(f"Failed to load private key: {e}")
        
        # Load public key if private not available
        if not loaded and self._public_key_path.exists():
            try:
                with open(self._public_key_path, "rb") as f:
                    self._public_key = serialization.load_pem_public_key(f.read())
                    logger.info(f"Loaded verify key from {self._public_key_path}")
                    loaded = True
            except Exception as e:
                logger.error(f"Failed to load public key: {e}")
        
        return loaded
    
    def generate_keys(self, save: bool = True) -> Tuple[bytes, bytes]:
        """
        Generate new Ed25519 keypair.
        
        Args:
            save: Whether to save keys to configured paths
            
        Returns:
            Tuple of (private_key_pem, public_key_pem)
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library not available")
        
        # Generate keypair
        self._private_key = Ed25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()
        
        # Serialize keys
        private_pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(self._password)
            if self._password else serialization.NoEncryption(),
        )
        
        public_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        
        # Save to files
        if save:
            self._private_key_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self._private_key_path, "wb") as f:
                f.write(private_pem)
            os.chmod(self._private_key_path, 0o600)  # Read/write owner only
            
            with open(self._public_key_path, "wb") as f:
                f.write(public_pem)
            os.chmod(self._public_key_path, 0o644)  # Read by all
            
            logger.info(f"Generated and saved new signing keypair")
        
        return private_pem, public_pem
    
    def _canonicalize_log_entry(self, log_data: Dict[str, Any]) -> bytes:
        """
        Create canonical byte representation of log entry for signing.
        
        Uses sorted JSON to ensure deterministic serialization.
        Excludes signature field if present.
        """
        # Create copy without signature
        data = {k: v for k, v in log_data.items() if k != "signature"}
        
        # Handle datetime serialization
        def serialize_value(v):
            if isinstance(v, datetime):
                return v.isoformat()
            elif isinstance(v, dict):
                return {k: serialize_value(val) for k, val in v.items()}
            elif isinstance(v, list):
                return [serialize_value(item) for item in v]
            return v
        
        data = serialize_value(data)
        
        # Canonical JSON: sorted keys, no extra whitespace
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return canonical.encode("utf-8")
    
    def sign_log_entry(self, log_data: Dict[str, Any]) -> Optional[str]:
        """
        Sign an audit log entry.
        
        Args:
            log_data: Dictionary containing log entry fields
            
        Returns:
            Base64-encoded Ed25519 signature, or None if signing disabled
        """
        if not self._enabled or not self._private_key:
            return None
        
        try:
            canonical = self._canonicalize_log_entry(log_data)
            signature = self._private_key.sign(canonical)
            return b64encode(signature).decode("ascii")
        except Exception as e:
            logger.error(f"Failed to sign log entry: {e}")
            return None
    
    def verify_log_entry(
        self,
        log_data: Dict[str, Any],
        signature: str,
    ) -> bool:
        """
        Verify an audit log entry signature.
        
        Args:
            log_data: Dictionary containing log entry fields
            signature: Base64-encoded Ed25519 signature
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not self._enabled or not self._public_key:
            logger.warning("Verification not available - no public key")
            return False
        
        try:
            canonical = self._canonicalize_log_entry(log_data)
            sig_bytes = b64decode(signature.encode("ascii"))
            self._public_key.verify(sig_bytes, canonical)
            return True
        except InvalidSignature:
            logger.warning("Invalid signature detected - log may be tampered")
            return False
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
    
    def get_public_key_fingerprint(self) -> Optional[str]:
        """
        Get SHA-256 fingerprint of public key.
        
        Useful for identifying which key signed a log.
        """
        if not self._enabled or not self._public_key:
            return None
        
        try:
            pub_bytes = self._public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            fingerprint = hashlib.sha256(pub_bytes).hexdigest()[:16]
            return f"ed25519:{fingerprint}"
        except Exception as e:
            logger.error(f"Failed to get key fingerprint: {e}")
            return None
    
    @property
    def is_signing_enabled(self) -> bool:
        """Check if signing is available."""
        return self._enabled and self._private_key is not None
    
    @property
    def is_verification_enabled(self) -> bool:
        """Check if verification is available."""
        return self._enabled and self._public_key is not None


# Global signer instance
_audit_signer: Optional[AuditLogSigner] = None


def get_audit_signer() -> AuditLogSigner:
    """Get or create global audit log signer instance."""
    global _audit_signer
    if _audit_signer is None:
        _audit_signer = AuditLogSigner()
    return _audit_signer


def sign_audit_log(log_data: Dict[str, Any]) -> Optional[str]:
    """Convenience function to sign an audit log entry."""
    return get_audit_signer().sign_log_entry(log_data)


def verify_audit_log(log_data: Dict[str, Any], signature: str) -> bool:
    """Convenience function to verify an audit log entry."""
    return get_audit_signer().verify_log_entry(log_data, signature)
