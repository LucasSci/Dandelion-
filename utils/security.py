from __future__ import annotations

import base64
import hashlib
import hmac
import struct
import time
from dataclasses import dataclass
from typing import Iterable, Mapping

Permission = str


ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "admin": {"*"},
    "gm": {
        "vtt:roll",
        "vtt:combat:update",
        "vtt:event:publish",
        "vtt:map:generate",
    },
    "player": {"vtt:roll", "vtt:map:generate"},
    "auditor": {"vtt:audit:read"},
}


@dataclass(frozen=True)
class SecurityContext:
    user_id: str
    roles: tuple[str, ...]
    org_id: str | None
    attributes: dict[str, str]
    mfa_verified: bool


def normalize_roles(roles: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({role.strip().lower() for role in roles if role.strip()}))


def permissions_for_roles(roles: Iterable[str]) -> set[Permission]:
    permissions: set[Permission] = set()
    for role in normalize_roles(roles):
        permissions.update(ROLE_PERMISSIONS.get(role, set()))
    return permissions


def has_permission(roles: Iterable[str], action: Permission) -> bool:
    permissions = permissions_for_roles(roles)
    if "*" in permissions:
        return True
    return action in permissions


def evaluate_abac(
    context: SecurityContext,
    action: Permission,
    resource: Mapping[str, str] | None = None,
) -> bool:
    if not resource:
        return True
    if "admin" in context.roles:
        return True
    resource_org = resource.get("org_id")
    if resource_org and context.org_id and resource_org != context.org_id:
        return False
    owner_id = resource.get("owner_id")
    if owner_id and owner_id != context.user_id and "gm" not in context.roles:
        return False
    classification = resource.get("classification")
    if classification == "restricted" and "gm" not in context.roles:
        return False
    return True


def authorize_action(
    context: SecurityContext,
    action: Permission,
    resource: Mapping[str, str] | None = None,
) -> bool:
    return has_permission(context.roles, action) and evaluate_abac(context, action, resource)


def _decode_base32_secret(secret: str) -> bytes:
    normalized = secret.strip().replace(" ", "").upper()
    padding = "=" * (-len(normalized) % 8)
    return base64.b32decode(normalized + padding)


def generate_totp(secret: str, for_time: int | None = None, digits: int = 6, step: int = 30) -> str:
    counter = int((for_time or int(time.time())) / step)
    counter_bytes = struct.pack(">Q", counter)
    key = _decode_base32_secret(secret)
    hmac_digest = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    offset = hmac_digest[-1] & 0x0F
    code = struct.unpack(">I", hmac_digest[offset : offset + 4])[0] & 0x7FFFFFFF
    token = str(code % (10**digits)).zfill(digits)
    return token


def verify_totp(
    secret: str,
    token: str,
    for_time: int | None = None,
    digits: int = 6,
    step: int = 30,
    allowed_drift: int = 1,
) -> bool:
    if not token:
        return False
    current_time = for_time or int(time.time())
    for offset in range(-allowed_drift, allowed_drift + 1):
        candidate_time = current_time + (offset * step)
        if hmac.compare_digest(generate_totp(secret, candidate_time, digits, step), token):
            return True
    return False
