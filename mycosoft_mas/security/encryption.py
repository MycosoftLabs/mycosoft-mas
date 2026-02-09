"""Encryption Service. Created: February 3, 2026"""
import base64
import hashlib
from typing import Optional

class EncryptionService:
    """Data encryption service."""
    
    def __init__(self, key: bytes = b"mycosoft_encryption_key_32bytes!"):
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
