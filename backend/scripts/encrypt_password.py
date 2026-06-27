"""Script to encrypt LinkedIn password for secure storage in .env file.

Usage:
    python backend/scripts/encrypt_password.py

This script:
1. Prompts for your LinkedIn password (input is hidden)
2. Encrypts it using your ENCRYPTION_KEY from .env
3. Outputs the encrypted value to add to .env as LINKEDIN_PASSWORD_ENCRYPTED

Security:
- The encrypted password is stored in .env (never commit .env to git!)
- The password is decrypted at runtime only when needed
- Uses Fernet (AES-256) encryption with your ENCRYPTION_KEY
"""

import getpass
import os
import sys
from pathlib import Path

# Load .env file manually to avoid importing app.core.config
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# Load environment variables from .env
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)



def encrypt_text(text: str, encryption_key: str) -> str:
    """Encrypt text using Fernet encryption.
    
    Args:
        text: Plain text to encrypt
        encryption_key: Base64-encoded encryption key
        
    Returns:
        Encrypted text as base64 string
    """
    cipher = Fernet(encryption_key.encode())
    encrypted_bytes = cipher.encrypt(text.encode())
    return encrypted_bytes.decode()


def main():
    """Encrypt LinkedIn password for storage in .env."""
    print("=" * 70)
    print("LinkedIn Password Encryption Utility")
    print("=" * 70)
    print()
    
    # Check if ENCRYPTION_KEY is set
    encryption_key = os.getenv("ENCRYPTION_KEY")
    
    if not encryption_key:
        print("✗ ERROR: ENCRYPTION_KEY not found in .env file")
        print()
        print("Please set ENCRYPTION_KEY in your .env file first:")
        print("1. Run: python backend/generate_secrets.py")
        print("2. Copy the ENCRYPTION_KEY to your .env file")
        print("3. Then run this script again")
        sys.exit(1)
    
    print("This script will encrypt your LinkedIn password for secure storage.")
    print("The encrypted password will be stored in .env as LINKEDIN_PASSWORD_ENCRYPTED")
    print()
    print("⚠️  IMPORTANT:")
    print("   - Your password is encrypted, not hashed (it can be decrypted)")
    print("   - NEVER commit your .env file to git")
    print("   - Keep your ENCRYPTION_KEY secure")
    print("   - This is only needed for Playwright browser automation")
    print("   - Kimi WebBridge does NOT need credentials (recommended)")
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
        print("📝 Next steps:")
        print("1. Add LINKEDIN_PASSWORD_ENCRYPTED to your .env file")
        print("2. Verify setup: python backend/test_setup.py")
        print("3. Start development: Phase 4 implementation")
        print()
        
    except Exception as e:
        print(f"\n✗ ERROR: Failed to encrypt password: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
