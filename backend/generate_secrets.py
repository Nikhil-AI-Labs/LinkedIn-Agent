"""Generate secure secrets for .env file.

Run this script to generate:
- ENCRYPTION_KEY (32-byte base64 for AES-256)
- JWT_SECRET (random secure key)
"""

import base64
import os
import secrets


def generate_encryption_key() -> str:
    """Generate 32-byte base64-encoded encryption key."""
    return base64.b64encode(os.urandom(32)).decode()


def generate_jwt_secret() -> str:
    """Generate secure JWT secret (64 characters)."""
    return secrets.token_urlsafe(48)


def main() -> None:
    """Print generated secrets."""
    print("=" * 70)
    print("Generated Secrets for .env File")
    print("=" * 70)
    print()
    print("Copy these values to your .env file:")
    print()
    print(f"ENCRYPTION_KEY={generate_encryption_key()}")
    print(f"JWT_SECRET={generate_jwt_secret()}")
    print()
    print("=" * 70)
    print("⚠️  Keep these secrets secure! Never commit .env to version control.")
    print("=" * 70)


if __name__ == "__main__":
    main()
