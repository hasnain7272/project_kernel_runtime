# crypto.py

"""
Security and Encryption core logic.
Provides symmetric encryption for sensitive data like API keys (BYOK).
"""
import os
import base64
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Try to get the key from environment, fallback to a deterministic key for local dev
# In production, THIS MUST BE SET EXPLICITLY
_raw_key = os.environ.get("APP_SECRET_KEY")
if not _raw_key:
    logger.warning("APP_SECRET_KEY not set. Using fallback dev key. DO NOT USE IN PROD.")
    # Fallback needs to be a valid 32-byte url-safe base64-encoded string
    _raw_key = base64.urlsafe_b64encode(b"0" * 32).decode("utf-8")

_fernet = Fernet(_raw_key)


def encrypt_string(data: str) -> str:
    if not data:
        return data
    return _fernet.encrypt(data.encode("utf-8")).decode("utf-8")


def decrypt_string(encrypted_data: str) -> str:
    if not encrypted_data:
        return encrypted_data
    try:
        return _fernet.decrypt(encrypted_data.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        # Return fallback or empty if decryption fails to avoid crashing
        return ""
