from __future__ import annotations

from typing import Mapping

from fastapi import Depends, HTTPException, Request, status, WebSocket

from utils.audit import log_audit_event
from utils.security import SecurityContext, authorize_action, normalize_roles, verify_totp


def _mfa_secret_for_user(user_id: str) -> str | None:
    return (
        _env_var(f"MFA_SECRET_{user_id}")
        or _env_var("MFA_SHARED_SECRET")
    )


def _env_var(name: str) -> str | None:
    value = __import__("os").getenv(name)
    return value.strip() if value else None


def _resource_attributes(headers: Mapping[str, str]) -> dict[str, str]:
    attrs: dict[str, str] = {}
    if headers.get("X-Resource-Org"):
        attrs["org_id"] = headers["X-Resource-Org"]
    if headers.get("X-Resource-Owner"):
        attrs["owner_id"] = headers["X-Resource-Owner"]
    if headers.get("X-Resource-Classification"):
        attrs["classification"] = headers["X-Resource-Classification"].lower()
    return attrs


def _security_context_from_headers(headers: Mapping[str, str], mfa_required: bool) -> SecurityContext:
    user_id = headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-User-Id")
    roles = normalize_roles(
        (headers.get("X-User-Roles") or headers.get("X-User-Role") or "").split(",")
    )
    org_id = headers.get("X-User-Org")
    mfa_token = headers.get("X-MFA-Token")
    secret = _mfa_secret_for_user(user_id)
    mfa_verified = bool(secret and verify_totp(secret, mfa_token or ""))
    if mfa_required and not mfa_verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA required")
    return SecurityContext(
        user_id=user_id,
        roles=roles,
        org_id=org_id,
        attributes={"ip": headers.get("X-Forwarded-For", "")},
        mfa_verified=mfa_verified,
    )


def authorize(action: str, mfa_required: bool = False):
    async def dependency(request: Request) -> SecurityContext:
        context = _security_context_from_headers(request.headers, mfa_required)
        resource_attrs = _resource_attributes(request.headers)
        allowed = authorize_action(context, action, resource_attrs)
        log_audit_event(
            {
                "event": "authorization",
                "user_id": context.user_id,
                "action": action,
                "allowed": allowed,
                "roles": list(context.roles),
                "resource": resource_attrs or None,
                "mfa": context.mfa_verified,
            },
            encrypt_fields={"user_id"},
        )
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return context

    return Depends(dependency)


def authorize_websocket(websocket: WebSocket, action: str) -> SecurityContext:
    context = _security_context_from_headers(websocket.headers, mfa_required=False)
    resource_attrs = _resource_attributes(websocket.headers)
    allowed = authorize_action(context, action, resource_attrs)
    log_audit_event(
        {
            "event": "authorization",
            "user_id": context.user_id,
            "action": action,
            "allowed": allowed,
            "roles": list(context.roles),
            "resource": resource_attrs or None,
            "mfa": context.mfa_verified,
            "channel": "websocket",
        },
        encrypt_fields={"user_id"},
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return context
