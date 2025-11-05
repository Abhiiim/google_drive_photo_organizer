"""Custom SQLAlchemy types."""

from __future__ import annotations

from sqlalchemy.types import Text, TypeDecorator

from core.security import decrypt_text, encrypt_text


class EncryptedText(TypeDecorator):
    """Type decorator that transparently encrypts/decrypts string values."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):  # noqa: D401
        if value is None:
            return None
        return encrypt_text(value)

    def process_result_value(self, value, dialect):  # noqa: D401
        if value is None:
            return None
        return decrypt_text(value)


__all__ = ["EncryptedText"]


