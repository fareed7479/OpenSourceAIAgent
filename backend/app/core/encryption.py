import base64
import logging
from cryptography.fernet import Fernet
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Fernet cipher
_fernet_key = settings.ENCRYPTION_KEY

if not _fernet_key:
    logger.warning("ENCRYPTION_KEY not set in environment settings. Generating transient key for this session.")
    _fernet_key = Fernet.generate_key().decode()
else:
    # Ensure it's a valid 32-byte url-safe base64-encoded key
    try:
        # Try creating Fernet instance to validate
        Fernet(_fernet_key.encode())
    except Exception as e:
        logger.error(f"Invalid ENCRYPTION_KEY set. Generating a transient fallback key. Error: {e}")
        _fernet_key = Fernet.generate_key().decode()

cipher = Fernet(_fernet_key.encode())

def encrypt_token(token: str) -> str:
    """Encrypt a string token using Fernet symmetric encryption."""
    if not token:
        return ""
    encrypted_bytes = cipher.encrypt(token.encode())
    return encrypted_bytes.decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a Fernet encrypted token string."""
    if not encrypted_token:
        return ""
    try:
        decrypted_bytes = cipher.decrypt(encrypted_token.encode())
        return decrypted_bytes.decode()
    except Exception as e:
        logger.error(f"Failed to decrypt token: {e}")
        return ""
