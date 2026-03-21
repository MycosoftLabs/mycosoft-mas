"""Encryption Service. Created: February 3, 2026"""

import base64
import os


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
        import hashlib

        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        aes_key = hashlib.sha256(self.key).digest()
        aesgcm = AESGCM(aes_key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        return base64.b64encode(nonce + ciphertext).decode()

    def decrypt(self, ciphertext: str) -> str:
        import hashlib

        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        aes_key = hashlib.sha256(self.key).digest()
        aesgcm = AESGCM(aes_key)
        data = base64.b64decode(ciphertext)
        nonce = data[:12]
        payload = data[12:]
        return aesgcm.decrypt(nonce, payload, None).decode()

    def hash_password(self, password: str) -> str:
        import bcrypt

        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password: str, hashed: str) -> bool:
        import bcrypt

        return bcrypt.checkpw(password.encode(), hashed.encode())
