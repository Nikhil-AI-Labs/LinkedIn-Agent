"""Encryption utilities for sensitive data."""

import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data.

    Uses Fernet (symmetric encryption) with key derived from ENCRYPTION_KEY.
    """

    def __init__(self, encryption_key: str) -> None:
        """Initialize encryption service with derived Fernet key.

        Args:
            encryption_key: Base encryption key from environment
        """
        # Derive Fernet key from encryption key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"linkedin-ai-agent-salt",  # Static salt for deterministic key
            iterations=100_000,
            backend=default_backend(),
        )
        key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
        self.fernet = Fernet(key)

    def encrypt_text(self, plaintext: str) -> str:
        """Encrypt plaintext string.

        Args:
            plaintext: Text to encrypt

        Returns:
            Base64-encoded encrypted text

        Examples:
            >>> service = EncryptionService("my-key")
            >>> encrypted = service.encrypt_text("secret-token")
            >>> decrypted = service.decrypt_text(encrypted)
            >>> assert decrypted == "secret-token"
        """
        if not plaintext:
            return ""

        encrypted_bytes = self.fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted_bytes).decode()

    def decrypt_text(self, encrypted: str) -> str:
        """Decrypt encrypted string.

        Args:
            encrypted: Base64-encoded encrypted text

        Returns:
            Decrypted plaintext

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails
        """
        if not encrypted:
            return ""

        encrypted_bytes = base64.urlsafe_b64decode(encrypted.encode())
        decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
        return decrypted_bytes.decode()


# Global encryption service instance
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """Get global encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService(settings.encryption_key)
    return _encryption_service


def encrypt_text(plaintext: str) -> str:
    """Convenience function to encrypt text.

    Args:
        plaintext: Text to encrypt

    Returns:
        Encrypted text
    """
    return get_encryption_service().encrypt_text(plaintext)


def decrypt_text(encrypted: str) -> str:
    """Convenience function to decrypt text.

    Args:
        encrypted: Encrypted text

    Returns:
        Decrypted plaintext
    """
    return get_encryption_service().decrypt_text(encrypted)
