import os
from typing import Final

from cryptography.fernet import Fernet, InvalidToken


FERNET_KEY_ENV: Final[str] = "DATA_ENCRYPTION_KEY"


def _get_fernet() -> Fernet:
    key = os.getenv(FERNET_KEY_ENV)
    if not key:
        raise ValueError("Missing DATA_ENCRYPTION_KEY for encrypting sensitive data.")
    return Fernet(key.encode())


def encrypt_sensitive_data(value: str) -> str:
    fernet = _get_fernet()
    token = fernet.encrypt(value.encode())
    return token.decode()


def decrypt_sensitive_data(token: str) -> str:
    fernet = _get_fernet()
    try:
        plaintext = fernet.decrypt(token.encode())
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted token.") from exc
    return plaintext.decode()
