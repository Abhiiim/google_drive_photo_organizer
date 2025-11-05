"""Utility helpers for encrypting and decrypting sensitive data."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from core.config import get_settings
from core.logger import get_logger


logger = get_logger(__name__)


@lru_cache
def _get_fernet() -> Fernet:
    settings = get_settings()
    if not settings.encryption_key:
        raise ValueError("Encryption key is not configured")
    key = settings.encryption_key
    if isinstance(key, str):
        key_bytes = key.encode("utf-8")
    else:  # pragma: no cover - defensive type handling
        key_bytes = key
    return Fernet(key_bytes)


def encrypt_text(value: Optional[str]) -> Optional[str]:
    """Encrypt plain text using the configured Fernet key."""

    if value is None:
        return None
    token = _get_fernet().encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_text(value: Optional[str]) -> Optional[str]:
    """Decrypt an encrypted token, returning the original plain text."""

    if value is None:
        return None
    try:
        plain = _get_fernet().decrypt(value.encode("utf-8"))
        return plain.decode("utf-8")
    except InvalidToken:
        logger.warning("security.decrypt_failed", message="Invalid encryption token")
        return value


