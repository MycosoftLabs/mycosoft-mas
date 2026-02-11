"""Encryption Service. Created: February 3, 2026"""
import base64
import hashlib
import os
from typing import Optional

class EncryptionService:
    """Data encryption service."""
    
    def __init__(self, key: bytes = None):
        # Load key from environment variable - NEVER use hardcoded keys
        if key is None:
            key_env = os.environ.get("ENCRYPTION_KEY")
            if key_env:
                # Key should be base64-encoded in environment
                self.key = base64.b64decode(key_env)
            else:
                # Generate a secure random key if not provided
                # In production, this should always come from environment/secrets manager
                import secrets
                self.key = secrets.token_bytes(32)
        else:
            self.key = key
    
    def encrypt(self, plaintext: str) -> str:
        from cryptography.fernet import Fernet
        key = base64.urlsafe_b64encode(hashlib.sha256(self.key).digest())
        f = Fernet(key)
        return f.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        from cryptography.fernet import Fernet
        key = base64.urlsafe_b64encode(hashlib.sha256(self.key).digest())
        f = Fernet(key)
        return f.decrypt(ciphertext.encode()).decode()
    
    def hash_password(self, password: str) -> str:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    def verify_password(self, password: str, hashed: str) -> bool:
        import bcrypt
        return bcrypt.checkpw(password.encode(), hashed.encode())
