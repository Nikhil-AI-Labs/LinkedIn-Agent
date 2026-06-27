# LinkedIn Password Encryption Guide

## Overview

The LinkedIn AI Agent supports browser automation via Playwright for LinkedIn operations when OAuth is not available. For security, LinkedIn passwords must be encrypted before storing them in the `.env` file.

## Why Encryption?

- **Security**: Plain-text passwords in `.env` files are a security risk
- **Git Safety**: Even though `.env` is gitignored, encryption adds an extra layer of protection
- **Runtime Decryption**: The application decrypts the password only when needed for authentication
- **AES-256**: Uses Fernet (symmetric encryption) with your unique `ENCRYPTION_KEY`

## When Do You Need This?

You **ONLY** need to encrypt your LinkedIn password if:

1. **AUTH_MODE=browser** in your `.env` file
2. **BROWSER_PROVIDER=playwright** in your `.env` file
3. You don't have existing session cookies to reuse

### Recommended Setup (No Password Needed)

```env
AUTH_MODE=browser
BROWSER_PROVIDER=kimi_webbridge
```

Kimi WebBridge reuses your existing browser session - **no credentials required**.

### Fallback Setup (Password Required)

```env
AUTH_MODE=browser
BROWSER_PROVIDER=playwright
LINKEDIN_USERNAME=your.email@example.com
LINKEDIN_PASSWORD_ENCRYPTED=<encrypted value here>
```

## Encryption Process

### Step 1: Ensure ENCRYPTION_KEY is Set

First, make sure you have an `ENCRYPTION_KEY` in your `.env` file:

```bash
# Generate secrets if you haven't already
python backend/generate_secrets.py
```

This outputs:
```
ENCRYPTION_KEY=<base64-encoded-32-byte-key>
JWT_SECRET=<random-secret>
```

Copy the `ENCRYPTION_KEY` to your `.env` file.

### Step 2: Run the Encryption Script

```bash
cd backend
python scripts/encrypt_password.py
```

You'll be prompted:

```
Enter your LinkedIn password (input hidden): ********
Confirm your LinkedIn password: ********

✓ Encrypting password...
✓ Password encrypted successfully

======================================================================
Add this to your .env file:
======================================================================
LINKEDIN_PASSWORD_ENCRYPTED=gAAAAABl...encrypted_value...==
======================================================================
```

### Step 3: Add to .env File

Copy the encrypted value and add it to your `.env` file:

```env
LINKEDIN_PASSWORD_ENCRYPTED=gAAAAABl...encrypted_value...==
```

### Step 4: Verify Setup

```bash
python backend/test_setup.py
```

You should see:
```
✓ Testing configuration...
  Auth mode: browser
  Browser provider: playwright
  LinkedIn username: your.email@example.com
  ✓ Playwright credentials present
  ⚠ Warning: Playwright has high LinkedIn detection risk. Consider Kimi WebBridge.
```

## How It Works

### Encryption (One-Time Setup)

```python
from app.core.crypto import encrypt_text

password = "your_linkedin_password"
encrypted = encrypt_text(password)
# Store encrypted value in .env
```

### Decryption (Runtime)

```python
from app.core.crypto import decrypt_text
from app.core.config import settings

# Automatic decryption when needed
password = decrypt_text(settings.linkedin_password_encrypted)
# Use password for authentication
```

### Security Model

1. **ENCRYPTION_KEY**: 32-byte random key, stored in `.env` (never committed)
2. **Fernet Encryption**: Symmetric encryption (AES-128 in CBC mode with HMAC authentication)
3. **Base64 Encoding**: Encrypted output is base64-encoded for safe storage
4. **Runtime Only**: Password is decrypted in memory only when needed

## Security Best Practices

### ✅ DO

- Keep `.env` file out of version control (`.gitignore` includes it)
- Use strong, unique LinkedIn password
- Rotate `ENCRYPTION_KEY` if `.env` is ever exposed
- Use Kimi WebBridge instead of Playwright when possible
- Limit Playwright usage to trusted environments only

### ❌ DON'T

- Never commit `.env` file to git
- Never share your `ENCRYPTION_KEY` or encrypted password
- Never use the same `ENCRYPTION_KEY` across multiple projects
- Don't use Playwright on shared/public servers (LinkedIn will detect it)

## Troubleshooting

### Error: "ENCRYPTION_KEY not found"

**Problem**: The encryption script can't find `ENCRYPTION_KEY` in `.env`

**Solution**:
```bash
# Generate new encryption key
python backend/generate_secrets.py

# Add ENCRYPTION_KEY to .env
echo "ENCRYPTION_KEY=<generated_key>" >> .env
```

### Error: "Passwords do not match"

**Problem**: The password confirmation didn't match

**Solution**: Run the script again and enter the same password twice

### Error: "Decryption failed"

**Problem**: The `ENCRYPTION_KEY` changed after encrypting the password

**Solution**: Re-encrypt your password with the new key:
```bash
python backend/scripts/encrypt_password.py
```

### Warning: "Playwright without credentials will fail"

**Problem**: Playwright mode is enabled but no credentials are set

**Solutions**:
1. **Switch to Kimi WebBridge** (recommended):
   ```env
   BROWSER_PROVIDER=kimi_webbridge
   ```

2. **Encrypt and add credentials**:
   ```bash
   python backend/scripts/encrypt_password.py
   # Add output to .env
   ```

## Alternative: Session Cookie Reuse

Playwright can reuse existing LinkedIn session cookies without credentials:

1. Log in to LinkedIn in your default browser
2. Set `BROWSER_PROVIDER=playwright` without credentials
3. Playwright will attempt to reuse session cookies

**Note**: This is less reliable than Kimi WebBridge and may fail if:
- LinkedIn logs you out
- Session cookies expire
- Browser profile is cleared

## Migration Guide

### From Plain-Text Password

If you currently have `LINKEDIN_PASSWORD` (plain-text):

1. Run encryption script:
   ```bash
   python backend/scripts/encrypt_password.py
   ```

2. Update `.env`:
   ```env
   # Remove old field
   # LINKEDIN_PASSWORD=plain_text_password
   
   # Add new encrypted field
   LINKEDIN_PASSWORD_ENCRYPTED=gAAAAABl...encrypted_value...==
   ```

3. The application automatically uses the encrypted field

### To Kimi WebBridge (Recommended)

Switch from Playwright to Kimi WebBridge:

```env
# Old setup (Playwright with credentials)
BROWSER_PROVIDER=playwright
LINKEDIN_USERNAME=your.email@example.com
LINKEDIN_PASSWORD_ENCRYPTED=gAAAAABl...

# New setup (Kimi WebBridge, no credentials)
BROWSER_PROVIDER=kimi_webbridge
# LINKEDIN_USERNAME and LINKEDIN_PASSWORD_ENCRYPTED can be removed
```

Kimi WebBridge is safer, simpler, and less likely to be detected by LinkedIn.

## Technical Details

### Encryption Algorithm

- **Cipher**: Fernet (AES-128-CBC + HMAC-SHA256)
- **Key Derivation**: Not used (uses raw `ENCRYPTION_KEY`)
- **IV**: Random, generated per encryption
- **Authentication**: HMAC-SHA256 (prevents tampering)

### Implementation

See `backend/app/core/crypto.py`:

```python
from cryptography.fernet import Fernet
import base64

def encrypt_text(text: str) -> str:
    """Encrypt text using ENCRYPTION_KEY."""
    cipher = Fernet(settings.encryption_key.encode())
    encrypted_bytes = cipher.encrypt(text.encode())
    return encrypted_bytes.decode()

def decrypt_text(encrypted_text: str) -> str:
    """Decrypt text using ENCRYPTION_KEY."""
    cipher = Fernet(settings.encryption_key.encode())
    decrypted_bytes = cipher.decrypt(encrypted_text.encode())
    return decrypted_bytes.decode()
```

## FAQ

**Q: Is encrypted password safe to store in .env?**
A: Yes, as long as:
- `.env` is never committed to git
- `ENCRYPTION_KEY` is kept secret
- Both files have proper file permissions (chmod 600)

**Q: Can I use the same encrypted password on different machines?**
A: Only if you use the same `ENCRYPTION_KEY`. Otherwise, you must re-encrypt.

**Q: What if my ENCRYPTION_KEY leaks?**
A: 
1. Generate a new `ENCRYPTION_KEY` immediately
2. Re-encrypt your LinkedIn password
3. Update `.env` on all machines
4. Consider changing your LinkedIn password

**Q: Do I need this for OAuth mode?**
A: No. OAuth tokens are encrypted separately when stored in the database. This is only for browser mode credentials.

**Q: Can I see my decrypted password?**
A: Yes, but only through code. There's no built-in "view password" command for security reasons.

## Support

If you encounter issues:

1. Check `backend/test_setup.py` output for specific errors
2. Verify `ENCRYPTION_KEY` is set correctly in `.env`
3. Ensure Python dependencies are installed: `pip install -r requirements.txt`
4. Check logs for detailed error messages

For more help, see:
- `NEXT_STEPS.md` - Setup instructions
- `README.md` - Project overview
- `backend/app/core/crypto.py` - Encryption implementation
