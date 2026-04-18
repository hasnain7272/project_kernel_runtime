"""
Security and encryption helpers.
"""
import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)
_KEY_FILE = Path.cwd() / ".runtime_secret.key"


def _load_or_create_local_key() -> str:
    if _KEY_FILE.exists():
        return _KEY_FILE.read_text(encoding="utf-8").strip()

    key = Fernet.generate_key().decode("utf-8")
    _KEY_FILE.write_text(key, encoding="utf-8")
    logger.warning(f"APP_SECRET_KEY not set. Generated local runtime key at {_KEY_FILE}.")
    return key


_raw_key = os.environ.get("APP_SECRET_KEY") or _load_or_create_local_key()
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
    except Exception as exc:
        logger.error(f"Decryption failed: {exc}")
        return ""
