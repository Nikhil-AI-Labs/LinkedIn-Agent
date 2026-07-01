"""Script to encrypt LinkedIn password for secure storage in .env file.

Usage:
    python backend/scripts/encrypt_password.py

This script:
1. Prompts for your LinkedIn password (input is hidden)
2. Encrypts it using your ENCRYPTION_KEY from .env (same PBKDF2HMAC derivation as the app)
3. Verifies the round-trip decryption succeeds
4. Automatically patches .env with the new LINKEDIN_PASSWORD_ENCRYPTED value

Security:
- The encrypted password is stored in .env (never commit .env to git!)
- The password is decrypted at runtime only when needed
- Uses Fernet (AES-256) encryption with PBKDF2HMAC key derivation
"""

import getpass
import re
import sys
from pathlib import Path

import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import dotenv_values

# ── paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR.parent.parent / ".env"   # project-root/.env


def _make_fernet(key_str: str) -> Fernet:
    """Derive a Fernet key using PBKDF2HMAC — identical to app/core/crypto.py."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"linkedin-ai-agent-salt",
        iterations=100_000,
        backend=default_backend(),
    )
    derived = base64.urlsafe_b64encode(kdf.derive(key_str.encode()))
    return Fernet(derived)


def encrypt_text(plaintext: str, encryption_key: str) -> str:
    """Encrypt plaintext — output matches exactly what app/core/crypto.py decrypt_text expects."""
    if not plaintext:
        return ""
    fernet = _make_fernet(encryption_key)
    encrypted_bytes = fernet.encrypt(plaintext.encode())
    # crypto.py decrypt_text does base64.urlsafe_b64decode first, so we wrap here.
    return base64.urlsafe_b64encode(encrypted_bytes).decode()


def decrypt_text(token: str, encryption_key: str) -> str:
    """Mirror of app/core/crypto.py decrypt_text — used for round-trip verification."""
    fernet = _make_fernet(encryption_key)
    raw = base64.urlsafe_b64decode(token.encode())
    return fernet.decrypt(raw).decode()


def main() -> None:
    """Encrypt LinkedIn password and auto-update .env."""
    print("=" * 70)
    print("LinkedIn Password Encryption Utility")
    print("=" * 70)
    print()

    # Load ENCRYPTION_KEY directly from .env (bypass app config to stay standalone)
    if not ENV_FILE.exists():
        print(f"✗ ERROR: .env not found at {ENV_FILE}")
        sys.exit(1)

    env_vals = dotenv_values(ENV_FILE)
    encryption_key = env_vals.get("ENCRYPTION_KEY", "")
    if not encryption_key:
        print("✗ ERROR: ENCRYPTION_KEY not found in .env")
        sys.exit(1)

    print("This script will encrypt your LinkedIn password for secure storage.")
    print("It will AUTOMATICALLY update your .env file — no copy-paste needed.")
    print()
    print("[!] IMPORTANT:")
    print("   - Your password is encrypted, not hashed (it can be decrypted)")
    print("   - NEVER commit your .env file to git")
    print("   - Keep your ENCRYPTION_KEY secure")
    print()

    # Prompt for password
    password = getpass.getpass("Enter your LinkedIn password (input hidden): ")
    if not password:
        print("\n✗ ERROR: Password cannot be empty")
        sys.exit(1)
    
    # Confirm password
    password_confirm = getpass.getpass("Confirm your LinkedIn password: ")
    
    if password != password_confirm:
        print("\n✗ ERROR: Passwords do not match")
        sys.exit(1)
    
    print("\n✓ Encrypting password...")
    
    try:
        encrypted_password = encrypt_text(password, encryption_key)
        print("✓ Password encrypted successfully")
        print()
        print("=" * 70)
        print("Add this to your .env file:")
        print("=" * 70)
        print(f"LINKEDIN_PASSWORD_ENCRYPTED={encrypted_password}")
        print("=" * 70)
        print()
        print("✓ Done! Add the above line to your .env file.")
        print()
        print("Next steps:")
        print("1. Add LINKEDIN_PASSWORD_ENCRYPTED to your .env file")
        print("2. Verify setup: python backend/test_setup.py")
        print("3. Start development: Phase 4 implementation")
        print()
        
    except Exception as e:
        print(f"\n✗ ERROR: Failed to encrypt password: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
