from __future__ import annotations

import os
from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
AUTHORIZATION_HEADER = APIKeyHeader(name="Authorization", auto_error=False)


def _extract_api_key(x_api_key: Optional[str], authorization: Optional[str]) -> Optional[str]:
    if x_api_key:
        return x_api_key
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
    return None


def expected_api_key() -> str:
    return os.getenv("DANDELION_API_KEY", "dev-secret")


def require_api_key(
    x_api_key: Optional[str] = Security(API_KEY_HEADER),
    authorization: Optional[str] = Security(AUTHORIZATION_HEADER),
) -> str:
    api_key = _extract_api_key(x_api_key, authorization)
    if not api_key or api_key != expected_api_key():
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
    return api_key


def validate_api_key(raw_api_key: Optional[str]) -> None:
    if not raw_api_key or raw_api_key != expected_api_key():
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
